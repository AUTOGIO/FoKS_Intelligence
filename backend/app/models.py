from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """Represents a past exchange in the chat history."""

    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """Input contract for the /chat endpoint."""

    message: str
    history: list[ChatMessage] | None = None
    input_type: str = "text"
    source: str = "shortcuts"
    metadata: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    """Normalized chat response wrapper."""

    reply: str
    raw: dict[str, Any] | None = None


class VisionRequest(BaseModel):
    """Placeholder request for future screenshot/vision analysis."""

    description: str
    image_url: str | None = None
    metadata: dict[str, Any] | None = None


class VisionResponse(BaseModel):
    """Placeholder response while vision models are not available."""

    summary: str
    details: dict[str, Any] | None = None


class TaskRequest(BaseModel):
    """Contract for triggering local automations."""

    type: str = Field(..., alias="task_name")
    args: dict[str, Any] = Field(default_factory=dict, alias="params")
    timeout: int | None = None
    source: str = "shortcuts"
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(populate_by_name=True)


class TaskResult(BaseModel):
    """Normalized execution result returned to clients."""

    task: str
    success: bool
    duration_ms: int
    payload: dict[str, Any] | None = None
    error: str | None = None
