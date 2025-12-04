from __future__ import annotations

import base64
from typing import Optional

from app.services import model_registry
from app.services.logging_utils import get_logger
from app.services.lmstudio_client import LMStudioClient
from app.services.model_registry import ModelInfo

logger = get_logger(__name__)
_CLIENT = LMStudioClient()


def _select_model(model: Optional[str]) -> ModelInfo:
    if model:
        return model_registry.resolve_model(model)
    return model_registry.get_default_model("vision")


async def analyze_image(
    image_bytes: bytes,
    prompt: str,
    *,
    model: Optional[str] = None,
) -> dict:
    if not image_bytes:
        raise ValueError("image_bytes must not be empty")
    model_info = _select_model(model)
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    logger.info(
        "Dispatching LM Studio vision request",
        extra={"payload": {"model": model_info.name, "prompt_length": len(prompt)}},
    )
    return await _CLIENT.vision(
        image_base64=encoded,
        prompt=prompt,
        model_name=model_info.name,
    )

