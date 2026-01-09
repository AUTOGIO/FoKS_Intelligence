from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Any

import httpx
from app.config import settings
from app.models import ChatMessage
from app.services import model_registry
from app.services.identity_guard import identity_guard, sanitize_response
from app.services.logging_utils import get_logger
from app.services.model_registry import ModelInfo

logger = get_logger(__name__)


class UTF8JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that always preserves UTF-8 characters."""

    def encode(self, obj: Any) -> str:
        # Override encode to always use ensure_ascii=False
        # Don't pass cls to avoid recursion - just use ensure_ascii=False
        return json.dumps(obj, ensure_ascii=False)


@dataclass
class LMStudioResult:
    model: str
    response: Any
    provider: str = "lmstudio"
    duration_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "provider": self.provider,
            "duration_ms": self.duration_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "response": self.response,
            "raw": self.raw,
        }


class LMStudioClientError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.details = details or {}


ClientFactory = Callable[[], httpx.AsyncClient]


class LMStudioClient:
    """OpenAI-compatible client for local LM Studio (chat, embeddings, vision, streaming)."""

    def __init__(self, *, client_factory: ClientFactory | None = None) -> None:
        self.base_url = settings.lmstudio_base_url.rstrip("/")
        self._client_factory = client_factory
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            if self._client_factory:
                self._client = self._client_factory()
            else:
                timeout = httpx.Timeout(settings.default_timeout_seconds)
                limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
                self._client = httpx.AsyncClient(timeout=timeout, limits=limits)
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_url(self, path: str) -> str:
        if not path:
            return self.base_url
        if path.startswith("http"):
            return path
        base = self.base_url.rstrip("/")
        suffix = path if path.startswith("/") else f"/{path}"
        return f"{base}{suffix}"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if settings.lmstudio_api_key:
            headers["Authorization"] = f"Bearer {settings.lmstudio_api_key}"
        return headers

    def _select_model(
        self, model_name: str | None, task_type: str, require_tools: bool
    ) -> ModelInfo:
        if model_name:
            return model_registry.resolve_model(model_name)
        normalized = (task_type or "chat").lower()
        if require_tools:
            for entry in model_registry.list_models():
                if entry.supports_tools:
                    return entry
        try:
            return model_registry.get_default_model(normalized)
        except ValueError:
            return model_registry.get_default_model("chat")

    def _serialize_messages(
        self, message: str, history: list[ChatMessage] | None
    ) -> list[dict[str, str]]:
        """
        Serialize chat messages for LM Studio payload.

        When identity guard is enabled, injects LOCAL_SYSTEM_PROMPT as the first message
        to enforce local AI identity and prevent cloud provider references.
        """
        # #region agent log
        log_path = "/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/.cursor/debug.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "D",
                        "location": "lmstudio_client.py:111",
                        "message": "Message in _serialize_messages",
                        "data": {
                            "message": message,
                            "message_repr": repr(message),
                            "message_bytes": message.encode("utf-8").hex(),
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
        # #endregion
        serialized: list[dict[str, str]] = []

        # Inject local system prompt FIRST when identity guard is enabled
        if identity_guard.should_inject_system_prompt():
            serialized.append(identity_guard.build_system_message())

        if history:
            for item in history:
                payload = (
                    item.model_dump()
                    if hasattr(item, "model_dump")
                    else {"role": item.role, "content": item.content}
                )
                serialized.append(payload)
        serialized.append({"role": "user", "content": message})
        # #region agent log
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "D",
                        "location": "lmstudio_client.py:129",
                        "message": "Serialized messages",
                        "data": {"serialized_sample": str(serialized)[:300]},
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
        # #endregion
        return serialized

    def _usage_stats(self, data: dict[str, Any]) -> dict[str, int]:
        usage = data.get("usage") or {}
        completion = usage.get("completion_tokens")
        if completion is None:
            completion = usage.get("completionTokens", 0)
        return {
            "input_tokens": usage.get("prompt_tokens", usage.get("promptTokens", 0)),
            "output_tokens": completion or 0,
        }

    async def _execute_with_retry(self, request_coro: Callable[[], Any]):
        attempts = max(1, settings.default_retry_attempts)
        backoff = settings.retry_backoff_seconds
        for attempt in range(attempts):
            try:
                return await request_coro()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if 400 <= status < 500:
                    raise LMStudioClientError(
                        "LM Studio rejected the request", status=status
                    ) from exc
                if attempt == attempts - 1:
                    raise LMStudioClientError("LM Studio server error", status=status) from exc
            except httpx.TimeoutException as exc:
                if attempt == attempts - 1:
                    raise LMStudioClientError("LM Studio request timed out") from exc
            except httpx.RequestError as exc:
                if attempt == attempts - 1:
                    raise LMStudioClientError("LM Studio connection error") from exc
            await asyncio.sleep(backoff * (2**attempt))
        raise LMStudioClientError("LM Studio request failed after retries")

    async def _request_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> tuple[dict[str, Any], int]:
        headers = self._headers()
        start = time.perf_counter()
        # #region agent log
        json_bytes_default = json.dumps(payload).encode("utf-8")
        json_bytes_ensure_ascii_false = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        payload_str = str(payload)
        has_portuguese = any(ord(c) > 127 for c in payload_str)
        log_path = "/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/.cursor/debug.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "A",
                        "location": "lmstudio_client.py:169",
                        "message": "Payload before serialization",
                        "data": {
                            "payload_sample": payload_str[:200],
                            "has_portuguese": has_portuguese,
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
            f.write(
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "A",
                        "location": "lmstudio_client.py:170",
                        "message": "JSON bytes comparison",
                        "data": {
                            "default_hex": json_bytes_default[:100].hex(),
                            "ensure_ascii_false_hex": json_bytes_ensure_ascii_false[:100].hex(),
                            "default_str": json_bytes_default[:100].decode(
                                "utf-8", errors="replace"
                            ),
                            "ensure_ascii_false_str": json_bytes_ensure_ascii_false[:100].decode(
                                "utf-8", errors="replace"
                            ),
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
            f.write(
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "B",
                        "location": "lmstudio_client.py:171",
                        "message": "Headers being sent",
                        "data": {"headers": headers, "content_type": headers.get("Content-Type")},
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
        # #endregion

        async def _perform() -> httpx.Response:
            client = await self._get_client()

            # #region agent log - Hypothesis A: Payload construction before serialization
            log_path = (
                "/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/.cursor/debug.log"
            )
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    payload_str = json.dumps(payload, ensure_ascii=False)
                    f.write(
                        json.dumps(
                            {
                                "sessionId": "debug-session",
                                "runId": "run1",
                                "hypothesisId": "A",
                                "location": "lmstudio_client.py:291",
                                "message": "Payload dict before JSON serialization",
                                "data": {
                                    "payload_str": payload_str[:1000],
                                    "has_portuguese": any(ord(c) > 127 for c in payload_str),
                                    "automação_present": "automação" in payload_str,
                                },
                                "timestamp": int(time.time() * 1000),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            except Exception:
                pass
            # #endregion

            # Fix: Manually serialize JSON with ensure_ascii=False to preserve Portuguese characters
            # Bypass httpx's automatic JSON encoding by manually encoding to UTF-8 bytes
            json_str = json.dumps(payload, ensure_ascii=False)
            json_bytes = json_str.encode("utf-8")

            # #region agent log - Hypothesis B: JSON serialization produces correct bytes
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    # Find Portuguese characters in the JSON string
                    portuguese_chars = [c for c in json_str if ord(c) > 127]
                    portuguese_sample = "".join(portuguese_chars[:10]) if portuguese_chars else ""
                    f.write(
                        json.dumps(
                            {
                                "sessionId": "debug-session",
                                "runId": "run1",
                                "hypothesisId": "B",
                                "location": "lmstudio_client.py:297",
                                "message": "JSON bytes after manual serialization",
                                "data": {
                                    "json_str_sample": json_str[:500],
                                    "json_bytes_len": len(json_bytes),
                                    "json_bytes_hex": json_bytes.hex()[:400],
                                    "portuguese_chars_found": len(portuguese_chars),
                                    "portuguese_sample": portuguese_sample,
                                    "can_decode_back": json_bytes.decode("utf-8")[:200],
                                },
                                "timestamp": int(time.time() * 1000),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            except Exception:
                pass
            # #endregion

            # Ensure Content-Length is set explicitly and disable compression
            headers_with_length = headers.copy()
            headers_with_length["Content-Length"] = str(len(json_bytes))
            # Explicitly disable compression to prevent any encoding corruption
            headers_with_length["Accept-Encoding"] = "identity"

            # #region agent log - Hypothesis C: Headers are correct
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(
                        json.dumps(
                            {
                                "sessionId": "debug-session",
                                "runId": "run1",
                                "hypothesisId": "C",
                                "location": "lmstudio_client.py:301",
                                "message": "Headers before httpx.post",
                                "data": {
                                    "headers": headers_with_length,
                                    "content_type": headers_with_length.get("Content-Type"),
                                    "content_length": headers_with_length.get("Content-Length"),
                                    "accept_encoding": headers_with_length.get("Accept-Encoding"),
                                },
                                "timestamp": int(time.time() * 1000),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            except Exception:
                pass
            # #endregion

            # #region agent log - Hypothesis D: Verify bytes right before httpx.post call
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    # Double-check the bytes are correct
                    decoded_check = json_bytes.decode("utf-8")
                    has_automação = "automação" in decoded_check
                    automação_position = decoded_check.find("automação") if has_automação else -1
                    if automação_position >= 0:
                        context_start = max(0, automação_position - 20)
                        context_end = min(len(decoded_check), automação_position + 30)
                        context = decoded_check[context_start:context_end]
                        context_bytes = json_bytes[context_start:context_end]
                    else:
                        context = ""
                        context_bytes = b""

                    f.write(
                        json.dumps(
                            {
                                "sessionId": "debug-session",
                                "runId": "run1",
                                "hypothesisId": "D",
                                "location": "lmstudio_client.py:360",
                                "message": "Bytes verification immediately before httpx.post",
                                "data": {
                                    "bytes_len": len(json_bytes),
                                    "bytes_hex_sample": json_bytes[:400].hex(),
                                    "decoded_sample": decoded_check[:500],
                                    "has_automação": has_automação,
                                    "automação_context": context,
                                    "automação_context_bytes_hex": context_bytes.hex(),
                                    "automação_bytes": (
                                        json_bytes[
                                            automação_position : automação_position
                                            + len("automação")
                                        ].hex()
                                        if automação_position >= 0
                                        else ""
                                    ),
                                },
                                "timestamp": int(time.time() * 1000),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            except Exception:
                pass
            # #endregion

            # Send request with raw UTF-8 bytes - httpx should send these bytes as-is
            # Using content= parameter ensures httpx doesn't re-encode
            # #region agent log - Final verification before sending
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    # Verify bytes one final time right before httpx.post
                    final_check = json_bytes.decode("utf-8", errors="strict")
                    f.write(
                        json.dumps(
                            {
                                "sessionId": "debug-session",
                                "runId": "run1",
                                "hypothesisId": "D",
                                "location": "lmstudio_client.py:446",
                                "message": "Final bytes verification - IMMEDIATELY before httpx.post",
                                "data": {
                                    "bytes_length": len(json_bytes),
                                    "can_decode_strict": True,
                                    "contains_automação": "automação" in final_check,
                                    "automação_bytes_hex": (
                                        json_bytes[
                                            final_check.find("automação") : final_check.find(
                                                "automação"
                                            )
                                            + len("automação")
                                        ].hex()
                                        if "automação" in final_check
                                        else "NOT_FOUND"
                                    ),
                                    "content_length_header": headers_with_length.get(
                                        "Content-Length"
                                    ),
                                },
                                "timestamp": int(time.time() * 1000),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            except Exception:
                pass
            # #endregion
            response = await client.post(
                url,
                content=json_bytes,  # Send pre-encoded UTF-8 bytes directly
                headers=headers_with_length,
                timeout=timeout or settings.default_timeout_seconds,
            )

            # #region agent log - Hypothesis E: Response headers might reveal encoding issues
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(
                        json.dumps(
                            {
                                "sessionId": "debug-session",
                                "runId": "run1",
                                "hypothesisId": "E",
                                "location": "lmstudio_client.py:365",
                                "message": "Response received - check for encoding clues",
                                "data": {
                                    "status_code": response.status_code,
                                    "response_headers": dict(response.headers),
                                    "content_type_received": response.headers.get(
                                        "Content-Type", ""
                                    ),
                                },
                                "timestamp": int(time.time() * 1000),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            except Exception:
                pass
            # #endregion
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(
                        json.dumps(
                            {
                                "sessionId": "debug-session",
                                "runId": "post-fix-v3",
                                "hypothesisId": "A",
                                "location": "lmstudio_client.py:315",
                                "message": "Response received from LM Studio",
                                "data": {
                                    "status_code": response.status_code,
                                    "response_headers": dict(response.headers),
                                },
                                "timestamp": int(time.time() * 1000),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            except Exception:
                pass  # Ignore logging errors
            # #endregion
            response.raise_for_status()
            return response

        response = await self._execute_with_retry(_perform)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        response_data = response.json()
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                response_str = json.dumps(response_data, ensure_ascii=False)
                f.write(
                    json.dumps(
                        {
                            "sessionId": "debug-session",
                            "runId": "post-fix-v3",
                            "hypothesisId": "A",
                            "location": "lmstudio_client.py:354",
                            "message": "Response JSON parsed",
                            "data": {
                                "response_sample": response_str[:500],
                                "has_portuguese_in_response": any(
                                    ord(c) > 127 for c in response_str
                                ),
                            },
                            "timestamp": int(time.time() * 1000),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        except Exception:
            pass  # Ignore logging errors
        # #endregion
        return response_data, elapsed_ms

    def _result_from_payload(
        self,
        model_info: ModelInfo,
        data: dict[str, Any],
        duration_ms: int,
        response: Any,
    ) -> dict[str, Any]:
        usage = self._usage_stats(data)
        return LMStudioResult(
            model=model_info.name,
            response=response,
            duration_ms=duration_ms,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            raw=data,
        ).to_dict()

    async def chat(
        self,
        message: str,
        *,
        history: list[ChatMessage] | None = None,
        model_name: str | None = None,
        task_type: str = "chat",
        tools_required: bool = False,
    ) -> dict[str, Any]:
        model_info = self._select_model(model_name, task_type, tools_required)
        payload = {
            "model": model_info.name,
            "messages": self._serialize_messages(message, history),
        }
        data, duration = await self._request_json(self._build_url("/chat/completions"), payload)
        reply = self._extract_text(data)

        # Sanitize response for cloud identity leakage when guard is enabled
        reply = sanitize_response(reply)

        logger.info(
            "LM Studio chat completed",
            extra={"payload": {"model": model_info.name, "duration_ms": duration}},
        )
        return self._result_from_payload(model_info, data, duration, reply)

    async def embeddings(self, text: str, *, model_name: str | None = None) -> dict[str, Any]:
        model_info = self._select_model(model_name, "embeddings", False)
        payload = {"model": model_info.name, "input": text}
        data, duration = await self._request_json(self._build_url("/embeddings"), payload)
        embedding = self._extract_embedding(data)
        return self._result_from_payload(model_info, data, duration, embedding)

    async def vision(
        self,
        *,
        image_base64: str,
        prompt: str,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        model_info = self._select_model(model_name, "vision", False)

        # Build messages list with optional system prompt injection
        messages: list[dict[str, Any]] = []
        if identity_guard.should_inject_system_prompt():
            messages.append(identity_guard.build_system_message())

        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                    },
                ],
            }
        )

        payload = {
            "model": model_info.name,
            "messages": messages,
        }
        data, duration = await self._request_json(
            self._build_url("/chat/completions"),
            payload,
            timeout=settings.stream_timeout_seconds,
        )
        reply = self._extract_text(data)

        # Sanitize response for cloud identity leakage when guard is enabled
        reply = sanitize_response(reply)

        return self._result_from_payload(model_info, data, duration, reply)

    async def stream_chat(
        self,
        message: str,
        *,
        history: list[ChatMessage] | None = None,
        model_name: str | None = None,
        task_type: str = "chat",
        tools_required: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream chat responses from LM Studio.

        Note: System prompt injection is applied via _serialize_messages().
        Response sanitization is NOT applied to streaming responses as it would
        require buffering the entire response, defeating the purpose of streaming.
        The system prompt provides the primary protection against identity leakage.
        """
        model_info = self._select_model(model_name, task_type, tools_required)
        payload = {
            "model": model_info.name,
            "messages": self._serialize_messages(message, history),
            "stream": True,
        }
        headers = self._headers()
        url = self._build_url("/chat/completions")
        client = await self._get_client()
        start = time.perf_counter()

        # Fix: Manually serialize JSON with ensure_ascii=False for streaming too
        encoder = UTF8JSONEncoder()
        json_bytes = encoder.encode(payload).encode("utf-8")

        try:
            async with client.stream(
                "POST",
                url,
                content=json_bytes,
                headers=headers,
                timeout=settings.stream_timeout_seconds,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    if line.strip().startswith("data: [DONE]"):
                        yield {
                            "model": model_info.name,
                            "provider": "lmstudio",
                            "duration_ms": int((time.perf_counter() - start) * 1000),
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "response": "",
                            "done": True,
                        }
                        break
                    if line.startswith("data: "):
                        try:
                            payload_json = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue
                        delta = payload_json.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield {
                                "model": model_info.name,
                                "provider": "lmstudio",
                                "duration_ms": int((time.perf_counter() - start) * 1000),
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "response": content,
                                "done": False,
                            }
        except httpx.HTTPStatusError as exc:
            raise LMStudioClientError(
                "LM Studio streaming error", status=exc.response.status_code
            ) from exc
        except httpx.RequestError as exc:
            raise LMStudioClientError("LM Studio streaming connection error") from exc

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, AttributeError):
            return ""

    @staticmethod
    def _extract_embedding(data: dict[str, Any]) -> list[float]:
        try:
            return data["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError):
            return []
