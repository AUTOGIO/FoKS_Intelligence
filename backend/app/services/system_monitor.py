"""System Monitor Service - Real-time telemetry injection for LLM context.

This module gathers local system metrics (CPU, memory, uptime,
active automations) and formats them for injection into the LLM's system
prompt, enabling the assistant to answer queries about system status
with real data.

Optimized for Apple Silicon M3 with efficient metric collection.
"""

from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass
from datetime import datetime

import psutil  # type: ignore[import-untyped]
from app.config import settings
from app.services.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SystemMetrics:
    """Immutable system metrics snapshot."""

    cpu_percent: float
    memory_percent: float
    uptime_str: str
    hostname: str
    timestamp: str
    active_workflows: list[str]

    def to_telemetry_block(self) -> str:
        """Format metrics as telemetry block for LLM injection."""
        workflow_list = ", ".join(self.active_workflows) if self.active_workflows else "None"
        return f"""
[REAL-TIME SYSTEM TELEMETRY]
- Host: {self.hostname} (macOS M3)
- Timestamp: {self.timestamp}
- CPU: {self.cpu_percent}% | RAM: {self.memory_percent}%
- Uptime: {self.uptime_str}
- Active Workflows: {workflow_list}
- Backend Status: ONLINE (FoKS Intelligence)
""".strip()


