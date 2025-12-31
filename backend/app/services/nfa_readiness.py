"""NFA readiness check service."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.fbp_client import FBPClient, FBPClientError
from app.services.logging_utils import get_logger

logger = get_logger(__name__)


async def check_nfa_readiness() -> dict[str, Any]:
    """
    Check NFA system readiness.

    Verifies:
    - FBP socket exists at configured path
    - FBP health endpoint is reachable (1 second timeout)
    - Required environment variables are set

    Returns:
        Dictionary with readiness status:
        - fbp_socket: bool
        - fbp_health: "ok" or "error"
        - env_vars: dict with username, password, cnpj (bool each)
        - status: "READY" or "BLOCKED"
    """
    logger.info("NFA readiness check requested")

    # Check socket existence
    socket_path = settings.fbp_socket_path
    socket_exists = Path(socket_path).exists()

    # Check FBP health with 1 second timeout
    fbp_health = "error"
    if socket_exists:
        try:
            client = FBPClient()
            # Use asyncio.wait_for to enforce 1 second timeout
            health_result = await asyncio.wait_for(
                client.health(),
                timeout=1.0,
            )
            await client.close()
            # Check if health response indicates success
            # FBPResult has status (HTTP code) and payload
            if (
                health_result.get("status") == 200
                or health_result.get("payload", {}).get("status") == "ok"
            ):
                fbp_health = "ok"
            else:
                fbp_health = "error"
        except TimeoutError:
            logger.warning(
                "FBP health check timed out after 1 second",
                extra={"payload": {"socket_path": socket_path}},
            )
            fbp_health = "error"
        except FBPClientError as exc:
            logger.warning(
                "FBP health check failed",
                exc_info=True,
                extra={
                    "payload": {
                        "error": str(exc),
                        "socket_path": socket_path,
                    }
                },
            )
            fbp_health = "error"
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "FBP health check error",
                exc_info=True,
                extra={
                    "payload": {
                        "error_type": type(exc).__name__,
                        "socket_path": socket_path,
                    }
                },
            )
            fbp_health = "error"
    else:
        logger.warning(
            "FBP socket does not exist",
            extra={"payload": {"socket_path": socket_path}},
        )

    # Check environment variables
    env_vars = {
        "username": bool(os.getenv("NFA_USERNAME")),
        "password": bool(os.getenv("NFA_PASSWORD")),
        "cnpj": bool(os.getenv("NFA_EMITENTE_CNPJ")),
    }

    # Determine overall status
    all_env_vars_present = all(env_vars.values())
    is_ready = (
        socket_exists
        and fbp_health == "ok"
        and all_env_vars_present
    )
    status = "READY" if is_ready else "BLOCKED"

    result = {
        "fbp_socket": socket_exists,
        "fbp_health": fbp_health,
        "env_vars": env_vars,
        "status": status,
    }

    logger.info(
        "NFA readiness check completed",
        extra={"payload": result},
    )

    return result
