from __future__ import annotations

from typing import Any

from app.models import ChatMessage
from app.services import model_registry
from app.services.lmstudio_client import LMStudioClient
from app.services.logging_utils import get_logger
from app.services.model_registry import ModelInfo

logger = get_logger(__name__)
_CLIENT = LMStudioClient()


def _select_model(model: str | None, task_type: str, tools_required: bool) -> ModelInfo:
    if model:
        return model_registry.resolve_model(model)
    if tools_required:
        for entry in model_registry.list_models():
            if entry.supports_tools:
                return entry
    return model_registry.get_default_model(task_type)


async def generate_chat_response(
    message: str,
    *,
    history: list[ChatMessage] | None = None,
    stream: bool = False,
    model: str | None = None,
    task_type: str = "chat",
    tools_required: bool = False,
) -> Any:
    model_info = _select_model(model, task_type, tools_required)
    logger.info(
        "Dispatching LM Studio chat",
        extra={"payload": {"model": model_info.name, "stream": stream, "task_type": task_type}},
    )
    if stream:
        return _CLIENT.stream_chat(
            message,
            history=history,
            model_name=model_info.name,
            task_type=task_type,
            tools_required=tools_required,
        )
    return await _CLIENT.chat(
        message,
        history=history,
        model_name=model_info.name,
        task_type=task_type,
        tools_required=tools_required,
    )

