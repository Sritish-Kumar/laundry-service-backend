import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.constants import UserRole
from app.exceptions.custom_exceptions import AuthenticationError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def current_utc() -> datetime:
    return datetime.now(UTC)

def generate_jti() -> str:
    return str(uuid.uuid4())


def create_access_token(*, user_id: uuid.UUID, role: UserRole, session_id: uuid.UUID) -> str:
    issued_at = current_utc()
    expire = issued_at + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "role": role.value,
        "type": "access",
        "jti": generate_jti(),
        "iat": issued_at,
        "exp": expire,
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(*, user_id: uuid.UUID, session_id: uuid.UUID) -> str:
    issued_at = current_utc()
    expire = issued_at + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "type": "refresh",
        "jti": generate_jti(),
        "iat": issued_at,
        "exp": expire,
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return _decode_token(token, expected_type="access")


def decode_refresh_token(token: str) -> dict[str, Any]:
    return _decode_token(token, expected_type="refresh")


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _decode_token(token: str, *, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc

    if payload.get("type") != expected_type:
        raise AuthenticationError("Invalid token type")

    return payload
