"""
JWT & Password utilities
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from loguru import logger

from api.config import api_config


def hash_password(password: str) -> str:
    """Hash password with SHA-256 + random salt"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${pwd_hash}"


def verify_password(password: str, stored: str) -> bool:
    """Verify password against stored hash"""
    try:
        salt, pwd_hash = stored.split("$", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == pwd_hash
    except (ValueError, AttributeError):
        return False


def create_access_token(user_id: int, role: str) -> str:
    """Create JWT access token"""
    cfg = api_config.jwt
    expire = datetime.now(timezone.utc) + timedelta(minutes=cfg["expire_minutes"])
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
    }
    token = jwt.encode(payload, cfg["secret_key"], algorithm=cfg["algorithm"])
    return token


def decode_access_token(token: str) -> Optional[dict]:
    """Decode JWT access token"""
    cfg = api_config.jwt
    try:
        payload = jwt.decode(token, cfg["secret_key"], algorithms=[cfg["algorithm"]])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None
