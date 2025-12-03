"""Tests for authentication middleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status
from starlette.requests import Request

from app.middleware.auth import AuthMiddleware


class TestAuthMiddleware:
    """Tests for AuthMiddleware."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = MagicMock(spec=Request)
        request.url.path = "/test"
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create a mock call_next function."""
        return AsyncMock(return_value=MagicMock())

    @patch("app.middleware.auth.settings")
    async def test_auth_middleware_no_api_key_configured(self, mock_settings, mock_request, mock_call_next):
        """Test middleware allows requests when no API key configured."""
        mock_settings.api_key = None
        middleware = AuthMiddleware(MagicMock())

        response = await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once()

    @patch("app.middleware.auth.settings")
    async def test_auth_middleware_public_endpoint(self, mock_settings, mock_request, mock_call_next):
        """Test middleware allows public endpoints without auth."""
        mock_settings.api_key = "test-key"
        mock_request.url.path = "/health"
        middleware = AuthMiddleware(MagicMock())

        response = await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once()

    @patch("app.middleware.auth.settings")
    async def test_auth_middleware_valid_api_key_header(self, mock_settings, mock_request, mock_call_next):
        """Test middleware allows requests with valid API key in header."""
        mock_settings.api_key = "test-key"
        mock_request.headers = {"X-API-Key": "test-key"}
        middleware = AuthMiddleware(MagicMock())

        response = await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once()

    @patch("app.middleware.auth.settings")
    async def test_auth_middleware_valid_api_key_bearer(self, mock_settings, mock_request, mock_call_next):
        """Test middleware allows requests with valid API key in Bearer token."""
        mock_settings.api_key = "test-key"
        mock_request.headers = {"Authorization": "Bearer test-key"}
        middleware = AuthMiddleware(MagicMock())

        response = await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once()

    @patch("app.middleware.auth.settings")
    async def test_auth_middleware_invalid_api_key(self, mock_settings, mock_request, mock_call_next):
        """Test middleware rejects requests with invalid API key."""
        mock_settings.api_key = "test-key"
        mock_request.headers = {"X-API-Key": "wrong-key"}
        middleware = AuthMiddleware(MagicMock())

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        mock_call_next.assert_not_called()

    @patch("app.middleware.auth.settings")
    async def test_auth_middleware_missing_api_key(self, mock_settings, mock_request, mock_call_next):
        """Test middleware rejects requests without API key."""
        mock_settings.api_key = "test-key"
        mock_request.headers = {}
        middleware = AuthMiddleware(MagicMock())

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        mock_call_next.assert_not_called()

    @patch("app.middleware.auth.settings")
    async def test_auth_middleware_docs_endpoint(self, mock_settings, mock_request, mock_call_next):
        """Test middleware allows /docs endpoint without auth."""
        mock_settings.api_key = "test-key"
        mock_request.url.path = "/docs"
        middleware = AuthMiddleware(MagicMock())

        response = await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once()

    @patch("app.middleware.auth.settings")
    async def test_auth_middleware_no_client(self, mock_settings, mock_request, mock_call_next):
        """Test middleware handles requests without client info."""
        mock_settings.api_key = "test-key"
        mock_request.client = None
        mock_request.headers = {"X-API-Key": "wrong-key"}
        middleware = AuthMiddleware(MagicMock())

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

