from __future__ import annotations

from typing import Any

from app.services.logging_utils import get_logger

logger = get_logger(__name__)


class ArchitecturalViolationError(Exception):
    """Raised when an architectural boundary or rule is violated."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}
        logger.error(f"ARCHITECTURAL VIOLATION: {message}", extra=self.details)


def assert_deterministic_command(payload: dict[str, Any]) -> None:
    """
    Ensures that commands sent to FBP are deterministic and don't contain
    ambiguous logic or "suggestions" that imply FBP autonomy.
    """
    # Rule: Commands must be non-empty and have a structured format
    if not payload:
        raise ArchitecturalViolationError("FBP command payload cannot be empty.")

    # Rule: Commands should not contain 'allow_autonomous_retry' or similar flags
    forbidden_keys = {"allow_autonomous_retry", "suggest_alternatives", "negotiate"}
    found_forbidden = forbidden_keys.intersection(payload.keys())
    if found_forbidden:
        raise ArchitecturalViolationError(
            f"FBP command contains autonomy-implying keys: {found_forbidden}",
            details={"payload": payload},
        )


def assert_evidence_response(response: dict[str, Any]) -> None:
    """
    Ensures that FBP responses are evidence-based and do not contain
    unsolicited alternative decisions or "negotiations".
    """
    if not isinstance(response, dict):
        raise ArchitecturalViolationError(
            f"FBP response must be a dictionary, got {type(response)}"
        )

    # Check for core compliance: success, data, errors/evidence
    essential_keys = {"success"}
    missing = essential_keys - set(response.keys())
    if missing:
        raise ArchitecturalViolationError(
            f"FBP response missing essential compliance keys: {missing}",
            details={"response": response},
        )

    # Rule: FBP must not report "autonomous corrections" as success without being commanded
    if response.get("autonomous_correction") is True:
        raise ArchitecturalViolationError(
            "FBP reported an autonomous correction, which violates the Bailiff role.",
            details={"response": response},
        )


def assert_advisory_llm_usage(output: str, source: str = "LLM") -> None:
    """
    Ensures that LLM output is used strictly for advisory purposes (summaries, plans, drafts)
     and does not directly contain executable code or control flow tokens that
     the Control Plane might blindly execute.
    """
    if not output:
        return

    # Heuristic: Check for common "execution" tokens that might indicate the LLM
    # is trying to "steer" the control plane directly instead of advising.
    steering_tokens = ["EXECUTE_IMMEDIATELY", "FORCE_RETRY", "OVERRIDE_AUTH"]
    for token in steering_tokens:
        if token in output:
            raise ArchitecturalViolationError(
                f"Advisory {source} output contains steering token: {token}",
                details={"source": source, "output_snippet": output[:100]},
            )
