import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import bcrypt
from jose import jwt
from app.core.config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, maxmem=64 * 1024 * 1024)
    return "$scrypt$16384$8$1$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(derived).decode()


def verify_password(password: str, encoded: str) -> bool:
    try:
        if encoded.startswith("$scrypt$"):
            _, _, n, r, p, salt, expected = encoded.split("$")
            if (n, r, p) != ("16384", "8", "1"):
                return False
            derived = hashlib.scrypt(password.encode("utf-8"), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), maxmem=64 * 1024 * 1024)
            return hmac.compare_digest(derived, base64.b64decode(expected))
        if encoded.startswith(("$2a$", "$2b$", "$2y$")):
            raw = password.encode("utf-8")
            return len(raw) <= 72 and bcrypt.checkpw(raw, encoded.encode())
    except (ValueError, TypeError):
        return False
    return False


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expires = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return jwt.encode({"sub": subject, "exp": expires, "typ": "access", "jti": uuid4().hex}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
