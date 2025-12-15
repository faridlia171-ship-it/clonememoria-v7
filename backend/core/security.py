import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from backend.core.config import settings

logger = logging.getLogger(__name__)
logger.info("SECURITY_MODULE_LOADED", extra={"file": __file__})

# ============================================================
# PASSWORD / HASHING CONFIG
# ============================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# bcrypt hard limit (bytes, not characters)
MAX_BCRYPT_PASSWORD_BYTES = 72

# ============================================================
# PASSWORD UTILITIES
# ============================================================

def _password_byte_length(password: str) -> int:
    return len(password.encode("utf-8"))


def validate_password(password: str) -> None:
    """
    Validate password BEFORE hashing.
    This is mandatory to avoid bcrypt runtime failures.
    """
    if not password or not password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be empty"
        )

    if _password_byte_length(password) > MAX_BCRYPT_PASSWORD_BYTES:
        logger.warning(
            "PASSWORD_TOO_LONG",
            extra={"byte_length": _password_byte_length(password)}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password too long (max 72 bytes, avoid emojis or special characters)"
        )


def get_password_hash(password: str) -> str:
    """
    Hash a password securely after validation.
    """
    validate_password(password)
    logger.debug("PASSWORD_HASHING")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    """
    logger.debug("PASSWORD_VERIFICATION_ATTEMPT")
    return pwd_context.verify(plain_password, hashed_password)

# ============================================================
# JWT ACCESS TOKENS
# ============================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()

    expire = (
        datetime.utcnow() + expires_delta
        if expires_delta
        else datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    logger.info(
        "ACCESS_TOKEN_CREATED",
        extra={
            "user_id": data.get("sub"),
            "expires_at": expire.isoformat()
        }
    )

    return encoded_jwt


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

        logger.debug("ACCESS_TOKEN_DECODED", extra={"user_id": user_id})
        return payload

    except JWTError as e:
        logger.error("ACCESS_TOKEN_DECODE_ERROR", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

# ============================================================
# REFRESH TOKENS
# ============================================================

REFRESH_TOKEN_EXPIRE_DAYS = 30


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()

    expire = (
        datetime.utcnow() + expires_delta
        if expires_delta
        else datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )

    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    logger.info(
        "REFRESH_TOKEN_CREATED",
        extra={
            "user_id": data.get("sub"),
            "expires_at": expire.isoformat()
        }
    )

    return encoded_jwt


def decode_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        if payload.get("type") != "refresh" or not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        logger.debug(
            "REFRESH_TOKEN_DECODED",
            extra={"user_id": payload.get("sub")}
        )

        return payload

    except JWTError as e:
        logger.error("REFRESH_TOKEN_DECODE_ERROR", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
