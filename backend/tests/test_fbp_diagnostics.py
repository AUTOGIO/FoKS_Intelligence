"""Tests for FBP diagnostics service and router."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import FBPDiagnosticsResponse, PingCheck, SocketCheck, VersionCheck
from app.services import fbp_diagnostics


@pytest.mark.asyncio
async def test_check_socket_exists():
    """Test socket check when socket exists."""
    with patch("app.services.fbp_diagnostics.settings") as mock_settings, \
         patch("app.services.fbp_diagnostics.Path") as mock_path_class, \
         patch("app.services.fbp_diagnostics.os.access") as mock_access:
        
        mock_settings.fbp_socket_path = "/tmp/fbp.sock"
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.is_socket.return_value = True
        mock_path_class.return_value = mock_path
        mock_access.return_value = True
        
        result = fbp_diagnostics._check_socket()
        
        assert result["exists"] is True
        assert result["is_socket"] is True
        assert result["accessible"] is True
        assert result["path"] == "/tmp/fbp.sock"


@pytest.mark.asyncio
async def test_check_socket_not_exists():
    """Test socket check when socket does not exist."""
    with patch("app.services.fbp_diagnostics.settings") as mock_settings, \
         patch("app.services.fbp_diagnostics.Path") as mock_path_class:
        
        mock_settings.fbp_socket_path = "/tmp/fbp.sock"
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path
        
        result = fbp_diagnostics._check_socket()
        
        assert result["exists"] is False
        assert result["is_socket"] is False
        assert result["accessible"] is False


@pytest.mark.asyncio
async def test_check_socket_not_socket_file():
    """Test socket check when path exists but is not a socket."""
    with patch("app.services.fbp_diagnostics.settings") as mock_settings, \
         patch("app.services.fbp_diagnostics.Path") as mock_path_class:
        
        mock_settings.fbp_socket_path = "/tmp/fbp.sock"
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.is_socket.return_value = False
        mock_path_class.return_value = mock_path
        
        result = fbp_diagnostics._check_socket()
        
        assert result["exists"] is True
        assert result["is_socket"] is False
        assert result["accessible"] is False


@pytest.mark.asyncio
async def test_run_fbp_diagnostics_success():
    """Test successful FBP diagnostics run."""
    mock_health_response = {
        "status": 200,
        "payload": {
            "status": "ok",
            "version": "0.1.0",
            "machine": "iMac M3",
            "project": "FBP",
        },
        "duration_ms": 15,
    }
    
    with patch("app.services.fbp_diagnostics._check_socket") as mock_check, \
         patch("app.services.fbp_diagnostics.FBPClient") as mock_client_class:
        
        mock_check.return_value = {
            "exists": True,
            "is_socket": True,
            "accessible": True,
            "path": "/tmp/fbp.sock",
        }
        
        mock_client = MagicMock()
        mock_client.health = AsyncMock(return_value=mock_health_response)
        mock_client.close = AsyncMock()
        mock_client_class.return_value = mock_client
        
        result = await fbp_diagnostics.run_fbp_diagnostics()
        
        assert result["overall_status"] == "READY"
        assert result["socket_check"]["exists"] is True
        assert result["version_check"]["success"] is True
        assert result["ping_check"]["success"] is True
        assert result["version_check"]["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_run_fbp_diagnostics_socket_missing():
    """Test FBP diagnostics when socket is missing (early exit)."""
    with patch("app.services.fbp_diagnostics._check_socket") as mock_check, \
         patch("app.services.fbp_diagnostics.FBPClient") as mock_client_class:
        
        mock_check.return_value = {
            "exists": False,
            "is_socket": False,
            "accessible": False,
            "path": "/tmp/fbp.sock",
        }
        
        mock_client = MagicMock()
        mock_client.health = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.close = AsyncMock()
        mock_client_class.return_value = mock_client
        
        result = await fbp_diagnostics.run_fbp_diagnostics()
        
        # Early exit: socket missing, so version/ping checks are not attempted
        assert result["overall_status"] == "BLOCKED"
        assert result["socket_check"]["exists"] is False
        assert result["version_check"] == {}  # Empty (not attempted due to early exit)
        assert result["ping_check"] == {}  # Empty (not attempted due to early exit)
        
        # Verify FBPClient was never called (early exit prevents connection attempts)
        assert mock_client_class.call_count == 0


@pytest.mark.asyncio
async def test_run_fbp_diagnostics_version_check_fails():
    """Test FBP diagnostics when version check fails."""
    with patch("app.services.fbp_diagnostics._check_socket") as mock_check, \
         patch("app.services.fbp_diagnostics.FBPClient") as mock_client_class:
        
        mock_check.return_value = {
            "exists": True,
            "is_socket": True,
            "accessible": True,
            "path": "/tmp/fbp.sock",
        }
        
        from app.services.fbp_client import FBPClientError
        
        mock_client = MagicMock()
        mock_client.health = AsyncMock(side_effect=FBPClientError("Connection error"))
        mock_client.close = AsyncMock()
        mock_client_class.return_value = mock_client
        
        result = await fbp_diagnostics.run_fbp_diagnostics()
        
        assert result["overall_status"] == "BLOCKED"
        assert result["socket_check"]["exists"] is True
        assert result["version_check"]["success"] is False
        assert "error" in result["version_check"]


@pytest.mark.asyncio
async def test_run_fbp_diagnostics_ping_timeout():
    """Test FBP diagnostics when ping times out."""
    import asyncio
    
    with patch("app.services.fbp_diagnostics._check_socket") as mock_check, \
         patch("app.services.fbp_diagnostics.FBPClient") as mock_client_class, \
         patch("app.services.fbp_diagnostics.asyncio.wait_for") as mock_wait:
        
        mock_check.return_value = {
            "exists": True,
            "is_socket": True,
            "accessible": True,
            "path": "/tmp/fbp.sock",
        }
        
        # First call (version check) succeeds
        # Second call (ping check) times out
        mock_health_response = {
            "status": 200,
            "payload": {"status": "ok"},
            "duration_ms": 10,
        }
        
        mock_client = MagicMock()
        mock_client.health = AsyncMock(return_value=mock_health_response)
        mock_client.close = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Make wait_for raise TimeoutError on second call
        call_count = 0
        async def mock_wait_for(coro, timeout):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call (version check) - no wait_for
                return await coro
            else:
                # Second call (ping check) - timeout
                raise asyncio.TimeoutError()
        
        with patch("app.services.fbp_diagnostics.asyncio.wait_for", side_effect=mock_wait_for):
            result = await fbp_diagnostics.run_fbp_diagnostics()
        
        assert result["version_check"]["success"] is True
        assert result["ping_check"]["success"] is False
        assert "timeout" in result["ping_check"]["error"].lower()


def test_fbp_diagnostics_router_success():
    """Test FBP diagnostics router endpoint."""
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    
    with patch("app.routers.fbp_diagnostics.fbp_diagnostics.run_fbp_diagnostics") as mock_run:
        mock_run.return_value = {
            "socket_check": {
                "exists": True,
                "is_socket": True,
                "accessible": True,
                "path": "/tmp/fbp.sock",
            },
            "version_check": {
                "success": True,
                "status": 200,
                "version": "0.1.0",
                "machine": "iMac M3",
                "project": "FBP",
                "data": {},
            },
            "ping_check": {
                "success": True,
                "status": 200,
                "response_time_ms": 15,
                "data": {},
            },
            "overall_status": "READY",
        }
        
        response = client.post("/fbp/diagnostics/run")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "READY"
        assert data["socket_check"]["exists"] is True
        assert data["version_check"]["success"] is True
        assert data["ping_check"]["success"] is True


def test_fbp_diagnostics_router_error():
    """Test FBP diagnostics router when service raises exception."""
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    
    with patch("app.routers.fbp_diagnostics.fbp_diagnostics.run_fbp_diagnostics") as mock_run:
        mock_run.side_effect = Exception("Unexpected error")
        
        response = client.post("/fbp/diagnostics/run")
        assert response.status_code == 500
        assert "FBP diagnostics failed" in response.json()["detail"]
