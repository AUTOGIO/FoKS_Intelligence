from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models import ChatRequest, ChatResponse
from app.services import chat_service
from app.services.lmstudio_client import LMStudioClientError
from app.services.logging_utils import get_logger

router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger(__name__)


@router.post("/", response_model=ChatResponse)
async def create_chat(request: ChatRequest) -> ChatResponse:
    """Relay chat messages to the local LM Studio server."""
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Mensagem vazia não é permitida.",
        )

    metadata = request.metadata or {}
    task_type = metadata.get("task_type", "chat")
    tools_required = bool(metadata.get("tools_required"))

    try:
        result = await chat_service.generate_chat_response(
            request.message,
            history=request.history,
            stream=False,
            model=request.model,
            task_type=task_type,
            tools_required=tools_required,
        )
    except LMStudioClientError as exc:
        logger.error("LM Studio rejected chat request", extra={"payload": {"error": str(exc)}})
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error in /chat", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno no endpoint /chat.") from exc

    reply = result.get("response", "")
    return ChatResponse(reply=reply, raw=result)

