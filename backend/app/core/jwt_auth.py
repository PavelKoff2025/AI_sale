"""JWT token generation and validation for API protection.

Widget clients get a short-lived token via POST /api/auth/token (no credentials
needed — the token just limits abuse). Admin endpoints still use X-Admin-Key.
"""

import logging
import secrets
import time

import jwt
from fastapi import Depends, Header, HTTPException, Request

from app.core.config import settings

logger = logging.getLogger("ai_sale.jwt")

_runtime_secret: str | None = None


def _get_secret() -> str:
    global _runtime_secret
    if settings.jwt_secret:
        return settings.jwt_secret
    if _runtime_secret is None:
        _runtime_secret = secrets.token_hex(32)
        logger.warning("JWT_SECRET not set — using auto-generated secret (tokens won't survive restart)")
    return _runtime_secret


def create_token(subject: str = "widget", extra: dict | None = None) -> tuple[str, int]:
    """Return (token, expires_in_seconds)."""
    secret = _get_secret()
    expires_in = settings.jwt_expire_minutes * 60
    payload = {
        "sub": subject,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in,
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_token(token: str) -> dict:
    secret = _get_secret()
    try:
        return jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def verify_jwt(request: Request, authorization: str = Header(default="")) -> dict:
    """Dependency for JWT-protected endpoints.

    Skipped when jwt_secret is empty (dev mode — no auth required).
    """
    if not settings.jwt_secret:
        return {"sub": "dev", "mode": "no-auth"}

    token = ""
    if authorization.startswith("Bearer "):
        token = authorization[7:]

    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization: Bearer <token>")

    return decode_token(token)
