from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.models import ChatMessage
from app.services import model_registry
from app.services.lmstudio_client import LMStudioClient, LMStudioClientError
from app.services.model_registry import ModelInfo


class _DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class _DummyStream:
    def __init__(self, lines):
        self._lines = lines

    def raise_for_status(self):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _DummyClient:
    def __init__(self, payload, *, stream_lines=None, side_effect=None):
        self._payload = payload
        self._side_effect = side_effect
        self._stream_lines = stream_lines or []
        self.post = AsyncMock(side_effect=self._post)

    async def _post(self, *args, **kwargs):
        if self._side_effect:
            raise self._side_effect
        return _DummyResponse(self._payload)

    def stream(self, *args, **kwargs):
        return _DummyStream(self._stream_lines)

    async def aclose(self):
        return None


@pytest.fixture
def fake_model(tmp_path: Path) -> ModelInfo:
    return ModelInfo(
        name="qwen3-14b-mlx",
        category="chat",
        model_path=tmp_path / "model",
        format="mlx",
        quantization="4bit",
        max_context=8192,
        supports_tools=True,
    )


@pytest.fixture(autouse=True)
def _mock_registry(monkeypatch, fake_model):
    monkeypatch.setattr(model_registry, "resolve_model", lambda name: fake_model)
    monkeypatch.setattr(model_registry, "get_default_model", lambda task: fake_model)
    monkeypatch.setattr(model_registry, "list_models", lambda: [fake_model])


@pytest.mark.asyncio
async def test_chat_returns_structured_payload(fake_model):
    payload = {
        "choices": [{"message": {"content": "Hello"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    client = LMStudioClient(client_factory=lambda: _DummyClient(payload))
    result = await client.chat("oi")
    assert result["model"] == fake_model.name
    assert result["response"] == "Hello"
    assert result["input_tokens"] == 10


@pytest.mark.asyncio
async def test_stream_chat_yields_chunks():
    stream_lines = [
        'data: {"choices": [{"delta": {"content": "Olá"}}]}',
        'data: {"choices": [{"delta": {"content": " mundo"}, "finish_reason": "stop"}]}',
        "data: [DONE]",
    ]
    client = LMStudioClient(client_factory=lambda: _DummyClient({}, stream_lines=stream_lines))
    chunks = []
    async for item in client.stream_chat("oi", history=[ChatMessage(role="user", content="a")]):
        chunks.append(item)
    assert chunks[0]["response"] == "Olá"
    assert chunks[-1]["done"] is True


@pytest.mark.asyncio
async def test_embeddings_returns_vector():
    payload = {"data": [{"embedding": [0.1, 0.2]}], "usage": {"prompt_tokens": 2, "completion_tokens": 0}}
    client = LMStudioClient(client_factory=lambda: _DummyClient(payload))
    result = await client.embeddings("texto")
    assert result["response"] == [0.1, 0.2]


@pytest.mark.asyncio
async def test_request_error_raises_client_error():
    request = httpx.Request("POST", "http://localhost")
    side_effect = httpx.RequestError("boom", request=request)
    client = LMStudioClient(client_factory=lambda: _DummyClient({}, side_effect=side_effect))
    with pytest.raises(LMStudioClientError):
        await client.chat("oi")
