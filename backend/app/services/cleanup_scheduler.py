"""Scheduler for automatic data cleanup."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import os

from app.config import settings
from app.services.conversation_store import conversation_store
from app.services.logging_utils import get_logger

logger = get_logger("cleanup_scheduler")


class CleanupScheduler:
    """Scheduler for automatic cleanup tasks."""

    def __init__(self) -> None:
        """Initialize cleanup scheduler."""
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.cleanup_days = int(os.getenv("CLEANUP_DAYS", "30"))
        self.cleanup_interval_hours = int(os.getenv("CLEANUP_INTERVAL_Hours", "24"))

    async def start(self) -> None:
        """Start the cleanup scheduler."""
        if self._running:
            logger.warning("Cleanup scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Cleanup scheduler started (cleanup every %d hours, delete conversations older than %d days)",
            self.cleanup_interval_hours,
            self.cleanup_days,
        )

    async def stop(self) -> None:
        """Stop the cleanup scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Cleanup scheduler stopped")

    async def _run_loop(self) -> None:
        """Main cleanup loop."""
        while self._running:
            try:
                await self._cleanup_old_conversations()
                await asyncio.sleep(self.cleanup_interval_hours * 3600)
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                logger.error("Error in cleanup scheduler: %s", exc, exc_info=True)
                # Wait before retrying
                await asyncio.sleep(3600)  # Retry in 1 hour

    async def _cleanup_old_conversations(self) -> None:
        """Clean up old conversations."""
        try:
            deleted_count = conversation_store.cleanup_old_conversations(self.cleanup_days)
            if deleted_count > 0:
                logger.info("Cleaned up %d old conversations (older than %d days)", deleted_count, self.cleanup_days)
            else:
                logger.debug("No old conversations to clean up")
        except Exception as exc:  # noqa: BLE001
            logger.error("Error cleaning up old conversations: %s", exc, exc_info=True)


# Global cleanup scheduler instance
cleanup_scheduler = CleanupScheduler()

