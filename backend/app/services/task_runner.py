from __future__ import annotations

import asyncio
import shlex
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.services import fbp_service
from app.services.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class TaskEnvelope:
    task: str
    success: bool
    duration_ms: int
    payload: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
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
        args: Dict[str, Any],
        *,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        task = (task_type or "").lower()
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
            return self._finalize(task, True, duration, payload=result)
        except Exception as exc:  # noqa: BLE001
            duration = int((time.perf_counter() - start) * 1000)
            return self._finalize(task, False, duration, error=str(exc))

    async def _delegate_to_fbp(self, task: str, args: Dict[str, Any]) -> Dict[str, Any]:
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

    async def _task_run_shell(self, args: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        command = args.get("cmd")
        if not command:
            raise ValueError("Missing 'cmd' argument")
        return await self._run_command(["/bin/zsh", "-c", command], timeout)

    async def _task_run_script(self, args: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        path = args.get("path")
        if not path:
            raise ValueError("Missing 'path' argument")
        script = Path(path)
        if not script.exists():
            raise FileNotFoundError(f"Script not found: {path}")
        return await self._run_command(["/bin/bash", str(script)], timeout)

    async def _task_run_apple_script(self, args: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        source = args.get("source")
        if not source:
            raise ValueError("Missing 'source' argument")
        return await self._run_command(["osascript", "-e", source], timeout)

    async def _task_run_shortcut(self, args: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        name = args.get("name")
        if not name:
            raise ValueError("Missing 'name' argument")
        command = ["shortcuts", "run", name]
        if args.get("input"):
            command.extend(["--input", args["input"]])
        return await self._run_command(command, timeout)

    async def _task_run_keyboard_maestro_macro(self, args: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        macro_id = args.get("macro_id")
        if not macro_id:
            raise ValueError("Missing 'macro_id' argument")
        script = f'tell application "Keyboard Maestro Engine" to do script "{macro_id}"'
        return await self._run_command(["osascript", "-e", script], timeout)

    async def _task_open_url(self, args: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        url = args.get("url")
        if not url:
            raise ValueError("Missing 'url' argument")
        return await self._run_command(["open", url], timeout)

    async def _task_open_app(self, args: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        app = args.get("app")
        if not app:
            raise ValueError("Missing 'app' argument")
        if Path(app).exists():
            command = ["open", app]
        else:
            command = ["open", "-a", app]
        return await self._run_command(command, timeout)

    async def _task_notify(self, args: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        title = self._sanitize(args.get("title", "FoKS Intelligence"))
        message = self._sanitize(args.get("message", ""))
        subtitle = self._sanitize(args.get("subtitle", ""))
        if not message:
            raise ValueError("Missing 'message' argument")
        script = f'display notification "{message}" with title "{title}"'
        if subtitle:
            script += f' subtitle "{subtitle}"'
        return await self._run_command(["osascript", "-e", script], timeout)

    async def _task_say(self, args: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        text = args.get("text")
        if not text:
            raise ValueError("Missing 'text' argument")
        command = ["say", text]
        voice = args.get("voice")
        if voice:
            command.extend(["-v", voice])
        return await self._run_command(command, timeout)

    async def _task_system_status(self, args: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        status = await asyncio.wait_for(run_in_threadpool(self._collect_system_status), timeout)
        return status

    async def _run_command(
        self,
        command: List[str],
        timeout: int,
        input_data: Optional[str] = None,
    ) -> Dict[str, Any]:
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
        except asyncio.TimeoutError as exc:
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

    def _collect_system_status(self) -> Dict[str, Any]:
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
        payload: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
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

