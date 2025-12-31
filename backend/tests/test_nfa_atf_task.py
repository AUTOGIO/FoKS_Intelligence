"""Tests for NFA ATF task endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest  # noqa: F401
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_nfa_atf_endpoint_success():
    """Test successful NFA ATF task execution."""
    # Mock the task runner
    mock_result = {
        "task": "nfa_atf",
        "success": True,
        "duration_ms": 5000,
        "payload": {
            "status": "success",
            "nfa_number": "900501884",
            "danfe_path": (
                "/Users/dnigga/Downloads/NFA_Outputs/"
                "NFA_900501884_DANFE.pdf"
            ),
            "dar_path": (
                "/Users/dnigga/Downloads/NFA_Outputs/"
                "NFA_900501884_DAR.pdf"
            ),
            "logs": "Browser initialized\nLogin successful\n",
        },
    }

    patch_path = "app.routers.tasks.task_runner.run_task"
    with patch(patch_path, new_callable=AsyncMock) as mock_run:
        mock_run.return_value = mock_result

        response = client.post(
            "/tasks/run/nfa-atf",
            json={
                "from_date": "08/12/2025",
                "to_date": "10/12/2025",
                "matricula": "1595504",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["task"] == "nfa_atf"
        assert data["status"] == "success"
        assert "danfe" in data["pdf_paths"]
        assert "dar" in data["pdf_paths"]
        assert "DANFE.pdf" in data["pdf_paths"]["danfe"]
        assert "DAR.pdf" in data["pdf_paths"]["dar"]
        assert data["logs"] == "Browser initialized\nLogin successful\n"
        assert data["metadata"]["nfa_number"] == "900501884"


@pytest.mark.asyncio
async def test_nfa_atf_endpoint_with_nfa_number():
    """Test NFA ATF endpoint with specific NFA number."""
    mock_result = {
        "task": "nfa_atf",
        "success": True,
        "duration_ms": 5000,
        "payload": {
            "status": "success",
            "nfa_number": "900501884",
            "danfe_path": (
                "/Users/dnigga/Downloads/NFA_Outputs/"
                "NFA_900501884_DANFE.pdf"
            ),
            "dar_path": (
                "/Users/dnigga/Downloads/NFA_Outputs/"
                "NFA_900501884_DAR.pdf"
            ),
            "logs": "Browser initialized\n",
        },
    }

    patch_path = "app.routers.tasks.task_runner.run_task"
    with patch(patch_path, new_callable=AsyncMock) as mock_run:
        mock_run.return_value = mock_result

        response = client.post(
            "/tasks/run/nfa-atf",
            json={
                "from_date": "08/12/2025",
                "to_date": "10/12/2025",
                "matricula": "1595504",
                "nfa_number": "900501884",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        # Verify nfa_number was passed to task runner
        call_args = mock_run.call_args
        assert call_args[1]["args"]["nfa_number"] == "900501884"


@pytest.mark.asyncio
async def test_nfa_atf_endpoint_error():
    """Test NFA ATF endpoint error handling."""
    mock_result = {
        "task": "nfa_atf",
        "success": False,
        "duration_ms": 2000,
        "error": "NFA ATF automation failed: Login failed",
        "payload": {
            "status": "error",
            "error_type": "login_failed",
            "message": "Login failed: Invalid credentials",
            "logs": "Browser initialized\nLogin failed\n",
        },
    }

    patch_path = "app.routers.tasks.task_runner.run_task"
    with patch(patch_path, new_callable=AsyncMock) as mock_run:
        mock_run.return_value = mock_result

        response = client.post(
            "/tasks/run/nfa-atf",
            json={
                "from_date": "08/12/2025",
                "to_date": "10/12/2025",
                "matricula": "1595504",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["task"] == "nfa_atf"
        assert data["status"] == "error"
        assert "Login failed" in data["logs"]
        assert data["metadata"]["error_type"] == "login_failed"


@pytest.mark.asyncio
async def test_nfa_atf_endpoint_validation_error():
    """Test NFA ATF endpoint with missing required fields."""
    response = client.post(
        "/tasks/run/nfa-atf",
        json={
            "from_date": "08/12/2025",
            # Missing to_date and matricula
        },
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_nfa_atf_endpoint_timeout():
    """Test NFA ATF endpoint timeout handling."""
    mock_result = {
        "task": "nfa_atf",
        "success": False,
        "duration_ms": 900000,
        "error": "Command timed out after 900s",
    }

    patch_path = "app.routers.tasks.task_runner.run_task"
    with patch(patch_path, new_callable=AsyncMock) as mock_run:
        mock_run.return_value = mock_result

        response = client.post(
            "/tasks/run/nfa-atf",
            json={
                "from_date": "08/12/2025",
                "to_date": "10/12/2025",
                "matricula": "1595504",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "timed out" in data["metadata"]["error"].lower()
