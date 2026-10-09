from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from app.models import User, ChatRoom, ChatRoomMember, Message, MessageAttachment, Upload
from app.schemas.message import MessageCreate
from app.services.uploads import signed_url, safe_path


def membership(db: Session, room_id: int, user_id: int) -> ChatRoomMember:
    member = db.scalar(select(ChatRoomMember).join(ChatRoom, ChatRoom.id == ChatRoomMember.room_id).where(ChatRoomMember.room_id == room_id, ChatRoomMember.user_id == user_id, ChatRoom.is_active.is_(True)))
    if not member:
        raise HTTPException(403, "你没有访问该会话的权限")
    return member


def load_message(db: Session, message_id: int) -> Message:
    message = db.scalar(select(Message).where(Message.id == message_id).options(selectinload(Message.attachments)))
    if not message:
        raise HTTPException(404, "消息不存在")
    return message


def serialize_many(db: Session, messages: list[Message], viewer_id: int) -> list[dict]:
    reply_ids = {message.reply_to_message_id for message in messages if message.reply_to_message_id}
    replies = {message.id: message for message in db.scalars(select(Message).where(Message.id.in_(reply_ids)).options(selectinload(Message.attachments)))} if reply_ids else {}
    all_messages = messages + list(replies.values())
    user_ids = {message.sender_id for message in all_messages}
    names = dict(db.execute(select(User.id, User.username).where(User.id.in_(user_ids))).all()) if user_ids else {}

    def preview(message):
        attachments = [] if message.is_recalled else [{"id": item.id, "message_id": item.message_id, "upload_id": item.upload_id, "attachment_type": item.attachment_type, "original_name": item.original_name, "file_url": signed_url(item.upload_id, viewer_id) if item.upload_id else "", "mime_type": item.mime_type, "file_size": item.file_size, "created_at": item.created_at} for item in message.attachments]
        return {"id": message.id, "sender_id": message.sender_id, "sender_username": names.get(message.sender_id), "message_type": message.message_type, "content": None if message.is_recalled else message.content, "is_recalled": message.is_recalled, "created_at": message.created_at, "attachments": attachments}

    return [{**preview(message), "room_id": message.room_id, "client_message_id": message.client_message_id, "reply_to_message_id": message.reply_to_message_id, "replied_message": preview(replies[message.reply_to_message_id]) if message.reply_to_message_id in replies else None, "recalled_at": message.recalled_at} for message in messages]


def create_message(db: Session, payload: MessageCreate, user_id: int) -> tuple[dict, bool, list[int]]:
    member = membership(db, payload.room_id, user_id)
    if member.is_muted:
        raise HTTPException(403, "你已被禁言，暂时无法发送消息")
    content = payload.content.strip() if payload.content else None
    content = content or None
    if not content and not payload.attachments:
        raise HTTPException(400, "请输入消息或选择附件")
    upload_ids = [item.upload_id for item in payload.attachments]
    if len(set(upload_ids)) != len(upload_ids):
        raise HTTPException(400, "同一附件不能重复发送")

    def replay():
        existing = db.scalar(select(Message).where(Message.room_id == payload.room_id, Message.sender_id == user_id, Message.client_message_id == payload.client_message_id).options(selectinload(Message.attachments))) if payload.client_message_id else None
        if existing:
            if (existing.content, existing.message_type, existing.reply_to_message_id, [item.upload_id for item in existing.attachments]) != (content, payload.message_type, payload.reply_to_message_id, upload_ids):
                raise HTTPException(409, "这次发送已处理，请重新发送修改后的消息")
            return serialize_many(db, [existing], user_id)[0]
        return None

    existing = replay()
    if existing:
        return existing, False, []
    if payload.reply_to_message_id:
        reply = load_message(db, payload.reply_to_message_id)
        if reply.room_id != payload.room_id:
            raise HTTPException(400, "回复的消息不在当前会话中")
    uploads = []
    for upload_id in upload_ids:
        upload = db.get(Upload, upload_id)
        if not upload:
            raise HTTPException(404, "附件不存在，请重新上传")
        if upload.owner_id != user_id:
            raise HTTPException(403, "只能发送自己上传的附件")
        if db.scalar(select(MessageAttachment.id).where(MessageAttachment.upload_id == upload_id)):
            raise HTTPException(409, "该附件已发送，请重新选择文件")
        safe_path(upload.storage_path)
        uploads.append(upload)
    if payload.message_type == "text" and uploads:
        raise HTTPException(400, "附件消息类型不正确")
    if payload.message_type in {"image", "file", "mixed"} and not uploads:
        raise HTTPException(400, "请选择要发送的附件")
    if payload.message_type == "image" and any(upload.attachment_type != "image" for upload in uploads):
        raise HTTPException(400, "图片消息只能包含图片")
    message = Message(room_id=payload.room_id, sender_id=user_id, client_message_id=payload.client_message_id, message_type=payload.message_type, content=content, reply_to_message_id=payload.reply_to_message_id)
    db.add(message)
    try:
        db.flush()
        for upload in uploads:
            db.add(MessageAttachment(message_id=message.id, upload_id=upload.id, attachment_type=upload.attachment_type, original_name=upload.original_name, stored_name=upload.stored_name, storage_path=upload.storage_path, file_url="", mime_type=upload.mime_type, file_size=upload.file_size))
        db.get(ChatRoom, payload.room_id).updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = replay()
        if existing:
            return existing, False, []
        raise HTTPException(409, "附件已发送，请重新选择文件")
    message = load_message(db, message.id)
    member_ids = list(db.scalars(select(ChatRoomMember.user_id).where(ChatRoomMember.room_id == payload.room_id)))
    return serialize_many(db, [message], user_id)[0], True, member_ids
