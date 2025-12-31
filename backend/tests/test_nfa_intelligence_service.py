"""Tests for NFA Intelligence Service."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.nfa_intelligence import NFAIntelligenceService


@pytest.fixture
def nfa_service():
    """Create NFA Intelligence Service instance."""
    return NFAIntelligenceService()


@pytest.fixture
def mock_task_runner():
    """Create mock TaskRunner."""
    mock = AsyncMock()
    return mock


@pytest.mark.asyncio
async def test_run_batch_success(nfa_service, mock_task_runner):
    """Test successful batch processing."""
    nfa_service.task_runner = mock_task_runner

    # Mock successful task results
    mock_task_runner.run_task = AsyncMock(
        side_effect=[
            {
                "success": True,
                "duration_ms": 5000,
                "payload": {
                    "status": "success",
                    "nfa_number": "900501884",
                    "danfe_path": "/path/to/DANFE.pdf",
                    "dar_path": "/path/to/DAR.pdf",
                },
            },
            {
                "success": True,
                "duration_ms": 4500,
                "payload": {
                    "status": "success",
                    "nfa_number": "900501885",
                    "danfe_path": "/path/to/DANFE2.pdf",
                    "dar_path": "/path/to/DAR2.pdf",
                },
            },
        ]
    )

    items_list = [
        {"loja": "1595504", "cpf": "12345678901"},
        {"loja": "1595505", "cpf": "12345678902"},
    ]

    results = await nfa_service.run_batch(
        items_list=items_list,
        from_date="01/01/2024",
        to_date="31/01/2024",
        headless=True,
    )

    assert len(results) == 2
    assert all(r["success"] for r in results)
    assert results[0]["nfa_count"] == 1
    assert results[1]["nfa_count"] == 1
    assert len(results[0]["pdfs"]) == 2  # DANFE + DAR
    assert len(results[1]["pdfs"]) == 2


@pytest.mark.asyncio
async def test_run_batch_partial_failure(nfa_service, mock_task_runner):
    """Test batch processing with partial failures."""
    nfa_service.task_runner = mock_task_runner

    # Mock mixed results
    mock_task_runner.run_task = AsyncMock(
        side_effect=[
            {
                "success": True,
                "duration_ms": 5000,
                "payload": {
                    "status": "success",
                    "nfa_number": "900501884",
                    "danfe_path": "/path/to/DANFE.pdf",
                    "dar_path": "/path/to/DAR.pdf",
                },
            },
            Exception("Login failed"),
            {
                "success": False,
                "duration_ms": 2000,
                "error": "Timeout error",
            },
        ]
    )

    items_list = [
        {"loja": "1595504", "cpf": "12345678901"},
        {"loja": "1595505", "cpf": "12345678902"},
        {"loja": "1595506", "cpf": "12345678903"},
    ]

    results = await nfa_service.run_batch(
        items_list=items_list,
        from_date="01/01/2024",
        to_date="31/01/2024",
    )

    assert len(results) == 3
    assert results[0]["success"] is True
    assert results[1]["success"] is False
    assert results[2]["success"] is False
    assert "error" in results[1]
    assert "error" in results[2]


@pytest.mark.asyncio
async def test_run_batch_zero_nfas(nfa_service, mock_task_runner):
    """Test batch processing when no NFAs are found."""
    nfa_service.task_runner = mock_task_runner

    # Mock result with no NFA
    mock_task_runner.run_task = AsyncMock(
        return_value={
            "success": True,
            "duration_ms": 3000,
            "payload": {
                "status": "success",
                "nfa_number": None,
                "danfe_path": "",
                "dar_path": "",
            },
        }
    )

    items_list = [{"loja": "1595504", "cpf": "12345678901"}]

    results = await nfa_service.run_batch(
        items_list=items_list,
        from_date="01/01/2024",
        to_date="31/01/2024",
    )

    assert len(results) == 1
    assert results[0]["success"] is True
    assert results[0]["nfa_count"] == 0
    assert len(results[0]["pdfs"]) == 0


@pytest.mark.asyncio
async def test_normalize_result_success(nfa_service):
    """Test result normalization for success case."""
    result_dict = {
        "success": True,
        "duration_ms": 5000,
        "payload": {
            "status": "success",
            "nfa_number": "900501884",
            "danfe_path": "/path/to/DANFE.pdf",
            "dar_path": "/path/to/DAR.pdf",
        },
    }

    normalized = await nfa_service.normalize_result(
        result_dict, employee_data={"loja": "1595504", "cpf": "12345678901"}
    )

    assert normalized["success"] is True
    assert normalized["nfa_count"] == 1
    assert normalized["nfa_number"] == "900501884"
    assert len(normalized["pdfs"]) == 2
    assert normalized["employee"]["loja"] == "1595504"
    assert "timestamp" in normalized


@pytest.mark.asyncio
async def test_normalize_result_error(nfa_service):
    """Test result normalization for error case."""
    result_dict = {
        "success": False,
        "duration_ms": 2000,
        "error": "Login failed: Invalid credentials",
    }

    normalized = await nfa_service.normalize_result(
        result_dict, employee_data={"loja": "1595504", "cpf": "12345678901"}
    )

    assert normalized["success"] is False
    assert normalized["nfa_count"] == 0
    assert "error" in normalized
    assert normalized["error_classification"] == "authentication_error"


@pytest.mark.asyncio
async def test_generate_report(nfa_service, tmp_path):
    """Test report generation."""
    from app.services.nfa_intelligence import REPORTS_DIR

    # Temporarily override reports directory
    original_reports_dir = REPORTS_DIR
    with patch("app.services.nfa_intelligence.REPORTS_DIR", tmp_path):
        batch_results = [
            {
                "success": True,
                "employee": {"loja": "1595504", "cpf": "12345678901"},
                "nfa_count": 1,
                "nfa_number": "900501884",
                "pdfs": [
                    {"type": "DANFE", "path": "/path/to/DANFE.pdf"},
                    {"type": "DAR", "path": "/path/to/DAR.pdf"},
                ],
                "timestamp": datetime.now().isoformat(),
            },
            {
                "success": False,
                "employee": {"loja": "1595505", "cpf": "12345678902"},
                "error": "Login failed",
                "error_classification": "authentication_error",
                "nfa_count": 0,
                "pdfs": [],
                "timestamp": datetime.now().isoformat(),
            },
        ]

        report_path = await nfa_service.generate_report(
            batch_results=batch_results,
            from_date="01/01/2024",
            to_date="31/01/2024",
        )

        assert Path(report_path).exists()

        with open(report_path, "r", encoding="utf-8") as f:
            report_data = json.load(f)

        assert report_data["metadata"]["from_date"] == "01/01/2024"
        assert report_data["summary"]["total_items"] == 2
        assert report_data["summary"]["success_count"] == 1
        assert report_data["summary"]["failure_count"] == 1
        assert report_data["summary"]["total_nfas_found"] == 1
        assert "authentication_error" in report_data["summary"]["error_classifications"]


@pytest.mark.asyncio
async def test_load_employees_from_file_json(nfa_service, tmp_path):
    """Test loading employees from JSON file."""
    json_file = tmp_path / "data_input_final.json"
    json_file.write_text(
        json.dumps(
            [
                {"loja": "1595504", "cpf": "12345678901"},
                {"loja": "1595505", "cpf": "12345678902"},
            ],
            indent=2,
        ),
        encoding="utf-8",
    )

    employees = await nfa_service.load_employees_from_file(str(json_file))

    assert len(employees) == 2
    assert employees[0]["loja"] == "1595504"
    assert employees[1]["cpf"] == "12345678902"


@pytest.mark.asyncio
async def test_load_employees_from_file_csv(nfa_service, tmp_path):
    """Test loading employees from CSV file."""
    csv_file = tmp_path / "data_input_final.csv"
    csv_file.write_text(
        "loja,cpf,matricula\n1595504,12345678901,1595504\n1595505,12345678902,1595505",
        encoding="utf-8",
    )

    employees = await nfa_service.load_employees_from_file(str(csv_file))

    assert len(employees) == 2
    assert employees[0]["loja"] == "1595504"
    assert employees[0]["matricula"] == "1595504"


@pytest.mark.asyncio
async def test_load_employees_from_file_not_found(nfa_service):
    """Test loading employees from non-existent file."""
    employees = await nfa_service.load_employees_from_file("/nonexistent/path")

    assert employees == []


@pytest.mark.asyncio
async def test_error_classification(nfa_service):
    """Test error classification."""
    assert nfa_service._classify_error(Exception("Login failed")) == "authentication_error"
    assert nfa_service._classify_error(Exception("Timeout error")) == "timeout_error"
    assert nfa_service._classify_error(Exception("Element not found")) == "not_found_error"
    assert nfa_service._classify_error(Exception("Download failed")) == "download_error"
    assert nfa_service._classify_error(Exception("Network error")) == "network_error"
    assert nfa_service._classify_error(Exception("Unknown error")) == "unknown_error"
