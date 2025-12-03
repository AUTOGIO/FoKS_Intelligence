"""Cache service for conversations."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from app.services.logging_utils import get_logger

logger = get_logger("conversation_cache")


class ConversationCache:
    """In-memory cache for conversations with TTL."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300) -> None:
        """
        Initialize conversation cache.

        Args:
            max_size: Maximum number of conversations to cache
            ttl_seconds: Time to live in seconds (default: 5 minutes)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[int, Dict[str, Any]] = {}
        self._access_times: Dict[int, float] = {}

    def get(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """
        Get conversation from cache.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation data if found and not expired, None otherwise
        """
        if conversation_id not in self._cache:
            return None

        # Check if expired
        if time.time() - self._access_times[conversation_id] > self.ttl_seconds:
            logger.debug("Cache expired for conversation %d", conversation_id)
            del self._cache[conversation_id]
            del self._access_times[conversation_id]
            return None

        # Update access time
        self._access_times[conversation_id] = time.time()
        return self._cache[conversation_id]

    def set(self, conversation_id: int, data: Dict[str, Any]) -> None:
        """
        Store conversation in cache.

        Args:
            conversation_id: Conversation ID
            data: Conversation data to cache
        """
        # Evict oldest if cache is full
        if len(self._cache) >= self.max_size and conversation_id not in self._cache:
            self._evict_oldest()

        self._cache[conversation_id] = data
        self._access_times[conversation_id] = time.time()
        logger.debug("Cached conversation %d", conversation_id)

    def invalidate(self, conversation_id: int) -> None:
        """
        Remove conversation from cache.

        Args:
            conversation_id: Conversation ID to invalidate
        """
        if conversation_id in self._cache:
            del self._cache[conversation_id]
            del self._access_times[conversation_id]
            logger.debug("Invalidated cache for conversation %d", conversation_id)

    def clear(self) -> None:
        """Clear all cached conversations."""
        self._cache.clear()
        self._access_times.clear()
        logger.info("Cache cleared")

    def _evict_oldest(self) -> None:
        """Evict the least recently used conversation."""
        if not self._access_times:
            return

        oldest_id = min(self._access_times.items(), key=lambda x: x[1])[0]
        del self._cache[oldest_id]
        del self._access_times[oldest_id]
        logger.debug("Evicted conversation %d from cache", oldest_id)

    def cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_ids = [
            conv_id
            for conv_id, access_time in self._access_times.items()
            if current_time - access_time > self.ttl_seconds
        ]

        for conv_id in expired_ids:
            del self._cache[conv_id]
            del self._access_times[conv_id]

        if expired_ids:
            logger.debug("Cleaned up %d expired cache entries", len(expired_ids))

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
        }


# Global cache instance
conversation_cache = ConversationCache()