class SystemMonitor:
    """
    Gathers real-time system metrics and formats them for LLM context.

    Provides hardware stats (CPU, memory, uptime) and active automation
    status to enable the LLM to answer system status queries accurately.
    """

    def __init__(self) -> None:
        """Initialize the system monitor."""
        self._cached_automations: list[str] | None = None

    def get_hardware_stats(self) -> dict[str, float | str]:
        """
        Collect current hardware statistics.

        Returns:
            Dictionary with CPU usage (%), memory usage (%), and system uptime.
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Get system uptime (macOS-specific)
            uptime_str = self._get_uptime()

            return {
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory_percent, 1),
                "uptime": uptime_str,
            }
        except Exception as e:
            logger.warning(
                "Failed to collect hardware stats",
                exc_info=True,
                extra={"error": str(e)},
            )
            return {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "uptime": "Unknown",
            }

    def _get_uptime(self) -> str:
        """
        Get system uptime string (macOS-optimized).

        Returns:
            Human-readable uptime string (e.g., "2 days, 3 hours").
        """
        try:
            if platform.system() == "Darwin":  # macOS
                # Use sysctl for macOS uptime
                result = subprocess.run(
                    ["sysctl", "-n", "kern.boottime"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode == 0:
                    boot_timestamp = int(result.stdout.strip().split()[3].strip(","))
                    uptime_seconds = int(datetime.now().timestamp()) - boot_timestamp
                    return self._format_uptime(uptime_seconds)
            # Fallback to psutil for other systems
            boot_time = psutil.boot_time()
            uptime_seconds = int(datetime.now().timestamp()) - boot_time
            return self._format_uptime(uptime_seconds)
        except Exception as e:
            logger.debug(
                "Failed to get uptime",
                exc_info=True,
                extra={"error": str(e)},
            )
            return "Unknown"

    @staticmethod
    def _format_uptime(seconds: int) -> str:
        """
        Format uptime seconds into human-readable string.

        Args:
            seconds: Uptime in seconds.

        Returns:
            Formatted string (e.g., "2 days, 3 hours, 15 minutes").
        """
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0 and days == 0:  # Only show minutes if less than a day
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

        if not parts:
            return "Less than a minute"
        return ", ".join(parts)

    def get_active_automations(self) -> list[str]:
        """
        Get list of currently active/running automations.

        For now, returns a mock list. In the future, this can be extended
        to query actual automation status from FBP backend, launchd, or
        other sources.

        Returns:
            List of automation status strings
            (e.g., ["NFA_Invoice_Sync (Running)", ...]).
        """
        # TODO: Replace with real automation status queries
        # Potential sources:
        # - FBP backend API for job status
        # - launchd plist status checks
        # - Process monitoring for specific automation scripts
        return [
            "NFA_Invoice_Sync (Running)",
            "Redesim_Crawler (Idle)",
            "Email_Dispatcher (Waiting)",
        ]

    @staticmethod
    def _collect_metrics() -> SystemMetrics:
        """
        Collect current system metrics efficiently.

        Optimized for Apple Silicon M3:
        - Uses non-blocking CPU measurement when possible
        - Fast memory access via psutil
        - Efficient uptime calculation for macOS.

        Returns:
            SystemMetrics dataclass with all collected metrics.

        Raises:
            RuntimeError: If metric collection fails critically.
        """
        try:
            # CPU: Use interval=0.1 for quick non-blocking measurement
            # On M3, this is fast enough and doesn't block the event loop
            cpu_usage = psutil.cpu_percent(interval=0.1)
            if cpu_usage < 0:  # Fallback if first call returns -1
                cpu_usage = psutil.cpu_percent(interval=0.1)

            # Memory: Fast read, no blocking
            memory = psutil.virtual_memory()
            ram_usage = round(memory.percent, 1)
            cpu_usage = round(cpu_usage, 1)

            # Uptime: Optimized for macOS
            uptime_str = SystemMonitor._get_uptime_fast()

            # Hostname: Cache-friendly
            hostname = platform.node()

            # Timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Active workflows (mock for now, can be extended)
            active_workflows = SystemMonitor._get_active_workflows()

            return SystemMetrics(
                cpu_percent=cpu_usage,
                memory_percent=ram_usage,
                uptime_str=uptime_str,
                hostname=hostname,
                timestamp=timestamp,
                active_workflows=active_workflows,
            )
        except Exception as e:
            logger.error(
                "Failed to collect system metrics",
                exc_info=True,
                extra={
                    "payload": {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    }
                },
            )
            # Return safe fallback metrics
            return SystemMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                uptime_str="Unknown",
                hostname=platform.node(),
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                active_workflows=[],
            )

    @staticmethod
    def _get_uptime_fast() -> str:
        """
        Get system uptime string optimized for macOS.

        Uses sysctl on macOS for faster access, falls back to psutil.
        """
        try:
            if platform.system() == "Darwin":  # macOS
                result = subprocess.run(
                    ["sysctl", "-n", "kern.boottime"],
                    capture_output=True,
                    text=True,
                    timeout=1,  # Reduced timeout for faster failure
                    check=False,
                )
                if result.returncode == 0 and result.stdout.strip():
                    boot_timestamp = int(result.stdout.strip().split()[3].strip(","))
                    uptime_seconds = int(datetime.now().timestamp()) - boot_timestamp
                    return SystemMonitor._format_uptime(uptime_seconds)
            # Fallback to psutil
            boot_time = psutil.boot_time()
            uptime_seconds = int(datetime.now().timestamp()) - boot_time
            return SystemMonitor._format_uptime(uptime_seconds)
        except (
            ValueError,
            IndexError,
            subprocess.TimeoutExpired,
            OSError,
        ) as e:
            logger.debug(
                "Uptime calculation failed, using fallback",
                extra={
                    "payload": {
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                },
            )
            try:
                boot_time = psutil.boot_time()
                uptime_seconds = int(datetime.now().timestamp()) - boot_time
                return SystemMonitor._format_uptime(uptime_seconds)
            except Exception:
                return "Unknown"

    @staticmethod
    def _get_active_workflows() -> list[str]:
        """
        Get list of currently active workflows.

        Currently returns mock data. Can be extended to:
        - Query FBP backend API for job status
        - Check launchd plist status
        - Monitor specific automation processes

        Returns:
            List of workflow status strings.
        """
        # TODO: Replace with real workflow status queries
        # Potential integration points:
        # - FBP backend: await fbp_client.get_active_jobs()
        # - launchd: subprocess.run(["launchctl", "list"])
        # - Process monitoring: psutil.process_iter()
        return [
            "NFA_Invoice_Sync (Running)",
            "Redesim_Crawler (Idle)",
            "System_Health_Check (Active)",
        ]

    @staticmethod
    def get_telemetry_data() -> dict[str, str | float | list[str]]:
        """
        Get raw system telemetry data as a structured dictionary.

        This method provides the single source of truth for system metrics.
        Used by both the LLM context injection and the JSON API endpoint.

        Returns:
            Dictionary with system telemetry data:
            {
                "host": str,
                "timestamp": str,
                "cpu_percent": float,
                "ram_percent": float,
                "uptime": str,
                "active_tasks": list[str],
                "status": str
            }
        """
        try:
            metrics = SystemMonitor._collect_metrics()
            # Determine status based on environment
            status = "ONLINE"
            if settings.environment == "development":
                status += " (Development Mode)"
            elif settings.environment == "production":
                status += " (Production Mode)"

            return {
                "host": metrics.hostname,
                "timestamp": metrics.timestamp,
                "cpu_percent": metrics.cpu_percent,
                "ram_percent": metrics.memory_percent,
                "uptime": metrics.uptime_str,
                "active_tasks": metrics.active_workflows,
                "status": status,
            }
        except Exception as e:
            logger.error(
                "Failed to collect telemetry data",
                exc_info=True,
                extra={
                    "payload": {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    }
                },
            )
            # Return safe fallback data
            return {
                "host": platform.node(),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cpu_percent": 0.0,
                "ram_percent": 0.0,
                "uptime": "Unknown",
                "active_tasks": [],
                "status": "UNAVAILABLE",
            }

    @staticmethod
    def get_context_block() -> str:
        """
        Generate formatted system telemetry block for direct message injection.

        This method uses get_telemetry_data() to ensure consistency (DRY).
        Optimized for performance on Apple Silicon M3.
        Used for prepending context to user messages in the chat router.

        Returns:
            Formatted telemetry block ready to prepend to user messages.
            Returns fallback message if collection fails.
        """
        try:
            # Use get_telemetry_data() as single source of truth
            data = SystemMonitor.get_telemetry_data()
            active_tasks = data["active_tasks"]
            # Type guard: ensure active_tasks is a list
            if isinstance(active_tasks, list):
                workflow_list = ", ".join(active_tasks) if active_tasks else "None"
            else:
                workflow_list = "None"

            host = data["host"]
            timestamp = data["timestamp"]
            cpu = data["cpu_percent"]
            ram = data["ram_percent"]
            uptime = data["uptime"]
            status = data["status"]

            context = f"""
[REAL-TIME SYSTEM TELEMETRY]
- Host: {host} (macOS M3)
- Timestamp: {timestamp}
- CPU: {cpu}% | RAM: {ram}%
- Uptime: {uptime}
- Active Workflows: {workflow_list}
- Backend Status: {status} (FoKS Intelligence)
"""
            return context.strip()
        except Exception as e:
            logger.error(
                "Failed to generate context block",
                exc_info=True,
                extra={
                    "payload": {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    }
                },
            )
            return "[SYSTEM CONTEXT UNAVAILABLE]"


# Singleton instance for application-wide use
system_monitor = SystemMonitor()


def get_system_monitor() -> SystemMonitor:
    """Return the singleton system monitor instance."""
    return system_monitor
