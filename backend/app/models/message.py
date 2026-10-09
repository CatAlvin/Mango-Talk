from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, func, text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("room_id", "sender_id", "client_message_id", name="uq_message_client"),
        Index("ix_messages_room_cursor", "room_id", "id"),
    )
    client_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    room_id: Mapped[int] = mapped_column(ForeignKey("chat_rooms.id"), nullable=False, index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    message_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="text",
        server_default="text",
        index=True,
    )

    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    reply_to_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id"),
        nullable=True,
        index=True,
    )

    is_recalled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )

    recalled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    attachments: Mapped[list["MessageAttachment"]] = relationship(
        "MessageAttachment",
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="MessageAttachment.id.asc()",
    )
