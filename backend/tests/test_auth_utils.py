from datetime import datetime, timedelta, timezone

import jwt

from config import settings
from core.auth_utils import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_verify_roundtrip():
    hashed = hash_password("s3cret-pw")
    assert hashed != "s3cret-pw"
    assert verify_password("s3cret-pw", hashed)


def test_wrong_password_rejected():
    hashed = hash_password("s3cret-pw")
    assert not verify_password("wrong-pw", hashed)


def test_token_roundtrip_carries_sub_and_role():
    token = create_access_token("user-123", "radiologist")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["role"] == "radiologist"


def test_expired_token_returns_none():
    expired = jwt.encode(
        {
            "sub": "user-123",
            "role": "admin",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        settings.auth_secret_key,
        algorithm="HS256",
    )
    assert decode_token(expired) is None


def test_token_signed_with_other_key_returns_none():
    forged = jwt.encode(
        {
            "sub": "user-123",
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "not-the-real-key-but-long-enough-for-hs256-minimums",
        algorithm="HS256",
    )
    assert decode_token(forged) is None


def test_garbage_token_returns_none():
    assert decode_token("not.a.jwt") is None
