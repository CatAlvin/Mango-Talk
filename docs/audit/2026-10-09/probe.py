"""Isolated review probes; never connects to the configured MySQL database.

Run from repository root with backend/.venv/Scripts/python.exe.
--serve exposes only seeded review data on 127.0.0.1:8019.
"""
import asyncio
import io
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ["JWT_SECRET_KEY"] = "isolated-audit-key-not-for-deployment"
from sqlalchemy import create_engine, select, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile, Headers
from app.core.config import settings
from app.db import session

settings.UPLOAD_ROOT = str(OUT / "uploads")
Path(settings.UPLOAD_ROOT).mkdir(exist_ok=True)
session.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
session.SessionLocal = sessionmaker(bind=session.engine, autoflush=False)
from app.main import app
from app.models import User, ChatRoom, ChatRoomMember, Message
from app.core.security import create_access_token, hash_password
from app.core.security import verify_password
from app.api.uploads import upload_file
from app.services.ws_manager import manager
from app.db.deps import get_db

session.Base.metadata.create_all(session.engine)
results = {}
try:
    password_hash = hash_password("audit-only-123")
    results["password_hash"] = "ok"
except Exception as exc:
    password_hash = "unused"
    results["password_hash"] = type(exc).__name__ + ": " + str(exc)

with session.SessionLocal() as db:
    users = [User(username=name, phone=f"1390000000{i}", password_hash=password_hash) for i, name in enumerate(["audit_alice", "audit_bob", "audit_carol"], 1)]
    db.add_all(users)
    db.flush()
    db.add_all([ChatRoom(id=1, type="private"), ChatRoom(id=2, type="group", name="产品讨论", owner_id=1)])
    db.flush()
    db.add_all([ChatRoomMember(room_id=r, user_id=u, role="owner" if u == 1 and r == 2 else "member") for r in [1, 2] for u in [1, 2]])
    for i in range(1, 61):
        db.add(Message(id=i, room_id=1, sender_id=1 if i % 2 else 2, content=f"审查消息 {i:02d}", created_at=datetime(2026, 10, 9, 9) + timedelta(minutes=i)))
    db.add(Message(id=61, room_id=1, sender_id=2, content="这里回复的是历史消息", reply_to_message_id=55, created_at=datetime(2026, 10, 9, 10, 1)))
    db.add(Message(id=62, room_id=2, sender_id=2, content="欢迎讨论产品改进", created_at=datetime(2026, 10, 9, 10, 2)))
    db.commit()
    db.get(Message, 49).reply_to_message_id = 55
    db.commit()

if "--serve" in sys.argv:
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8019, log_level="warning")
    sys.exit()

client = TestClient(app)
alice_token = create_access_token("1")
alice_headers = {"Authorization": f"Bearer {alice_token}"}
carol_headers = {"Authorization": f"Bearer {create_access_token('3')}"}
response = client.get("/messages/room/1", headers=alice_headers)
ids = [item["id"] for item in response.json()]
results["history_default"] = {"status": response.status_code, "first": ids[0], "last": ids[-1], "count": len(ids), "total_seeded": 61}
results["nonmember_history_status"] = client.get("/messages/room/1", headers=carol_headers).status_code
queries = []
@event.listens_for(session.engine, "before_cursor_execute")
def count_queries(conn, cursor, statement, parameters, context, executemany):
    queries.append(statement)
response = client.get("/messages/room/1?limit=200", headers=alice_headers)
results["history_query_count"] = {"messages": len(response.json()), "queries": len(queries)}
results["backend_reply_preview"] = response.json()[-1]["replied_message"]["content"]
event.remove(session.engine, "before_cursor_execute", count_queries)
response = client.post("/uploads", headers=alice_headers, files={"file": ("audit.txt", b"audit", "text/plain")})
results["upload_http"] = {"status": response.status_code, "body": response.text}

# Invoke handler separately: production routing currently prevents reaching it.
with session.SessionLocal() as db:
    alice = db.get(User, 1)
    upload = asyncio.run(upload_file(UploadFile(io.BytesIO(b"<!doctype html><title>Inert audit fixture</title>"), filename="audit.html", headers=Headers({"content-type": "text/html"})), alice))
metadata = upload["data"]
anonymous_file = client.get(metadata["file_url"])
results["upload_handler_html_and_anonymous_download"] = {"handler_accepted": True, "anonymous_status": anonymous_file.status_code, "content_type": anonymous_file.headers.get("content-type")}
forged = {k: v for k, v in metadata.items() if k != "uploaded_by"}
response = client.post("/messages", headers=carol_headers, json={"room_id": 2, "message_type": "file", "attachments": [forged]})
results["nonmember_send_status"] = response.status_code
with session.SessionLocal() as db:
    db.add(ChatRoomMember(room_id=2, user_id=3))
    db.commit()
response = client.post("/messages", headers=carol_headers, json={"room_id": 2, "message_type": "file", "attachments": [forged]})
results["other_user_can_reuse_upload"] = response.status_code
client.post("/messages/1/recall", headers=alice_headers)
response = client.get("/messages/room/1", headers=alice_headers)
results["recalled_content_returned"] = response.json()[0]["content"]
results["bcrypt_password_suffix_ignored"] = verify_password('a' * 72 + 'Y', hash_password('a' * 72 + 'X'))
with session.SessionLocal() as db:
    db.add(User(username='13900000002', password_hash=password_hash))
    db.commit()
try:
    response = client.post('/auth/login', json={'identifier': '13900000002', 'password': 'audit-only-123'})
    results['username_phone_namespace_collision'] = response.status_code
except Exception as exc:
    results['username_phone_namespace_collision'] = type(exc).__name__ + ': ' + str(exc)
print(json.dumps(results, ensure_ascii=False, indent=2), flush=True)
OUT.joinpath("results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print("Starting websocket probes", flush=True)
with client.websocket_connect(f"/ws/rooms/1?token={alice_token}") as ws:
    ws.receive_json()
    ws.send_json({"action": "send_message", "data": {"content": "probe-valid-websocket"}})
    results["websocket_valid_event"] = ws.receive_json()["event"]
for label, payload in [("array_payload", []), ("numeric_content", {"action": "send_message", "data": {"content": 7}})]:
    try:
        with client.websocket_connect(f"/ws/rooms/1?token={alice_token}") as ws:
            ws.receive_json()
            ws.send_json(payload)
            # Context exit surfaces the endpoint exception without waiting forever.
    except Exception as exc:
        results[label] = type(exc).__name__ + ": " + str(exc)
class FailedSocket:
    async def send_json(self, payload):
        raise RuntimeError("isolated-send-failure")
from app.api.ws import safe_send_personal_message
failed = FailedSocket()
manager.active_connections[99].append(failed)
results["safe_send_false_is_ignored"] = asyncio.run(safe_send_personal_message(failed, 99, {}))
results["failed_connection_kept"] = failed in manager.active_connections.get(99, [])
manager.disconnect(99, failed)
with client.websocket_connect(f"/ws/rooms/1?token={alice_token}") as ws:
    ws.receive_json()
    with session.SessionLocal() as db:
        db.get(User, 1).is_active = False
        db.commit()
    ws.send_json({'action': 'send_message', 'data': {'content': 'disabled-user-probe'}})
    results['disabled_user_existing_ws_event'] = ws.receive_json()['event']
OUT.joinpath("results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(results, ensure_ascii=False, indent=2))
