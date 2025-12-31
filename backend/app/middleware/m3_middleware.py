"""M3-optimized middleware for request processing."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.services.logging_utils import get_logger

logger = get_logger("m3_middleware")


class M3OptimizationMiddleware(BaseHTTPMiddleware):
    """Middleware to optimize request processing for M3 hardware."""

    def __init__(self, app: Callable) -> None:
        """Initialize M3 optimization middleware."""
        super().__init__(app)
        # Create semaphore to limit concurrent requests based on M3 cores
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_tasks)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with M3 optimizations."""
        # Skip optimization for health checks
        if request.url.path == "/health":
            return await call_next(request)

        # Limit concurrent requests based on M3 capabilities
        async with self.semaphore:
            # Use asyncio to optimize for M3's performance cores
            response = await call_next(request)
            return response

