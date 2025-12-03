from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, tasks, vision

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

