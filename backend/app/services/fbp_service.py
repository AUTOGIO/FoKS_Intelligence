"""FBP Service - Coordinates and delegates execution to FBP Backend.

⚠️ ARCHITECTURAL GUARDRAIL:
This module COORDINATES execution. Do NOT add execution logic here.
Do NOT own execution state. Do NOT implement browser automation or form filling.
Delegate ALL execution to FBP Backend via FBPClient. This is the control plane,
not the execution authority.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.fbp_client import FBPClient
from app.services.logging_utils import get_logger
from fastapi.concurrency import run_in_threadpool

_CLIENT = FBPClient()
logger = get_logger(__name__)

# Obsidian log directory
OBSIDIAN_LOG_DIR = Path.home() / "Obsidian" / "Business" / "NFA_Log"


def _write_obsidian_log(
    cpf: str,
    success: bool,
    message: str,
    timestamp: str,
) -> None:
    """
    Write NFA log entry to Obsidian (synchronous, runs in threadpool).

    Args:
        cpf: CPF that was processed
        success: Whether the NFA operation succeeded
        message: Message from FBP response
        timestamp: ISO timestamp string
    """
    try:
        # Ensure log directory exists
        OBSIDIAN_LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Generate filename: YYYY-MM-DD.md
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = OBSIDIAN_LOG_DIR / f"{date_str}.md"

        # Format log entry
        status = "✅ SUCCESS" if success else "❌ FAILURE"
        log_entry = (
            f"\n## {timestamp}\n\n"
            f"- **CPF**: `{cpf}`\n"
            f"- **Status**: {status}\n"
            f"- **Message**: {message}\n\n---\n"
        )

        # Append to file (create if doesn't exist)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)

        logger.debug(
            "Obsidian log written",
            extra={
                "payload": {
                    "log_file": str(log_file),
                    "cpf_length": len(cpf),
                    "success": success,
                }
            },
        )
    except Exception as exc:  # noqa: BLE001
        # Never let logging block automation
        logger.warning(
            "Failed to write Obsidian log",
            exc_info=True,
            extra={
                "payload": {
                    "error_type": type(exc).__name__,
                    "log_dir": str(OBSIDIAN_LOG_DIR),
                }
            },
        )


async def run_health_check() -> dict[str, Any]:
    return await _CLIENT.health()


async def run_nfa(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Run NFA automation and log to Obsidian.

    Args:
        payload: NFA request payload with 'cpf' and optional 'test' flag

    Returns:
        FBP response dictionary
    """
    # Extract CPF for logging
    cpf = payload.get("cpf", "unknown")
    timestamp = datetime.now().isoformat()

    # Execute FBP NFA request
    result = await _CLIENT.nfa(payload)

    # Extract success status and message from FBP response
    fbp_status = result.get("status", 0)
    fbp_payload = result.get("payload", {})
    success = fbp_status == 200 or fbp_payload.get("success", False)
    message = fbp_payload.get("message") or fbp_payload.get("error") or "NFA operation completed"

    # Write to Obsidian log (non-blocking, wrapped in try/except)
    try:
        await run_in_threadpool(
            _write_obsidian_log,
            cpf=cpf,
            success=success,
            message=message,
            timestamp=timestamp,
        )
    except Exception as exc:  # noqa: BLE001
        # Logging failure should never block automation
        logger.warning(
            "Obsidian log write failed (non-blocking)",
            exc_info=True,
            extra={
                "payload": {
                    "error_type": type(exc).__name__,
                }
            },
        )

    return result


async def run_redesim(payload: dict[str, Any]) -> dict[str, Any]:
    return await _CLIENT.redesim(payload)


async def run_browser_action(payload: dict[str, Any]) -> dict[str, Any]:
    return await _CLIENT.browser(payload)


async def run_utils(payload: dict[str, Any]) -> dict[str, Any]:
    return await _CLIENT.utils(payload)
