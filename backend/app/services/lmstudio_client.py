from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

import httpx

from app.config import settings
from app.models import ChatMessage
from app.services import model_registry
from app.services.logging_utils import get_logger
from app.services.model_registry import ModelInfo

logger = get_logger(__name__)


@dataclass
class LMStudioResult:
    model: str
    response: Any
    provider: str = "lmstudio"
    duration_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    raw: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
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
        status: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.details = details or {}


ClientFactory = Callable[[], httpx.AsyncClient]


class LMStudioClient:
    """OpenAI-compatible client for local LM Studio (chat, embeddings, vision, streaming)."""

    def __init__(self, *, client_factory: Optional[ClientFactory] = None) -> None:
        self.base_url = settings.lmstudio_base_url.rstrip("/")
        self._client_factory = client_factory
        self._client: Optional[httpx.AsyncClient] = None

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

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if settings.lmstudio_api_key:
            headers["Authorization"] = f"Bearer {settings.lmstudio_api_key}"
        return headers

    def _select_model(self, model_name: Optional[str], task_type: str, require_tools: bool) -> ModelInfo:
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

    def _serialize_messages(self, message: str, history: Optional[List[ChatMessage]]) -> List[Dict[str, str]]:
        serialized: List[Dict[str, str]] = []
        if history:
            for item in history:
                payload = item.model_dump() if hasattr(item, "model_dump") else {"role": item.role, "content": item.content}
                serialized.append(payload)
        serialized.append({"role": "user", "content": message})
        return serialized

    def _usage_stats(self, data: Dict[str, Any]) -> Dict[str, int]:
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
                    raise LMStudioClientError("LM Studio rejected the request", status=status) from exc
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
        payload: Dict[str, Any],
        *,
        timeout: Optional[float] = None,
    ) -> tuple[Dict[str, Any], int]:
        headers = self._headers()
        start = time.perf_counter()

        async def _perform() -> httpx.Response:
            client = await self._get_client()
            response = await client.post(
                url,
                json=payload,
                headers=headers,
                timeout=timeout or settings.default_timeout_seconds,
            )
            response.raise_for_status()
            return response

        response = await self._execute_with_retry(_perform)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return response.json(), elapsed_ms

    def _result_from_payload(
        self,
        model_info: ModelInfo,
        data: Dict[str, Any],
        duration_ms: int,
        response: Any,
    ) -> Dict[str, Any]:
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
        history: Optional[List[ChatMessage]] = None,
        model_name: Optional[str] = None,
        task_type: str = "chat",
        tools_required: bool = False,
    ) -> Dict[str, Any]:
        model_info = self._select_model(model_name, task_type, tools_required)
        payload = {
            "model": model_info.name,
            "messages": self._serialize_messages(message, history),
        }
        data, duration = await self._request_json(self._build_url("/chat/completions"), payload)
        reply = self._extract_text(data)
        logger.info(
            "LM Studio chat completed",
            extra={"payload": {"model": model_info.name, "duration_ms": duration}},
        )
        return self._result_from_payload(model_info, data, duration, reply)

    async def embeddings(self, text: str, *, model_name: Optional[str] = None) -> Dict[str, Any]:
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
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        model_info = self._select_model(model_name, "vision", False)
        payload = {
            "model": model_info.name,
            "messages": [
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
            ],
        }
        data, duration = await self._request_json(
            self._build_url("/chat/completions"),
            payload,
            timeout=settings.stream_timeout_seconds,
        )
        reply = self._extract_text(data)
        return self._result_from_payload(model_info, data, duration, reply)

    async def stream_chat(
        self,
        message: str,
        *,
        history: Optional[List[ChatMessage]] = None,
        model_name: Optional[str] = None,
        task_type: str = "chat",
        tools_required: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None]:
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

        try:
            async with client.stream(
                "POST",
                url,
                json=payload,
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
            raise LMStudioClientError("LM Studio streaming error", status=exc.response.status_code) from exc
        except httpx.RequestError as exc:
            raise LMStudioClientError("LM Studio streaming connection error") from exc

    @staticmethod
    def _extract_text(data: Dict[str, Any]) -> str:
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, AttributeError):
            return ""

    @staticmethod
    def _extract_embedding(data: Dict[str, Any]) -> List[float]:
        try:
            return data["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError):
            return []

