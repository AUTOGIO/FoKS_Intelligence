from __future__ import annotations

from fastapi import APIRouter

from app.models import VisionRequest, VisionResponse
from app.services.logging_utils import get_logger

router = APIRouter(prefix="/vision", tags=["vision"])
logger = get_logger(__name__)


@router.post("/analyze", response_model=VisionResponse)
async def analyze(request: VisionRequest) -> VisionResponse:
    """Placeholder endpoint until the vision stack is wired up."""
    summary = (
        "Requisição registrada. A camada de visão ainda será conectada ao LM Studio."
    )
    logger.info("Vision placeholder called", extra={"source": request.metadata})
    return VisionResponse(
        summary=summary,
        details={
            "description": request.description,
            "metadata": request.metadata or {},
            "note": "Vision model not yet implemented",
        },
    )

