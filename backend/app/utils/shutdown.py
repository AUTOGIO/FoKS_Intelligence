"""Graceful shutdown utilities."""

from __future__ import annotations

import signal
import sys
from typing import Callable, List

from app.services.logging_utils import get_logger

logger = get_logger("shutdown")

_shutdown_handlers: List[Callable[[], None]] = []


def register_shutdown_handler(handler: Callable[[], None]) -> None:
    """Register a function to be called on shutdown."""
    _shutdown_handlers.append(handler)


def _signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals."""
    logger.info("Received signal %d, initiating graceful shutdown...", signum)
    for handler in _shutdown_handlers:
        try:
            handler()
        except Exception as exc:  # noqa: BLE001
            logger.error("Error in shutdown handler: %s", exc)
    sys.exit(0)


def setup_graceful_shutdown() -> None:
    """Setup graceful shutdown handlers."""
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    logger.info("Graceful shutdown handlers registered")

