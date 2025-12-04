"""Tasks router for FoKS Intelligence."""

from __future__ import annotations

from fastapi import APIRouter

from app.models import TaskRequest, TaskResult
from app.services.logging_utils import get_logger
from app.services.task_runner import TaskRunner

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = get_logger(__name__)
task_runner = TaskRunner()


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

