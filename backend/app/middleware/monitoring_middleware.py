"""Monitoring middleware for tracking request metrics."""

from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.monitoring import monitoring
from app.services.logging_utils import get_logger

logger = get_logger("monitoring_middleware")


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to track request metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track request metrics."""
        start_time = time.time()
        endpoint = request.url.path
        success = True
        error_type = None

        try:
            response = await call_next(request)
            # Consider 2xx and 3xx as success
            if response.status_code >= 400:
                success = False
                error_type = f"HTTP_{response.status_code}"
            return response
        except Exception as exc:  # noqa: BLE001
            success = False
            error_type = type(exc).__name__
            logger.error("Request failed: %s", exc)
            raise
        finally:
            response_time_ms = (time.time() - start_time) * 1000
            monitoring.record_request(success=success, response_time_ms=response_time_ms)

