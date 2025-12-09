from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import httpx
from app.config import settings
from app.services.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class FBPResult:
    endpoint: str
    payload: Dict[str, Any]
    status: int
    provider: str = "fbp"
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "endpoint": self.endpoint,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "payload": self.payload,
        }


class FBPClientError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        endpoint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.endpoint = endpoint
        self.details = details or {}


ClientFactory = Callable[[], httpx.AsyncClient]


class FBPClient:
    """Async client responsável por conversar com o FBP backend."""

    def __init__(self, *, client_factory: Optional[ClientFactory] = None) -> None:
        self.base_url = settings.fbp_base_url.rstrip("/")
        self._use_socket = settings.fbp_transport.lower() == "socket"
        self._socket_path = settings.fbp_socket_path if self._use_socket else None
        self._client_factory = client_factory
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            if self._client_factory:
                self._client = self._client_factory()
            else:
                timeout = httpx.Timeout(settings.default_timeout_seconds)
                limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
                transport: Optional[httpx.AsyncHTTPTransport] = None
                if self._use_socket and self._socket_path:
                    transport = httpx.AsyncHTTPTransport(uds=self._socket_path)
                self._client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=timeout,
                    limits=limits,
                    transport=transport,
                )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _execute_with_retry(self, request_coro, endpoint: str):
        attempts = max(1, settings.default_retry_attempts)
        backoff = settings.retry_backoff_seconds
        for attempt in range(attempts):
            try:
                return await request_coro()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if 400 <= status < 500:
                    raise FBPClientError("FBP request rejected", status=status, endpoint=endpoint) from exc
                if attempt == attempts - 1:
                    raise FBPClientError("FBP server error", status=status, endpoint=endpoint) from exc
                logger.warning(
                    "FBP retry due to server error",
                    extra={"payload": {"endpoint": endpoint, "status": status, "attempt": attempt + 1}},
                )
            except httpx.TimeoutException as exc:
                if attempt == attempts - 1:
                    raise FBPClientError("FBP request timed out", endpoint=endpoint) from exc
                logger.warning(
                    "FBP retry due to timeout",
                    extra={"payload": {"endpoint": endpoint, "attempt": attempt + 1}},
                )
            except httpx.RequestError as exc:
                if attempt == attempts - 1:
                    raise FBPClientError("FBP connection error", endpoint=endpoint) from exc
                logger.warning(
                    "FBP retry due to connection error",
                    extra={"payload": {"endpoint": endpoint, "attempt": attempt + 1}},
                )
            await asyncio.sleep(backoff * (2**attempt))
        raise FBPClientError("FBP request failed after retries", endpoint=endpoint)

    async def _request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        client = await self._get_client()
        url = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        start = time.perf_counter()
        logger.info("FBP request", extra={"payload": {"method": method, "endpoint": url}})

        async def _perform():
            response = await client.request(method, url, json=payload)
            response.raise_for_status()
            return response

        response = await self._execute_with_retry(_perform, url)
        duration = int((time.perf_counter() - start) * 1000)
        logger.info(
            "FBP response",
            extra={"payload": {"endpoint": url, "status": response.status_code, "duration_ms": duration}},
        )
        return FBPResult(
            endpoint=url,
            payload=response.json(),
            status=response.status_code,
            duration_ms=duration,
        ).to_dict()

    async def health(self) -> Dict[str, Any]:
        return await self._request("GET", "/health")

    async def nfa(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/nfa", data)

    async def redesim(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/redesim", data)

    async def browser(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/browser", data)

    async def utils(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/utils", data)

