"""Tests for TaskRunner service."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services import task_runner
from app.services.task_runner import TaskRunner


@pytest.mark.asyncio
async def test_run_shell_success(monkeypatch):
    runner = TaskRunner()

    async def fake_run_command(self, command, timeout, input_data=None):
        return {"stdout": "ok", "stderr": "", "returncode": 0}

    monkeypatch.setattr(TaskRunner, "_run_command", fake_run_command)
    result = await runner.run_task("run_shell", {"cmd": "echo 1"})
    assert result["success"] is True
    assert result["task"] == "run_shell"


@pytest.mark.asyncio
async def test_run_shell_missing_cmd():
    runner = TaskRunner()
    result = await runner.run_task("run_shell", {})
    assert result["success"] is False
    assert "Missing" in result["error"]


@pytest.mark.asyncio
async def test_delegate_nfa(monkeypatch):
    runner = TaskRunner()
    monkeypatch.setattr(task_runner.fbp_service, "run_nfa", AsyncMock(return_value={"provider": "fbp"}))
    result = await runner.run_task("nfa", {"job": "123"})
    task_runner.fbp_service.run_nfa.assert_awaited()
    assert result["payload"]["provider"] == "fbp"


@pytest.mark.asyncio
async def test_run_command_timeout(monkeypatch):
    runner = TaskRunner()

    async def fake_run_command(*_, **__):
        raise TimeoutError("boom")

    monkeypatch.setattr(TaskRunner, "_run_command", fake_run_command)
    result = await runner.run_task("open_url", {"url": "https://example.com"})
    assert result["success"] is False
    assert "boom" in result["error"]


@pytest.mark.asyncio
async def test_system_status(monkeypatch):
    runner = TaskRunner()
    result = await runner.run_task("system_status", {})
    assert result["success"] is True
    assert "cpu_percent" in result["payload"]


@pytest.mark.asyncio
async def test_unknown_task():
    runner = TaskRunner()
    result = await runner.run_task("does_not_exist", {})
    assert result["success"] is False
    assert result["task"] == "does_not_exist"
