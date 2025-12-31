"""Tests for NFA Intelligence Router."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.nfa_intelligence import NFAIntelligenceService


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_nfa_intelligence(monkeypatch):
    """Mock NFA Intelligence Service."""
    mock_service = AsyncMock(spec=NFAIntelligenceService)

    # Mock load_employees_from_file
    mock_service.load_employees_from_file = AsyncMock(
        return_value=[
            {"loja": "1595504", "cpf": "12345678901"},
            {"loja": "1595505", "cpf": "12345678902"},
        ]
    )

    # Mock run_batch
    mock_service.run_batch = AsyncMock(
        return_value=[
            {
                "success": True,
                "employee": {"loja": "1595504", "cpf": "12345678901"},
                "nfa_count": 1,
                "nfa_number": "900501884",
                "pdfs": [
                    {"type": "DANFE", "path": "/path/to/DANFE.pdf"},
                    {"type": "DAR", "path": "/path/to/DAR.pdf"},
                ],
                "timestamp": "2024-01-15T10:00:00",
            },
            {
                "success": True,
                "employee": {"loja": "1595505", "cpf": "12345678902"},
                "nfa_count": 1,
                "nfa_number": "900501885",
                "pdfs": [
                    {"type": "DANFE", "path": "/path/to/DANFE2.pdf"},
                    {"type": "DAR", "path": "/path/to/DAR2.pdf"},
                ],
                "timestamp": "2024-01-15T10:01:00",
            },
        ]
    )

    # Mock generate_report
    mock_service.generate_report = AsyncMock(
        return_value="/tmp/reports/NFA_ATF_RUN_2024-01-15_100000.json"
    )

    # Patch the router's service instance
    import app.routers.nfa_intelligence as nfa_intelligence_router

    monkeypatch.setattr(nfa_intelligence_router, "nfa_intelligence", mock_service)

    return mock_service


def test_nfa_intelligence_endpoint_auto_employees(client, mock_nfa_intelligence):
    """Test NFA Intelligence endpoint with auto employee loading."""
    response = client.post(
        "/nfa/intelligence/run",
        json={
            "from_date": "01/01/2024",
            "to_date": "31/01/2024",
            "employees": "auto",
            "headless": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["report_path"] is not None
    assert "summary" in data
    assert data["summary"]["total_items"] == 2
    assert data["summary"]["success_count"] == 2

    # Verify service methods were called
    mock_nfa_intelligence.load_employees_from_file.assert_called_once()
    mock_nfa_intelligence.run_batch.assert_called_once()
    mock_nfa_intelligence.generate_report.assert_called_once()


def test_nfa_intelligence_endpoint_provided_employees(client, mock_nfa_intelligence):
    """Test NFA Intelligence endpoint with provided employee list."""
    response = client.post(
        "/nfa/intelligence/run",
        json={
            "from_date": "01/01/2024",
            "to_date": "31/01/2024",
            "employees": [
                {"loja": "1595504", "cpf": "12345678901"},
                {"loja": "1595505", "cpf": "12345678902"},
            ],
            "headless": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify load_employees_from_file was NOT called
    mock_nfa_intelligence.load_employees_from_file.assert_not_called()
    mock_nfa_intelligence.run_batch.assert_called_once()


def test_nfa_intelligence_endpoint_missing_required_fields(client):
    """Test NFA Intelligence endpoint with missing required fields."""
    response = client.post(
        "/nfa/intelligence/run",
        json={
            "from_date": "01/01/2024",
            # Missing to_date
            "employees": "auto",
        },
    )

    assert response.status_code == 422  # Validation error


def test_nfa_intelligence_endpoint_no_employees_found(client, mock_nfa_intelligence):
    """Test NFA Intelligence endpoint when no employees are found."""
    mock_nfa_intelligence.load_employees_from_file = AsyncMock(return_value=[])

    response = client.post(
        "/nfa/intelligence/run",
        json={
            "from_date": "01/01/2024",
            "to_date": "31/01/2024",
            "employees": "auto",
        },
    )

    assert response.status_code == 400
    assert "No employees found" in response.json()["detail"]


def test_nfa_intelligence_endpoint_batch_failure(client, mock_nfa_intelligence):
    """Test NFA Intelligence endpoint when batch processing fails."""
    mock_nfa_intelligence.run_batch = AsyncMock(side_effect=Exception("Batch processing failed"))

    response = client.post(
        "/nfa/intelligence/run",
        json={
            "from_date": "01/01/2024",
            "to_date": "31/01/2024",
            "employees": "auto",
        },
    )

    assert response.status_code == 500
    assert "failed" in response.json()["detail"].lower()


def test_nfa_intelligence_endpoint_with_all_options(client, mock_nfa_intelligence):
    """Test NFA Intelligence endpoint with all optional parameters."""
    response = client.post(
        "/nfa/intelligence/run",
        json={
            "from_date": "01/01/2024",
            "to_date": "31/01/2024",
            "employees": [
                {"loja": "1595504", "cpf": "12345678901", "matricula": "1595504"},
            ],
            "headless": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify headless parameter was passed
    call_args = mock_nfa_intelligence.run_batch.call_args
    assert call_args[1]["headless"] is False


def test_nfa_intelligence_endpoint_partial_failure(client, mock_nfa_intelligence):
    """Test NFA Intelligence endpoint with partial batch failures."""
    mock_nfa_intelligence.run_batch = AsyncMock(
        return_value=[
            {
                "success": True,
                "employee": {"loja": "1595504", "cpf": "12345678901"},
                "nfa_count": 1,
                "timestamp": "2024-01-15T10:00:00",
            },
            {
                "success": False,
                "employee": {"loja": "1595505", "cpf": "12345678902"},
                "error": "Login failed",
                "error_classification": "authentication_error",
                "nfa_count": 0,
                "timestamp": "2024-01-15T10:01:00",
            },
        ]
    )

    # Mock report generation to return a real path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = Path(tmpdir) / "NFA_ATF_RUN_test.json"
        report_path.write_text(
            json.dumps(
                {
                    "metadata": {"from_date": "01/01/2024", "to_date": "31/01/2024"},
                    "summary": {
                        "total_items": 2,
                        "success_count": 1,
                        "failure_count": 1,
                        "success_rate": 50.0,
                        "total_nfas_found": 1,
                        "total_pdfs_downloaded": 2,
                        "error_classifications": {"authentication_error": 1},
                    },
                    "results": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        mock_nfa_intelligence.generate_report = AsyncMock(return_value=str(report_path))

        response = client.post(
            "/nfa/intelligence/run",
            json={
                "from_date": "01/01/2024",
                "to_date": "31/01/2024",
                "employees": "auto",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["summary"]["success_count"] == 1
        assert data["summary"]["failure_count"] == 1
        assert data["summary"]["success_rate"] == 50.0
