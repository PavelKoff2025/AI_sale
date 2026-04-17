"""Tests for JWT token generation and validation."""

import time

import pytest

from app.core.jwt_auth import create_token, decode_token


def test_create_and_decode():
    token, expires_in = create_token(subject="test-user")
    assert expires_in > 0
    payload = decode_token(token)
    assert payload["sub"] == "test-user"
    assert "iat" in payload
    assert "exp" in payload


def test_extra_claims():
    token, _ = create_token(subject="widget", extra={"ip": "127.0.0.1"})
    payload = decode_token(token)
    assert payload["ip"] == "127.0.0.1"


def test_invalid_token():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        decode_token("invalid.token.here")
    assert exc_info.value.status_code == 401


def test_expired_token():
    import jwt as pyjwt
    from app.core.jwt_auth import _get_secret
    from app.core.config import settings

    secret = _get_secret()
    payload = {"sub": "test", "iat": int(time.time()) - 7200, "exp": int(time.time()) - 3600}
    token = pyjwt.encode(payload, secret, algorithm=settings.jwt_algorithm)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()
