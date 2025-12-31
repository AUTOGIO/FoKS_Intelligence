"""OASE (Observational Automation Suggestion Engine) HTTP client."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.services.logging_utils import get_logger

logger = get_logger(__name__)


class OASEClientError(RuntimeError):
    """Error raised when OASE client operations fail."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        endpoint: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.endpoint = endpoint
        self.details = details or {}


class OASEClient:
    """HTTP client for OASE (Observational Automation Suggestion Engine)."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        """Initialize OASE client.

        Args:
            base_url: OASE base URL (defaults to settings.oase_base_url)
            timeout: Request timeout in seconds (defaults to settings.default_timeout_seconds)
        """
        self.base_url = (base_url or settings.oase_base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.default_timeout_seconds
        self._client: httpx.AsyncClient | None = None

        logger.debug(
            "OASE client initialized",
            extra={
                "payload": {
                    "base_url": self.base_url,
                    "timeout": self.timeout,
                }
            },
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_knowledge_units(self) -> list[dict[str, Any]]:
        """Get recent knowledge units from OASE.

        Returns:
            List of knowledge unit dictionaries

        Raises:
            OASEClientError: If request fails
        """
        client = await self._get_client()
        endpoint = "/api/knowledge-units/"

        try:
            logger.info("Fetching knowledge units from OASE", extra={"endpoint": endpoint})
            response = await client.get(endpoint)
            response.raise_for_status()
            data = response.json()

            # Handle different response formats
            if isinstance(data, dict) and "knowledge_units" in data:
                knowledge_units = data["knowledge_units"]
            elif isinstance(data, list):
                knowledge_units = data
            else:
                knowledge_units = []

            logger.info(
                "Knowledge units retrieved",
                extra={"count": len(knowledge_units)},
            )
            return knowledge_units

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            error_msg = f"OASE returned {status}: {e.response.text}"
            logger.warning(
                "OASE request failed with status",
                extra={"status": status, "endpoint": endpoint, "error": error_msg},
            )
            raise OASEClientError(
                error_msg,
                status=status,
                endpoint=endpoint,
                details={"response_text": e.response.text},
            ) from e

        except httpx.RequestError as e:
            error_msg = f"Failed to connect to OASE: {str(e)}"
            logger.warning(
                "OASE connection failed",
                extra={"endpoint": endpoint, "error": str(e)},
            )
            raise OASEClientError(
                error_msg,
                endpoint=endpoint,
                details={"connection_error": str(e)},
            ) from e

        except Exception as e:
            error_msg = f"Unexpected error querying OASE: {str(e)}"
            logger.error(
                "Unexpected OASE error",
                exc_info=True,
                extra={"endpoint": endpoint, "error": str(e)},
            )
            raise OASEClientError(
                error_msg,
                endpoint=endpoint,
                details={"unexpected_error": str(e)},
            ) from e

    async def health_check(self) -> bool:
        """Check if OASE is available.

        Returns:
            True if OASE is responding, False otherwise
        """
        client = await self._get_client()
        try:
            response = await client.get("/health/", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

