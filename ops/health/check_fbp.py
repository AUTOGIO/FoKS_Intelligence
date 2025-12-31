#!/usr/bin/env python3
"""
FBP backend health checker.

Supports:
- UNIX socket mode (default): /tmp/fbp.sock
- TCP port mode (fallback): http://127.0.0.1:9500

Handles:
- FBP offline / unreachable
- 5xx errors caused by missing Google/Gmail packages
"""
from __future__ import annotations

import os
import socket
import sys
from pathlib import Path
from typing import Optional


try:
    import httpx
except ImportError as exc:  # pragma: no cover - simple dependency guard
    print("ERROR: httpx is not installed. Activate the FBP venv and run: pip install httpx", file=sys.stderr)
    raise SystemExit(1) from exc


# Configuration: prefer socket, fallback to TCP
SOCKET_PATH = os.getenv("FBP_SOCKET_PATH", "/tmp/fbp.sock")
TCP_BASE_URL = os.getenv("FBP_HTTP_URL", "http://127.0.0.1:9500")
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


def check_socket_health(socket_path: str, endpoint: str) -> tuple[bool, Optional[str], Optional[str]]:
    """Check health via UNIX socket.
    
    Returns:
        (success, response_body, error_message)
    """
    import http.client
    
    class UnixHTTPConnection(http.client.HTTPConnection):
        def __init__(self, socket_path: str) -> None:
            super().__init__("localhost")
            self.socket_path = socket_path
        
        def connect(self) -> None:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.settimeout(3.0)
            self.sock.connect(self.socket_path)
    
    try:
        conn = UnixHTTPConnection(socket_path)
        conn.request("GET", endpoint)
        resp = conn.getresponse()
        body = resp.read().decode()
        conn.close()
        
        if 200 <= resp.status < 300:
            return True, body, None
        return False, body, f"HTTP {resp.status}"
    except FileNotFoundError:
        return False, None, "Socket not found"
    except ConnectionRefusedError:
        return False, None, "Connection refused"
    except Exception as e:
        return False, None, f"{type(e).__name__}: {e}"


def check_tcp_health(base_url: str, endpoint: str) -> tuple[bool, Optional[str], Optional[str]]:
    """Check health via TCP HTTP.
    
    Returns:
        (success, response_body, error_message)
    """
    url = f"{base_url}{endpoint}"
    try:
        with httpx.Client() as client:
            response = client.get(url, timeout=3.0)
        
        if 200 <= response.status_code < 300:
            return True, response.text, None
        return False, response.text, f"HTTP {response.status_code}"
    except httpx.RequestError as exc:
        return False, None, str(exc)


def main() -> int:
    socket_path = Path(SOCKET_PATH)
    
    # Strategy: Try socket first (default mode), then TCP (fallback)
    print(f"FBP health check starting...")
    print(f"  Socket path: {SOCKET_PATH}")
    print(f"  TCP fallback: {TCP_BASE_URL}")
    print()
    
    # 1. Try UNIX socket (preferred)
    if socket_path.exists() and socket_path.is_socket():
        print(f"Trying UNIX socket: {SOCKET_PATH}")
        success, body, error = check_socket_health(SOCKET_PATH, HEALTH_ENDPOINT)
        
        if success:
            print(f"[OK] FBP health via socket -> OK")
            return 0
        
        print(f"[WARN] Socket exists but health failed: {error}", file=sys.stderr)
        if body:
            google_hint = classify_google_issue(body)
            if google_hint:
                print(google_hint, file=sys.stderr)
    else:
        print(f"Socket not available at {SOCKET_PATH}")
    
    # 2. Try TCP (fallback for debug mode)
    print(f"Trying TCP: {TCP_BASE_URL}{HEALTH_ENDPOINT}")
    success, body, error = check_tcp_health(TCP_BASE_URL, HEALTH_ENDPOINT)
    
    if success:
        print(f"[OK] FBP health via TCP -> OK")
        return 0
    
    # Both failed
    print(f"[FAIL] FBP health check failed", file=sys.stderr)
    print(f"  Socket: {SOCKET_PATH} - {'exists' if socket_path.exists() else 'missing'}", file=sys.stderr)
    print(f"  TCP: {TCP_BASE_URL} - {error}", file=sys.stderr)
    print()
    print("Hints:", file=sys.stderr)
    print("  - Start FBP with: ops/scripts/fbp_boot.sh (socket mode)", file=sys.stderr)
    print("  - Or TCP mode: FBP_PORT=9500 /path/to/FBP_Backend/scripts/start.sh", file=sys.stderr)
    
    if body:
        google_hint = classify_google_issue(body)
        if google_hint:
            print(google_hint, file=sys.stderr)
            print("Suggested action: pip install -r requirements.txt (in FBP venv)", file=sys.stderr)
    
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
