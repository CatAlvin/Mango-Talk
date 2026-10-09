from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy import or_, select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, security
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, token_fingerprint
from app.db.deps import get_db
from app.models import User, RevokedToken, UserIdentity
from app.schemas.user import UserRegister, UserLogin, RegisterResponse, AuthResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    username = payload.username.strip()
    phone = payload.phone.strip() if payload.phone else None
    if len(username) < 3 or any(char.isspace() for char in username):
        raise HTTPException(400, "用户名至少需要 3 个字符，不能包含空格")
    if phone and not (phone.isascii() and phone.isdigit() and 6 <= len(phone) <= 20):
        raise HTTPException(400, "请输入有效的手机号")
    identifiers = [username] + ([phone] if phone else [])
    if db.scalar(select(User.id).where(or_(User.username.in_(identifiers), User.phone.in_(identifiers))).limit(1)):
        raise HTTPException(409, "用户名或手机号已被使用")
    user = User(username=username, phone=phone, password_hash=hash_password(payload.password), role="user", is_active=True)
    db.add(user)
    try:
        db.flush()
        db.add_all([UserIdentity(identifier=value, user_id=user.id) for value in set(identifiers)])
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "用户名或手机号已被使用")
    db.refresh(user)
    return {"message": "账号已创建", "user": user}


@router.post("/login", response_model=AuthResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    identifier = payload.identifier.strip()
    users = db.scalars(select(User).where(or_(User.username == identifier, User.phone == identifier))).all()
    if len(users) > 1:
        raise HTTPException(409, "该登录名对应多个账号，请联系管理员")
    user = users[0] if users else None
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "用户名、手机号或密码不正确")
    if not user.is_active:
        raise HTTPException(403, "账号已停用")
    if not user.password_hash.startswith("$scrypt$"):
        user.password_hash = hash_password(payload.password)
        db.commit()
    return {"access_token": create_access_token(str(user.id)), "token_type": "bearer", "user": user}


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    payload = jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < datetime.now(timezone.utc).replace(tzinfo=None)))
    db.merge(RevokedToken(token_hash=token_fingerprint(credentials.credentials), expires_at=datetime.fromtimestamp(payload["exp"], timezone.utc).replace(tzinfo=None)))
    db.commit()
    return {"message": "已退出登录"}
