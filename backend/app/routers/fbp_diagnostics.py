"""FBP diagnostics router for comprehensive readiness validation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models import FBPDiagnosticsResponse
from app.services import fbp_diagnostics
from app.services.logging_utils import get_logger

router = APIRouter(prefix="/fbp/diagnostics", tags=["fbp-diagnostics"])
logger = get_logger(__name__)


@router.post("/run", response_model=FBPDiagnosticsResponse)
async def run_fbp_diagnostics() -> FBPDiagnosticsResponse:
    """
    Run comprehensive FBP diagnostics.
    
    Performs:
    - Socket existence and accessibility check
    - Version/health information retrieval
    - Simple ping task via health endpoint
    
    Returns:
        FBPDiagnosticsResponse with diagnostic results and overall status
        
    Raises:
        HTTPException: If diagnostics fail completely (should not happen)
    """
    logger.info("FBP diagnostics endpoint requested")

    try:
        result = await fbp_diagnostics.run_fbp_diagnostics()

        logger.info(
            "FBP diagnostics completed",
            extra={
                "payload": {
                    "overall_status": result.get("overall_status"),
                    "socket_ok": result.get("socket_check", {}).get("exists", False),
                    "version_ok": result.get("version_check", {}).get("success", False),
                    "ping_ok": result.get("ping_check", {}).get("success", False),
                }
            },
        )

        return FBPDiagnosticsResponse(**result)

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "FBP diagnostics failed",
            exc_info=True,
            extra={
                "payload": {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            },
        )
        raise HTTPException(
            status_code=500,
            detail=f"FBP diagnostics failed: {str(exc)}",
        ) from exc
