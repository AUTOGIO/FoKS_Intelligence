from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.config import settings
from app.middleware.auth import AuthMiddleware
from app.middleware.m3_middleware import M3OptimizationMiddleware
from app.middleware.monitoring_middleware import MonitoringMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import (
    chat,
    conversations,
    fbp_diagnostics,
    metrics,
    nfa_atf,
    nfa_intelligence,
    nfa_trigger,
    oase,
    system,
    system_readiness,
    tasks,
    telemetry,
    tools_dashboard,
    vision,
)
from app.services.logging_utils import get_logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = get_logger(__name__)


async def _verify_router_registration(app: FastAPI) -> None:
    """
    Defensive startup check to ensure critical routers are registered.

    Logs all registered routes and verifies system endpoints exist.
    This prevents silent registration failures in production.
    """
    routes = [route.path for route in app.routes if hasattr(route, "path")]
    system_routes = [r for r in routes if r.startswith("/system")]

    # Check for critical system endpoints
    system_models_registered = "/system/models" in routes
    system_identity_guard_registered = "/system/identity-guard/status" in routes
    system_status_registered = "/system/status" in routes

    logger.info(
        "Router registration verified",
        extra={
            "total_routes": len(routes),
            "system_routes": system_routes,
            "system_models_registered": system_models_registered,
            "system_identity_guard_registered": (system_identity_guard_registered),
            "system_status_registered": system_status_registered,
        },
    )

    # Assert critical system endpoints are registered
    # (fail loudly if missing)
    expected_system_endpoints = [
        "/system/models",
        "/system/identity-guard/status",
        "/system/status",
    ]
    missing_endpoints = [ep for ep in expected_system_endpoints if ep not in routes]

    if missing_endpoints:
        error_msg = f"Critical system endpoints not registered: {missing_endpoints}"
        logger.error(error_msg, extra={"missing_endpoints": missing_endpoints})
        # Log but don't raise - allow app to start for debugging
        # In production, monitoring should alert on this log entry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan context manager for startup/shutdown."""
    # Startup
    await _verify_router_registration(app)
    logger.info(
        "FoKS Intelligence backend started",
        extra={"environment": settings.environment},
    )
    yield
    # Shutdown
    logger.info("FoKS Intelligence backend shutting down")


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.enable_monitoring_middleware:
    app.add_middleware(MonitoringMiddleware)

if settings.enable_rate_limit_middleware:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_requests_per_minute,
    )

if settings.enable_m3_middleware:
    app.add_middleware(M3OptimizationMiddleware)

if settings.require_auth_middleware:
    app.add_middleware(AuthMiddleware)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Simple health check consumed by Apple Shortcuts."""
    return {
        "status": "ok",
        "environment": settings.environment,
        "app": settings.app_name,
    }


app.include_router(chat.router)
app.include_router(vision.router)
app.include_router(tasks.router)
app.include_router(nfa_atf.router)
app.include_router(nfa_intelligence.router)
app.include_router(nfa_trigger.router)
app.include_router(fbp_diagnostics.router)
app.include_router(metrics.router)
app.include_router(system.router)
app.include_router(system_readiness.router)
app.include_router(conversations.router)
app.include_router(tools_dashboard.router)
app.include_router(telemetry.router)
app.include_router(oase.router)
