"""FBP diagnostics service for comprehensive readiness checks."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.fbp_client import FBPClient, FBPClientError
from app.services.logging_utils import get_logger

logger = get_logger(__name__)


async def run_fbp_diagnostics() -> dict[str, Any]:
    """
    Run comprehensive FBP diagnostics.
    
    Checks:
    1. Socket exists and is accessible
    2. FBP version/health information
    3. Simple ping task via health endpoint
    
    Returns:
        Dictionary with diagnostic results:
        - socket_check: dict with exists, is_socket, accessible
        - version_check: dict with version info or error
        - ping_check: dict with ping result or error
        - overall_status: "READY" or "BLOCKED"
    """
    logger.info("FBP diagnostics requested")

    diagnostics = {
        "socket_check": _check_socket(),
        "version_check": {},
        "ping_check": {},
        "overall_status": "BLOCKED",
    }

    # Early exit if socket does not exist (avoid unnecessary 5+ second timeouts)
    if not diagnostics["socket_check"]["exists"]:
        logger.info(
            "FBP diagnostics early exit — socket missing",
            extra={"payload": diagnostics["socket_check"]},
        )
        diagnostics["overall_status"] = "BLOCKED"
        return diagnostics

    # Version check (via health endpoint)
    try:
        client = FBPClient()
        health_result = await client.health()
        await client.close()

        diagnostics["version_check"] = {
            "success": True,
            "status": health_result.get("status", 0),
            "data": health_result.get("payload", {}),
        }

        # Extract version info if available
        payload = health_result.get("payload", {})
        diagnostics["version_check"]["version"] = payload.get("version", "unknown")
        diagnostics["version_check"]["machine"] = payload.get("machine", "unknown")
        diagnostics["version_check"]["project"] = payload.get("project", "unknown")

    except FBPClientError as exc:
        logger.warning(
            "FBP version check failed",
            exc_info=True,
            extra={
                "payload": {
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            },
        )
        diagnostics["version_check"] = {
            "success": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "FBP version check error",
            exc_info=True,
            extra={
                "payload": {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            },
        )
        diagnostics["version_check"] = {
            "success": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
        }

    # Ping check (simple health ping with timeout)
    try:
        client = FBPClient()
        # Use asyncio.wait_for to enforce 2 second timeout for ping
        ping_result = await asyncio.wait_for(
            client.health(),
            timeout=2.0,
        )
        await client.close()

        diagnostics["ping_check"] = {
            "success": True,
            "status": ping_result.get("status", 0),
            "response_time_ms": ping_result.get("duration_ms", 0),
            "data": ping_result.get("payload", {}),
        }

    except TimeoutError:
        logger.warning(
            "FBP ping check timed out",
            extra={
                "payload": {
                    "timeout_seconds": 2.0,
                }
            },
        )
        diagnostics["ping_check"] = {
            "success": False,
            "error": "Ping timed out after 2 seconds",
            "error_type": "TimeoutError",
        }
    except FBPClientError as exc:
        logger.warning(
            "FBP ping check failed",
            exc_info=True,
            extra={
                "payload": {
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            },
        )
        diagnostics["ping_check"] = {
            "success": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "FBP ping check error",
            exc_info=True,
            extra={
                "payload": {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            },
        )
        diagnostics["ping_check"] = {
            "success": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
        }

    # Determine overall status
    socket_ok = diagnostics["socket_check"]["exists"] and diagnostics["socket_check"]["is_socket"]
    version_ok = diagnostics["version_check"].get("success", False)
    ping_ok = diagnostics["ping_check"].get("success", False)

    if socket_ok and version_ok and ping_ok:
        diagnostics["overall_status"] = "READY"
    else:
        diagnostics["overall_status"] = "BLOCKED"

    logger.info(
        "FBP diagnostics completed",
        extra={
            "payload": {
                "overall_status": diagnostics["overall_status"],
                "socket_ok": socket_ok,
                "version_ok": version_ok,
                "ping_ok": ping_ok,
            }
        },
    )

    return diagnostics


def _check_socket() -> dict[str, Any]:
    """
    Check if FBP socket exists and is accessible.
    
    Returns:
        Dictionary with:
        - exists: bool
        - is_socket: bool
        - accessible: bool (read/write permissions)
        - path: str
    """
    socket_path_str = settings.fbp_socket_path
    socket_path = Path(socket_path_str)

    check_result = {
        "exists": False,
        "is_socket": False,
        "accessible": False,
        "path": socket_path_str,
    }

    if not socket_path.exists():
        logger.debug(
            "FBP socket does not exist",
            extra={"payload": {"socket_path": socket_path_str}},
        )
        return check_result

    check_result["exists"] = True

    if not socket_path.is_socket():
        logger.warning(
            "FBP socket path exists but is not a socket",
            extra={"payload": {"socket_path": socket_path_str}},
        )
        return check_result

    check_result["is_socket"] = True

    # Check permissions
    if os.access(socket_path, os.R_OK | os.W_OK):
        check_result["accessible"] = True
    else:
        logger.warning(
            "FBP socket exists but lacks read/write permissions",
            extra={"payload": {"socket_path": socket_path_str}},
        )

    return check_result
