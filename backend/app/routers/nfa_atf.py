"""NFA ATF router for FoKS Intelligence."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.models import TaskResult
from app.services.logging_utils import get_logger
from app.services.task_runner import TaskRunner

router = APIRouter(prefix="/tasks/nfa_atf", tags=["nfa_atf"])
logger = get_logger(__name__)
task_runner = TaskRunner()


class NFAATFRequest(BaseModel):
    """Request model for NFA ATF automation."""

    from_date: str = Field(..., description="Start date in dd/mm/yyyy format")
    to_date: str = Field(..., description="End date in dd/mm/yyyy format")
    matricula: str | None = Field(None, description="Matricula number (optional)")
    output_dir: str | None = Field(
        None,
        description=(
            "Output directory for PDFs "
            "(defaults to /Users/dnigga/Downloads/NFA_Outputs)"
        ),
    )
    headless: bool = Field(True, description="Run browser in headless mode")
    nfa_number: str | None = Field(
        None, description="Specific NFA number to select (optional)"
    )
    timeout: int | None = Field(
        None, description="Timeout in seconds (default: 600)"
    )


@router.post("/run", response_model=TaskResult)
async def run_nfa_atf(request: NFAATFRequest) -> TaskResult:
    """
    Execute NFA ATF automation task.

    This endpoint runs the Playwright automation script to:
    1. Log into ATF system
    2. Navigate to FIS_308
    3. Fill filters and select NFA
    4. Download DANFE (Imprimir) PDF - first action
    5. Download Taxa Serviço PDF - second action

    Both downloads execute in sequence for each NFA.

    Returns structured result with file paths.
    """
    args = {
        "from_date": request.from_date,
        "to_date": request.to_date,
    }

    if request.matricula:
        args["matricula"] = request.matricula
    if request.output_dir:
        args["output_dir"] = request.output_dir
    if request.nfa_number:
        args["nfa_number"] = request.nfa_number
    args["headless"] = request.headless

    result = await task_runner.run_task(
        task_type="nfa_atf",
        args=args,
        timeout=request.timeout or 600,
    )

    logger.info(
        "NFA ATF task dispatched",
        extra={
            "payload": {
                "task": "nfa_atf",
                "success": result["success"],
                "from_date": request.from_date,
                "to_date": request.to_date,
            }
        },
    )

    return TaskResult(**result)


@router.get("/validate")
async def validate_nfa_atf() -> dict[str, Any]:
    """
    Validate NFA ATF automation setup.

    Checks:
    - Script file exists
    - Script is executable
    - Configuration file exists
    - Output directory is writable

    Returns validation status.
    """
    from pathlib import Path

    validation_results = {
        "status": "ok",
        "checks": {},
        "errors": [],
    }

    # Check script exists
    script_path = Path(__file__).resolve().parent.parent.parent.parent / "ops" / "scripts" / "nfa" / "nfa_atf.py"
    if script_path.exists():
        validation_results["checks"]["script_exists"] = True
        validation_results["checks"]["script_path"] = str(script_path)
    else:
        validation_results["status"] = "error"
        validation_results["checks"]["script_exists"] = False
        validation_results["errors"].append(f"Script not found: {script_path}")

    # Check config exists
    config_path = script_path.parent / "config.json"
    if config_path.exists():
        validation_results["checks"]["config_exists"] = True
    else:
        validation_results["status"] = "error"
        validation_results["checks"]["config_exists"] = False
        validation_results["errors"].append(f"Config not found: {config_path}")

    # Check output directory
    output_dir = Path("/Users/dnigga/Downloads/NFA_Outputs")
    if output_dir.exists() and output_dir.is_dir():
        if os.access(output_dir, os.W_OK):
            validation_results["checks"]["output_dir_writable"] = True
        else:
            validation_results["status"] = "error"
            validation_results["checks"]["output_dir_writable"] = False
            validation_results["errors"].append(f"Output directory not writable: {output_dir}")
    else:
        validation_results["status"] = "error"
        validation_results["checks"]["output_dir_writable"] = False
        validation_results["errors"].append(f"Output directory not found: {output_dir}")

    logger.info(
        "NFA ATF validation completed",
        extra={"payload": validation_results},
    )

    return validation_results

