from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class MessageAttachmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    upload_id: str = Field(min_length=32, max_length=32, pattern=r"^[a-f0-9]{32}$")


class MessageAttachmentPublic(BaseModel):
    id: int
    message_id: int
    upload_id: str | None
    attachment_type: str
    original_name: str
    file_url: str
    mime_type: str | None
    file_size: int
    created_at: datetime


class MessageReplyPreview(BaseModel):
    id: int
    sender_id: int
    sender_username: str | None = None
    message_type: str
    content: str | None
    is_recalled: bool
    created_at: datetime
    attachments: list[MessageAttachmentPublic] = Field(default_factory=list)


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    room_id: int = Field(gt=0)
    client_message_id: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    message_type: Literal["text", "image", "file", "mixed"] = "text"
    content: str | None = Field(default=None, max_length=10000)
    reply_to_message_id: int | None = Field(default=None, gt=0)
    attachments: list[MessageAttachmentCreate] = Field(default_factory=list, max_length=10)


class MessagePublic(MessageReplyPreview):
    room_id: int
    client_message_id: str | None = None
    reply_to_message_id: int | None
    replied_message: MessageReplyPreview | None = None
    recalled_at: datetime | None


class MessageActionResponse(BaseModel):
    message: str
    data: MessagePublic


class MessageSync(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=200)
