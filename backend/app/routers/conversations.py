"""Conversations router for FoKS Intelligence."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import (
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
)
from app.services.conversation_cache import conversation_cache
from app.services.conversation_store import conversation_store
from app.services.logging_utils import get_logger
from app.services.webhook_service import webhook_service

router = APIRouter(prefix="/conversations", tags=["conversations"])

logger = get_logger("conversations_router")


@router.post("/", response_model=ConversationResponse)
async def create_conversation(payload: ConversationCreate) -> ConversationResponse:
    """
    Create a new conversation.

    Args:
        payload: Conversation creation data

    Returns:
        ConversationResponse: Created conversation
    """
    try:
        conversation = conversation_store.create_conversation(
            user_id=payload.user_id,
            title=payload.title,
            source=payload.source,
        )
        response = ConversationResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            source=conversation.source,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat(),
            message_count=0,
        )

        # Send webhook if enabled
        if settings.webhook_enabled:
            await webhook_service.send_webhook(
                "conversation.created",
                {
                    "conversation_id": conversation.id,
                    "user_id": conversation.user_id,
                    "title": conversation.title,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        # Cache is not needed for new conversations
        return response
    except Exception as exc:  # noqa: BLE001
        logger.error("Error creating conversation: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating conversation")


@router.get("/", response_model=ConversationListResponse)
async def list_conversations(
    user_id: str = Query(..., description="User identifier"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of conversations"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> ConversationListResponse:
    """
    List conversations for a user.

    Args:
        user_id: User identifier
        limit: Maximum number of conversations
        offset: Offset for pagination

    Returns:
        ConversationListResponse: List of conversations
    """
    try:
        conversations = conversation_store.list_conversations(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
        # Get total count for proper pagination
        total = conversation_store.count_conversations(user_id)

        return ConversationListResponse(
            conversations=[
                ConversationResponse(
                    id=conv.id,
                    user_id=conv.user_id,
                    title=conv.title,
                    source=conv.source,
                    created_at=conv.created_at.isoformat(),
                    updated_at=conv.updated_at.isoformat(),
                    message_count=len(conv.messages),
                )
                for conv in conversations
            ],
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Error listing conversations: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Error listing conversations")


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    user_id: str | None = Query(None, description="User identifier for validation"),
) -> ConversationResponse:
    """
    Get a conversation by ID.

    Args:
        conversation_id: Conversation ID
        user_id: Optional user ID for validation

    Returns:
        ConversationResponse: Conversation details
    """
    # Try cache first if enabled
    if settings.cache_enabled:
        cached = conversation_cache.get(conversation_id)
        if cached:
            logger.debug("Cache hit for conversation %d", conversation_id)
            return ConversationResponse(**cached)

    conversation = conversation_store.get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    response = ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        source=conversation.source,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
        message_count=len(conversation.messages),
    )

    # Cache the response if enabled
    if settings.cache_enabled:
        conversation_cache.set(conversation_id, response.model_dump())

    return response


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: int,
    user_id: str | None = Query(None, description="User identifier for validation"),
) -> list[MessageResponse]:
    """
    Get all messages for a conversation.

    Args:
        conversation_id: Conversation ID
        user_id: Optional user ID for validation

    Returns:
        List of messages
    """
    # Validate conversation exists and belongs to user
    conversation = conversation_store.get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = conversation_store.get_messages(conversation_id)
    return [
        MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at.isoformat(),
        )
        for msg in messages
    ]


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    user_id: str | None = Query(None, description="User identifier for validation"),
) -> dict:
    """
    Delete a conversation.

    Args:
        conversation_id: Conversation ID
        user_id: Optional user ID for validation

    Returns:
        Success message
    """
    success = conversation_store.delete_conversation(conversation_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Invalidate cache
    if settings.cache_enabled:
        conversation_cache.invalidate(conversation_id)

    return {"success": True, "message": f"Conversation {conversation_id} deleted"}


@router.patch("/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: int,
    title: str = Query(..., description="New conversation title"),
) -> dict:
    """
    Update conversation title.

    Args:
        conversation_id: Conversation ID
        title: New title

    Returns:
        Success message
    """
    success = conversation_store.update_conversation_title(conversation_id, title)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Invalidate cache since title changed
    if settings.cache_enabled:
        conversation_cache.invalidate(conversation_id)

    return {"success": True, "message": f"Conversation {conversation_id} title updated"}


@router.get("/{conversation_id}/export")
async def export_conversation(
    conversation_id: int,
    user_id: str | None = Query(None, description="User identifier for validation"),
    format: str = Query("json", description="Export format: json or jsonl"),
) -> JSONResponse:
    """
    Export a conversation in JSON or JSONL format.

    Args:
        conversation_id: Conversation ID
        user_id: Optional user ID for validation
        format: Export format (json or jsonl)

    Returns:
        JSONResponse: Exported conversation data
    """
    # Validate conversation exists and belongs to user
    conversation = conversation_store.get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get messages
    messages = conversation_store.get_messages(conversation_id)

    # Build export data
    export_data = {
        "conversation_id": conversation.id,
        "user_id": conversation.user_id,
        "title": conversation.title,
        "source": conversation.source,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
        "message_count": len(messages),
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ],
    }

    if format == "jsonl":
        # JSONL format: one JSON object per line
        jsonl_lines = []
        jsonl_lines.append(json.dumps(export_data))
        for msg in messages:
            jsonl_lines.append(
                json.dumps(
                    {
                        "conversation_id": conversation.id,
                        "message_id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat(),
                    }
                )
            )
        return JSONResponse(
            content="\n".join(jsonl_lines),
            media_type="application/x-ndjson",
            headers={
                "Content-Disposition": f'attachment; filename="conversation_{conversation_id}.jsonl"'
            },
        )

    # Default JSON format
    return JSONResponse(
        content=export_data,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="conversation_{conversation_id}.json"'
        },
    )

