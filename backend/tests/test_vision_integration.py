from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import model_registry, vision_service
from app.services.model_registry import ModelInfo


@pytest.fixture
def fake_model(tmp_path: Path) -> ModelInfo:
    return ModelInfo(
        name="qwen3-vision-mlx",
        category="vision",
        model_path=tmp_path / "model",
        format="mlx",
        quantization="full",
        max_context=65536,
        supports_vision=True,
    )


@pytest.fixture(autouse=True)
def _mock_registry(monkeypatch, fake_model):
    monkeypatch.setattr(model_registry, "resolve_model", lambda name: fake_model)
    monkeypatch.setattr(model_registry, "get_default_model", lambda task: fake_model)


@pytest.mark.asyncio
async def test_analyze_image_calls_lmstudio(monkeypatch):
    fake_result = {
        "model": "qwen3-vision-mlx",
        "provider": "lmstudio",
        "duration_ms": 1,
        "input_tokens": 0,
        "output_tokens": 0,
        "response": "ok",
    }
    dummy_client = MagicMock()
    dummy_client.vision = AsyncMock(return_value=fake_result)
    monkeypatch.setattr(vision_service, "_CLIENT", dummy_client)

    image = b"\x89PNG"
    result = await vision_service.analyze_image(image, "describe this")

    dummy_client.vision.assert_awaited()
    assert result["response"] == "ok"
    assert result["model"] == "qwen3-vision-mlx"


@pytest.mark.asyncio
async def test_analyze_image_requires_bytes():
    with pytest.raises(ValueError):
        await vision_service.analyze_image(b"", "prompt")
