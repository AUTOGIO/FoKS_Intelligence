"""NFA Intelligence router for batch processing and reporting."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.logging_utils import get_logger
from app.services.nfa_intelligence import NFAIntelligenceService

router = APIRouter(prefix="/nfa/intelligence", tags=["nfa_intelligence"])
logger = get_logger(__name__)
nfa_intelligence = NFAIntelligenceService()


class EmployeeItem(BaseModel):
    """Employee item model."""

    loja: str = Field(..., description="Loja identifier")
    cpf: str = Field(..., description="CPF (Brazilian tax ID)")
    matricula: str | None = Field(None, description="Optional matricula (defaults to loja)")


class NFAIntelligenceRequest(BaseModel):
    """Request model for NFA Intelligence batch processing."""

    from_date: str = Field(..., description="Start date in dd/mm/yyyy format")
    to_date: str = Field(..., description="End date in dd/mm/yyyy format")
    employees: str | list[EmployeeItem] = Field(
        ...,
        description=(
            "Either 'auto' to load from FBP_Backend/data_input_final, "
            "or a list of employee items"
        ),
    )
    headless: bool = Field(True, description="Run browser in headless mode")


class NFAIntelligenceResponse(BaseModel):
    """Response model for NFA Intelligence batch processing."""

    status: str = Field(..., description="Status: 'success' or 'error'")
    report_path: str | None = Field(None, description="Path to generated report file")
    summary: dict[str, Any] = Field(..., description="Summary statistics")
    error: str | None = Field(None, description="Error message if status is 'error'")


@router.post("/run", response_model=NFAIntelligenceResponse)
async def run_nfa_intelligence(request: NFAIntelligenceRequest) -> NFAIntelligenceResponse:
    """
    Execute NFA Intelligence batch processing.

    This endpoint:
    1. Loads employee list (auto or provided)
    2. Runs NFA/ATF automation for each employee
    3. Generates a comprehensive report
    4. Returns summary and report path

    Returns structured result with report path and summary statistics.
    """
    logger.info(
        "NFA Intelligence batch request received",
        extra={
            "payload": {
                "from_date": request.from_date,
                "to_date": request.to_date,
                "employees_type": "auto" if request.employees == "auto" else "provided",
                "headless": request.headless,
            }
        },
    )

    try:
        # Load employee list
        if request.employees == "auto":
            employees_list = await nfa_intelligence.load_employees_from_file()
            if not employees_list:
                raise HTTPException(
                    status_code=400,
                    detail="No employees found in data_input_final file. Check file path and format.",
                )
            logger.info(
                "Loaded employees from file",
                extra={"payload": {"count": len(employees_list)}},
            )
        else:
            # Convert Pydantic models to dicts
            if isinstance(request.employees, list):
                employees_list = [item.model_dump() for item in request.employees]
            else:
                # Fallback (should not happen due to Pydantic validation)
                employees_list = []
            logger.info(
                "Using provided employee list",
                extra={"payload": {"count": len(employees_list)}},
            )

        # Run batch processing
        batch_results = await nfa_intelligence.run_batch(
            items_list=employees_list,
            from_date=request.from_date,
            to_date=request.to_date,
            headless=request.headless,
        )

        # Generate report
        report_path = await nfa_intelligence.generate_report(
            batch_results=batch_results,
            from_date=request.from_date,
            to_date=request.to_date,
        )

        # Extract summary from report
        import json

        with open(report_path, encoding="utf-8") as f:
            report_data = json.load(f)
            summary = report_data.get("summary", {})

        logger.info(
            "NFA Intelligence batch completed",
            extra={
                "payload": {
                    "report_path": report_path,
                    "total_items": summary.get("total_items", 0),
                    "success_count": summary.get("success_count", 0),
                    "failure_count": summary.get("failure_count", 0),
                }
            },
        )

        return NFAIntelligenceResponse(
            status="success",
            report_path=report_path,
            summary=summary,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "NFA Intelligence batch failed",
            exc_info=True,
            extra={"payload": {"error": str(e), "error_type": type(e).__name__}},
        )
        raise HTTPException(
            status_code=500,
            detail=f"NFA Intelligence batch processing failed: {str(e)}",
        ) from e


@router.get("/validate")
async def validate_nfa_intelligence() -> dict[str, Any]:
    """
    Validate NFA Intelligence layer setup.

    Checks:
    - Service can be instantiated
    - Employee loader can access data file
    - Reports directory exists and is writable
    - All dependencies are available

    Returns validation status.
    """
    from pathlib import Path

    validation_results = {
        "status": "ok",
        "checks": {},
        "errors": [],
        "summary": {},
    }

    try:
        # Check service instantiation
        try:
            service = NFAIntelligenceService()
            validation_results["checks"]["service_instantiation"] = True
        except Exception as e:
            validation_results["status"] = "error"
            validation_results["checks"]["service_instantiation"] = False
            validation_results["errors"].append(f"Service instantiation failed: {str(e)}")

        # Check reports directory
        reports_dir = Path(__file__).resolve().parent.parent.parent.parent / "reports"
        if reports_dir.exists() and reports_dir.is_dir():
            import os

            if os.access(reports_dir, os.W_OK):
                validation_results["checks"]["reports_dir_writable"] = True
            else:
                validation_results["status"] = "error"
                validation_results["checks"]["reports_dir_writable"] = False
                validation_results["errors"].append(f"Reports directory not writable: {reports_dir}")
        else:
            validation_results["status"] = "error"
            validation_results["checks"]["reports_dir_writable"] = False
            validation_results["errors"].append(f"Reports directory not found: {reports_dir}")

        # Check employee data file (optional - may not exist)
        employee_file = Path("/Users/dnigga/Documents/FBP_Backend/data_input_final")
        if employee_file.exists():
            validation_results["checks"]["employee_file_exists"] = True
            validation_results["checks"]["employee_file_path"] = str(employee_file)
        else:
            validation_results["checks"]["employee_file_exists"] = False
            validation_results["checks"]["employee_file_path"] = str(employee_file)
            # Not an error - file is optional

        # Try to load employees (if file exists)
        if employee_file.exists():
            try:
                employees = await nfa_intelligence.load_employees_from_file(str(employee_file))
                validation_results["checks"]["employee_loader_works"] = True
                validation_results["summary"]["employee_count"] = len(employees)
            except Exception as e:
                validation_results["status"] = "error"
                validation_results["checks"]["employee_loader_works"] = False
                validation_results["errors"].append(f"Employee loader failed: {str(e)}")

        logger.info(
            "NFA Intelligence validation completed",
            extra={"payload": validation_results},
        )

    except Exception as e:
        validation_results["status"] = "error"
        validation_results["errors"].append(f"Validation failed: {str(e)}")
        logger.error(
            "NFA Intelligence validation error",
            exc_info=True,
            extra={"payload": {"error": str(e)}},
        )

    return validation_results
