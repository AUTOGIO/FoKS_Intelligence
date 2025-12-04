#!/usr/bin/env python3
"""
FBP backend health checker.

Handles:
- FBP offline / unreachable
- 5xx errors caused by missing Google/Gmail packages
"""
from __future__ import annotations

import sys
from typing import Optional


try:
    import httpx
except ImportError as exc:  # pragma: no cover - simple dependency guard
    print("ERROR: httpx is not installed. Activate the FBP venv and run: pip install httpx", file=sys.stderr)
    raise SystemExit(1) from exc


BASE_URL = "http://127.0.0.1:8000"
HEALTH_ENDPOINT = "/health"


def classify_google_issue(body: str) -> Optional[str]:
    text = body.lower()
    google_markers = [
        "google",
        "gmail",
        "google-api-python-client",
        "oauth2",
        "oauthlib",
        "google.auth",
    ]
    if any(marker in text for marker in google_markers):
        return (
            "FBP appears online but returned an error related to Google/Gmail packages.\n"
            "Hint: ensure Gmail/Google dependencies are installed in the FBP virtualenv."
        )
    return None


def main() -> int:
    url = f"{BASE_URL}{HEALTH_ENDPOINT}"
    print(f"FBP health check: {url}")

    try:
        with httpx.Client() as client:
            response = client.get(url, timeout=3.0)
    except httpx.RequestError as exc:
        print(f"[FAIL] FBP offline or unreachable: {exc}", file=sys.stderr)
        print("Hint: start FBP with ops/scripts/fbp_boot.sh", file=sys.stderr)
        return 1

    if 200 <= response.status_code < 300:
        print(f"[OK] FBP health -> {response.status_code}")
        return 0

    body_text = response.text or ""
    google_hint = classify_google_issue(body_text)
    print(f"[FAIL] FBP health -> HTTP {response.status_code}", file=sys.stderr)

    if google_hint:
        print(google_hint, file=sys.stderr)
        print("Suggested action (inside FBP venv): pip install -r requirements.txt", file=sys.stderr)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())


