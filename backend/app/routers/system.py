"""System information and utilities router."""

from __future__ import annotations

import platform
import sys
from typing import Dict

from fastapi import APIRouter

from app.config import settings
from app.services.logging_utils import get_logger
from app.services.monitoring import monitoring
from app.utils.db_monitoring import get_database_stats
from app.utils.m3_optimizations import get_system_info, recommend_model_config

router = APIRouter(prefix="/system", tags=["system"])

logger = get_logger("system_router")


@router.get("/info")
async def system_info() -> Dict:
    """
    Get system information including M3-specific details.

    Returns:
        dict: System information including Python version, platform, hardware, and optimizations
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
async def get_recommendations() -> Dict:
    """
    Get hardware-specific recommendations for model configuration.

    Returns:
        dict: Recommended model configuration based on M3 hardware
    """
    logger.info("Model recommendations requested")
    return recommend_model_config()


@router.get("/metrics")
async def get_metrics() -> Dict:
    """
    Get application metrics (alias for /metrics).

    Returns:
        dict: Current metrics
    """
    return monitoring.get_stats()


@router.get("/database/stats")
async def database_stats() -> Dict:
    """
    Get database statistics including size and record counts.

    Returns:
        dict: Database statistics
    """
    logger.info("Database stats requested")
    return get_database_stats()

