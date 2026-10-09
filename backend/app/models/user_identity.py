from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class UserIdentity(Base):
    """A shared unique namespace for usernames and phone numbers."""
    __tablename__ = "user_identities"
    identifier: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
