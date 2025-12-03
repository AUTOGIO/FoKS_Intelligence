from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

from app.models import ChatRequest, ChatResponse
from app.services.lmstudio_client import LMStudioClient
from app.services.logging_utils import get_logger

router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger(__name__)
lmstudio_client = LMStudioClient()


@router.post("/", response_model=ChatResponse)
async def create_chat(request: ChatRequest) -> ChatResponse:
    """Relay chat messages to the local LM Studio server."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Mensagem vazia não é permitida.")

    try:
        raw_response = await lmstudio_client.chat(request.message, request.history)
        reply = LMStudioClient.extract_reply(raw_response)
        logger.info(
            "Chat processed",
            extra={"source": request.source, "input_type": request.input_type},
        )
        return ChatResponse(reply=reply, raw=raw_response)
    except httpx.HTTPStatusError as exc:
        logger.error("LM Studio rejected the request", exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao conversar com o LM Studio.") from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error in /chat", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno no endpoint /chat.") from exc

