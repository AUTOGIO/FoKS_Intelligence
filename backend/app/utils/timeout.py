"""Timeout utilities for endpoints."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from fastapi import HTTPException

from app.services.logging_utils import get_logger

logger = get_logger("timeout")

T = TypeVar("T")


def timeout(seconds: float):
    """
    Decorator to add timeout to async endpoint.

    Args:
        seconds: Timeout in seconds

    Returns:
        Decorated function with timeout
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except TimeoutError:
                logger.warning(
                    "Endpoint %s timed out after %.2f seconds",
                    func.__name__,
                    seconds,
                )
                raise HTTPException(
                    status_code=504,
                    detail=f"Request timed out after {seconds} seconds",
                )
        return wrapper
    return decorator

