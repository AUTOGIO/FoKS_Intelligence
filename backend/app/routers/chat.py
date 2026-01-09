from __future__ import annotations

import json
import time

from app.models import ChatRequest, ChatResponse
from app.services import chat_service
from app.services.lmstudio_client import LMStudioClientError
from app.services.logging_utils import get_logger
from app.services.system_monitor import SystemMonitor
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger(__name__)


@router.post("/", response_model=ChatResponse)
async def create_chat(request: ChatRequest) -> ChatResponse:
    """
    Relay chat messages to the local LM Studio server.

    Automatically injects real-time system telemetry into each request
    to enable accurate system status queries.
    """
    # Fix: Sanitize input string - strip leading/trailing quotes
    # that might come from Raycast
    sanitized_message = request.message.strip('"').strip("'").strip()
    # #region agent log
    try:
        log_data = {
            "sessionId": "debug-session",
            "runId": "post-fix-v3",
            "hypothesisId": "C",
            "location": "chat.py:19",
            "message": "Message sanitization",
            "data": {
                "original_message": request.message,
                "sanitized_message": sanitized_message,
                "message_repr": repr(sanitized_message),
                "message_bytes": sanitized_message.encode("utf-8").hex(),
            },
            "timestamp": int(time.time() * 1000),
        }
        log_path = (
            "/Users/dnigga/Documents/_PROJECTS_OFICIAL/" "FoKS_Intelligence/.cursor/debug.log"
        )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Ignore logging errors
    # #endregion
    if not sanitized_message or not sanitized_message.strip():
        raise HTTPException(
            status_code=400,
            detail="Mensagem vazia não é permitida.",
        )

    metadata = request.metadata or {}
    task_type = metadata.get("task_type", "chat")
    tools_required = bool(metadata.get("tools_required"))

    # Generate System Context and inject into user message
    # This provides real-time telemetry to the LLM for accurate
    # status queries
    try:
        system_context = SystemMonitor.get_context_block()
        augmented_message = f"{system_context}\n\nUSER REQUEST: {sanitized_message}"
    except Exception as e:
        # If context generation fails, proceed without it but log
        logger.warning(
            "System context generation failed, proceeding without " "telemetry",
            extra={
                "payload": {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            },
        )
        augmented_message = sanitized_message

    try:
        result = await chat_service.generate_chat_response(
            augmented_message,
            history=request.history,
            stream=False,
            model=request.model,
            task_type=task_type,
            tools_required=tools_required,
        )
    except LMStudioClientError as exc:
        logger.error(
            "LM Studio rejected chat request",
            extra={"payload": {"error": str(exc)}},
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error in /chat", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno no endpoint /chat.") from exc

    reply = result.get("response", "")
    return ChatResponse(reply=reply, raw=result)
