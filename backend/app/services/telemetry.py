#!/usr/bin/env python3
"""Telemetry Service - System Metrics for FoKS Intelligence"""

from datetime import datetime
from typing import Any

import psutil


def get_system_metrics() -> dict[str, Any]:
    """Get current system metrics"""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()

        # Memory metrics
        memory = psutil.virtual_memory()

        # Disk metrics
        disk = psutil.disk_usage('/')

        # Network metrics
        net_io = psutil.net_io_counters()

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "frequency_mhz": cpu_freq.current if cpu_freq else 0
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_system_health() -> dict[str, Any]:
    """Check if system can handle more workload"""
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)

    return {
        "healthy": mem.percent < 85 and cpu < 90,
        "memory_percent": mem.percent,
        "cpu_percent": cpu,
        "memory_available_gb": round(mem.available / (1024**3), 2),
        "can_spawn_browser": mem.available > 2 * (1024**3)  # 2GB free
    }


def should_pause_batch() -> bool:
    """Returns True if system is under stress"""
    health = check_system_health()
    return not health["healthy"]


# Quick test
if __name__ == "__main__":
    import json
    print("=== System Metrics ===")
    print(json.dumps(get_system_metrics(), indent=2))
    print("\n=== Health Check ===")
    print(json.dumps(check_system_health(), indent=2))
