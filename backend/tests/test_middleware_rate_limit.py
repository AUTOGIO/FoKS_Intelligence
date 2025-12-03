"""Tests for rate limiting middleware."""

from __future__ import annotations

from time import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.middleware.rate_limit import RateLimitMiddleware


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = MagicMock(spec=Request)
        request.url.path = "/test"
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create a mock call_next function."""
        return AsyncMock(return_value=Response(content="OK", status_code=200))

    async def test_rate_limit_allows_request(self, mock_request, mock_call_next):
        """Test middleware allows request under limit."""
        middleware = RateLimitMiddleware(MagicMock(), requests_per_minute=60)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        mock_call_next.assert_called_once()

    async def test_rate_limit_health_endpoint(self, mock_request, mock_call_next):
        """Test middleware allows health endpoint without limit."""
        mock_request.url.path = "/health"
        middleware = RateLimitMiddleware(MagicMock(), requests_per_minute=1)

        # Make multiple requests to health endpoint
        for _ in range(10):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

        assert mock_call_next.call_count == 10

    async def test_rate_limit_exceeds_limit(self, mock_request, mock_call_next):
        """Test middleware blocks requests exceeding limit."""
        middleware = RateLimitMiddleware(MagicMock(), requests_per_minute=2)

        # Make requests up to limit
        for _ in range(2):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

        # Next request should be blocked
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 429
        assert b"Rate limit exceeded" in response.content or "Rate limit exceeded" in str(response.content)

    async def test_rate_limit_cleans_old_requests(self, mock_request, mock_call_next):
        """Test middleware cleans old requests from tracking."""
        middleware = RateLimitMiddleware(MagicMock(), requests_per_minute=2)

        # Manually add old requests (older than 1 minute)
        current_time = time()
        old_time = current_time - 70  # 70 seconds ago
        identifier = f"ip:{mock_request.client.host}"
        middleware.requests[identifier] = [old_time]

        # Should allow new request since old one is cleaned
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200

        # Verify old request was cleaned
        assert len(middleware.requests[identifier]) == 1
        assert middleware.requests[identifier][0] > old_time

    async def test_rate_limit_different_ips(self, mock_request, mock_call_next):
        """Test middleware tracks different IPs separately."""
        middleware = RateLimitMiddleware(MagicMock(), requests_per_minute=1)

        # Request from IP 1
        mock_request.client.host = "127.0.0.1"
        response1 = await middleware.dispatch(mock_request, mock_call_next)
        assert response1.status_code == 200

        # Request from IP 2 (should be allowed)
        mock_request.client.host = "192.168.1.1"
        response2 = await middleware.dispatch(mock_request, mock_call_next)
        assert response2.status_code == 200

        # Both IPs should be tracked separately
        assert len(middleware.requests) == 2

    async def test_rate_limit_no_client(self, mock_request, mock_call_next):
        """Test middleware handles requests without client info."""
        mock_request.client = None
        middleware = RateLimitMiddleware(MagicMock(), requests_per_minute=60)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        # Should use "unknown" as IP
        assert "unknown" in middleware.requests

