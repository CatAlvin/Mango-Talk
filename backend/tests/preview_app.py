"""Disposable local browser-QA service; no production database or credentials."""
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

directory = Path(__file__).resolve().parent / ".runtime-manual"
directory.mkdir(exist_ok=True)
os.environ.update(APP_ENV="test", DATABASE_URL=f"sqlite:///{(directory / 'preview.sqlite').as_posix()}", JWT_SECRET_KEY="local-browser-review-secret-never-used-in-production", UPLOAD_ROOT=str(directory / "uploads"))

from app.db.migrate import migrate
from app.db.session import SessionLocal
from app.models import User, ChatRoom, ChatRoomMember, Message, UserIdentity
from app.core.security import hash_password

migrate()
with SessionLocal() as db:
    if not db.get(User, 1):
        for index, name in [(1, "review_alice"), (2, "review_bob"), (3, "review_carol")]:
            db.add(User(id=index, username=name, password_hash=hash_password("review-password-2026")))
            db.flush()
            db.add(UserIdentity(identifier=name, user_id=index))
        db.add_all([ChatRoom(id=1, type="group", name="浏览器回归", owner_id=1), ChatRoom(id=2, type="private", private_key="1:2")])
        db.flush()
        db.add_all([ChatRoomMember(room_id=room, user_id=user, role="owner" if room == 1 and user == 1 else "member") for room, users in [(1, [1, 2, 3]), (2, [1, 2])] for user in users])
        for index in range(1, 126):
            db.add(Message(id=index, room_id=1, sender_id=1 if index % 2 else 2, content=f"回归记录 {index}", created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=126-index)))
        db.flush()
        db.add(Message(room_id=1, sender_id=2, content="点开引用可以回到较早的消息。", reply_to_message_id=5))
        db.commit()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8019, log_level="warning", access_log=False)
