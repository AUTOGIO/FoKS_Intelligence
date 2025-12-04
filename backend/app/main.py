from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.auth import AuthMiddleware
from app.middleware.m3_middleware import M3OptimizationMiddleware
from app.middleware.monitoring_middleware import MonitoringMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import chat, conversations, metrics, system, tasks, vision

app = FastAPI(title=settings.app_name)

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
app.include_router(metrics.router)
app.include_router(system.router)
app.include_router(conversations.router)

