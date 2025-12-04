from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from app.services import model_registry
from app.services.model_registry import ModelInfo


@pytest.fixture(autouse=True)
def _reload_registry(monkeypatch, tmp_path):
    mock_dir = tmp_path / "models"
    mock_dir.mkdir(parents=True, exist_ok=True)
    (mock_dir / "bitznbrewz").mkdir()
    monkeypatch.setattr("app.services.model_registry.settings.model_directories", [str(mock_dir)])
    model_registry.refresh_registry()
    yield
    model_registry.refresh_registry()


def test_list_models_returns_all_categories():
    categories = {info.category for info in model_registry.list_models()}
    assert {"chat", "reasoning", "embeddings", "vision", "scientific"}.issubset(categories)


def test_resolve_model_contains_metadata():
    info = model_registry.resolve_model("qwen3-14b-mlx")
    assert isinstance(info, ModelInfo)
    assert info.format == "mlx"
    assert info.quantization
    assert isinstance(info.model_path, Path)


def test_get_default_model_by_task():
    chat_model = model_registry.get_default_model("chat")
    assert chat_model.category == "chat"

    vision_model = model_registry.get_default_model("vision")
    assert vision_model.supports_vision


def test_resolve_invalid_model():
    with pytest.raises(ValueError):
        model_registry.resolve_model("non-existent-model")

