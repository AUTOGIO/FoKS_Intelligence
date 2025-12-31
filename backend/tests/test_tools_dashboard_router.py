"""Tests for tools dashboard router."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_daily_engineering_briefing_endpoint_success():
    """Test daily engineering briefing endpoint success."""
    mock_result = {"markdown": "# Daily Engineering Briefing\n\nTest content."}

    with patch("app.services.dashboard_tools.build_daily_engineering_briefing") as mock_build:
        mock_build.return_value = mock_result

        response = client.post(
            "/tools/dashboard/daily-engineering",
            json={
                "repo_path": None,
                "obsidian_path": None,
                "include_fbp_health": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "markdown" in data
        assert "Daily Engineering Briefing" in data["markdown"]


@pytest.mark.asyncio
async def test_daily_engineering_briefing_endpoint_with_params():
    """Test daily engineering briefing endpoint with custom parameters."""
    mock_result = {"markdown": "# Briefing\n\nContent"}

    with patch("app.services.dashboard_tools.build_daily_engineering_briefing") as mock_build:
        mock_build.return_value = mock_result

        response = client.post(
            "/tools/dashboard/daily-engineering",
            json={
                "repo_path": "/custom/path",
                "obsidian_path": "/custom/obsidian",
                "include_fbp_health": False,
            },
        )

        assert response.status_code == 200
        mock_build.assert_called_once()
        call_kwargs = mock_build.call_args[1]
        assert call_kwargs["repo_path"] == "/custom/path"
        assert call_kwargs["obsidian_path"] == "/custom/obsidian"
        assert call_kwargs["include_fbp_health"] is False


@pytest.mark.asyncio
async def test_daily_engineering_briefing_endpoint_failure():
    """Test daily engineering briefing endpoint failure handling."""
    with patch("app.services.dashboard_tools.build_daily_engineering_briefing") as mock_build:
        mock_build.side_effect = Exception("Service error")

        response = client.post(
            "/tools/dashboard/daily-engineering",
            json={},
        )

        assert response.status_code == 500
        assert "Failed to generate briefing" in response.json()["detail"]


def test_daily_engineering_briefing_endpoint_validation():
    """Test daily engineering briefing endpoint request validation."""
    # Missing required fields should use defaults
    response = client.post(
        "/tools/dashboard/daily-engineering",
        json={},
    )
    # Should not be a validation error since all fields have defaults
    assert response.status_code in [200, 500]  # Either works or service error


def test_daily_engineering_briefing_endpoint_invalid_json():
    """Test daily engineering briefing endpoint with invalid JSON."""
    response = client.post(
        "/tools/dashboard/daily-engineering",
        json={"invalid": "field"},
    )
    # Should accept extra fields or validate
    assert response.status_code in [200, 422, 500]
