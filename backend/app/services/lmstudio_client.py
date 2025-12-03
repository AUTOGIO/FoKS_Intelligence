from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.models import ChatMessage
from app.services.logging_utils import get_logger

logger = get_logger(__name__)


class LMStudioClient:
    """Simple OpenAI-compatible client for the local LM Studio server."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.base_url = base_url or settings.lmstudio_base_url
        self.model = model or settings.lmstudio_model
        self.api_key = api_key or settings.lmstudio_api_key

    async def chat(self, message: str, history: Optional[List[ChatMessage]] = None) -> Dict[str, Any]:
        """Send a chat completion request and return the raw JSON response."""
        payload = {
            "model": self.model,
            "messages": self._build_messages(message, history),
        }

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        logger.info(
            "Sending prompt to LM Studio",
            extra={"model": self.model, "base_url": self.base_url},
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.base_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.info("LM Studio responded", extra={"has_choices": "choices" in data})
            return data

    def _build_messages(
        self,
        message: str,
        history: Optional[List[ChatMessage]],
    ) -> List[Dict[str, str]]:
        serialized_history: List[Dict[str, str]] = []
        if history:
            serialized_history = [{"role": item.role, "content": item.content} for item in history]
        serialized_history.append({"role": "user", "content": message})
        return serialized_history

    @staticmethod
    def extract_reply(data: Dict[str, Any]) -> str:
        """Extract assistant text from an OpenAI-style response."""
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError):
            return "Nenhuma resposta foi gerada pelo modelo local."
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.models import ChatMessage
from app.services.logging_utils import get_logger
from app.utils.circuit_breaker import CircuitBreaker, CircuitState

logger = get_logger("lmstudio_client")

# Global circuit breaker for LM Studio
lmstudio_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=60.0,
    expected_exception=Exception,
)


class LMStudioError(Exception):
    """Base exception for LM Studio errors."""

    error_code: str = "LM_STUDIO_ERROR"

    def __init__(self, message: str, error_code: str = "LM_STUDIO_ERROR", details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class DatabaseError(Exception):
    """Exception for database errors."""

    error_code: str = "DATABASE_ERROR"


class ValidationError(Exception):
    """Exception for validation errors."""

    error_code: str = "VALIDATION_ERROR"


class LMStudioClient:
    def __init__(self) -> None:
        self.base_url = settings.lmstudio_base_url
        self.model = settings.lmstudio_model
        self.api_key = settings.lmstudio_api_key
        # HTTP connection pool for better performance
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling."""
        if self._client is None:
            limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
            timeout = httpx.Timeout(settings.request_timeout_seconds, connect=10.0)
            self._client = httpx.AsyncClient(limits=limits, timeout=timeout)
        return self._client

    async def close(self) -> None:
        """Close HTTP client connection pool."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _retry_request(
        self,
        request_func,
        *args,
        max_retries: Optional[int] = None,
        backoff_seconds: Optional[float] = None,
        **kwargs,
    ) -> Any:
        """
        Retry a request with exponential backoff.

        Args:
            request_func: Async function to retry
            *args: Positional arguments for request_func
            max_retries: Maximum number of retries (defaults to settings.max_retries)
            backoff_seconds: Initial backoff in seconds (defaults to settings.retry_backoff_seconds)
            **kwargs: Keyword arguments for request_func

        Returns:
            Result from request_func

        Raises:
            LMStudioError: If all retries fail
        """
        max_retries = max_retries or settings.max_retries
        backoff_seconds = backoff_seconds or settings.retry_backoff_seconds

        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                return await request_func(*args, **kwargs)
            except httpx.HTTPStatusError as exc:
                # Don't retry on client errors (4xx)
                if 400 <= exc.response.status_code < 500:
                    raise LMStudioError(
                        f"LM Studio client error: {exc.response.status_code}",
                        error_code="LM_STUDIO_CLIENT_ERROR",
                        details={"status_code": exc.response.status_code, "response": exc.response.text},
                    ) from exc
                # Retry on server errors (5xx) and network errors
                last_exception = exc
                if attempt < max_retries:
                    wait_time = backoff_seconds * (2 ** attempt)
                    logger.warning(
                        "LM Studio request failed (attempt %d/%d), retrying in %.2fs: %s",
                        attempt + 1,
                        max_retries + 1,
                        wait_time,
                        exc,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise LMStudioError(
                        f"LM Studio server error after {max_retries + 1} attempts: {exc.response.status_code}",
                        error_code="LM_STUDIO_SERVER_ERROR",
                        details={"status_code": exc.response.status_code, "attempts": max_retries + 1},
                    ) from exc
            except httpx.RequestError as exc:
                # Network errors - retry
                last_exception = exc
                if attempt < max_retries:
                    wait_time = backoff_seconds * (2 ** attempt)
                    logger.warning(
                        "LM Studio network error (attempt %d/%d), retrying in %.2fs: %s",
                        attempt + 1,
                        max_retries + 1,
                        wait_time,
                        exc,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise LMStudioError(
                        f"LM Studio network error after {max_retries + 1} attempts",
                        error_code="LM_STUDIO_NETWORK_ERROR",
                        details={"attempts": max_retries + 1},
                    ) from exc
            except Exception as exc:  # noqa: BLE001
                # Unexpected errors - don't retry
                raise LMStudioError(
                    f"Unexpected error in LM Studio request: {exc}",
                    error_code="LM_STUDIO_UNEXPECTED_ERROR",
                ) from exc

        # Should never reach here, but just in case
        if last_exception:
            raise LMStudioError(
                "LM Studio request failed after all retries",
                error_code="LM_STUDIO_ERROR",
            ) from last_exception

    async def chat(self, message: str, history: Optional[List[ChatMessage]] = None) -> Dict[str, Any]:
        """
        Sends a chat-completion request to LM Studio (OpenAI-compatible) with retry logic.

        Args:
            message: User message
            history: Optional conversation history

        Returns:
            Response from LM Studio

        Raises:
            LMStudioError: If request fails after retries
        """
        # Use provided model or default
        model_to_use = model or self.model

        payload: Dict[str, Any] = {
            "model": model_to_use,
            "messages": [],
        }

        if history:
            # Use model_dump for Pydantic v2 compatibility
            payload["messages"].extend(
                [m.model_dump() if hasattr(m, "model_dump") else m.dict() for m in history]
            )

        payload["messages"].append({"role": "user", "content": message})

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async def _make_request() -> Dict[str, Any]:
            logger.info("Sending request to LM Studio...")
            client = await self._get_client()
            response = await client.post(self.base_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.info("Received response from LM Studio")
            return data

        # Use circuit breaker to protect against cascading failures
        if lmstudio_circuit_breaker.get_state() == CircuitState.OPEN:
            raise LMStudioError(
                "LM Studio circuit breaker is OPEN. Service unavailable.",
                error_code="LM_STUDIO_CIRCUIT_OPEN",
            )

        try:
            result = await self._retry_request(_make_request)
            lmstudio_circuit_breaker._on_success()
            return result
        except Exception as exc:
            lmstudio_circuit_breaker._on_failure()
            raise

    async def vision(
        self,
        image_base64: str,
        description: str,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sends a vision request to LM Studio (OpenAI-compatible vision API).

        Args:
            image_base64: Base64 encoded image
            description: Description or prompt for the image
            model: Optional model name (uses default if not provided)

        Returns:
            dict: Response from LM Studio
        """
        payload: Dict[str, Any] = {
            "model": model or self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": description},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                            },
                        },
                    ],
                },
            ],
        }

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        logger.info("Sending vision request to LM Studio...")
        try:
            client = await self._get_client()
            response = await client.post(self.base_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.info("Received vision response from LM Studio")
            return data
        except httpx.HTTPStatusError as exc:
            logger.error("Vision API error: %s", exc)
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("Error in vision request: %s", exc)
            raise

    async def stream_chat(
        self, message: str, history: Optional[List[ChatMessage]] = None
    ) -> Any:
        """
        Streams a chat-completion request to LM Studio (OpenAI-compatible streaming).

        Args:
            message: User message
            history: Optional conversation history

        Yields:
            dict: Streaming chunks with 'chunk' and 'done' keys
        """
        # Use provided model or default
        model_to_use = model or self.model

        payload: Dict[str, Any] = {
            "model": model_to_use,
            "messages": [],
            "stream": True,
        }

        if history:
            payload["messages"].extend(
                [m.model_dump() if hasattr(m, "model_dump") else m.dict() for m in history]
            )

        payload["messages"].append({"role": "user", "content": message})

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        logger.info("Sending streaming request to LM Studio...")
        try:
            client = await self._get_client()
            async with client.stream("POST", self.base_url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip() or line.startswith("data: [DONE]"):
                            continue
                        if line.startswith("data: "):
                            try:
                                import json

                                data = json.loads(line[6:])  # Remove "data: " prefix
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield {"chunk": content, "done": False}
                                    # Check if this is the final chunk
                                    if data["choices"][0].get("finish_reason"):
                                        yield {"chunk": "", "done": True}
                                        break
                            except Exception as exc:  # noqa: BLE001
                                logger.warning("Error parsing streaming chunk: %s", exc)
                                continue
        except httpx.HTTPStatusError as exc:
            logger.error("Streaming API error: %s", exc)
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("Error in streaming request: %s", exc)
            raise

    @staticmethod
    def extract_reply(data: Dict[str, Any]) -> str:
        """
        Extracts assistant reply text from OpenAI-style response.
        """
        try:
            return data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to extract reply: %s", exc)
            return "Sorry, I had an issue extracting the model response."

