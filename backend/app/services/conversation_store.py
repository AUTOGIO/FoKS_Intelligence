"""Service for managing conversation storage."""

from __future__ import annotations

import time
from datetime import datetime
from typing import List, Optional

from sqlalchemy.exc import OperationalError, DisconnectionError

from app.config import settings
from app.models import conversation
from app.models.conversation import Conversation, Message, SessionLocal
from app.services.logging_utils import get_logger

logger = get_logger("conversation_store")


class ConversationStore:
    """Service for managing conversations."""

    def __init__(self) -> None:
        """Initialize conversation store."""
        self.db = SessionLocal()

    def _retry_db_operation(self, operation, max_retries: int = 3, backoff: float = 1.0):
        """
        Retry database operation with exponential backoff.

        Args:
            operation: Function to execute
            max_retries: Maximum number of retries
            backoff: Initial backoff in seconds

        Returns:
            Operation result

        Raises:
            Exception: If all retries fail
        """
        last_exception = None
        for attempt in range(max_retries):
            try:
                return operation()
            except (OperationalError, DisconnectionError) as exc:
                last_exception = exc
                if attempt < max_retries - 1:
                    wait_time = backoff * (2 ** attempt)
                    logger.warning(
                        "Database connection error (attempt %d/%d), retrying in %.2fs: %s",
                        attempt + 1,
                        max_retries,
                        wait_time,
                        exc,
                    )
                    time.sleep(wait_time)
                    # Recreate session on connection error
                    self.db.close()
                    self.db = SessionLocal()
                else:
                    logger.error("Database operation failed after %d retries", max_retries)
                    raise
            except Exception as exc:
                # Don't retry on non-connection errors
                raise

        if last_exception:
            raise last_exception

    def create_conversation(
        self,
        user_id: str,
        title: Optional[str] = None,
        source: str = "shortcuts",
    ) -> Conversation:
        """
        Create a new conversation.

        Args:
            user_id: User identifier
            title: Optional conversation title
            source: Source of the conversation

        Returns:
            Conversation: Created conversation
        """
        def _create():
            conversation = Conversation(
                user_id=user_id,
                title=title,
                source=source,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)
            logger.info("Created conversation %d for user %s", conversation.id, user_id)
            return conversation

        return self._retry_db_operation(_create)

    def get_conversation(self, conversation_id: int, user_id: Optional[str] = None) -> Optional[Conversation]:
        """
        Get conversation by ID.

        Args:
            conversation_id: Conversation ID
            user_id: Optional user ID for validation

        Returns:
            Conversation or None if not found
        """
        query = self.db.query(Conversation).filter(Conversation.id == conversation_id)
        if user_id:
            query = query.filter(Conversation.user_id == user_id)
        return query.first()

    def list_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Conversation]:
        """
        List conversations for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of conversations to return
            offset: Offset for pagination

        Returns:
            List of conversations
        """
        return (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_conversations(self, user_id: str) -> int:
        """
        Count total conversations for a user.

        Args:
            user_id: User identifier

        Returns:
            Total count of conversations
        """
        return (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .count()
        )

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
    ) -> Message:
        """
        Add a message to a conversation.

        Args:
            conversation_id: Conversation ID
            role: Message role (user, assistant, system)
            content: Message content

        Returns:
            Message: Created message
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=datetime.utcnow(),
        )
        self.db.add(message)

        # Update conversation updated_at
        conversation = self.get_conversation(conversation_id)
        if conversation:
            conversation.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(message)
        logger.info("Added message to conversation %d", conversation_id)
        return message

    def get_messages(self, conversation_id: int) -> List[Message]:
        """
        Get all messages for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of messages ordered by creation time
        """
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )

    def delete_conversation(self, conversation_id: int, user_id: Optional[str] = None) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: Conversation ID
            user_id: Optional user ID for validation

        Returns:
            True if deleted, False if not found
        """
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            return False

        self.db.delete(conversation)
        self.db.commit()
        logger.info("Deleted conversation %d", conversation_id)
        return True

    def update_conversation_title(self, conversation_id: int, title: str) -> bool:
        """
        Update conversation title.

        Args:
            conversation_id: Conversation ID
            title: New title

        Returns:
            True if updated, False if not found
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False

        conversation.title = title
        conversation.updated_at = datetime.utcnow()
        self.db.commit()
        logger.info("Updated title for conversation %d", conversation_id)
        return True

    def cleanup_old_conversations(self, days: int = 30) -> int:
        """
        Delete conversations older than specified days.

        Args:
            days: Number of days

        Returns:
            Number of conversations deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted = (
            self.db.query(Conversation)
            .filter(Conversation.updated_at < cutoff_date)
            .delete()
        )
        self.db.commit()
        logger.info("Cleaned up %d old conversations", deleted)
        return deleted

    def close(self) -> None:
        """Close database session."""
        self.db.close()


# Global instance
conversation_store = ConversationStore()

