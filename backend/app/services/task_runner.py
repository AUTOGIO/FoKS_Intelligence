"""Task Runner - Coordinates task execution across systems.

⚠️ ARCHITECTURAL GUARDRAIL:
This module COORDINATES execution. Do NOT add execution logic here.
Do NOT own execution state. For automation tasks (nfa, redesim, browser),
ALWAYS delegate to FBP Backend via fbp_service. This is the control plane,
not the execution authority. Keep coordination separate from execution.
"""

from __future__ import annotations

import asyncio
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psutil
from app.config import settings
from app.services import fbp_service
from app.services.logging_utils import get_logger
from app.services.script_runner import run_local_script
from fastapi.concurrency import run_in_threadpool

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

logger = get_logger(__name__)


@dataclass
class TaskEnvelope:
    task: str
    success: bool
    duration_ms: int
    payload: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "payload": self.payload or {},
            "error": self.error,
        }


class TaskRunner:
    """Async task runner for FoKS/macOS automation."""

    async def run_task(
        self,
        task_type: str,
        args: dict[str, Any],
        *,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        task = (task_type or "").lower().replace("-", "_")
        timeout = timeout or settings.default_timeout_seconds

        if task in {"nfa", "redesim", "browser", "utils"}:
            return await self._delegate_to_fbp(task, args)

        handler = getattr(self, f"_task_{task}", None)
        if handler is None:
            return self._finalize(task, False, 0, error=f"Unsupported task '{task_type}'")

        start = time.perf_counter()
        try:
            result = await handler(args, timeout)
            duration = int((time.perf_counter() - start) * 1000)
            # Check if result indicates an error (for tasks that return error status in payload)
            if isinstance(result, dict) and result.get("status") == "error":
                # Return error result with payload containing error details
                return self._finalize(
                    task,
                    False,
                    duration,
                    payload=result,
                    error=result.get("message", "Task failed"),
                )
            return self._finalize(task, True, duration, payload=result)
        except Exception as exc:  # noqa: BLE001
            duration = int((time.perf_counter() - start) * 1000)
            return self._finalize(task, False, duration, error=str(exc))

    async def _delegate_to_fbp(self, task: str, args: dict[str, Any]) -> dict[str, Any]:
        start = time.perf_counter()
        try:
            if task == "nfa":
                result = await fbp_service.run_nfa(args)
            elif task == "redesim":
                result = await fbp_service.run_redesim(args)
            elif task == "browser":
                result = await fbp_service.run_browser_action(args)
            else:
                result = await fbp_service.run_utils(args)
            duration = int((time.perf_counter() - start) * 1000)
            return self._finalize(task, True, duration, payload=result)
        except Exception as exc:  # noqa: BLE001
            duration = int((time.perf_counter() - start) * 1000)
            return self._finalize(task, False, duration, error=str(exc))

    async def _task_run_shell(self, args: dict[str, Any], timeout: int) -> dict[str, Any]:
        command = args.get("cmd")
        if not command:
            raise ValueError("Missing 'cmd' argument")
        return await self._run_command(["/bin/zsh", "-c", command], timeout)

    async def _task_run_script(self, args: dict[str, Any], timeout: int) -> dict[str, Any]:
        path = args.get("path")
        if not path:
            raise ValueError("Missing 'path' argument")
        script = Path(path)
        if not script.exists():
            raise FileNotFoundError(f"Script not found: {path}")
        return await self._run_command(["/bin/bash", str(script)], timeout)

    async def _task_run_apple_script(self, args: dict[str, Any], timeout: int) -> dict[str, Any]:
        source = args.get("source")
        if not source:
            raise ValueError("Missing 'source' argument")
        return await self._run_command(["osascript", "-e", source], timeout)

    async def _task_run_shortcut(self, args: dict[str, Any], timeout: int) -> dict[str, Any]:
        name = args.get("name")
        if not name:
            raise ValueError("Missing 'name' argument")
        command = ["shortcuts", "run", name]
        if args.get("input"):
            command.extend(["--input", args["input"]])
        return await self._run_command(command, timeout)

    async def _task_run_keyboard_maestro_macro(
        self, args: dict[str, Any], timeout: int
    ) -> dict[str, Any]:
        macro_id = args.get("macro_id")
        if not macro_id:
            raise ValueError("Missing 'macro_id' argument")
        script = f'tell application "Keyboard Maestro Engine" to do script "{macro_id}"'
        return await self._run_command(["osascript", "-e", script], timeout)

    async def _task_open_url(self, args: dict[str, Any], timeout: int) -> dict[str, Any]:
        url = args.get("url")
        if not url:
            raise ValueError("Missing 'url' argument")
        return await self._run_command(["open", url], timeout)

    async def _task_open_app(self, args: dict[str, Any], timeout: int) -> dict[str, Any]:
        app = args.get("app")
        if not app:
            raise ValueError("Missing 'app' argument")
        if Path(app).exists():
            command = ["open", app]
        else:
            command = ["open", "-a", app]
        return await self._run_command(command, timeout)

    async def _task_notify(self, args: dict[str, Any], timeout: int) -> dict[str, Any]:
        title = self._sanitize(args.get("title", "FoKS Intelligence"))
        message = self._sanitize(args.get("message", ""))
        subtitle = self._sanitize(args.get("subtitle", ""))
        if not message:
            raise ValueError("Missing 'message' argument")
        script = f'display notification "{message}" with title "{title}"'
        if subtitle:
            script += f' subtitle "{subtitle}"'
        return await self._run_command(["osascript", "-e", script], timeout)

    async def _task_say(self, args: dict[str, Any], timeout: int) -> dict[str, Any]:
        text = args.get("text")
        if not text:
            raise ValueError("Missing 'text' argument")
        command = ["say", text]
        voice = args.get("voice")
        if voice:
            command.extend(["-v", voice])
        return await self._run_command(command, timeout)

    async def _task_system_status(self, args: dict[str, Any], timeout: int) -> dict[str, Any]:
        status = await asyncio.wait_for(run_in_threadpool(self._collect_system_status), timeout)
        return status

    async def _task_nfa_atf(self, args: dict[str, Any], timeout: int) -> dict[str, Any]:
        """
        Execute NFA ATF automation script using script_runner service.

        Args:
            args: Dictionary with from_date, to_date, matricula, output_dir, nfa_number, headless
            timeout: Maximum execution time in seconds (default: 900 for ATF)

        Returns:
            Dictionary with status, nfa_number, danfe_path, dar_path, logs, error details
        """
        # Validate required arguments
        from_date = args.get("from_date")
        to_date = args.get("to_date")
        if not from_date or not to_date:
            raise ValueError("Missing required arguments: 'from_date' and 'to_date'")

        # Prepare script arguments (only pass non-None values)
        # script_runner converts snake_case to kebab-case (from_date -> --from-date)
        script_args: dict[str, Any] = {
            "from_date": from_date,
            "to_date": to_date,
        }

        if args.get("matricula"):
            script_args["matricula"] = args["matricula"]
        if args.get("output_dir"):
            script_args["output_dir"] = args["output_dir"]
        if args.get("nfa_number"):
            script_args["nfa_number"] = args["nfa_number"]
        if args.get("max_nfas"):
            script_args["max_nfas"] = args["max_nfas"]
        # download_dar parameter is deprecated - both downloads always execute
        # Keeping for backward compatibility but not passing it to script
        # Only add headless if explicitly False (default is False for visual mode)
        if args.get("headless") is True:
            script_args["headless"] = True

        # Use 15 minutes (900s) timeout for ATF
        atf_timeout = 900

        logger.info(
            "Running NFA ATF script",
            extra={
                "payload": {
                    "script": "nfa_atf.py",
                    "args": script_args,
                    "timeout": atf_timeout,
                }
            },
        )

        # Execute script using script_runner service
        script_result = await run_local_script(
            script="nfa_atf.py",
            args=script_args,
            timeout=atf_timeout,
        )

        # Extract output (should be JSON dict from script)
        if isinstance(script_result.output, dict):
            result = script_result.output.copy()
        else:
            # Fallback: create error result if output is not JSON
            result = {
                "status": "error",
                "error_type": "invalid_output",
                "message": "Script output is not valid JSON",
                "context": {"raw_output": str(script_result.output)},
            }

        # Add logs from stderr
        result["logs"] = script_result.errors or script_result.stderr

        # If script exited with error but didn't return error status, mark as error
        if script_result.exit_code != 0 and result.get("status") != "error":
            result["status"] = "error"
            if "error_type" not in result:
                result["error_type"] = "script_error"
            if "message" not in result:
                result["message"] = script_result.errors or "Script exited with non-zero code"

        logger.info(
            "NFA ATF script execution completed",
            extra={
                "payload": {
                    "status": result.get("status"),
                    "exit_code": script_result.exit_code,
                    "has_danfe": bool(result.get("danfe_path")),
                    "has_dar": bool(result.get("dar_path")),
                }
            },
        )

        return result

    async def _run_command(
        self,
        command: list[str],
        timeout: int,
        input_data: str | None = None,
    ) -> dict[str, Any]:
        start = time.perf_counter()
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE if input_data else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input_data.encode() if input_data else None),
                timeout=timeout,
            )
        except TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise TimeoutError(f"Command timed out after {timeout}s") from exc

        duration = int((time.perf_counter() - start) * 1000)
        payload = {
            "command": " ".join(shlex.quote(part) for part in command),
            "returncode": process.returncode,
            "stdout": (stdout or b"").decode().strip(),
            "stderr": (stderr or b"").decode().strip(),
        }
        if process.returncode != 0:
            raise RuntimeError(payload["stderr"] or "Command failed")
        payload["elapsed_ms"] = duration
        return payload

    def _collect_system_status(self) -> dict[str, Any]:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        virtual_memory = psutil.virtual_memory()
        disk_usage = psutil.disk_usage("/")
        temps = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": virtual_memory.percent,
            "memory_available": virtual_memory.available,
            "disk_percent": disk_usage.percent,
            "load_avg": psutil.getloadavg(),
            "temperatures": {k: [t.current for t in v] for k, v in temps.items()},
        }

    def _finalize(
        self,
        task: str,
        success: bool,
        duration_ms: int,
        *,
        payload: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        envelope = TaskEnvelope(
            task=task,
            success=success,
            duration_ms=duration_ms,
            payload=payload,
            error=error,
        ).to_dict()
        log_method = logger.info if success else logger.warning
        log_method("Task completed", extra={"payload": envelope})
        return envelope

    @staticmethod
    def _sanitize(value: str) -> str:
        return value.replace('"', '\\"')
