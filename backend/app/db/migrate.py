"""Idempotent schema upgrade; run explicitly before starting the API."""
from pathlib import Path
from uuid import uuid4
from sqlalchemy import inspect, select, text
from sqlalchemy.orm.attributes import flag_modified
from app.core.config import settings
from app.db.session import Base, SessionLocal, engine
from app import models
from app.models import ChatRoom, ChatRoomMember, Message, MessageAttachment, Upload, User, UserIdentity

VERSION = "20261009_01"


def migrate():
    existing = inspect(engine).get_table_names()
    changes = {
        "messages": {"client_message_id": "VARCHAR(64) NULL"},
        "message_attachments": {"upload_id": "VARCHAR(32) NULL"},
        "chat_rooms": {"private_key": "VARCHAR(50) NULL"},
        "chat_room_members": {"last_read_message_id": "INTEGER NOT NULL DEFAULT 0"},
    }
    with engine.begin() as connection:
        for table, additions in changes.items():
            if table not in existing:
                continue
            columns = {column["name"] for column in inspect(connection).get_columns(table)}
            for column, definition in additions.items():
                if column not in columns:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for user in db.scalars(select(User).order_by(User.id)):
            for identifier in set(filter(None, [user.username, user.phone])):
                if not db.get(UserIdentity, identifier):
                    db.add(UserIdentity(identifier=identifier, user_id=user.id))
                    db.flush()
        used_keys = set(db.scalars(select(ChatRoom.private_key).where(ChatRoom.private_key.is_not(None))))
        for room in db.scalars(select(ChatRoom).where(ChatRoom.type == "private", ChatRoom.private_key.is_(None)).order_by(ChatRoom.id)):
            members = list(db.scalars(select(ChatRoomMember.user_id).where(ChatRoomMember.room_id == room.id).order_by(ChatRoomMember.user_id)))
            if len(members) == 2:
                key = ":".join(str(value) for value in members)
                if key not in used_keys:
                    original_updated_at = room.updated_at
                    room.private_key = key
                    # Backfilling identity must not change the room's activity time.
                    room.updated_at = original_updated_at
                    flag_modified(room, "updated_at")
                    used_keys.add(key)
        root = Path(settings.UPLOAD_ROOT).resolve()
        for attachment, sender_id in db.execute(select(MessageAttachment, Message.sender_id).join(Message, Message.id == MessageAttachment.message_id).where(MessageAttachment.upload_id.is_(None))):
            # Legacy paths are converted only when they resolve inside upload root.
            old_path = Path(attachment.storage_path)
            absolute = old_path.resolve() if old_path.is_absolute() else (root / old_path).resolve()
            if not absolute.is_relative_to(root):
                continue
            upload_id = uuid4().hex
            path = absolute.relative_to(root).as_posix()
            db.add(Upload(id=upload_id, owner_id=sender_id, attachment_type=attachment.attachment_type, original_name=attachment.original_name, stored_name=attachment.stored_name, storage_path=path, mime_type=attachment.mime_type or "application/octet-stream", file_size=attachment.file_size))
            db.flush()
            attachment.upload_id = upload_id
        db.commit()
    # CREATE TABLE doesn't add indexes to existing tables. These are additive.
    for table in (Message.__table__, MessageAttachment.__table__, ChatRoom.__table__):
        indexes = {item["name"] for item in inspect(engine).get_indexes(table.name)}
        indexes |= {item["name"] for item in inspect(engine).get_unique_constraints(table.name)}
        definitions = {
            "messages": [("uq_message_client", "room_id, sender_id, client_message_id", True), ("ix_messages_room_cursor", "room_id, id", False)],
            "message_attachments": [("uq_attachment_upload", "upload_id", True)],
            "chat_rooms": [("uq_room_private", "private_key", True)],
        }
        for name, columns, unique in definitions[table.name]:
            # A fresh schema already has equivalent unnamed unique constraints.
            if name in indexes:
                continue
            with engine.begin() as connection:
                connection.execute(text(f"CREATE {'UNIQUE ' if unique else ''}INDEX {name} ON {table.name} ({columns})"))
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(32) PRIMARY KEY)"))
        found = connection.execute(text("SELECT version FROM schema_migrations WHERE version = :version"), {"version": VERSION}).first()
        if not found:
            connection.execute(text("INSERT INTO schema_migrations (version) VALUES (:version)"), {"version": VERSION})
    Path(settings.UPLOAD_ROOT).mkdir(parents=True, exist_ok=True)
    print(f"Database schema ready: {VERSION}")


if __name__ == "__main__":
    migrate()
