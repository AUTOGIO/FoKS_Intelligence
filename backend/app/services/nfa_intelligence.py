"""NFA Intelligence Service for batch processing and reporting."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT
from app.services.logging_utils import get_logger
from app.services.task_runner import TaskRunner

logger = get_logger(__name__)

# Reports directory
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Maximum concurrency for batch processing (CPU-safe)
MAX_CONCURRENT_NFA_TASKS = 3


class NFAIntelligenceService:
    """Service for intelligent NFA/ATF batch processing and reporting."""

    def __init__(self):
        """Initialize NFA Intelligence Service."""
        self.task_runner = TaskRunner()

    async def run_batch(
        self,
        items_list: list[dict[str, Any]],
        from_date: str,
        to_date: str,
        headless: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Run NFA/ATF automation for a batch of employees.

        Args:
            items_list: List of dictionaries with 'loja' and 'cpf' keys
            from_date: Start date in dd/mm/yyyy format
            to_date: End date in dd/mm/yyyy format
            headless: Run browser in headless mode

        Returns:
            List of result dictionaries with normalized data
        """
        logger.info(
            "Starting NFA batch processing",
            extra={
                "payload": {
                    "item_count": len(items_list),
                    "from_date": from_date,
                    "to_date": to_date,
                    "headless": headless,
                }
            },
        )

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_NFA_TASKS)
        results: list[dict[str, Any]] = []

        async def process_item(item: dict[str, Any]) -> dict[str, Any]:
            """Process a single employee item."""
            async with semaphore:
                loja = item.get("loja", "")
                cpf = item.get("cpf", "")
                # Use loja as matricula if not provided
                matricula = item.get("matricula", loja)

                logger.info(
                    "Processing NFA item",
                    extra={
                        "payload": {
                            "loja": loja,
                            "cpf": cpf,
                            "matricula": matricula,
                        }
                    },
                )

                try:
                    # Call TaskRunner for this employee
                    task_result = await self.task_runner.run_task(
                        task_type="nfa_atf",
                        args={
                            "from_date": from_date,
                            "to_date": to_date,
                            "matricula": matricula,
                            "headless": headless,
                        },
                        timeout=600,  # 10 minutes per task
                    )

                    # Normalize result
                    normalized = await self.normalize_result(
                        task_result,
                        employee_data={"loja": loja, "cpf": cpf, "matricula": matricula},
                    )

                    logger.info(
                        "NFA item processed successfully",
                        extra={"payload": {"loja": loja, "success": normalized.get("success", False)}},
                    )

                    return normalized

                except Exception as e:
                    logger.error(
                        "NFA item processing failed",
                        exc_info=True,
                        extra={
                            "payload": {
                                "loja": loja,
                                "cpf": cpf,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            }
                        },
                    )

                    # Return error result (resumable batch - continue on failure)
                    return {
                        "success": False,
                        "employee": {"loja": loja, "cpf": cpf, "matricula": matricula},
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "error_classification": self._classify_error(e),
                        "nfa_count": 0,
                        "pdfs": [],
                        "timestamp": datetime.now().isoformat(),
                    }

        # Process all items with controlled concurrency
        tasks = [process_item(item) for item in items_list]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        logger.info(
            "NFA batch processing completed",
            extra={
                "payload": {
                    "total_items": len(items_list),
                    "results_count": len(results),
                    "success_count": sum(1 for r in results if r.get("success", False)),
                    "failure_count": sum(1 for r in results if not r.get("success", False)),
                }
            },
        )

        return results

    async def normalize_result(
        self,
        result_dict: dict[str, Any],
        employee_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Normalize TaskRunner result into structured format.

        Args:
            result_dict: TaskRunner result dictionary
            employee_data: Optional employee data (loja, cpf, matricula)

        Returns:
            Normalized result dictionary
        """
        success = result_dict.get("success", False)
        payload = result_dict.get("payload", {})
        error = result_dict.get("error")

        # Extract NFA data from payload
        nfa_status = payload.get("status", "unknown")
        nfa_number = payload.get("nfa_number")
        danfe_path = payload.get("danfe_path", "")
        dar_path = payload.get("dar_path", "")

        # Count NFAs (1 if we have an NFA number, 0 otherwise)
        nfa_count = 1 if nfa_number and nfa_number != "unknown" else 0

        # Collect PDF paths
        pdfs = []
        if danfe_path:
            pdfs.append({"type": "DANFE", "path": danfe_path})
        if dar_path:
            pdfs.append({"type": "DAR", "path": dar_path})

        # Build normalized result
        normalized = {
            "success": success and nfa_status == "success",
            "employee": employee_data or {},
            "nfa_count": nfa_count,
            "nfa_number": nfa_number if nfa_number and nfa_number != "unknown" else None,
            "pdfs": pdfs,
            "danfe_path": danfe_path if danfe_path else None,
            "dar_path": dar_path if dar_path else None,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": result_dict.get("duration_ms", 0),
        }

        # Add error information if present
        if error or nfa_status == "error":
            normalized["error"] = error or payload.get("error", "Unknown error")
            normalized["error_type"] = "TaskRunnerError"
            normalized["error_classification"] = self._classify_error_from_message(
                normalized["error"]
            )

        return normalized

    def _classify_error(self, exception: Exception) -> str:
        """
        Classify error type for reporting.

        Args:
            exception: Exception object

        Returns:
            Error classification string
        """
        error_msg = str(exception).lower()

        if "login" in error_msg or "credential" in error_msg or "authentication" in error_msg:
            return "authentication_error"
        if "timeout" in error_msg:
            return "timeout_error"
        if "not found" in error_msg or "missing" in error_msg:
            return "not_found_error"
        if "download" in error_msg or "pdf" in error_msg:
            return "download_error"
        if "network" in error_msg or "connection" in error_msg:
            return "network_error"

        return "unknown_error"

    def _classify_error_from_message(self, error_message: str) -> str:
        """Classify error from error message string."""
        if not error_message:
            return "unknown_error"
        return self._classify_error(Exception(error_message))

    async def generate_report(
        self,
        batch_results: list[dict[str, Any]],
        from_date: str,
        to_date: str,
    ) -> str:
        """
        Generate JSON report from batch results.

        Args:
            batch_results: List of normalized result dictionaries
            from_date: Start date used for the batch
            to_date: End date used for the batch

        Returns:
            Path to generated report file
        """
        # Calculate summary statistics
        total_items = len(batch_results)
        success_count = sum(1 for r in batch_results if r.get("success", False))
        failure_count = total_items - success_count
        total_nfas = sum(r.get("nfa_count", 0) for r in batch_results)
        total_pdfs = sum(len(r.get("pdfs", [])) for r in batch_results)

        # Error classification counts
        error_classifications: dict[str, int] = {}
        for result in batch_results:
            if not result.get("success", False):
                error_type = result.get("error_classification", "unknown_error")
                error_classifications[error_type] = error_classifications.get(error_type, 0) + 1

        # Build report structure
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "from_date": from_date,
                "to_date": to_date,
                "report_type": "NFA_ATF_BATCH",
            },
            "summary": {
                "total_items": total_items,
                "success_count": success_count,
                "failure_count": failure_count,
                "success_rate": round((success_count / total_items * 100) if total_items > 0 else 0, 2),
                "total_nfas_found": total_nfas,
                "total_pdfs_downloaded": total_pdfs,
                "error_classifications": error_classifications,
            },
            "results": batch_results,
        }

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"NFA_ATF_RUN_{timestamp}.json"
        report_path = REPORTS_DIR / filename

        # Write report
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(
            "NFA report generated",
            extra={
                "payload": {
                    "report_path": str(report_path),
                    "total_items": total_items,
                    "success_count": success_count,
                    "failure_count": failure_count,
                }
            },
        )

        return str(report_path)

    async def load_employees_from_file(
        self, file_path: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Load employee list from data_input_final file.

        Args:
            file_path: Optional custom file path. Defaults to FBP_Backend/data_input_final

        Returns:
            List of employee dictionaries with 'loja' and 'cpf' keys
        """
        if file_path is None:
            file_path = "/Users/dnigga/Documents/FBP_Backend/data_input_final"

        path = Path(file_path)
        if not path.exists():
            logger.warning(
                "Employee data file not found",
                extra={"payload": {"file_path": str(path)}},
            )
            return []

        try:
            # Try JSON first
            if path.suffix == ".json":
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                    # Handle both list and dict formats
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict) and "employees" in data:
                        return data["employees"]
                    return []

            # Try CSV format (simple parsing)
            if path.suffix == ".csv":
                employees = []
                with open(path, encoding="utf-8") as f:
                    lines = f.readlines()
                    # Assume header row
                    if len(lines) > 1:
                        # Try to detect header
                        header = lines[0].strip().split(",")
                        loja_idx = None
                        cpf_idx = None
                        matricula_idx = None

                        for i, col in enumerate(header):
                            col_lower = col.lower().strip()
                            if "loja" in col_lower:
                                loja_idx = i
                            if "cpf" in col_lower:
                                cpf_idx = i
                            if "matricula" in col_lower:
                                matricula_idx = i

                        # Parse rows
                        for line in lines[1:]:
                            parts = line.strip().split(",")
                            if len(parts) >= 2:
                                employee = {}
                                if loja_idx is not None and loja_idx < len(parts):
                                    employee["loja"] = parts[loja_idx].strip()
                                if cpf_idx is not None and cpf_idx < len(parts):
                                    employee["cpf"] = parts[cpf_idx].strip()
                                if matricula_idx is not None and matricula_idx < len(parts):
                                    employee["matricula"] = parts[matricula_idx].strip()
                                elif loja_idx is not None:
                                    # Use loja as matricula if matricula not found
                                    employee["matricula"] = employee.get("loja", "")

                                if employee:
                                    employees.append(employee)

                return employees

            # Try plain text (one employee per line: loja,cpf)
            with open(path, encoding="utf-8") as f:
                employees = []
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(",")
                    if len(parts) >= 2:
                        employees.append(
                            {
                                "loja": parts[0].strip(),
                                "cpf": parts[1].strip(),
                                "matricula": parts[0].strip(),  # Default to loja
                            }
                        )
                return employees

        except Exception as e:
            logger.error(
                "Failed to load employee data",
                exc_info=True,
                extra={"payload": {"file_path": str(path), "error": str(e)}},
            )
            return []
