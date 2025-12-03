from __future__ import annotations

import subprocess
from typing import Any, Dict

from app.services.logging_utils import get_logger

logger = get_logger(__name__)


class TaskRunner:
    """Executes local macOS automations in a controlled way."""

    def run(self, task_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch the requested task and return a normalized result."""
        logger.info("Running task", extra={"task_name": task_name, "params": params})
        try:
            handler = getattr(self, f"_handle_{task_name}", None)
            if not handler:
                raise ValueError(f"Tarefa não suportada: {task_name}")

            data = handler(params)
            return {"success": True, "message": "Tarefa executada", "data": data}
        except Exception as exc:  # noqa: BLE001
            logger.error("Task execution failed", exc_info=True)
            return {
                "success": False,
                "message": str(exc),
                "data": {"task_name": task_name},
            }

    def _handle_open_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = params.get("url")
        if not url:
            raise ValueError("Parâmetro 'url' é obrigatório para open_url.")
        subprocess.run(["open", url], check=True)
        return {"opened": url}

    def _handle_run_script(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params.get("path")
        if not path:
            raise ValueError("Parâmetro 'path' é obrigatório para run_script.")
        subprocess.run(["/bin/bash", path], check=True)
        return {"script": path}

    def _handle_say(self, params: Dict[str, Any]) -> Dict[str, Any]:
        text = params.get("text") or "FoKS Intelligence pronto."
        voice = params.get("voice")
        command = ["say"]
        if voice:
            command.extend(["-v", voice])
        command.append(text)
        subprocess.run(command, check=True)
        return {"text_spoken": text, "voice": voice}
from __future__ import annotations

import base64
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

from app.services.logging_utils import get_logger

logger = get_logger("task_runner")


class TaskRunner:
    """
    Automation layer for FoKS Intelligence.
    Handles macOS-specific tasks and integrations.
    """

    def run(self, task_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Running task '%s' with params: %s", task_name, params)

        task_map = {
            "open_url": self._open_url,
            "run_script": self._run_script,
            "say": self._say,
            "notification": self._notification,
            "get_clipboard": self._get_clipboard,
            "set_clipboard": self._set_clipboard,
            "screenshot": self._screenshot,
            "open_app": self._open_app,
        }

        task_func = task_map.get(task_name)
        if task_func:
            return task_func(params)

        return {
            "success": False,
            "message": f"Unknown task: {task_name}",
            "data": {},
        }

    def _open_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = params.get("url")
        if not url:
            return {"success": False, "message": "Missing 'url' parameter", "data": {}}

        try:
            subprocess.run(["open", url], check=False)
            return {"success": True, "message": f"Opened URL: {url}", "data": {}}
        except Exception as exc:  # noqa: BLE001
            logger.error("Error opening URL: %s", exc)
            return {"success": False, "message": str(exc), "data": {}}

    def _run_script(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params.get("path")
        if not path:
            return {"success": False, "message": "Missing 'path' parameter", "data": {}}

        try:
            subprocess.run(["/bin/bash", path], check=False)
            return {"success": True, "message": f"Executed script: {path}", "data": {}}
        except Exception as exc:  # noqa: BLE001
            logger.error("Error running script: %s", exc)
            return {"success": False, "message": str(exc), "data": {}}

    def _say(self, params: Dict[str, Any]) -> Dict[str, Any]:
        text = params.get("text")
        if not text:
            return {"success": False, "message": "Missing 'text' parameter", "data": {}}

        try:
            subprocess.run(["say", text], check=False)
            return {"success": True, "message": "Spoken text via macOS 'say'", "data": {}}
        except Exception as exc:  # noqa: BLE001
            logger.error("Error running 'say': %s", exc)
            return {"success": False, "message": str(exc), "data": {}}

    def _notification(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send macOS notification using osascript."""
        title = params.get("title", "FoKS Intelligence")
        message = params.get("message", "")
        subtitle = params.get("subtitle", "")

        if not message:
            return {"success": False, "message": "Missing 'message' parameter", "data": {}}

        try:
            script = f'''
            display notification "{message}" with title "{title}"'''
            if subtitle:
                script += f' subtitle "{subtitle}"'

            subprocess.run(
                ["osascript", "-e", script],
                check=False,
                capture_output=True,
            )
            return {"success": True, "message": "Notification sent", "data": {}}
        except Exception as exc:  # noqa: BLE001
            logger.error("Error sending notification: %s", exc)
            return {"success": False, "message": str(exc), "data": {}}

    def _get_clipboard(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get clipboard content."""
        try:
            result = subprocess.run(
                ["pbpaste"],
                capture_output=True,
                text=True,
                check=False,
            )
            clipboard_text = result.stdout
            return {
                "success": True,
                "message": "Clipboard content retrieved",
                "data": {"content": clipboard_text},
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("Error getting clipboard: %s", exc)
            return {"success": False, "message": str(exc), "data": {}}

    def _set_clipboard(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set clipboard content."""
        text = params.get("text")
        if not text:
            return {"success": False, "message": "Missing 'text' parameter", "data": {}}

        try:
            subprocess.run(
                ["pbcopy"],
                input=text,
                text=True,
                check=False,
            )
            return {"success": True, "message": "Clipboard content set", "data": {}}
        except Exception as exc:  # noqa: BLE001
            logger.error("Error setting clipboard: %s", exc)
            return {"success": False, "message": str(exc), "data": {}}

    def _screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Take screenshot and return base64 encoded image."""
        screenshot_type = params.get("type", "full")  # full, window, selection
        output_format = params.get("format", "png")

        try:
            with tempfile.NamedTemporaryFile(suffix=f".{output_format}", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            # macOS screenshot command
            if screenshot_type == "full":
                subprocess.run(["screencapture", "-x", tmp_path], check=False)
            elif screenshot_type == "window":
                subprocess.run(["screencapture", "-x", "-w", tmp_path], check=False)
            elif screenshot_type == "selection":
                subprocess.run(["screencapture", "-x", "-i", tmp_path], check=False)
            else:
                return {
                    "success": False,
                    "message": f"Invalid screenshot type: {screenshot_type}",
                    "data": {},
                }

            # Read and encode to base64
            with open(tmp_path, "rb") as f:
                image_data = f.read()
                image_base64 = base64.b64encode(image_data).decode("utf-8")

            # Cleanup
            Path(tmp_path).unlink(missing_ok=True)

            return {
                "success": True,
                "message": f"Screenshot taken ({screenshot_type})",
                "data": {
                    "image_base64": image_base64,
                    "format": output_format,
                    "size_bytes": len(image_data),
                },
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("Error taking screenshot: %s", exc)
            return {"success": False, "message": str(exc), "data": {}}

    def _open_app(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Open macOS application."""
        app_name = params.get("app")
        if not app_name:
            return {"success": False, "message": "Missing 'app' parameter", "data": {}}

        try:
            subprocess.run(["open", "-a", app_name], check=False)
            return {"success": True, "message": f"Opened app: {app_name}", "data": {}}
        except Exception as exc:  # noqa: BLE001
            logger.error("Error opening app: %s", exc)
            return {"success": False, "message": str(exc), "data": {}}

