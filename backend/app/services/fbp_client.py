from __future__ import annotations

import asyncio
import os
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.services.logging_utils import get_logger
from app.utils.architectural_assertions import (
    assert_deterministic_command,
    assert_evidence_response,
)

logger = get_logger(__name__)


@dataclass
class FBPResult:
    endpoint: str
    payload: dict[str, Any]
    status: int
    provider: str = "fbp"
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
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
        status: int | None = None,
        endpoint: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.endpoint = endpoint
        self.details = details or {}


ClientFactory = Callable[[], httpx.AsyncClient]


class FBPClient:
    """Async client responsável por conversar com o FBP backend."""

    def __init__(self, *, client_factory: ClientFactory | None = None) -> None:
        self._use_socket = settings.fbp_transport.lower() == "socket"
        self._socket_path = settings.fbp_socket_path if self._use_socket else None

        # For socket transport, base_url is "http://localhost" (UDS handles routing)
        # For TCP transport, use configured base_url or default
        if self._use_socket:
            self.base_url = "http://localhost"
        else:
            self.base_url = settings.fbp_base_url.rstrip("/")

        self._client_factory = client_factory
        self._client: httpx.AsyncClient | None = None

        logger.debug(
            "FBP client initialized",
            extra={
                "payload": {
                    "transport": "socket" if self._use_socket else "tcp",
                    "socket_path": self._socket_path if self._use_socket else None,
                    "base_url": self.base_url,
                }
            },
        )

    def _check_socket_exists(self) -> bool:
        """
        Check if FBP socket exists and is accessible.

        Performs fast lsof check to detect if process is listening before
        attempting httpx connection, reducing timeout delays.
        """
        if not self._use_socket or not self._socket_path:
            return True  # Not using socket transport

        socket_path = Path(self._socket_path)
        if not socket_path.exists():
            logger.warning(
                "FBP socket does not exist",
                extra={
                    "payload": {
                        "socket_path": str(socket_path),
                        "hint": "FBP backend may not be running. Start with: ops/scripts/fbp_boot.sh",
                    }
                },
            )
            return False

        if not socket_path.is_socket():
            logger.warning(
                "FBP socket path exists but is not a socket",
                extra={
                    "payload": {
                        "socket_path": str(socket_path),
                        "hint": "Remove stale file and restart FBP backend",
                    }
                },
            )
            return False

        # Fast check: verify process is listening on socket (before connection attempt)
        # This prevents 6+ second timeouts when socket exists but FBP is not running
        try:
            result = subprocess.run(
                ["lsof", str(socket_path)],
                capture_output=True,
                timeout=0.5,
            )
            if result.returncode != 0:
                logger.warning(
                    "Socket exists but no process is listening",
                    extra={"payload": {"socket": str(socket_path)}},
                )
                return False
        except Exception:  # noqa: BLE001
            # Fail silently and fall back to connection attempt
            # lsof may not be available or may fail for other reasons
            pass

        # Check socket permissions
        if not os.access(socket_path, os.R_OK | os.W_OK):
            logger.warning(
                "FBP socket exists but lacks read/write permissions",
                extra={
                    "payload": {
                        "socket_path": str(socket_path),
                        "hint": "Check socket permissions and ownership",
                    }
                },
            )
            return False

        return True

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create httpx client with proper transport configuration."""
        if self._client is None:
            if self._client_factory:
                self._client = self._client_factory()
            else:
                # Verify socket exists before creating client (socket transport only)
                if self._use_socket and not self._check_socket_exists():
                    raise FBPClientError(
                        "FBP socket not available",
                        endpoint="connection",
                        details={
                            "socket_path": self._socket_path,
                            "transport": "socket",
                        },
                    )

                # Configure timeout with separate connect/read timeouts
                timeout = httpx.Timeout(
                    connect=5.0,  # Connection timeout (socket or TCP)
                    read=settings.default_timeout_seconds,  # Read timeout
                    write=10.0,  # Write timeout
                    pool=5.0,  # Pool timeout
                )

                limits = httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=10,
                )

                transport: httpx.AsyncHTTPTransport | None = None
                if self._use_socket and self._socket_path:
                    # UNIX Domain Socket transport - no TCP fallback
                    transport = httpx.AsyncHTTPTransport(uds=self._socket_path)
                    logger.debug(
                        "FBP client using UNIX socket transport",
                        extra={
                            "payload": {
                                "socket_path": self._socket_path,
                                "base_url": self.base_url,
                            }
                        },
                    )
                else:
                    # TCP transport (only if explicitly configured)
                    logger.debug(
                        "FBP client using TCP transport",
                        extra={
                            "payload": {
                                "base_url": self.base_url,
                                "transport": "tcp",
                            }
                        },
                    )

                self._client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=timeout,
                    limits=limits,
                    transport=transport,
                )

                logger.info(
                    "FBP client created",
                    extra={
                        "payload": {
                            "transport": "socket" if self._use_socket else "tcp",
                            "socket_path": self._socket_path if self._use_socket else None,
                            "base_url": self.base_url,
                        }
                    },
                )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _execute_with_retry(self, request_coro, endpoint: str):
        """
        Execute request with exponential backoff retry logic.

        Retries on:
        - Connection errors (socket missing, connection refused)
        - Timeout errors
        - 5xx server errors

        Does NOT retry on:
        - 4xx client errors (bad request, unauthorized, etc.)
        """
        attempts = max(1, settings.default_retry_attempts)
        backoff = settings.retry_backoff_seconds

        for attempt in range(attempts):
            try:
                return await request_coro()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                # 4xx errors: client error, don't retry
                if 400 <= status < 500:
                    logger.error(
                        "FBP request rejected (client error)",
                        exc_info=True,
                        extra={
                            "payload": {
                                "endpoint": endpoint,
                                "status": status,
                                "attempt": attempt + 1,
                                "max_attempts": attempts,
                                "response": exc.response.text[:200] if exc.response else None,
                            }
                        },
                    )
                    raise FBPClientError(
                        "FBP request rejected",
                        status=status,
                        endpoint=endpoint,
                        details={"response": exc.response.text[:200] if exc.response else None},
                    ) from exc
                # 5xx errors: server error, retry
                if attempt == attempts - 1:
                    logger.error(
                        "FBP server error (max retries reached)",
                        exc_info=True,
                        extra={
                            "payload": {
                                "endpoint": endpoint,
                                "status": status,
                                "attempt": attempt + 1,
                                "max_attempts": attempts,
                            }
                        },
                    )
                    raise FBPClientError(
                        "FBP server error",
                        status=status,
                        endpoint=endpoint,
                    ) from exc
                logger.warning(
                    "FBP retry due to server error",
                    extra={
                        "payload": {
                            "endpoint": endpoint,
                            "status": status,
                            "attempt": attempt + 1,
                            "max_attempts": attempts,
                            "next_backoff_seconds": backoff * (2**attempt),
                        }
                    },
                )
            except httpx.TimeoutException as exc:
                if attempt == attempts - 1:
                    logger.error(
                        "FBP request timed out (max retries reached)",
                        exc_info=True,
                        extra={
                            "payload": {
                                "endpoint": endpoint,
                                "attempt": attempt + 1,
                                "max_attempts": attempts,
                                "timeout_seconds": settings.default_timeout_seconds,
                            }
                        },
                    )
                    raise FBPClientError(
                        "FBP request timed out",
                        endpoint=endpoint,
                        details={"timeout_seconds": settings.default_timeout_seconds},
                    ) from exc
                logger.warning(
                    "FBP retry due to timeout",
                    extra={
                        "payload": {
                            "endpoint": endpoint,
                            "attempt": attempt + 1,
                            "max_attempts": attempts,
                            "next_backoff_seconds": backoff * (2**attempt),
                            "timeout_seconds": settings.default_timeout_seconds,
                        }
                    },
                )
            except httpx.ConnectError as exc:
                # Connection errors: socket missing, connection refused, etc.
                if attempt == attempts - 1:
                    # Check socket again before final failure
                    socket_available = self._check_socket_exists() if self._use_socket else True
                    logger.error(
                        "FBP connection error (max retries reached)",
                        exc_info=True,
                        extra={
                            "payload": {
                                "endpoint": endpoint,
                                "attempt": attempt + 1,
                                "max_attempts": attempts,
                                "transport": "socket" if self._use_socket else "tcp",
                                "socket_path": self._socket_path if self._use_socket else None,
                                "socket_available": socket_available,
                                "error_type": type(exc).__name__,
                                "error_message": str(exc),
                            }
                        },
                    )
                    error_msg = "FBP connection error"
                    if self._use_socket and not socket_available:
                        error_msg = "FBP socket not available"
                    raise FBPClientError(
                        error_msg,
                        endpoint=endpoint,
                        details={
                            "transport": "socket" if self._use_socket else "tcp",
                            "socket_path": self._socket_path if self._use_socket else None,
                            "socket_available": socket_available,
                        },
                    ) from exc
                logger.warning(
                    "FBP retry due to connection error",
                    extra={
                        "payload": {
                            "endpoint": endpoint,
                            "attempt": attempt + 1,
                            "max_attempts": attempts,
                            "next_backoff_seconds": backoff * (2**attempt),
                            "transport": "socket" if self._use_socket else "tcp",
                            "error_type": type(exc).__name__,
                        }
                    },
                )
            except httpx.RequestError as exc:
                # Generic request errors (catch-all)
                if attempt == attempts - 1:
                    logger.error(
                        "FBP request error (max retries reached)",
                        exc_info=True,
                        extra={
                            "payload": {
                                "endpoint": endpoint,
                                "attempt": attempt + 1,
                                "max_attempts": attempts,
                                "error_type": type(exc).__name__,
                                "error_message": str(exc),
                            }
                        },
                    )
                    raise FBPClientError(
                        "FBP connection error",
                        endpoint=endpoint,
                        details={"error_type": type(exc).__name__, "error_message": str(exc)},
                    ) from exc
                logger.warning(
                    "FBP retry due to request error",
                    extra={
                        "payload": {
                            "endpoint": endpoint,
                            "attempt": attempt + 1,
                            "max_attempts": attempts,
                            "next_backoff_seconds": backoff * (2**attempt),
                            "error_type": type(exc).__name__,
                        }
                    },
                )

            # Exponential backoff: wait before retry
            backoff_seconds = backoff * (2**attempt)
            logger.debug(
                "FBP retry backoff",
                extra={
                    "payload": {
                        "endpoint": endpoint,
                        "attempt": attempt + 1,
                        "backoff_seconds": backoff_seconds,
                    }
                },
            )
            await asyncio.sleep(backoff_seconds)

        # Should never reach here, but safety check
        logger.error(
            "FBP request failed after all retries",
            extra={
                "payload": {
                    "endpoint": endpoint,
                    "max_attempts": attempts,
                }
            },
        )
        raise FBPClientError("FBP request failed after retries", endpoint=endpoint)

    async def _request(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute HTTP request to FBP backend with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., "/health", "/nfa")
            payload: Optional request payload (JSON-serializable dict)

        Returns:
            FBPResult dictionary with status, payload, and metadata

        Raises:
            FBPClientError: If request fails after retries
        """
        # Normalize endpoint URL
        url = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        start = time.perf_counter()

        logger.info(
            "FBP request initiated",
            extra={
                "payload": {
                    "method": method,
                    "endpoint": url,
                    "transport": "socket" if self._use_socket else "tcp",
                    "has_payload": payload is not None,
                }
            },
        )

        # Get client (will check socket if using socket transport)
        try:
            client = await self._get_client()
        except FBPClientError as exc:
            logger.error(
                "FBP client initialization failed",
                exc_info=True,
                extra={
                    "payload": {
                        "endpoint": url,
                        "error": str(exc),
                        "transport": "socket" if self._use_socket else "tcp",
                    }
                },
            )
            raise

        async def _perform() -> httpx.Response:
            if payload:
                assert_deterministic_command(payload)

            client = await self._get_client()
            return await client.request(
                method=method,
                url=url,  # Use url here, not endpoint
                json=payload,
                timeout=client.timeout,  # Use client's configured timeout
            )

        try:
            response = await self._execute_with_retry(_perform, url)
        except FBPClientError as exc:
            duration = int((time.perf_counter() - start) * 1000)
            logger.error(
                "FBP request failed",
                exc_info=True,
                extra={
                    "payload": {
                        "method": method,
                        "endpoint": url,
                        "duration_ms": duration,
                        "error": str(exc),
                        "error_status": exc.status,
                    }
                },
            )
            raise

        duration = int((time.perf_counter() - start) * 1000)

        # Parse response
        try:
            response_data = response.json()
            assert_evidence_response(response_data)
        except Exception as e:
            if "Architectural" in type(e).__name__:
                raise

            logger.warning(
                "FBP response is not valid JSON or failed compliance",
                exc_info=True,
                extra={
                    "payload": {
                        "endpoint": url,
                        "status": response.status_code,
                        "response_text": response.text[:200],
                        "error": str(e),
                    }
                },
            )
            response_data = {"raw_response": response.text[:500], "compliance_failed": True}

        logger.info(
            "FBP request completed",
            extra={
                "payload": {
                    "method": method,
                    "endpoint": url,
                    "status": response.status_code,
                    "duration_ms": duration,
                    "transport": "socket" if self._use_socket else "tcp",
                }
            },
        )

        return FBPResult(
            endpoint=url,
            payload=response_data,
            status=response.status_code,
            duration_ms=duration,
        ).to_dict()

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/health")

    async def nfa(self, data: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/nfa", data)

    async def redesim(self, data: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/redesim", data)

    async def browser(self, data: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/browser", data)

    async def utils(self, data: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/utils", data)

    async def run_script(self, script_content: str, timeout: int = 60) -> dict[str, Any]:
        """
        Executes a deterministic script on FBP Backend.
        Fulfills the Bailiff role.
        """
        payload = {"script_content": script_content, "timeout": timeout}
        return await self._request("POST", "/executor/run-bash", payload)
