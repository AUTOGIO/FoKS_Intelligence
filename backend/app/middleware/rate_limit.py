"""Rate limiting middleware for FoKS Intelligence."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from time import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.services.logging_utils import get_logger
from app.utils.token_bucket import TokenBucketRateLimiter

logger = get_logger("rate_limit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    For production, consider using Redis-based solution.
    """

    def __init__(self, app: Callable, requests_per_minute: int = 60) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute

        # Use token bucket if enabled, otherwise use simple counter
        if settings.rate_limit_use_token_bucket:
            self.token_bucket_limiter = TokenBucketRateLimiter(
                requests_per_minute=requests_per_minute,
                burst_capacity=settings.rate_limit_burst_capacity,
            )
            self.requests = None
        else:
            self.token_bucket_limiter = None
            self.requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit before processing request."""
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        # Get identifier: user_id from header/query if available, otherwise IP
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            try:
                user_id = request.query_params.get("user_id")
            except AttributeError:
                user_id = None

        client_ip = request.client.host if request.client else "unknown"

        # Use user_id if available, otherwise fall back to IP
        identifier = user_id if user_id else f"ip:{client_ip}"

        # Use token bucket if enabled
        if self.token_bucket_limiter:
            is_allowed, wait_time = self.token_bucket_limiter.is_allowed(identifier)
            remaining = int(self.token_bucket_limiter.get_remaining(identifier))

            if not is_allowed:
                logger.warning(
                    "Rate limit exceeded for %s: %s (wait %.2fs)",
                    "user" if user_id else "IP",
                    identifier,
                    wait_time,
                )
                response = Response(
                    content='{"detail": "Rate limit exceeded"}',
                    status_code=429,
                    media_type="application/json",
                )
                response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["Retry-After"] = str(int(wait_time))
                return response

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response

        # Simple counter-based rate limiting (original implementation)
        current_time = time()

        # Clean old requests (older than 1 minute)
        self.requests[identifier] = [
            req_time
            for req_time in self.requests[identifier]
            if current_time - req_time < 60
        ]

        # Check rate limit
        if len(self.requests[identifier]) >= self.requests_per_minute:
            logger.warning(
                "Rate limit exceeded for %s: %s",
                "user" if user_id else "IP",
                identifier,
            )
            response = Response(
                content='{"detail": "Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["Retry-After"] = "60"
            return response

        # Record request
        self.requests[identifier].append(current_time)

        response = await call_next(request)
        # Add rate limit headers
        remaining = self.requests_per_minute - len(self.requests[identifier])
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

