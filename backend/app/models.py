from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """Represents a past exchange in the chat history."""

    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """Input contract for the /chat endpoint."""

    message: str
    history: Optional[List[ChatMessage]] = None
    input_type: str = "text"
    source: str = "shortcuts"
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Normalized chat response wrapper."""

    reply: str
    raw: Optional[Dict[str, Any]] = None


class VisionRequest(BaseModel):
    """Placeholder request for future screenshot/vision analysis."""

    description: str
    image_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class VisionResponse(BaseModel):
    """Placeholder response while vision models are not available."""

    summary: str
    details: Optional[Dict[str, Any]] = None


class TaskRequest(BaseModel):
    """Contract for triggering local automations."""

    type: str = Field(..., alias="task_name")
    args: Dict[str, Any] = Field(default_factory=dict, alias="params")
    timeout: Optional[int] = None
    source: str = "shortcuts"
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)


class TaskResult(BaseModel):
    """Normalized execution result returned to clients."""

    task: str
    success: bool
    duration_ms: int
    payload: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
