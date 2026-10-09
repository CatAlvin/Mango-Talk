from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

class ChatRoomMember(Base):
    __tablename__ = "chat_room_members"
    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_room_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    last_read_message_id: Mapped[int] = mapped_column(default=0, server_default=text("0"), nullable=False)

    room_id: Mapped[int] = mapped_column(ForeignKey("chat_rooms.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="member",
        server_default="member",
    )
    nickname_in_room: Mapped[str | None] = mapped_column(String(50), nullable=True)

    is_muted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
