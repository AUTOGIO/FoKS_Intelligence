"""Monitoring and metrics service for FoKS Intelligence."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, TypedDict

from app.services.logging_utils import get_logger

logger = get_logger("monitoring")


class RequestStats(TypedDict):
    """Type for request statistics."""
    total: int
    success: int
    failures: int
    response_times: list[float]


class TaskStats(TypedDict):
    """Type for task statistics."""
    total: int
    success: int
    failures: int


class StatsDict(TypedDict):
    """Type for the main stats dictionary."""
    requests: RequestStats
    tasks: TaskStats


@dataclass
class RequestMetrics:
    """Metrics for API requests."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    endpoint_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))


@dataclass
class TaskMetrics:
    """Metrics for task execution."""

    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    task_type_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    task_times: list[float] = field(default_factory=list)


class MonitoringService:
    """Service for collecting and reporting metrics."""

    def __init__(self) -> None:
        """Initialize monitoring service."""
        self.request_metrics = RequestMetrics()
        self.task_metrics = TaskMetrics()
        self.start_time = time.time()
        self.stats: StatsDict = {
            "requests": {
                "total": 0,
                "success": 0,
                "failures": 0,
                "response_times": [],
            },
            "tasks": {
                "total": 0,
                "success": 0,
                "failures": 0,
            },
        }
        self._lock = __import__("threading").Lock()

    def record_request(
        self, success: bool = True, response_time_ms: float = 0
    ) -> str:
        """
        Record a request and return error ID.

        Args:
            success: Whether request was successful
            response_time_ms: Response time in milliseconds

        Returns:
            str: Error ID (8 chars UUID)
        """
        import uuid

        error_id = str(uuid.uuid4())[:8]
        self._lock.acquire()
        try:
            self.stats["requests"]["total"] += 1
            if success:
                self.stats["requests"]["success"] += 1
            else:
                self.stats["requests"]["failures"] += 1

            if response_time_ms > 0:
                self.stats["requests"]["response_times"].append(response_time_ms)
                # Keep only last 1000 response times
                if len(self.stats["requests"]["response_times"]) > 1000:
                    self.stats["requests"]["response_times"].pop(0)
        finally:
            self._lock.release()
        return error_id

    def record_task(
        self,
        task_name: str,
        success: bool,
        execution_time: float,
    ) -> None:
        """
        Record a task execution.

        Args:
            task_name: Name of the task
            success: Whether task was successful
            execution_time: Execution time in seconds
        """
        self._lock.acquire()
        try:
            self.stats["tasks"]["total"] += 1
            if success:
                self.stats["tasks"]["success"] += 1
            else:
                self.stats["tasks"]["failures"] += 1
        finally:
            self._lock.release()

    def get_stats(self) -> dict[str, Any]:
        """
        Get current statistics.

        Returns:
            dict: Current metrics and statistics
        """
        uptime = time.time() - self.start_time
        response_times = self.stats["requests"]["response_times"]
        avg_response_time_ms = (
            sum(response_times) / len(response_times) if response_times else 0.0
        )

        return {
            "uptime_seconds": uptime,
            "uptime_formatted": self._format_uptime(uptime),
            "requests": {
                "total": self.stats["requests"]["total"],
                "success": self.stats["requests"]["success"],
                "failures": self.stats["requests"]["failures"],
                "avg_response_time_ms": avg_response_time_ms,
            },
            "tasks": {
                "total": self.stats["tasks"]["total"],
                "success": self.stats["tasks"]["success"],
                "failures": self.stats["tasks"]["failures"],
            },
        }

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Format uptime in human-readable format."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")

        return " ".join(parts)


# Global instance
monitoring = MonitoringService()

