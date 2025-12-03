"""Webhook service for event notifications."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.services.logging_utils import get_logger

logger = get_logger("webhook_service")


class WebhookService:
    """Service for sending webhook notifications."""

    def __init__(self) -> None:
        """Initialize webhook service."""
        self.webhook_urls: List[str] = []
        webhook_env = settings.webhook_urls if hasattr(settings, "webhook_urls") else []
        if webhook_env:
            self.webhook_urls = webhook_env if isinstance(webhook_env, list) else webhook_env.split(",")

    async def send_webhook(
        self,
        event_type: str,
        data: Dict[str, Any],
        webhook_url: Optional[str] = None,
    ) -> bool:
        """
        Send webhook notification.

        Args:
            event_type: Type of event (e.g., "conversation.created", "chat.completed")
            data: Event data
            webhook_url: Optional specific webhook URL (overrides configured URLs)

        Returns:
            bool: True if sent successfully
        """
        if not webhook_url and not self.webhook_urls:
            logger.debug("No webhook URLs configured, skipping webhook")
            return False

        urls = [webhook_url] if webhook_url else self.webhook_urls

        payload = {
            "event": event_type,
            "timestamp": data.get("timestamp"),
            "data": data,
        }

        success_count = 0
        for url in urls:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.post(
                        url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )
                    response.raise_for_status()
                    logger.info("Webhook sent successfully to %s", url)
                    success_count += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to send webhook to %s: %s", url, exc)

        return success_count > 0


# Global webhook service instance
webhook_service = WebhookService()

