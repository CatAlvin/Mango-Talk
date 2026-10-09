from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class PrivateRoomCreate(BaseModel):
    target_user_id: int = Field(gt=0)

class GroupRoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    member_user_ids: list[int] = Field(default_factory=list, max_length=100)

class RoomPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    name: str | None
    owner_id: int | None
    avatar_url: str | None
    description: str | None
    is_active: bool
    created_at: datetime

class RoomActionResponse(BaseModel):
    message: str
    room: RoomPublic

class RoomListItem(BaseModel):
    id: int
    type: str
    name: str | None
    display_name: str
    owner_id: int | None
    avatar_url: str | None
    description: str | None
    is_active: bool
    member_count: int
    my_role: str
    joined_at: datetime
    created_at: datetime
    last_message: dict | None = None
    last_activity_at: datetime
    unread_count: int = 0


class RoomRead(BaseModel):
    message_id: int = Field(gt=0)
