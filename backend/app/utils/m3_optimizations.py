"""M3-specific optimizations for FoKS Intelligence."""

from __future__ import annotations

import os
import platform
import subprocess
from typing import Any, Dict

from app.config import settings
from app.services.logging_utils import get_logger

logger = get_logger("m3_optimizations")


def optimize_for_m3() -> Dict[str, Any]:
    """
    Apply M3-specific optimizations.

    Returns:
        dict: Optimization settings applied
    """
    optimizations: Dict[str, Any] = {}

    if not settings.is_m3:
        logger.info("Not running on M3, skipping M3-specific optimizations")
        return optimizations

    logger.info("Applying M3-specific optimizations...")

    # Set environment variables for optimal performance
    # Use performance cores for CPU-intensive tasks
    if settings.is_apple_silicon:
        # Optimize for Apple Silicon
        os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
        os.environ.setdefault("PYTHONUNBUFFERED", "1")

        # MLX optimizations (if using MLX models)
        os.environ.setdefault("MLX_DEFAULT_DEVICE", "gpu")  # Use GPU for MLX
        os.environ.setdefault("MLX_USE_ANE", "1")  # Use Neural Engine

        optimizations["mlx_device"] = "gpu"
        optimizations["neural_engine"] = settings.enable_neural_engine

    # Thread pool optimization for M3 (4 performance + 4 efficiency cores)
    # Use 4 workers for performance cores
    optimizations["max_workers"] = settings.optimal_workers
    optimizations["thread_pool_size"] = settings.optimal_workers

    # Memory optimization (16GB RAM)
    optimizations["max_memory_mb"] = (settings.memory_gb - 4) * 1024  # Leave 4GB for system
    optimizations["max_concurrent_tasks"] = settings.max_concurrent_tasks

    logger.info(
        "M3 optimizations applied: workers=%d, max_tasks=%d, memory_mb=%d",
        optimizations["max_workers"],
        optimizations["max_concurrent_tasks"],
        optimizations["max_memory_mb"],
    )

    return optimizations


def get_system_info() -> Dict[str, Any]:
    """
    Get detailed system information for M3.

    Returns:
        dict: System information
    """
    return {
        "hardware": {
            "model": settings.hardware_model,
            "is_apple_silicon": settings.is_apple_silicon,
            "is_m3": settings.is_m3,
            "cpu_cores": settings.cpu_cores,
            "memory_gb": settings.memory_gb,
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
        "optimizations": {
            "optimal_workers": settings.optimal_workers,
            "max_concurrent_tasks": settings.max_concurrent_tasks,
            "neural_engine_enabled": settings.enable_neural_engine,
            "max_request_size_mb": settings.max_request_size_mb,
        },
    }


def check_neural_engine_available() -> bool:
    """
    Check if Neural Engine is available.

    Returns:
        bool: True if Neural Engine is available
    """
    if not settings.is_apple_silicon:
        return False

    try:
        # Check for Core ML / Neural Engine availability
        result = subprocess.run(
            ["sysctl", "-n", "hw.optional.arm64"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "1"
    except Exception:  # noqa: BLE001
        return False


def recommend_model_config() -> Dict[str, Any]:
    """
    Recommend model configuration based on M3 hardware.

    Returns:
        dict: Recommended model configuration
    """
    recommendations = {
        "preferred_format": "MLX" if settings.is_apple_silicon else "GGUF",
        "quantization": "4-bit" if settings.memory_gb >= 16 else "8-bit",
        "max_model_size_gb": settings.memory_gb // 2,  # Use half of RAM for models
        "use_neural_engine": settings.enable_neural_engine and check_neural_engine_available(),
    }

    # M3-specific recommendations
    if settings.is_m3:
        recommendations.update(
            {
                "optimal_batch_size": 4,  # Use 4 performance cores
                "preferred_models": [
                    "qwen2.5-14b",  # Good balance for M3
                    "llama-3-8b-instruct",  # Efficient for M3
                    "phi-4-mini",  # Lightweight option
                ],
            }
        )

    return recommendations

