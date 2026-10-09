from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.user import UserPublic, UserSearchItem

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/search", response_model=list[UserSearchItem])
def search_users(
    keyword: str = Query(default="", max_length=32),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    keyword = keyword.strip()

    conditions = [
        User.is_active == True,
        User.id != current_user.id,
    ]

    if not keyword:
        return []
    if keyword:
        like_keyword = "%" + keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        conditions.append(
            or_(
                User.username.like(like_keyword, escape="\\"),
                User.phone == keyword,
            )
        )

    users = db.execute(
        select(User)
        .where(*conditions)
        .order_by(User.username.asc(), User.id.asc())
        .limit(limit)
    ).scalars().all()

    return [{"id": user.id, "username": user.username, "avatar_url": user.avatar_url, "phone": (user.phone[:3] + "****" + user.phone[-4:]) if user.phone and len(user.phone) >= 7 else None} for user in users]
