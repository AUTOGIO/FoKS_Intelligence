"""Tasks router for FoKS Intelligence."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.models import NFAATFTaskArgs, TaskRequest, TaskResult
from app.services.logging_utils import get_logger
from app.services.task_runner import TaskRunner

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = get_logger(__name__)
task_runner = TaskRunner()


# Use models from models.py
NFAATFRequest = NFAATFTaskArgs  # Alias for backward compatibility


@router.post("/run", response_model=TaskResult)
async def run_task(request: TaskRequest) -> TaskResult:
    """Execute an automation task via the shared TaskRunner."""
    result = await task_runner.run_task(
        task_type=request.type,
        args=request.args or {},
        timeout=request.timeout,
    )
    logger.info(
        "Task dispatched",
        extra={"payload": {"task": request.type, "success": result["success"], "source": request.source}},
    )
    return TaskResult(**result)


@router.post("/run/nfa-atf", response_model=dict[str, Any])
async def run_nfa_atf(request: NFAATFRequest) -> dict[str, Any]:
    """
    Execute NFA ATF automation task.

    This endpoint runs the Playwright automation script to:
    1. Log into ATF system
    2. Navigate to FIS_308
    3. Fill filters and select NFA
    4. Download DANFE and DAR PDFs

    Returns structured result with file paths.
    """
    args = {
        "from_date": request.from_date,
        "to_date": request.to_date,
        "matricula": request.matricula,
    }

    if request.nfa_number:
        args["nfa_number"] = request.nfa_number

    result = await task_runner.run_task(
        task_type="nfa_atf",
        args=args,
        timeout=900,  # 15 minutes as per requirements
    )

    logger.info(
        "NFA ATF task dispatched",
        extra={
            "payload": {
                "task": "nfa_atf",
                "success": result["success"],
                "from_date": request.from_date,
                "to_date": request.to_date,
                "matricula": request.matricula,
            }
        },
    )

    # Transform TaskRunner result to structured response format
    if result["success"] and result.get("payload"):
        payload = result["payload"]
        return {
            "task": "nfa_atf",
            "status": "success",
            "pdf_paths": {
                "danfe": payload.get("danfe_path"),
                "dar": payload.get("dar_path"),
            },
            "logs": payload.get("logs", ""),
            "metadata": {
                "nfa_number": payload.get("nfa_number"),
                "duration_ms": result.get("duration_ms", 0),
            },
        }
    else:
        # Error case - extract error details from payload if available
        error_payload = result.get("payload", {})
        error_message = result.get("error", "Unknown error")

        return {
            "task": "nfa_atf",
            "status": "error",
            "pdf_paths": {
                "danfe": error_payload.get("danfe_path"),
                "dar": error_payload.get("dar_path"),
            },
            "logs": error_payload.get("logs", error_message),
            "metadata": {
                "error": error_message,
                "error_type": error_payload.get("error_type"),
                "duration_ms": result.get("duration_ms", 0),
            },
        }

