"""Tests for NFA ATF router."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.task_runner import TaskRunner


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_task_runner(monkeypatch):
    """Mock TaskRunner for testing."""
    mock_runner = AsyncMock(spec=TaskRunner)
    mock_runner.run_task = AsyncMock(
        return_value={
            "task": "nfa_atf",
            "success": True,
            "duration_ms": 5000,
            "payload": {
                "status": "success",
                "nfa_number": "900501884",
                "danfe_path": "/Users/dnigga/Downloads/NFA_Outputs/NFA_900501884_DANFE.pdf",
                "dar_path": "/Users/dnigga/Downloads/NFA_Outputs/NFA_900501884_TAXA_SERVICO.pdf",
            },
            "error": None,
        }
    )

    # Patch the router's task_runner instance
    import app.routers.nfa_atf as nfa_atf_router
    monkeypatch.setattr(nfa_atf_router, "task_runner", mock_runner)

    return mock_runner


def test_nfa_atf_endpoint_success(client, mock_task_runner):
    """Test successful NFA ATF endpoint call - both downloads always execute."""
    response = client.post(
        "/tasks/nfa_atf/run",
        json={
            "from_date": "01/01/2024",
            "to_date": "31/01/2024",
            "matricula": "1595504",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["task"] == "nfa_atf"
    assert data["payload"]["status"] == "success"
    assert data["payload"]["nfa_number"] == "900501884"
    # Both downloads always execute in sequence
    assert data["payload"]["danfe_path"] is not None
    assert data["payload"]["dar_path"] is not None

    # Verify TaskRunner was called correctly
    mock_task_runner.run_task.assert_called_once()
    call_args = mock_task_runner.run_task.call_args
    assert call_args[1]["task_type"] == "nfa_atf"
    assert call_args[1]["args"]["from_date"] == "01/01/2024"
    assert call_args[1]["args"]["to_date"] == "31/01/2024"


def test_nfa_atf_endpoint_missing_required_fields(client):
    """Test NFA ATF endpoint with missing required fields."""
    response = client.post(
        "/tasks/nfa_atf/run",
        json={
            "from_date": "01/01/2024",
            # Missing to_date
        },
    )

    assert response.status_code == 422  # Validation error


def test_nfa_atf_endpoint_with_all_options(client, mock_task_runner):
    """Test NFA ATF endpoint with all optional parameters."""
    response = client.post(
        "/tasks/nfa_atf/run",
        json={
            "from_date": "01/01/2024",
            "to_date": "31/01/2024",
            "matricula": "1595504",
            "output_dir": "/custom/path",
            "headless": False,
            "nfa_number": "900501884",
            "timeout": 900,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify all options were passed
    call_args = mock_task_runner.run_task.call_args
    args = call_args[1]["args"]
    assert args["matricula"] == "1595504"
    assert args["output_dir"] == "/custom/path"
    assert args["headless"] is False
    assert args["nfa_number"] == "900501884"
    assert call_args[1]["timeout"] == 900


def test_nfa_atf_endpoint_error_response(client, mock_task_runner):
    """Test NFA ATF endpoint error response."""
    mock_task_runner.run_task = AsyncMock(
        return_value={
            "task": "nfa_atf",
            "success": False,
            "duration_ms": 2000,
            "payload": None,
            "error": "NFA ATF automation failed: Login failed",
        }
    )

    response = client.post(
        "/tasks/nfa_atf/run",
        json={
            "from_date": "01/01/2024",
            "to_date": "31/01/2024",
        },
    )

    assert response.status_code == 200  # Router returns 200 even on error
    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert "Login failed" in data["error"]

