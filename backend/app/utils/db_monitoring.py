"""Database monitoring utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import settings
from app.models.conversation import create_engine_instance, get_database_url
from app.services.logging_utils import get_logger

logger = get_logger("db_monitoring")


def get_database_size() -> dict[str, Any]:
    """
    Get database size information.

    Returns:
        dict: Database size information including size in bytes, MB, and path
    """
    db_url = get_database_url()

    if settings.use_postgresql:
        # PostgreSQL
        try:
            from sqlalchemy import text

            engine = create_engine_instance()
            with engine.connect() as conn:
                # Get database size
                result = conn.execute(
                    text(
                        """
                        SELECT pg_size_pretty(pg_database_size(current_database())) as size,
                               pg_database_size(current_database()) as size_bytes
                        """
                    )
                )
                row = result.fetchone()
                size_str = row[0] if row else "0 bytes"
                size_bytes = row[1] if row else 0

                return {
                    "size_bytes": size_bytes,
                    "size_mb": round(size_bytes / (1024**2), 2),
                    "size_formatted": size_str,
                    "type": "postgresql",
                    "url": db_url.split("@")[-1] if "@" in db_url else "postgresql",
                }
        except Exception as exc:  # noqa: BLE001
            logger.error("Error getting PostgreSQL size: %s", exc)
            return {
                "size_bytes": 0,
                "size_mb": 0,
                "size_formatted": "unknown",
                "type": "postgresql",
                "error": str(exc),
            }
    else:
        # SQLite
        db_path = Path(settings.database_path)
        if db_path.exists():
            size_bytes = db_path.stat().st_size
            return {
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / (1024**2), 2),
                "size_formatted": f"{round(size_bytes / (1024**2), 2)} MB",
                "type": "sqlite",
                "path": str(db_path),
            }
        else:
            return {
                "size_bytes": 0,
                "size_mb": 0,
                "size_formatted": "0 MB",
                "type": "sqlite",
                "path": str(db_path),
                "exists": False,
            }


def get_database_stats() -> dict[str, Any]:
    """
    Get comprehensive database statistics.

    Returns:
        dict: Database statistics including size, table counts, etc.
    """
    try:
        from app.models.conversation import Conversation, Message, SessionLocal

        db = SessionLocal()
        try:
            conversation_count = db.query(Conversation).count()
            message_count = db.query(Message).count()

            # Get size info
            size_info = get_database_size()

            return {
                **size_info,
                "conversation_count": conversation_count,
                "message_count": message_count,
                "avg_messages_per_conversation": (
                    round(message_count / conversation_count, 2)
                    if conversation_count > 0
                    else 0
                ),
            }
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        logger.error("Error getting database stats: %s", exc)
        return {
            "error": str(exc),
            "size_bytes": 0,
            "size_mb": 0,
        }

