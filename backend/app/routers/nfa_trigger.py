"""NFA trigger router for CPF-based NFA automation."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

from app.models import NFATriggerRequest, NFATriggerResponse
from app.services.logging_utils import get_logger
from app.services.task_runner import TaskRunner
from app.utils.validators import validate_cpf

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = get_logger(__name__)
task_runner = TaskRunner()


def _calculate_default_date_range(days_back: int = 30) -> tuple[str, str]:
    """
    Calculate default date range for NFA automation.

    Args:
        days_back: Number of days to look back (default: 30)

    Returns:
        Tuple of (from_date, to_date) in DD/MM/YYYY format
    """
    today = datetime.now()
    from_date_obj = today - timedelta(days=days_back)

    from_date = from_date_obj.strftime("%d/%m/%Y")
    to_date = today.strftime("%d/%m/%Y")

    return from_date, to_date


@router.post("/nfa", response_model=NFATriggerResponse)
async def trigger_nfa(request: NFATriggerRequest) -> NFATriggerResponse:
    """
    Trigger NFA automation for a given CPF.

    Uses NFA_ATF automation script with smart date defaults (last 30 days).
    This endpoint bypasses FBP and uses the direct Playwright automation.

    Args:
        request: NFATriggerRequest with CPF and test flag

    Returns:
        NFATriggerResponse with success status, message, and automation result

    Raises:
        HTTPException: If CPF validation fails or automation fails
    """
    logger.info(
        "NFA trigger requested",
        extra={
            "payload": {
                "cpf_length": len(request.cpf),
                "test_mode": request.test,
            }
        },
    )

    # Validate CPF
    is_valid, error_message = validate_cpf(request.cpf)
    if not is_valid:
        logger.warning(
            "Invalid CPF format",
            extra={"payload": {"cpf_length": len(request.cpf)}},
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CPF format: {error_message}",
        )

    # Calculate smart date range (last 30 days by default)
    from_date, to_date = _calculate_default_date_range(days_back=30)

    logger.info(
        "Using default date range for NFA automation",
        extra={
            "payload": {
                "from_date": from_date,
                "to_date": to_date,
                "cpf": request.cpf[:3] + "***",  # Partial CPF for logging
            }
        },
    )

    # Prepare task arguments for NFA_ATF automation
    task_args = {
        "from_date": from_date,
        "to_date": to_date,
        "matricula": "1595504",  # Default matricula
        "headless": True,
    }

    try:
        # Execute NFA_ATF automation via TaskRunner
        result = await task_runner.run_task(
            task_type="nfa_atf",
            args=task_args,
            timeout=900,  # 15 minutes
        )

        # Extract result details
        success = result.get("success", False)
        payload = result.get("payload", {})
        error = result.get("error")

        if success and payload:
            # Automation completed successfully
            nfa_number = payload.get("nfa_number", "unknown")
            danfe_path = payload.get("danfe_path")
            dar_path = payload.get("dar_path")

            message = f"NFA automation completed successfully (NFA: {nfa_number})"

            logger.info(
                "NFA trigger successful",
                extra={
                    "payload": {
                        "cpf_length": len(request.cpf),
                        "test_mode": request.test,
                        "nfa_number": nfa_number,
                        "has_danfe": bool(danfe_path),
                        "has_dar": bool(dar_path),
                    }
                },
            )

            # Build response with automation results
            fbp_response = {
                "status": 200,
                "payload": {
                    "success": True,
                    "message": message,
                    "nfa_number": nfa_number,
                    "danfe_path": danfe_path,
                    "dar_path": dar_path,
                    "from_date": from_date,
                    "to_date": to_date,
                },
            }
        else:
            # Automation failed
            error_msg = error or payload.get("message") or "NFA automation failed"
            message = f"NFA automation failed: {error_msg}"

            logger.warning(
                "NFA trigger failed",
                extra={
                    "payload": {
                        "cpf_length": len(request.cpf),
                        "test_mode": request.test,
                        "error": error_msg,
                    }
                },
            )

            fbp_response = {
                "status": 500,
                "payload": {
                    "success": False,
                    "error": error_msg,
                    "message": message,
                },
            }

        return NFATriggerResponse(
            success=success,
            message=message,
            fbp_response=fbp_response,
        )

    except Exception as exc:  # noqa: BLE001
        error_msg = f"Internal error during NFA automation: {str(exc)}"
        logger.error(
            "Unexpected error during NFA trigger",
            exc_info=True,
            extra={
                "payload": {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "cpf_length": len(request.cpf),
                }
            },
        )

        return NFATriggerResponse(
            success=False,
            message=error_msg,
            fbp_response={
                "status": 500,
                "payload": {
                    "success": False,
                    "error": str(exc),
                },
            },
        )
