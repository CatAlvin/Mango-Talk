"""Upgrade a real legacy schema, then repeat the upgrade without altering data."""

from datetime import datetime

from sqlalchemy import DateTime, create_engine, inspect, select, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db import migrate as migration
from app.models import ChatRoom, ChatRoomMember, MessageAttachment, Upload, User, UserIdentity


LEGACY_TABLES = {
    "chat_rooms": """
        id INTEGER PRIMARY KEY, type VARCHAR(20) NOT NULL, name VARCHAR(100),
        owner_id INTEGER, avatar_url VARCHAR(255), description VARCHAR(255),
        is_active BOOLEAN NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    """,
    "chat_room_members": """
        id INTEGER PRIMARY KEY, room_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        role VARCHAR(20) NOT NULL DEFAULT 'member', nickname_in_room VARCHAR(50),
        is_muted BOOLEAN NOT NULL DEFAULT 0,
        joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(room_id, user_id)
    """,
    "messages": """
        id INTEGER PRIMARY KEY, room_id INTEGER NOT NULL, sender_id INTEGER NOT NULL,
        message_type VARCHAR(20) NOT NULL DEFAULT 'text', content TEXT,
        reply_to_message_id INTEGER, is_recalled BOOLEAN NOT NULL DEFAULT 0,
        recalled_at DATETIME, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    """,
    "message_attachments": """
        id INTEGER PRIMARY KEY, message_id INTEGER NOT NULL, attachment_type VARCHAR(20) NOT NULL,
        original_name VARCHAR(255) NOT NULL, stored_name VARCHAR(255) NOT NULL,
        storage_path VARCHAR(500) NOT NULL, file_url VARCHAR(500) NOT NULL,
        mime_type VARCHAR(100), file_size INTEGER NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    """,
}


def snapshot(engine, columns=None):
    # SQLite may add .000000 when binding a datetime. Compare the timestamp
    # value rather than its storage spelling, while retaining every old field.
    date_fields = {
        table: {column["name"] for column in inspect(engine).get_columns(table) if isinstance(column["type"], DateTime)}
        for table in inspect(engine).get_table_names()
    }
    with engine.connect() as connection:
        return {
            table: [{
                key: datetime.fromisoformat(value) if key in date_fields[table] and isinstance(value, str) else value
                for key, value in row.items()
            } for row in connection.execute(text(
                f"SELECT {', '.join(fields) if fields else '*'} FROM {table} ORDER BY 1"
            )).mappings()]
            for table, fields in (
                columns.items() if columns else ((table, None) for table in inspect(engine).get_table_names())
            )
        }


def test_legacy_upgrade_is_repeatable_and_preserves_original_data(tmp_path, monkeypatch, password_hash):
    engine = create_engine(f"sqlite:///{(tmp_path / 'legacy.sqlite').as_posix()}")
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    upload_root = tmp_path / "uploads"
    legacy_file = upload_root / "messages" / "notes.txt"
    legacy_file.parent.mkdir(parents=True)
    legacy_file.write_bytes(b"Legacy notes")
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"Outside file")
    monkeypatch.setattr(settings, "UPLOAD_ROOT", str(upload_root))
    monkeypatch.setattr(migration, "engine", engine)
    monkeypatch.setattr(migration, "SessionLocal", sessions)
    User.__table__.create(engine)
    with sessions() as db:
        db.add_all([
            User(id=1, username="legacy_alice", phone="13900000001", password_hash=password_hash),
            User(id=2, username="legacy_bob", phone="13900000002", password_hash=password_hash),
            User(id=3, username="13900000002", password_hash=password_hash),
        ])
        db.commit()
    with engine.begin() as connection:
        for name, definition in LEGACY_TABLES.items():
            connection.execute(text(f"CREATE TABLE {name} ({definition})"))
        connection.execute(text("INSERT INTO chat_rooms (id, type, created_at, updated_at) VALUES (10, 'private', '2026-01-01 00:00:00', '2026-01-02 00:00:00'), (20, 'private', '2026-01-01 00:00:00', '2026-01-02 00:00:00')"))
        connection.execute(text("INSERT INTO chat_room_members (id, room_id, user_id, nickname_in_room) VALUES (1, 10, 1, 'Alice'), (2, 10, 2, 'Bob'), (3, 20, 1, NULL), (4, 20, 2, NULL)"))
        connection.execute(text("INSERT INTO messages (id, room_id, sender_id, message_type, content, reply_to_message_id, is_recalled, recalled_at) VALUES (100, 10, 1, 'file', 'Legacy caption', NULL, 0, NULL), (101, 10, 2, 'text', 'Legacy reply', 100, 0, NULL), (102, 20, 2, 'file', 'Recalled text', NULL, 1, '2026-01-03 00:00:00')"))
        connection.execute(text("INSERT INTO message_attachments (id, message_id, attachment_type, original_name, stored_name, storage_path, file_url, mime_type, file_size) VALUES (200, 100, 'file', 'notes.txt', 'notes.txt', :inside, '/uploads/messages/notes.txt', 'text/plain', 12), (201, 102, 'file', 'outside.txt', 'outside.txt', :outside, '/uploads/outside.txt', 'text/plain', 12)"), {"inside": str(legacy_file), "outside": str(outside)})

    old_columns = {table: [column["name"] for column in inspect(engine).get_columns(table)] for table in inspect(engine).get_table_names()}
    original = snapshot(engine, old_columns)
    try:
        migration.migrate()
        assert snapshot(engine, old_columns) == original
        first_upgrade = snapshot(engine)
        with sessions() as db:
            assert dict(db.execute(select(UserIdentity.identifier, UserIdentity.user_id)).all()) == {
                "legacy_alice": 1, "13900000001": 1, "legacy_bob": 2, "13900000002": 2,
            }
            assert db.get(ChatRoom, 10).private_key == "1:2"
            assert db.get(ChatRoom, 20).private_key is None
            assert [item.last_read_message_id for item in db.scalars(select(ChatRoomMember))] == [0, 0, 0, 0]
            attachment = db.get(MessageAttachment, 200)
            assert attachment.upload_id
            upload = db.get(Upload, attachment.upload_id)
            assert upload.owner_id == 1
            assert upload.storage_path == "messages/notes.txt"
            assert db.get(MessageAttachment, 201).upload_id is None
            assert list(db.scalars(select(Upload.id))) == [attachment.upload_id]
        migration.migrate()
        assert snapshot(engine) == first_upgrade
        assert legacy_file.read_bytes() == b"Legacy notes"
        assert outside.read_bytes() == b"Outside file"
    finally:
        engine.dispose()
