"""Token bucket algorithm for advanced rate limiting."""

from __future__ import annotations

import time
from collections import defaultdict

from app.services.logging_utils import get_logger

logger = get_logger("token_bucket")


class TokenBucket:
    """
    Token bucket implementation for rate limiting.

    Allows bursts of traffic while maintaining average rate limit.
    """

    def __init__(
        self,
        capacity: int,
        refill_rate: float,
        initial_tokens: int | None = None,
    ) -> None:
        """
        Initialize token bucket.

        Args:
            capacity: Maximum number of tokens (burst capacity)
            refill_rate: Tokens added per second
            initial_tokens: Initial token count (defaults to capacity)
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(initial_tokens if initial_tokens is not None else capacity)
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate

        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def get_available_tokens(self) -> float:
        """Get current number of available tokens."""
        self._refill()
        return self.tokens

    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Calculate time to wait before tokens become available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds to wait (0 if tokens available now)
        """
        self._refill()

        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


class TokenBucketRateLimiter:
    """Rate limiter using token bucket algorithm."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_capacity: int | None = None,
    ) -> None:
        """
        Initialize token bucket rate limiter.

        Args:
            requests_per_minute: Average requests per minute
            burst_capacity: Maximum burst capacity (defaults to requests_per_minute)
        """
        self.requests_per_minute = requests_per_minute
        self.refill_rate = requests_per_minute / 60.0  # Tokens per second
        self.burst_capacity = burst_capacity or requests_per_minute
        self.buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                capacity=self.burst_capacity,
                refill_rate=self.refill_rate,
            )
        )

    def is_allowed(self, identifier: str, tokens: int = 1) -> tuple[bool, float]:
        """
        Check if request is allowed.

        Args:
            identifier: Unique identifier (IP, user_id, etc.)
            tokens: Number of tokens to consume (default: 1)

        Returns:
            Tuple of (is_allowed, wait_time_seconds)
        """
        bucket = self.buckets[identifier]
        wait_time = bucket.get_wait_time(tokens)

        if wait_time == 0:
            bucket.consume(tokens)
            return True, 0.0

        return False, wait_time

    def get_remaining(self, identifier: str) -> float:
        """Get remaining tokens for identifier."""
        return self.buckets[identifier].get_available_tokens()

    def cleanup_old_buckets(self, max_age_seconds: int = 3600) -> int:
        """
        Remove buckets that haven't been used recently.

        Args:
            max_age_seconds: Maximum age in seconds

        Returns:
            Number of buckets removed
        """
        # Note: This is a simplified cleanup. In production, use TTL-based cleanup.
        # For now, we keep all buckets (memory will grow but acceptable for single instance)
        return 0

