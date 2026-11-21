import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)
_SCRYPT_N = 1 << 14
_SCRYPT_R = 8
_SCRYPT_P = 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=64)
    return "scrypt${}${}${}${}${}".format(
        _SCRYPT_N, _SCRYPT_R, _SCRYPT_P,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, n, r, p, salt_text, digest_text = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user: User) -> str:
    if not settings.jwt_secret_key:
        raise HTTPException(status_code=503, detail="Authentication is not configured. Set JWT_SECRET_KEY.")
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user.id), "iat": now, "exp": now + timedelta(days=settings.jwt_expiry_days)},
                      settings.jwt_secret_key, algorithm="HS256")


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                 db: Session = Depends(get_db)) -> User:
    if not settings.jwt_secret_key:
        raise HTTPException(status_code=503, detail="Authentication is not configured. Set JWT_SECRET_KEY.")
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Sign in to continue.", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=["HS256"])
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Your sign-in has expired. Please sign in again.", headers={"WWW-Authenticate": "Bearer"}) from exc
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User account not found.", headers={"WWW-Authenticate": "Bearer"})
    return user
