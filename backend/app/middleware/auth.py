"""Authentication middleware for API key validation."""

from __future__ import annotations

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.services.logging_utils import get_logger

logger = get_logger("auth_middleware")


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for API key authentication."""

    # Public endpoints that don't require authentication
    PUBLIC_ENDPOINTS = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next):
        """Check API key if authentication is enabled."""
        # Skip auth if no API key configured
        if not settings.api_key:
            return await call_next(request)

        # Skip auth for public endpoints
        if request.url.path in self.PUBLIC_ENDPOINTS:
            return await call_next(request)

        # Get API key from header
        api_key = request.headers.get("X-API-Key") or request.headers.get(
            "Authorization"
        )

        if api_key and api_key.startswith("Bearer "):
            api_key = api_key.replace("Bearer ", "")

        # Validate API key
        if not api_key or api_key != settings.api_key:
            logger.warning(
                "Unauthorized access attempt from %s to %s",
                request.client.host if request.client else "unknown",
                request.url.path,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)

