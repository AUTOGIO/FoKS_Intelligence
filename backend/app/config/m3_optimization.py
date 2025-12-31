"""M3 Resource Optimization and LM Studio Configuration Module.

This module provides:
- M3-aware resource limits and concurrency settings
- LM Studio client with semaphore-based concurrency control
- Configuration profiles (LIGHT, BALANCED, HEAVY)
- Monitoring utilities for resource usage

Designed for iMac M3 (8 cores: 4P+4E, 16 GB RAM) with macOS 26 Beta.
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ModelProfile(str, Enum):
    """LM Studio model profiles optimized for M3 16GB."""

    LIGHT = "light"
    """Small, fast models: 7-8B, 4-bit quantization.
    Latency: <100ms per token, RAM: ~4-5GB.
    Use for: fast chat, quick summarization.
    """

    BALANCED = "balanced"
    """Medium models: 12-14B, 4-bit quantization.
    Latency: 100-200ms per token, RAM: ~6-8GB.
    Use for: standard chat, code generation, analysis.
    """

    HEAVY = "heavy"
    """Larger models: 30B+, 4-bit quantization.
    Latency: 200+ms per token, RAM: 10-15GB.
    Use: manually opt-in only, for complex reasoning.
    """


@dataclass
class ModelConfig:
    """Configuration for a model profile on M3 hardware."""

    profile: ModelProfile
    model_name: str
    """Name or path of the model (MLX-optimized preferred)."""

    max_tokens: int
    """Maximum tokens to generate per request."""

    context_window: int
    """Context window size in tokens."""

    max_concurrent_requests: int
    """Max parallel generations (semaphore slot count)."""

    timeout_seconds: float
    """Request timeout (stream or full)."""

    quantization: str
    """Quantization level (e.g., 'Q4_K_M', '4-bit')."""


# Default M3 profiles
M3_PROFILES = {
    ModelProfile.LIGHT: ModelConfig(
        profile=ModelProfile.LIGHT,
        model_name="mlx-community/Mistral-7B-Instruct-v0.2-4bit",
        max_tokens=512,
        context_window=8192,
        max_concurrent_requests=1,
        timeout_seconds=60.0,
        quantization="4-bit",
    ),
    ModelProfile.BALANCED: ModelConfig(
        profile=ModelProfile.BALANCED,
        model_name="mlx-community/Hermes-2-Pro-Mistral-7B-4bit",  # or 13B if available
        max_tokens=1024,
        context_window=8192,
        max_concurrent_requests=1,
        timeout_seconds=90.0,
        quantization="4-bit",
    ),
    ModelProfile.HEAVY: ModelConfig(
        profile=ModelProfile.HEAVY,
        model_name="mlx-community/Mixtral-8x7B-Instruct-v0.1-4bit",
        max_tokens=2048,
        context_window=4096,  # Reduced to fit in 16GB
        max_concurrent_requests=1,
        timeout_seconds=180.0,
        quantization="4-bit",
    ),
}


class LMStudioConcurrencyManager:
    """Manages concurrent LM Studio requests with semaphore-based queueing.

    On M3 with 16GB RAM, limiting parallel generations prevents OOM and
    maintains responsive performance.
    """

    def __init__(self, max_concurrent: int = 1):
        """Initialize concurrency manager.

        Args:
            max_concurrent: Maximum concurrent LM Studio requests.
                           Recommended: 1-2 for M3 16GB.
        """
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        self._active_count = 0
        self._logger = logging.getLogger(__name__)

    async def acquire(self) -> None:
        """Acquire a slot for an LM Studio request.

        Waits if max_concurrent slots are in use.
        """
        self._active_count += 1
        if self._active_count > self._max_concurrent:
            self._logger.debug(
                f"LM Studio request queued (active={self._active_count - 1}, "
                f"max={self._max_concurrent})"
            )
        await self._semaphore.acquire()

    async def release(self) -> None:
        """Release a slot after LM Studio request completes."""
        self._semaphore.release()
        self._active_count -= 1

    async def execute(self, coro):
        """Execute a coroutine with concurrency control.

        Example:
            result = await manager.execute(lmstudio_client.chat(...))
        """
        async with self._semaphore:
            return await coro

    @property
    def max_concurrent(self) -> int:
        """Max concurrent requests."""
        return self._max_concurrent

    @property
    def active_count(self) -> int:
        """Current active requests."""
        return max(0, self._active_count - 1)


class M3ResourceBudget:
    """Resource allocation policy for M3 iMac.

    iMac M3 spec:
    - Chip: 8 cores (4 performance + 4 efficiency)
    - RAM: 16 GB unified memory
    - macOS: 26 Beta (Sonoma+)

    Recommended allocation:
    - LM Studio: 4-10 GB (model dependent)
    - FoKS backend: ~2 GB
    - FBP backend: ~2.5 GB
    - OS + headroom: ~3 GB
    """

    # Per-process soft limits (from launchd plists)
    FOKS_MEMORY_LIMIT_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB
    FBP_MEMORY_LIMIT_BYTES = 2.5 * 1024 * 1024 * 1024  # 2.5 GB
    LMSTUDIO_ESTIMATED_BYTES = 8 * 1024 * 1024 * 1024  # ~8 GB (model dependent)

    # Concurrency limits
    MAX_CONCURRENT_LM_REQUESTS = 1  # 1-2 for M3 16GB
    MAX_ASYNC_CONNECTIONS_PER_CLIENT = 10
    MAX_KEEPALIVE_CONNECTIONS_PER_CLIENT = 5

    # CPU/process limits
    MAX_UVICORN_WORKERS_PER_BACKEND = 1  # 1-2 for local M3 (async handles concurrency)
    PREFERRED_EVENT_LOOP = "uvloop"  # Over default asyncio

    @staticmethod
    def get_recommended_profile() -> ModelProfile:
        """Get recommended LM Studio profile for M3 16GB."""
        return ModelProfile.LIGHT  # Conservative default


# Recommended httpx AsyncClient settings for M3 backends
HTTPX_M3_DEFAULTS = {
    "timeout": 30.0,
    "limits": {
        "max_connections": 10,
        "max_keepalive_connections": 5,
    },
}

# uvicorn startup suggestions for M3
UVICORN_M3_DEFAULTS = {
    "host": "0.0.0.0",
    "port": 8000,  # or 8001 for FoKS
    "workers": 1,  # Single worker; async + uvloop handle concurrency
    "loop": "uvloop",  # Apple Silicon optimized (faster event loop)
    "http": "auto",  # auto-detect httptools (faster HTTP)
    "timeout_keep_alive": 5,
    "timeout_notify": 30,
    "access_log": True,
}


def get_logger_config() -> dict:
    """Return logging configuration for M3 backends.

    Structured logging with proper formatting for launchd / log streaming.
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": (
                    "%(asctime)s [%(name)s] [%(levelname)s] %(message)s"
                ),
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["default"],
        },
    }


