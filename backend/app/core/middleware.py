import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("ai_sale.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.time()

        logger.info(
            "[%s] %s %s",
            request_id,
            request.method,
            request.url.path,
        )

        try:
            response = await call_next(request)
            elapsed = round((time.time() - start) * 1000)
            logger.info(
                "[%s] %s %s → %d (%dms)",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                elapsed,
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            elapsed = round((time.time() - start) * 1000)
            logger.error(
                "[%s] %s %s → ERROR (%dms): %s",
                request_id,
                request.method,
                request.url.path,
                elapsed,
                str(e),
            )
            raise
