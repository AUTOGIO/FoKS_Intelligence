"""Prometheus-compatible metrics endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.services.monitoring import monitoring

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def metrics_root() -> dict[str, Any]:
    """
    JSON summary metrics endpoint at `/metrics`.

    Returns:
        dict: High-level metrics summary used by tests and dashboards.
    """
    stats = monitoring.get_stats()
    return {
        "total_requests": stats["requests"]["total"],
        "successful_requests": stats["requests"]["success"],
        "failed_requests": stats["requests"]["failures"],
        "avg_response_time_ms": stats["requests"]["avg_response_time_ms"],
        "total_tasks": stats["tasks"]["total"],
        "successful_tasks": stats["tasks"]["success"],
        "failed_tasks": stats["tasks"]["failures"],
        "uptime_seconds": stats["uptime_seconds"],
        "uptime_formatted": stats["uptime_formatted"],
    }


@router.get("/prometheus", response_class=PlainTextResponse)
async def prometheus_metrics() -> str:
    """
    Export metrics in Prometheus format.

    Returns:
        str: Metrics in Prometheus text format
    """
    stats = monitoring.get_stats()

    # Format as Prometheus metrics
    lines = [
        "# HELP foks_requests_total Total number of requests",
        "# TYPE foks_requests_total counter",
        f"foks_requests_total {stats['requests']['total']}",
        "",
        "# HELP foks_requests_success_total Total successful requests",
        "# TYPE foks_requests_success_total counter",
        f"foks_requests_success_total {stats['requests']['success']}",
        "",
        "# HELP foks_requests_failure_total Total failed requests",
        "# TYPE foks_requests_failure_total counter",
        f"foks_requests_failure_total {stats['requests']['failures']}",
        "",
        "# HELP foks_response_time_seconds Average response time",
        "# TYPE foks_response_time_seconds gauge",
        f"foks_response_time_seconds {stats['requests'].get('avg_response_time_ms', 0) / 1000.0}",
        "",
        "# HELP foks_tasks_total Total tasks executed",
        "# TYPE foks_tasks_total counter",
        f"foks_tasks_total {stats['tasks']['total']}",
        "",
        "# HELP foks_tasks_success_total Total successful tasks",
        "# TYPE foks_tasks_success_total counter",
        f"foks_tasks_success_total {stats['tasks']['success']}",
        "",
        "# HELP foks_uptime_seconds Application uptime",
        "# TYPE foks_uptime_seconds gauge",
        f"foks_uptime_seconds {stats['uptime_seconds']}",
    ]

    return "\n".join(lines)

