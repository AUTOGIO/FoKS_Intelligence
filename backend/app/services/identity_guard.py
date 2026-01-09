"""Local Identity Guard - Cloud Leakage Prevention for FoKS Intelligence.

This module enforces local-first AI identity by:
1. Injecting local system prompts before all requests
2. Scanning responses for cloud/external identity leakage
3. Replacing unsafe responses with local-safe fallbacks

Controlled via FOKS_LOCAL_IDENTITY_GUARD environment variable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern

from app.config import settings
from app.services.logging_utils import get_logger
from app.services.system_monitor import SystemMonitor

logger = get_logger(__name__)


@dataclass
class LeakageDetection:
    """Result of cloud leakage detection scan."""

    is_safe: bool
    detected_patterns: list[str]
    original_response: str
    sanitized_response: str | None = None


class IdentityGuard:
    """
    Enforces local AI identity and prevents cloud identity leakage.

    When enabled (FOKS_LOCAL_IDENTITY_GUARD=true):
    - System prompts are injected to enforce local identity
    - Responses are scanned for cloud provider references
    - Unsafe responses are replaced with local-safe fallbacks

    When disabled:
    - Only identity enforcement is bypassed
    - Transport safety (timeouts, retries) remains active
    """

    def __init__(self) -> None:
        self._compiled_patterns: list[Pattern[str]] | None = None
        self._enabled = settings.local_identity_guard

    @property
    def enabled(self) -> bool:
        """Check if identity guard is currently enabled."""
        return self._enabled

    @property
    def system_prompt(self) -> str:
        """Return the local system prompt for injection."""
        return settings.local_system_prompt

    def get_compiled_patterns(self) -> list[Pattern[str]]:
        """
        Lazily compile and cache regex patterns for cloud leakage detection.
        """
        if self._compiled_patterns is None:
            self._compiled_patterns = []
            for pattern in settings.cloud_leakage_patterns:
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    self._compiled_patterns.append(compiled)
                except re.error as e:
                    logger.warning(
                        "Invalid cloud leakage pattern",
                        extra={
                            "payload": {
                                "pattern": pattern,
                                "error": str(e),
                            }
                        },
                    )
        return self._compiled_patterns

    def build_system_message(self) -> dict[str, str]:
        """
        Build the system message dict for LM Studio payload.

        Appends real-time system context (CPU, memory, uptime,
        active automations) to enable the LLM to answer system status
        queries accurately.
        """
        base_prompt = self.system_prompt
        context_block = SystemMonitor.get_context_block()
        full_content = f"{base_prompt}\n\n{context_block}"
        return {"role": "system", "content": full_content}

    def scan_response(self, response: str) -> LeakageDetection:
        """
        Scan a response for cloud identity leakage.

        Args:
            response: The LM Studio response text to scan.

        Returns:
            LeakageDetection with scan results and optional sanitized response.
        """
        if not self._enabled:
            return LeakageDetection(
                is_safe=True,
                detected_patterns=[],
                original_response=response,
            )

        detected: list[str] = []
        patterns = self.get_compiled_patterns()

        for pattern in patterns:
            matches = pattern.findall(response)
            if matches:
                detected.extend(matches)

        if detected:
            logger.warning(
                "Cloud identity leakage detected in response",
                extra={
                    "payload": {
                        "detected_count": len(detected),
                        "patterns": detected[:5],  # Log first 5 for brevity
                    }
                },
            )
            return LeakageDetection(
                is_safe=False,
                detected_patterns=detected,
                original_response=response,
                sanitized_response=settings.local_fallback_response,
            )

        return LeakageDetection(
            is_safe=True,
            detected_patterns=[],
            original_response=response,
        )

    def sanitize_response(self, response: str) -> str:
        """
        Sanitize a response, replacing it if cloud leakage is detected.

        Args:
            response: The LM Studio response text.

        Returns:
            Original response if safe, fallback response if leakage detected.
        """
        if not self._enabled:
            return response

        detection = self.scan_response(response)
        if detection.is_safe:
            return response

        logger.info(
            "Response replaced due to cloud identity leakage",
            extra={"payload": {"detected": detection.detected_patterns[:3]}},
        )
        return detection.sanitized_response or settings.local_fallback_response

    def should_inject_system_prompt(self) -> bool:
        """Check if system prompt should be injected."""
        return self._enabled


# Singleton instance for application-wide use
identity_guard = IdentityGuard()


def get_identity_guard() -> IdentityGuard:
    """Return the singleton identity guard instance."""
    return identity_guard


def is_identity_guard_enabled() -> bool:
    """Check if identity guard is enabled."""
    return identity_guard.enabled


def get_local_system_prompt() -> str:
    """Get the local system prompt for injection."""
    return identity_guard.system_prompt


def build_system_message() -> dict[str, str]:
    """Build the system message dict for LM Studio payload."""
    return identity_guard.build_system_message()


def sanitize_response(response: str) -> str:
    """Sanitize response, replacing if cloud leakage detected."""
    return identity_guard.sanitize_response(response)


def scan_for_leakage(response: str) -> LeakageDetection:
    """Scan response for cloud identity leakage."""
    return identity_guard.scan_response(response)
