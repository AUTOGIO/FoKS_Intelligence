"""OASE (Observational Automation Suggestion Engine) router."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.logging_utils import get_logger
from app.services.oase_client import OASEClient, OASEClientError

router = APIRouter(prefix="/oase", tags=["oase"])

logger = get_logger(__name__)


class SuggestionItem(BaseModel):
    """Individual automation suggestion."""

    id: str
    summary: str
    confidence: float
    estimated_time_saved_min_per_week: int


class SuggestionsResponse(BaseModel):
    """Response for suggestions endpoint."""

    available: bool
    count: int
    suggestions: list[SuggestionItem]
    reason: str | None = None


def _knowledge_unit_to_suggestion(ku: dict[str, Any], index: int) -> SuggestionItem:
    """Transform a knowledge unit into a suggestion.

    Args:
        ku: Knowledge unit dictionary from OASE
        index: Index for generating unique ID

    Returns:
        SuggestionItem with transformed data
    """
    # Generate ID from knowledge unit
    ku_id = ku.get("signal_pattern", f"unknown_{index}")
    # Create a simple hash-like ID
    suggestion_id = f"ku_{datetime.now().strftime('%Y%m%d')}_{index:03d}"

    # Extract summary from signal pattern
    summary = ku.get("signal_pattern", "Pattern detected")

    # Extract confidence
    confidence = float(ku.get("confidence", 0.0))

    # Estimate time saved based on occurrence count and pattern type
    occurrence_count = ku.get("occurrence_count", 0)
    # Rough estimate: 2 minutes per occurrence, scaled by confidence
    estimated_time_saved_min_per_week = int(
        (occurrence_count * 2 * confidence) if occurrence_count > 0 else 0
    )

    return SuggestionItem(
        id=suggestion_id,
        summary=summary,
        confidence=confidence,
        estimated_time_saved_min_per_week=estimated_time_saved_min_per_week,
    )


def _filter_recent_suggestions(
    knowledge_units: list[dict[str, Any]], days: int = 1
) -> list[dict[str, Any]]:
    """Filter knowledge units to only include recent ones (last 24 hours).

    Client-side defensive filtering: checks created_at or last_seen within last 24 hours.

    Args:
        knowledge_units: List of knowledge unit dictionaries
        days: Number of days to look back (default: 1 for "today")

    Returns:
        Filtered list of knowledge units
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    recent = []

    for ku in knowledge_units:
        # Check created_at first (if OASE provides it), otherwise use last_seen
        timestamp_str = ku.get("created_at") or ku.get("last_seen")
        if not timestamp_str:
            continue

        try:
            # Parse ISO format timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            # Remove timezone for comparison
            if timestamp.replace(tzinfo=None) >= cutoff_date:
                recent.append(ku)
        except (ValueError, TypeError) as e:
            logger.debug(
                "Failed to parse timestamp",
                extra={"timestamp": timestamp_str, "error": str(e)},
            )
            # Exclude if we can't parse (defensive: better to hide than show stale data)
            continue

    return recent


@router.get("/suggestions/today", response_model=SuggestionsResponse)
async def get_suggestions_today() -> SuggestionsResponse:
    """
    Get automation suggestions worth reviewing today from OASE.

    This endpoint queries OASE for recent knowledge units and transforms them
    into actionable automation suggestions. It does NOT execute automations.

    Returns:
        SuggestionsResponse with list of suggestions or empty list if none found.
        Returns available=false if OASE is offline or times out.

    Behavior:
        - Calls OASE endpoint (knowledge units API)
        - 2-second timeout
        - Client-side filtering: confidence >= 0.5, last 24 hours
        - Graceful failure if OASE is offline
    """
    logger.info("Suggestions check requested")

    # Use 2-second timeout as specified
    client = OASEClient(timeout=2)

    try:
        # Try to get knowledge units from OASE with 2-second timeout
        knowledge_units = await client.get_knowledge_units()

        # Client-side filtering: last 24 hours
        recent_units = _filter_recent_suggestions(knowledge_units, days=1)

        # Transform to suggestions
        suggestions = [
            _knowledge_unit_to_suggestion(ku, idx)
            for idx, ku in enumerate(recent_units)
        ]

        # Client-side filtering: confidence >= 0.5
        min_confidence = 0.5
        high_confidence_suggestions = [
            s for s in suggestions if s.confidence >= min_confidence
        ]

        logger.info(
            "Suggestions retrieved",
            extra={
                "total_units": len(knowledge_units),
                "recent_units": len(recent_units),
                "high_confidence_suggestions": len(high_confidence_suggestions),
            },
        )

        return SuggestionsResponse(
            available=True,
            count=len(high_confidence_suggestions),
            suggestions=high_confidence_suggestions,
            reason=None,
        )

    except OASEClientError as e:
        logger.warning(
            "OASE client error",
            extra={"error": str(e), "status": e.status},
        )
        # Return graceful response: OASE offline
        return SuggestionsResponse(
            available=False,
            count=0,
            suggestions=[],
            reason="OASE offline",
        )

    except Exception as e:
        logger.error(
            "Unexpected error getting suggestions",
            exc_info=True,
            extra={"error": str(e)},
        )
        # Return graceful response: OASE offline
        return SuggestionsResponse(
            available=False,
            count=0,
            suggestions=[],
            reason="OASE offline",
        )

    finally:
        await client.close()

