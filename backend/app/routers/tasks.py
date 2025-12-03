"""Tasks router for FoKS Intelligence."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models import TaskRequest, TaskResult
from app.services.logging_utils import get_logger
from app.services.task_runner import TaskRunner

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = get_logger(__name__)
runner = TaskRunner()


@router.post("/run", response_model=TaskResult)
async def run_task(request: TaskRequest) -> TaskResult:
    """Execute local automations through the TaskRunner."""
    result = runner.run(request.task_name, request.params or {})
    logger.info(
        "Task executed",
        extra={
            "task_name": request.task_name,
            "source": request.source,
            "success": result.get("success"),
        },
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return TaskResult(**result)

