"""System information and utilities router."""

from __future__ import annotations

import platform
import sys

from app.config import settings
from app.services.identity_guard import identity_guard
from app.services.logging_utils import get_logger
from app.services.monitoring import monitoring
from app.services.system_monitor import SystemMonitor
from app.utils.db_monitoring import get_database_stats
from app.utils.m3_optimizations import get_system_info, recommend_model_config
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/system", tags=["system"])

logger = get_logger("system_router")


class LockedModelsResponse(BaseModel):
    """Response schema for locked model configuration."""

    chat: str
    reasoning: str
    embedding: str
    vision: str
    scientific: str
    identity_guard_enabled: bool


@router.get("/info")
async def system_info() -> dict:
    """
    Get system information including M3-specific details.

    Returns:
        dict: System information including Python version, platform,
        hardware, and optimizations
    """
    logger.info("System info requested")
    base_info = {
        "python_version": sys.version,
        "python_version_info": {
            "major": sys.version_info.major,
            "minor": sys.version_info.minor,
            "micro": sys.version_info.micro,
        },
        "platform": platform.platform(),
        "system": platform.system(),
        "processor": platform.processor(),
        "architecture": platform.architecture(),
        "machine": platform.machine(),
        "app_version": "1.3.0",
        "app_name": settings.app_name,
        "environment": settings.environment,
    }

    # Add M3-specific information
    m3_info = get_system_info()
    base_info.update(m3_info)

    return base_info


@router.get("/recommendations")
async def get_recommendations() -> dict:
    """
    Get hardware-specific recommendations for model configuration.

    Returns:
        dict: Recommended model configuration based on M3 hardware
    """
    logger.info("Model recommendations requested")
    return recommend_model_config()


@router.get("/metrics")
async def get_metrics() -> dict:
    """
    Get application metrics (alias for /metrics).

    Returns:
        dict: Current metrics
    """
    return monitoring.get_stats()


@router.get("/database/stats")
async def database_stats() -> dict:
    """
    Get database statistics including size and record counts.

    Returns:
        dict: Database statistics
    """
    logger.info("Database stats requested")
    return get_database_stats()


@router.get("/models", response_model=LockedModelsResponse)
async def get_locked_models() -> LockedModelsResponse:
    """
    Get FoKS-locked default models.

    Returns only the locked model configuration from FoKS settings.
    Does NOT expose LM Studio's dynamic inventory.

    This endpoint is read-only and returns deterministic, config-driven values.

    Returns:
        LockedModelsResponse: Locked model configuration for each task type
    """
    logger.info("Locked models requested")
    return LockedModelsResponse(
        chat=settings.locked_chat_model,
        reasoning=settings.locked_reasoning_model,
        embedding=settings.locked_embedding_model,
        vision=settings.locked_vision_model,
        scientific=settings.locked_scientific_model,
        identity_guard_enabled=identity_guard.enabled,
    )


@router.get("/identity-guard/status")
async def identity_guard_status() -> dict:
    """
    Get current identity guard status and configuration.

    Returns:
        dict: Identity guard status including enabled state and pattern count
    """
    logger.info("Identity guard status requested")
    patterns = identity_guard.get_compiled_patterns()
    return {
        "enabled": identity_guard.enabled,
        "pattern_count": len(patterns),
        "system_prompt_length": len(identity_guard.system_prompt),
        "fallback_response_configured": bool(settings.local_fallback_response),
    }


@router.get("/status")
async def system_status() -> dict[str, str | float | list[str]]:
    """
    Get real-time system telemetry data as JSON.

    This endpoint provides structured system metrics for external monitoring
    tools (Raycast, dashboards, etc.). Returns the same data source used
    for LLM context injection, ensuring consistency.

    Returns:
        dict: System telemetry data including:
        - host: System hostname
        - timestamp: Current timestamp
        - cpu_percent: CPU usage percentage
        - ram_percent: RAM usage percentage
        - uptime: System uptime string
        - active_tasks: List of active workflow status strings
        - status: Backend status (ONLINE/OFFLINE with mode)
    """
    logger.info("System status requested")
    return SystemMonitor.get_telemetry_data()
