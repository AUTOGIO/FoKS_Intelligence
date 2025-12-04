#!/usr/bin/env python3
"""
FoKS backend health checker.

Pings:
- /health
- /system/status
- /metrics
"""
from __future__ import annotations

import sys
from typing import List


try:
    import httpx
except ImportError as exc:  # pragma: no cover - simple dependency guard
    print("ERROR: httpx is not installed. Activate the FoKS venv and run: pip install httpx", file=sys.stderr)
    raise SystemExit(1) from exc


BASE_URL = "http://127.0.0.1:8000"
ENDPOINTS: List[str] = ["/health", "/system/status", "/metrics"]


def check_endpoint(client: httpx.Client, endpoint: str) -> bool:
    url = f"{BASE_URL}{endpoint}"
    try:
        response = client.get(url, timeout=3.0)
        response.raise_for_status()
        print(f"[OK] {url} -> {response.status_code}")
        return True
    except httpx.HTTPError as exc:
        print(f"[FAIL] {url} -> {exc}", file=sys.stderr)
        return False


def main() -> int:
    print("FoKS health check starting...")
    success = True

    with httpx.Client() as client:
        for endpoint in ENDPOINTS:
            if not check_endpoint(client, endpoint):
                success = False

    if success:
        print("FoKS health check: ALL OK")
        return 0

    print("FoKS health check: FAILURES DETECTED", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


