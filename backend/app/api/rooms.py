from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from app.api.deps import get_current_user
from app.db.deps import get_db
from app.models import ChatRoom, ChatRoomMember, Message, User
from app.schemas.room import PrivateRoomCreate, GroupRoomCreate, RoomActionResponse, RoomListItem, RoomRead
from app.services.messages import membership, load_message
from app.services.ws_manager import manager

router = APIRouter(prefix="/rooms", tags=["rooms"])


def private_key(first: int, second: int) -> str:
    return ":".join(str(value) for value in sorted([first, second]))


def make_private(db, user_id, target_id):
    if target_id == user_id:
        raise HTTPException(400, "请选择其他用户")
    target = db.get(User, target_id)
    if not target or not target.is_active:
        raise HTTPException(404, "该用户不存在或已停用")
    key = private_key(user_id, target_id)
    existing = db.scalar(select(ChatRoom).where(ChatRoom.private_key == key))
    if existing:
        if not existing.is_active:
            raise HTTPException(403, "该会话已停用")
        return existing, False
    room = ChatRoom(type="private", private_key=key)
    db.add(room)
    try:
        db.flush()
        db.add_all([ChatRoomMember(room_id=room.id, user_id=value) for value in [user_id, target_id]])
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(ChatRoom).where(ChatRoom.private_key == key))
        if not existing:
            raise
        return existing, False
    db.refresh(room)
    return room, True


@router.post("/private", response_model=RoomActionResponse)
async def create_private_room(payload: PrivateRoomCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    room, created = await run_in_threadpool(make_private, db, current_user.id, payload.target_user_id)
    if created:
        await manager.notify_users([current_user.id, payload.target_user_id], {"event": "room_created", "data": {"room_id": room.id}})
    return {"message": "会话已创建", "room": room}


def make_group(db, user_id, payload):
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "请输入群聊名称")
    member_ids = sorted(set(payload.member_user_ids) - {user_id})
    if not member_ids:
        raise HTTPException(400, "至少选择一位群成员")
    found = set(db.scalars(select(User.id).where(User.id.in_(member_ids), User.is_active.is_(True))))
    if set(member_ids) != found:
        raise HTTPException(400, "部分成员已不可用，请重新选择")
    room = ChatRoom(type="group", name=name, owner_id=user_id, description=payload.description.strip() if payload.description else None)
    db.add(room)
    db.flush()
    db.add(ChatRoomMember(room_id=room.id, user_id=user_id, role="owner"))
    db.add_all([ChatRoomMember(room_id=room.id, user_id=value) for value in member_ids])
    db.commit()
    db.refresh(room)
    return room, member_ids + [user_id]


@router.post("/group", response_model=RoomActionResponse, status_code=201)
async def create_group_room(payload: GroupRoomCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    room, members = await run_in_threadpool(make_group, db, current_user.id, payload)
    await manager.notify_users(members, {"event": "room_created", "data": {"room_id": room.id}})
    return {"message": "群聊已创建", "room": room}


@router.get("/mine", response_model=list[RoomListItem])
def list_my_rooms(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(ChatRoomMember, ChatRoom).join(ChatRoom, ChatRoom.id == ChatRoomMember.room_id).where(ChatRoomMember.user_id == current_user.id, ChatRoom.is_active.is_(True))).all()
    ids = [room.id for _, room in rows]
    if not ids:
        return []
    counts = dict(db.execute(select(ChatRoomMember.room_id, func.count()).where(ChatRoomMember.room_id.in_(ids)).group_by(ChatRoomMember.room_id)).all())
    names = {}
    for room_id, username in db.execute(select(ChatRoomMember.room_id, User.username).join(User, User.id == ChatRoomMember.user_id).where(ChatRoomMember.room_id.in_(ids), User.id != current_user.id)):
        names.setdefault(room_id, username)
    latest = select(Message.room_id, func.max(Message.id).label("last_id")).where(Message.room_id.in_(ids)).group_by(Message.room_id).subquery()
    last_messages = {message.room_id: message for message in db.scalars(select(Message).join(latest, Message.id == latest.c.last_id))}
    unread = dict(db.execute(select(Message.room_id, func.count()).join(ChatRoomMember, ChatRoomMember.room_id == Message.room_id).where(ChatRoomMember.user_id == current_user.id, Message.room_id.in_(ids), Message.id > ChatRoomMember.last_read_message_id, Message.sender_id != current_user.id, Message.is_recalled.is_(False)).group_by(Message.room_id)).all())
    result = []
    for member, room in rows:
        last = last_messages.get(room.id)
        summary = {"id": last.id, "sender_id": last.sender_id, "content": None if last.is_recalled else last.content, "message_type": last.message_type, "is_recalled": last.is_recalled, "created_at": last.created_at} if last else None
        result.append({"id": room.id, "type": room.type, "name": room.name, "display_name": names.get(room.id, "私聊") if room.type == "private" else room.name or "群聊", "owner_id": room.owner_id, "avatar_url": room.avatar_url, "description": room.description, "is_active": room.is_active, "member_count": counts.get(room.id, 0), "my_role": member.role, "joined_at": member.joined_at, "created_at": room.created_at, "last_message": summary, "last_activity_at": last.created_at if last else room.created_at, "unread_count": unread.get(room.id, 0)})
    return sorted(result, key=lambda item: (item["last_activity_at"], item["id"]), reverse=True)


@router.post("/{room_id}/read")
def mark_read(room_id: int, payload: RoomRead, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = membership(db, room_id, current_user.id)
    message = load_message(db, payload.message_id)
    if message.room_id != room_id:
        raise HTTPException(400, "消息不在当前会话中")
    member.last_read_message_id = max(member.last_read_message_id, message.id)
    db.commit()
    return {"room_id": room_id, "message_id": member.last_read_message_id}
