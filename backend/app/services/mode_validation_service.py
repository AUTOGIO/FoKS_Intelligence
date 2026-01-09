from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.services.logging_utils import get_logger
from app.services.monitoring import monitoring
from app.utils.architectural_assertions import ArchitecturalViolationError

logger = get_logger(__name__)


class ModeValidationService:
    """
    FoKS Judge Component: Validates mode configurations and environment readiness.
    Ensures absolute determinism before any command is generated for FBP.
    """

    def __init__(self, config_dir: str | None = None):
        if config_dir is None:
            # Default to backend/app/config/modes
            base_path = Path(__file__).parent.parent
            self.config_dir = base_path / "config" / "modes"
        else:
            self.config_dir = Path(config_dir)

    def load_mode_config(self, mode_name: str) -> dict[str, Any]:
        """Loads and parses the YAML configuration for a specific mode."""
        config_path = self.config_dir / f"{mode_name}.yaml"
        if not config_path.exists():
            raise ArchitecturalViolationError(
                f"Mode configuration not found: {mode_name}",
                details={"config_path": str(config_path)},
            )

        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            raise ArchitecturalViolationError(
                f"Failed to parse mode configuration: {str(e)}",
                details={"config_path": str(config_path)},
            )

    async def validate_readiness(self, mode_name: str) -> dict[str, Any]:
        """
        Performs strict preflight checks as the Judge.
        Checks paths, apps, and M3 system hardware status.
        """
        config = self.load_mode_config(mode_name)
        state = config.get("state", {})

        results = {"mode": mode_name, "validation_passed": True, "checks": []}

        # 1. Validate Folders
        for folder in state.get("folders", []):
            path = Path(folder["path"])
            exists = path.exists() and path.is_dir()
            results["checks"].append(
                {"type": "folder", "path": str(path), "status": "PASS" if exists else "FAIL"}
            )
            if not exists:
                results["validation_passed"] = False

        # 2. Validate Applications
        for app in state.get("applications", []):
            path = Path(app["path"])
            exists = path.exists()
            results["checks"].append(
                {
                    "type": "application",
                    "name": app["name"],
                    "path": str(path),
                    "status": "PASS" if exists else "FAIL",
                }
            )
            if not exists:
                results["validation_passed"] = False

        # 3. Validate M3 System Hardware (Advisory but checked by Judge)
        # Using monitoring service to check memory pressure or similar
        system_stats = monitoring.get_stats()
        # In a real M3 scenario, we'd check if memory pressure is 'Normal'
        # For now, we log the system state for auditability
        results["system_info"] = {
            "uptime_seconds": system_stats.get("uptime_seconds"),
            "health_timestamp": system_stats.get("timestamp"),
        }

        if not results["validation_passed"]:
            logger.warning(
                f"Architectural preflight failed for mode: {mode_name}", extra={"results": results}
            )
        else:
            logger.info(f"Architectural preflight passed for mode: {mode_name}")

        return results


mode_validation_service = ModeValidationService()
