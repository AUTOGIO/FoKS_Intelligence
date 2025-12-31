"""Tests for NFA ATF TaskRunner integration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.task_runner import TaskRunner


@pytest.mark.asyncio
async def test_nfa_atf_task_success(monkeypatch):
    """Test successful NFA ATF task execution - both downloads always execute."""
    runner = TaskRunner()

    # Mock script output - both DANFE and Taxa Serviço are always downloaded
    mock_stdout = json.dumps({
        "status": "success",
        "nfa_number": "900501884",
        "danfe_path": "/Users/dnigga/Downloads/NFA_Outputs/NFA_900501884_DANFE.pdf",
        "dar_path": "/Users/dnigga/Downloads/NFA_Outputs/NFA_900501884_TAXA_SERVICO.pdf",
    })

    async def fake_run_command(self, command, timeout, input_data=None):
        return {
            "command": " ".join(command),
            "returncode": 0,
            "stdout": mock_stdout,
            "stderr": "",
            "elapsed_ms": 5000,
        }

    monkeypatch.setattr(TaskRunner, "_run_command", fake_run_command)

    args = {
        "from_date": "01/01/2024",
        "to_date": "31/01/2024",
        "matricula": "1595504",
    }

    result = await runner.run_task("nfa_atf", args, timeout=600)

    assert result["success"] is True
    assert result["task"] == "nfa_atf"
    assert result["payload"]["status"] == "success"
    assert result["payload"]["nfa_number"] == "900501884"
    # Both downloads always execute in sequence
    assert "DANFE.pdf" in result["payload"]["danfe_path"]
    assert "TAXA_SERVICO.pdf" in result["payload"]["dar_path"]


@pytest.mark.asyncio
async def test_nfa_atf_task_missing_args():
    """Test NFA ATF task with missing required arguments."""
    runner = TaskRunner()

    args = {
        "from_date": "01/01/2024",
        # Missing to_date
    }

    result = await runner.run_task("nfa_atf", args, timeout=600)

    assert result["success"] is False
    assert "Missing required arguments" in result["error"]


@pytest.mark.asyncio
async def test_nfa_atf_task_script_error(monkeypatch):
    """Test NFA ATF task when script returns error status."""
    runner = TaskRunner()

    mock_stdout = json.dumps({
        "status": "error",
        "error": "Login failed: Invalid credentials",
        "nfa_number": None,
        "danfe_path": None,
        "dar_path": None,
    })

    async def fake_run_command(self, command, timeout, input_data=None):
        return {
            "command": " ".join(command),
            "returncode": 0,
            "stdout": mock_stdout,
            "stderr": "",
            "elapsed_ms": 2000,
        }

    monkeypatch.setattr(TaskRunner, "_run_command", fake_run_command)

    args = {
        "from_date": "01/01/2024",
        "to_date": "31/01/2024",
    }

    result = await runner.run_task("nfa_atf", args, timeout=600)

    assert result["success"] is False
    assert "NFA ATF automation failed" in result["error"]
    assert "Invalid credentials" in result["error"]


@pytest.mark.asyncio
async def test_nfa_atf_task_invalid_json(monkeypatch):
    """Test NFA ATF task when script output is not valid JSON."""
    runner = TaskRunner()

    async def fake_run_command(self, command, timeout, input_data=None):
        return {
            "command": " ".join(command),
            "returncode": 0,
            "stdout": "Some log output\nNo JSON here\n",
            "stderr": "",
            "elapsed_ms": 1000,
        }

    monkeypatch.setattr(TaskRunner, "_run_command", fake_run_command)

    args = {
        "from_date": "01/01/2024",
        "to_date": "31/01/2024",
    }

    result = await runner.run_task("nfa_atf", args, timeout=600)

    assert result["success"] is False
    assert "Failed to parse script output" in result["error"]


@pytest.mark.asyncio
async def test_nfa_atf_task_with_optional_args(monkeypatch):
    """Test NFA ATF task with all optional arguments."""
    runner = TaskRunner()

    mock_stdout = json.dumps({
        "status": "success",
        "nfa_number": "900501884",
        "danfe_path": "/custom/path/NFA_900501884_DANFE.pdf",
        "dar_path": "/custom/path/NFA_900501884_TAXA_SERVICO.pdf",
    })

    async def fake_run_command(self, command, timeout, input_data=None):
        # Verify command includes optional args
        command_str = " ".join(command)
        assert "--matricula" in command_str
        assert "--output-dir" in command_str
        assert "--nfa-number" in command_str
        assert "--headless" in command_str

        return {
            "command": command_str,
            "returncode": 0,
            "stdout": mock_stdout,
            "stderr": "",
            "elapsed_ms": 5000,
        }

    monkeypatch.setattr(TaskRunner, "_run_command", fake_run_command)

    args = {
        "from_date": "01/01/2024",
        "to_date": "31/01/2024",
        "matricula": "1595504",
        "output_dir": "/custom/path",
        "nfa_number": "900501884",
        "headless": True,
    }

    result = await runner.run_task("nfa_atf", args, timeout=600)

    assert result["success"] is True
    assert result["payload"]["status"] == "success"


@pytest.mark.asyncio
async def test_nfa_atf_task_timeout(monkeypatch):
    """Test NFA ATF task timeout handling."""
    runner = TaskRunner()

    async def fake_run_command(self, command, timeout, input_data=None):
        raise TimeoutError("Command timed out after 600s")

    monkeypatch.setattr(TaskRunner, "_run_command", fake_run_command)

    args = {
        "from_date": "01/01/2024",
        "to_date": "31/01/2024",
    }

    result = await runner.run_task("nfa_atf", args, timeout=600)

    assert result["success"] is False
    assert "timed out" in result["error"].lower()

