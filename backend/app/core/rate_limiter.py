import logging
import time
from collections import defaultdict

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger("ai_sale.rate_limiter")


class _TokenBucket:
    __slots__ = ("capacity", "tokens", "refill_rate", "last_refill")

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


_buckets: dict[str, _TokenBucket] = defaultdict(
    lambda: _TokenBucket(
        capacity=settings.rate_limit_rpm,
        refill_rate=settings.rate_limit_rpm / 60.0,
    )
)

_CLEANUP_INTERVAL = 300
_last_cleanup = time.monotonic()


def _cleanup_old_buckets():
    global _last_cleanup
    now = time.monotonic()
    if now - _last_cleanup < _CLEANUP_INTERVAL:
        return
    _last_cleanup = now
    stale = [
        ip for ip, b in _buckets.items()
        if now - b.last_refill > settings.rate_limit_cleanup_seconds
    ]
    for ip in stale:
        del _buckets[ip]


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


_RATE_LIMITED_PREFIXES = ("/api/chat", "/api/leads", "/api/voice")


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.rate_limit_enabled:
            return await call_next(request)

        path = request.url.path
        if not any(path.startswith(p) for p in _RATE_LIMITED_PREFIXES):
            return await call_next(request)

        client_ip = _get_client_ip(request)
        bucket = _buckets[client_ip]

        _cleanup_old_buckets()

        if not bucket.consume():
            logger.warning("Rate limit exceeded for %s on %s", client_ip, path)
            raise HTTPException(
                status_code=429,
                detail="Слишком много запросов. Пожалуйста, подождите.",
            )

        response = await call_next(request)
        remaining = max(0, int(bucket.tokens))
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_rpm)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
