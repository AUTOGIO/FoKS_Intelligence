from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None
    input_type: str = "text"  # "text", "voice", "screenshot", "share", "camera"
    source: str = "shortcuts"  # "shortcuts", "cli", "obsidian", etc.
    model: Optional[str] = None  # Optional model override
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    reply: str
    raw: Optional[Dict[str, Any]] = None


class VisionRequest(BaseModel):
    description: str
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    source: str = "shortcuts"
    metadata: Optional[Dict[str, Any]] = None


class VisionResponse(BaseModel):
    summary: str
    details: Optional[Dict[str, Any]] = None


class TaskRequest(BaseModel):
    task_name: str
    params: Dict[str, Any] = {}
    source: str = "shortcuts"
    metadata: Optional[Dict[str, Any]] = None


class TaskResult(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# Conversation models
class ConversationCreate(BaseModel):
    user_id: str
    title: Optional[str] = None
    source: str = "shortcuts"


class ConversationResponse(BaseModel):
    id: int
    user_id: str
    title: Optional[str]
    source: str
    created_at: str
    updated_at: str
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int
    limit: int
    offset: int

