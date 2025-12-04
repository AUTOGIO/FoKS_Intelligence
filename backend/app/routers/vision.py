from __future__ import annotations

import base64
from binascii import Error as BinasciiError

from fastapi import APIRouter, HTTPException

from app.models import VisionRequest, VisionResponse
from app.services import vision_service
from app.services.lmstudio_client import LMStudioClientError
from app.services.logging_utils import get_logger

router = APIRouter(prefix="/vision", tags=["vision"])
logger = get_logger(__name__)


def _decode_image(encoded: str) -> bytes:
    try:
        return base64.b64decode(encoded)
    except (BinasciiError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Imagem em base64 inválida.") from exc


@router.post("/analyze", response_model=VisionResponse)
async def analyze(request: VisionRequest) -> VisionResponse:
    """Analyze an image using local LM Studio multimodal capabilities."""
    if not request.image_base64:
        raise HTTPException(
            status_code=400,
            detail="O campo 'image_base64' é obrigatório enquanto não houver captura automática.",
        )

    image_bytes = _decode_image(request.image_base64)
    metadata = request.metadata or {}

    try:
        result = await vision_service.analyze_image(
            image_bytes,
            request.description,
            model=metadata.get("model"),
        )
    except LMStudioClientError as exc:
        logger.error("Vision request rejected", extra={"payload": {"error": str(exc)}})
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error in /vision", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno no endpoint /vision.") from exc

    summary = result.get("response") or "Vision response generated."
    details = {
        "model": result.get("model"),
        "provider": result.get("provider"),
        "metadata": metadata,
        "raw": result,
    }
    return VisionResponse(summary=summary, details=details)

