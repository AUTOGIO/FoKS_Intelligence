"""Telemetry Router - System Metrics API Endpoints"""

from fastapi import APIRouter

from app.services.telemetry import check_system_health, get_system_metrics

router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])


@router.get("/")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "telemetry"}


@router.get("/metrics")
async def metrics():
    """Get full system metrics"""
    return get_system_metrics()


@router.get("/health")
async def system_health():
    """Check system health for batch processing"""
    return check_system_health()
