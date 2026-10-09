from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool
from app.api.deps import get_current_user
from app.db.deps import get_db
from app.models import User, Message, ChatRoomMember
from app.schemas.message import MessageCreate, MessagePublic, MessageActionResponse, MessageSync
from app.services.messages import membership, create_message, load_message, serialize_many
from app.services.ws_manager import manager

router = APIRouter(prefix="/messages", tags=["messages"])


async def publish_message(data: dict, member_ids: list[int], event="new_message"):
    encoded = jsonable_encoder(data)
    await manager.broadcast(data["room_id"], {"event": event, "data": encoded})
    await manager.notify_users(member_ids, {"event": "room_updated", "data": {"room_id": data["room_id"], "message": encoded}})


@router.post("", response_model=MessageActionResponse, status_code=201)
async def send_message(payload: MessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data, created, member_ids = await run_in_threadpool(create_message, db, payload, current_user.id)
    if created:
        await publish_message(data, member_ids)
    return {"message": "消息已发送", "data": data}


@router.get("/room/{room_id}", response_model=list[MessagePublic])
def history(room_id: int, before_id: int | None = Query(default=None, gt=0), after_id: int | None = Query(default=None, gt=0), limit: int = Query(default=50, ge=1, le=100), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    membership(db, room_id, current_user.id)
    if before_id and after_id:
        raise HTTPException(400, "请使用一个分页方向")
    query = select(Message).where(Message.room_id == room_id).options(selectinload(Message.attachments))
    if after_id:
        query = query.where(Message.id > after_id).order_by(Message.id.asc())
    else:
        if before_id:
            query = query.where(Message.id < before_id)
        query = query.order_by(Message.id.desc())
    messages = list(db.scalars(query.limit(limit)))
    if not after_id:
        messages.reverse()
    return serialize_many(db, messages, current_user.id)


@router.get("/{message_id}/context", response_model=list[MessagePublic])
def context(message_id: int, limit: int = Query(default=50, ge=3, le=100), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    target = load_message(db, message_id)
    membership(db, target.room_id, current_user.id)
    query = select(Message).where(Message.room_id == target.room_id).options(selectinload(Message.attachments))
    before = list(db.scalars(query.where(Message.id < message_id).order_by(Message.id.desc()).limit(limit // 2)))
    after = list(db.scalars(query.where(Message.id >= message_id).order_by(Message.id.asc()).limit(limit - len(before))))
    return serialize_many(db, list(reversed(before)) + after, current_user.id)


@router.post("/room/{room_id}/sync", response_model=list[MessagePublic])
def sync_loaded(room_id: int, payload: MessageSync, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    membership(db, room_id, current_user.id)
    messages = list(db.scalars(select(Message).where(Message.room_id == room_id, Message.id.in_(payload.ids)).options(selectinload(Message.attachments)).order_by(Message.id)))
    return serialize_many(db, messages, current_user.id)


def recall_message(db, message_id, user_id):
    message = load_message(db, message_id)
    membership(db, message.room_id, user_id)
    if message.sender_id != user_id:
        raise HTTPException(403, "只能撤回自己发送的消息")
    changed = not message.is_recalled
    if changed:
        message.is_recalled = True
        message.recalled_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
    members = list(db.scalars(select(ChatRoomMember.user_id).where(ChatRoomMember.room_id == message.room_id)))
    return serialize_many(db, [message], user_id)[0], changed, members


@router.post("/{message_id}/recall", response_model=MessageActionResponse)
async def recall(message_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data, changed, members = await run_in_threadpool(recall_message, db, message_id, current_user.id)
    if changed:
        await publish_message(data, members, "message_recalled")
    return {"message": "消息已撤回", "data": data}
