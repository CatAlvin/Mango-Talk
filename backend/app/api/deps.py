from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import token_fingerprint
from app.db.deps import get_db
from app.models import User, RevokedToken

security = HTTPBearer(auto_error=False)


def get_user_from_token(token: str | None, db: Session) -> User:
    try:
        if not token:
            raise ValueError()
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], options={"require_exp": True})
        if payload.get("typ", "access") != "access" or db.get(RevokedToken, token_fingerprint(token)):
            raise ValueError()
        user_id = int(payload["sub"])
    except (JWTError, ValueError, TypeError, KeyError):
        raise HTTPException(401, "登录已过期，请重新登录")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(401, "账号不存在，请重新登录")
    if not user.is_active:
        raise HTTPException(403, "账号已停用")
    return user


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else None
    return get_user_from_token(token, db)
