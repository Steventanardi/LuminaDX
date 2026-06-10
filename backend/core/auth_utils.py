"""JWT creation/verification and bcrypt password helpers.

Uses the `bcrypt` package directly instead of passlib — passlib does not
support bcrypt >= 4.0 (the __about__ attribute was removed upstream).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from config import settings


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.auth_token_expire_hours)
    return jwt.encode(
        {"sub": user_id, "role": role, "exp": exp},
        settings.auth_secret_key,
        algorithm="HS256",
    )


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.auth_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
