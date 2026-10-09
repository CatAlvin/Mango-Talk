import asyncio
import json
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from app.api.deps import get_user_from_token
from app.api.messages import publish_message, recall_message
from app.db.session import SessionLocal
from app.schemas.message import MessageCreate
from app.services.messages import membership, create_message
from app.services.ws_manager import manager

router = APIRouter(prefix="/ws", tags=["websocket"])


def authenticated(token, room_id=None):
    with SessionLocal() as db:
        user = get_user_from_token(token, db)
        if room_id is not None:
            membership(db, room_id, user.id)
        return user.id


def send_from_socket(token, room_id, data):
    with SessionLocal() as db:
        user = get_user_from_token(token, db)
        payload = MessageCreate.model_validate({**data, "room_id": room_id})
        return create_message(db, payload, user.id)


def recall_from_socket(token, room_id, message_id):
    with SessionLocal() as db:
        user = get_user_from_token(token, db)
        from app.services.messages import load_message
        if load_message(db, message_id).room_id != room_id:
            raise HTTPException(400, "消息不在当前会话中")
        return recall_message(db, message_id, user.id)


async def handle(websocket, room_id=None):
    token = websocket.query_params.get("token")
    try:
        user_id = await run_in_threadpool(authenticated, token, room_id)
    except HTTPException:
        await websocket.close(code=1008)
        return

    async def guard():
        try:
            await run_in_threadpool(authenticated, token, room_id)
            return True
        except HTTPException:
            return False

    if room_id is None:
        await manager.connect_user(user_id, websocket, guard)
    else:
        await manager.connect(room_id, websocket, guard)
    try:
        if not await manager.send_personal_message(websocket, {"event": "connected", "data": {"room_id": room_id, "user_id": user_id}}):
            return
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=75)
            except asyncio.TimeoutError:
                await websocket.close(code=1001)
                break
            try:
                await run_in_threadpool(authenticated, token, room_id)
            except HTTPException as error:
                await manager.send_personal_message(websocket, {"event": "error", "data": {"message": error.detail}})
                await websocket.close(code=1008)
                break
            try:
                payload = json.loads(raw)
                if not isinstance(payload, dict):
                    raise ValueError()
                action = payload.get("action")
                if action == "ping":
                    if not await manager.send_personal_message(websocket, {"event": "pong", "data": {}}):
                        break
                elif room_id is not None and action == "send_message":
                    data = payload.get("data")
                    if not isinstance(data, dict):
                        raise ValueError()
                    message, created, members = await run_in_threadpool(send_from_socket, token, room_id, data)
                    if created:
                        await publish_message(message, members)
                    elif not await manager.send_personal_message(websocket, {"event": "new_message", "data": jsonable_encoder(message)}):
                        break
                elif room_id is not None and action == "recall_message":
                    data = payload.get("data")
                    if not isinstance(data, dict) or not isinstance(data.get("message_id"), int):
                        raise ValueError()
                    message, changed, members = await run_in_threadpool(recall_from_socket, token, room_id, data["message_id"])
                    if changed:
                        await publish_message(message, members, "message_recalled")
                else:
                    raise ValueError()
            except HTTPException as error:
                if not await manager.send_personal_message(websocket, {"event": "error", "data": {"message": error.detail}}):
                    break
            except (ValueError, ValidationError, TypeError):
                if not await manager.send_personal_message(websocket, {"event": "error", "data": {"message": "消息格式不正确，请重新发送"}}):
                    break
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        if room_id is None:
            manager.disconnect_user(user_id, websocket)
        else:
            manager.disconnect(room_id, websocket)


@router.websocket("/rooms/{room_id}")
async def room_socket(websocket: WebSocket, room_id: int):
    await handle(websocket, room_id)


@router.websocket("/users")
async def user_socket(websocket: WebSocket):
    await handle(websocket)