if __name__ == "__main__":
    # Quick validation script
    print("M3 Resource Optimization Module")
    print("="*50)
    print(f"Recommended profile: {M3ResourceBudget.get_recommended_profile()}")
    print(f"Max concurrent LM requests: {M3ResourceBudget.MAX_CONCURRENT_LM_REQUESTS}")
    print(f"Max uvicorn workers: {M3ResourceBudget.MAX_UVICORN_WORKERS_PER_BACKEND}")
    print(f"Event loop: {M3ResourceBudget.PREFERRED_EVENT_LOOP}")
    print()
    print("Model Profiles:")
    for profile, config in M3_PROFILES.items():
        print(f"  {profile.value}:")
        print(f"    Model: {config.model_name}")
        print(f"    Max tokens: {config.max_tokens}")
        print(f"    Context: {config.context_window}")
        print(f"    Concurrent requests: {config.max_concurrent_requests}")
    print()
    print("launchd StandardOutPath/StandardErrorPath:")
    print("  ~/Library/Logs/FoKS/com.foks.bootstrap.out.log")
    print("  ~/Library/Logs/FoKS/com.foks.bootstrap.err.log")
    print("  ~/Library/Logs/FoKS/com.fbp.bootstrap.out.log")
    print("  ~/Library/Logs/FoKS/com.fbp.bootstrap.err.log")
