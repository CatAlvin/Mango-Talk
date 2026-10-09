"""API tests use disposable SQLite databases and never read deployment credentials."""

import json
import os
from pathlib import Path
import sys
import tempfile
from dataclasses import dataclass
from uuid import uuid4

import anyio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
BOOTSTRAP_UPLOADS = tempfile.TemporaryDirectory(prefix="mango-tests-")
os.environ.update(
    APP_ENV="test",
    DATABASE_URL="sqlite://",
    JWT_SECRET_KEY="isolated-test-secret-with-at-least-32-characters",
    UPLOAD_ROOT=BOOTSTRAP_UPLOADS.name,
)

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db import session as database
from app.db.deps import get_db
from app.main import app
from app.models import ChatRoom, ChatRoomMember, Message, User
from app.api import ws as websocket_api
from app.services.ws_manager import manager


@dataclass
class API:
    client: TestClient
    session: sessionmaker
    tokens: dict[str, str]

    def headers(self, user="alice"):
        return {"Authorization": f"Bearer {self.tokens[user]}"}

    def send(self, *, user="alice", room=10, content="Hello", **extra):
        payload = {
            "room_id": room,
            "content": content,
            "client_message_id": str(uuid4()),
            **extra,
        }
        return self.client.post("/messages", headers=self.headers(user), json=payload)

    def upload(self, *, user="alice", name="notes.txt", body=b"Meeting notes", mime="text/plain"):
        return self.client.post(
            "/uploads", headers=self.headers(user), files={"file": (name, body, mime)}
        )

    def websocket(self, *, user="alice", room=10):
        return self.client.websocket_connect(f"/ws/rooms/{room}?token={self.tokens[user]}")

    def user_socket(self, user="alice"):
        return self.client.websocket_connect(f"/ws/users?token={self.tokens[user]}")


@pytest.fixture(scope="session")
def password_hash():
    return hash_password("test-password-123")


@pytest.fixture
def api(tmp_path, monkeypatch, password_hash):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'api.sqlite').as_posix()}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", sessions)
    monkeypatch.setattr(websocket_api, "SessionLocal", sessions)
    monkeypatch.setattr(settings, "UPLOAD_ROOT", str(tmp_path / "uploads"))
    Path(settings.UPLOAD_ROOT).mkdir()
    database.Base.metadata.create_all(engine)

    def isolated_db():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = isolated_db
    for connections in (manager.active_connections, manager.user_connections, manager.guards, manager.locks):
        connections.clear()
    with sessions() as db:
        db.add_all([
            User(id=1, username="alice", phone="13900000001", password_hash=password_hash),
            User(id=2, username="bob", phone="13900000002", password_hash=password_hash),
            User(id=3, username="carol", phone="13900000003", password_hash=password_hash),
        ])
        db.flush()
        db.add_all([
            ChatRoom(id=10, type="private"),
            ChatRoom(id=20, type="group", name="Design", owner_id=1),
            ChatRoom(id=30, type="private"),
        ])
        db.flush()
        db.add_all([
            ChatRoomMember(room_id=room, user_id=user)
            for room, users in [(10, [1, 2]), (20, [1, 2]), (30, [1, 3])]
            for user in users
        ])
        db.commit()

    tokens = {name: create_access_token(str(index)) for index, name in enumerate(["alice", "bob", "carol"], 1)}
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            yield API(client=client, session=sessions, tokens=tokens)
    finally:
        app.dependency_overrides.clear()
        for connections in (manager.active_connections, manager.user_connections, manager.guards, manager.locks):
            connections.clear()
        engine.dispose()


def receive_event(websocket):
    """Bound socket assertions so a missing broadcast fails rather than hangs CI.

    The project pins Starlette; its receive stream allows a cancellation deadline
    without blocking a background thread or using timing-dependent sleeps.
    """
    async def receive():
        with anyio.fail_after(3):
            return await websocket._send_rx.receive()

    message = websocket.portal.call(receive)
    websocket._raise_on_close(message)
    return json.loads(message["text"])
