from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import HTTPException
from jose import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import Upload, MessageAttachment, Message, ChatRoom, ChatRoomMember


def ensure_access(db: Session, upload: Upload, user_id: int):
    bound = db.execute(select(Message).join(MessageAttachment, MessageAttachment.message_id == Message.id).where(MessageAttachment.upload_id == upload.id)).scalar_one_or_none()
    if bound:
        if bound.is_recalled:
            raise HTTPException(410, "这条消息已撤回")
        member = db.scalar(select(ChatRoomMember.id).join(ChatRoom, ChatRoom.id == ChatRoomMember.room_id).where(ChatRoomMember.room_id == bound.room_id, ChatRoomMember.user_id == user_id, ChatRoom.is_active.is_(True)))
        if not member:
            raise HTTPException(403, "你没有访问该文件的权限")
    elif upload.owner_id != user_id:
        raise HTTPException(403, "你没有访问该文件的权限")


def signed_url(upload_id: str, user_id: int) -> str:
    token = jwt.encode({"sub": str(user_id), "typ": "attachment", "upload_id": upload_id, "exp": datetime.now(timezone.utc) + timedelta(minutes=10)}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return f"/uploads/{upload_id}/download?access_token={token}"


def metadata(upload: Upload, user_id: int) -> dict:
    return {"upload_id": upload.id, "attachment_type": upload.attachment_type, "original_name": upload.original_name, "mime_type": upload.mime_type, "file_size": upload.file_size, "file_url": signed_url(upload.id, user_id), "created_at": upload.created_at}


def safe_path(storage_path: str) -> Path:
    root = Path(settings.UPLOAD_ROOT).resolve()
    path = (root / storage_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(404, "文件不存在")
    return path
