#!/usr/bin/env python3
"""
Debug Mode: System State Diagnostic
Validates all hypotheses about system configuration and connectivity.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# #region agent log
DEBUG_LOG_PATH = Path("/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/.cursor/debug.log")

def log_debug(hypothesis_id: str, location: str, message: str, data: dict[str, Any]) -> None:
    """Write NDJSON debug log entry."""
    DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": int(datetime.now().timestamp() * 1000),
        "sessionId": "debug-session",
        "runId": "system-state-check",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
    }
    with open(DEBUG_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
# #endregion

def check_directory_exists(path: str) -> dict[str, Any]:
    """Check if a directory exists and is accessible."""
    p = Path(path)
    return {
        "path": path,
        "exists": p.exists(),
        "is_dir": p.is_dir() if p.exists() else False,
        "writable": os.access(path, os.W_OK) if p.exists() else False,
    }

def check_socket_exists(socket_path: str) -> dict[str, Any]:
    """Check if a UNIX socket exists and is listening."""
    p = Path(socket_path)
    result = {
        "socket_path": socket_path,
        "exists": p.exists(),
        "is_socket": p.is_socket() if p.exists() else False,
        "listening": False,
        "process": None,
    }
    
    if p.exists() and p.is_socket():
        # Check if process is listening
        try:
            lsof = subprocess.run(
                ["lsof", socket_path],
                capture_output=True,
                timeout=2,
            )
            if lsof.returncode == 0:
                result["listening"] = True
                result["process"] = lsof.stdout.decode().split("\n")[1:3]
        except Exception as e:
            result["lsof_error"] = str(e)
    
    return result

def check_tcp_port(port: int) -> dict[str, Any]:
    """Check if a TCP port is listening."""
    result = {
        "port": port,
        "listening": False,
        "process": None,
    }
    
    try:
        lsof = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
            capture_output=True,
            timeout=2,
        )
        if lsof.returncode == 0 and lsof.stdout:
            result["listening"] = True
            lines = lsof.stdout.decode().strip().split("\n")
            if len(lines) > 1:
                result["process"] = lines[1]
    except Exception as e:
        result["error"] = str(e)
    
    return result

def check_http_health(url: str, timeout: float = 3.0) -> dict[str, Any]:
    """Check HTTP health endpoint."""
    import urllib.request
    import urllib.error
    
    result = {
        "url": url,
        "reachable": False,
        "status_code": None,
        "response": None,
        "error": None,
    }
    
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result["reachable"] = True
            result["status_code"] = resp.status
            result["response"] = resp.read().decode()[:200]
    except urllib.error.HTTPError as e:
        result["status_code"] = e.code
        result["error"] = str(e)
    except urllib.error.URLError as e:
        result["error"] = f"URLError: {e.reason}"
    except Exception as e:
        result["error"] = str(e)
    
    return result

def check_socket_health(socket_path: str, endpoint: str = "/health") -> dict[str, Any]:
    """Check health via UNIX socket."""
    result = {
        "socket_path": socket_path,
        "endpoint": endpoint,
        "reachable": False,
        "response": None,
        "error": None,
    }
    
    try:
        import http.client
        
        # Create UNIX socket connection
        class UnixHTTPConnection(http.client.HTTPConnection):
            def __init__(self, socket_path: str) -> None:
                super().__init__("localhost")
                self.socket_path = socket_path
            
            def connect(self) -> None:
                self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock.connect(self.socket_path)
        
        conn = UnixHTTPConnection(socket_path)
        conn.request("GET", endpoint)
        resp = conn.getresponse()
        result["reachable"] = True
        result["status_code"] = resp.status
        result["response"] = resp.read().decode()[:200]
        conn.close()
    except FileNotFoundError:
        result["error"] = "Socket file not found"
    except ConnectionRefusedError:
        result["error"] = "Connection refused (socket exists but not listening)"
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    
    return result

def main() -> int:
    print("=" * 60)
    print("DEBUG MODE: System State Diagnostic")
    print("=" * 60)
    print()
    
    # H1: FBP socket vs port configuration
    print(">>> H1: FBP Socket vs Port Mode")
    fbp_socket = check_socket_exists("/tmp/fbp.sock")
    log_debug("H1", "debug_system_state.py:H1", "FBP socket check", fbp_socket)
    print(f"  Socket /tmp/fbp.sock: {'EXISTS' if fbp_socket['exists'] else 'MISSING'}")
    if fbp_socket["exists"]:
        print(f"    Is socket: {fbp_socket['is_socket']}")
        print(f"    Listening: {fbp_socket['listening']}")
    
    fbp_port_9500 = check_tcp_port(9500)
    log_debug("H1", "debug_system_state.py:H1", "FBP port 9500 check", fbp_port_9500)
    print(f"  Port 9500: {'LISTENING' if fbp_port_9500['listening'] else 'FREE'}")
    
    fbp_port_8000 = check_tcp_port(8000)
    log_debug("H1", "debug_system_state.py:H1", "FBP port 8000 check", fbp_port_8000)
    print(f"  Port 8000: {'LISTENING' if fbp_port_8000['listening'] else 'FREE'}")
    
    # Check FBP health via socket
    if fbp_socket["listening"]:
        fbp_socket_health = check_socket_health("/tmp/fbp.sock", "/health")
        log_debug("H1", "debug_system_state.py:H1", "FBP socket health", fbp_socket_health)
        print(f"  Socket health: {'OK' if fbp_socket_health['reachable'] else 'FAIL'}")
    
    # Check FBP health via TCP (what monitoring expects)
    fbp_http_health = check_http_health("http://127.0.0.1:9500/health")
    log_debug("H1", "debug_system_state.py:H1", "FBP HTTP health (port 9500)", fbp_http_health)
    print(f"  HTTP health (9500): {'OK' if fbp_http_health['reachable'] else 'FAIL'}")
    if fbp_http_health.get("error"):
        print(f"    Error: {fbp_http_health['error']}")
    print()
    
    # H2: Log directory exists
    print(">>> H2: Log Directory")
    log_dir = check_directory_exists("/Users/dnigga/Library/Logs/FoKS")
    log_debug("H2", "debug_system_state.py:H2", "Log directory check", log_dir)
    print(f"  /Users/dnigga/Library/Logs/FoKS: {'EXISTS' if log_dir['exists'] else 'MISSING'}")
    if log_dir["exists"]:
        print(f"    Writable: {log_dir['writable']}")
    print()
    
    # H3: Cloudflare domain readiness (check config)
    print(">>> H3: Cloudflare Domain Readiness")
    foks_config_path = "/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/app/config.py"
    config_check = {
        "config_exists": Path(foks_config_path).exists(),
        "has_giovannini_origin": False,
    }
    if Path(foks_config_path).exists():
        with open(foks_config_path) as f:
            content = f.read()
            config_check["has_giovannini_origin"] = "giovannini.us" in content
            config_check["has_foks_subdomain"] = "foks.giovannini.us" in content
            config_check["has_fbp_subdomain"] = "fbp.giovannini.us" in content
    log_debug("H3", "debug_system_state.py:H3", "Cloudflare config check", config_check)
    print(f"  Config has giovannini.us: {'YES' if config_check['has_giovannini_origin'] else 'NO'}")
    print()
    
    # H4: FoKS port configuration
    print(">>> H4: FoKS Port Configuration")
    foks_port_8000 = check_tcp_port(8000)
    log_debug("H4", "debug_system_state.py:H4", "FoKS port 8000 check", foks_port_8000)
    print(f"  Port 8000: {'LISTENING' if foks_port_8000['listening'] else 'FREE'}")
    
    foks_health = check_http_health("http://127.0.0.1:8000/health")
    log_debug("H4", "debug_system_state.py:H4", "FoKS health check", foks_health)
    print(f"  FoKS health: {'OK' if foks_health['reachable'] else 'FAIL'}")
    if foks_health.get("error"):
        print(f"    Error: {foks_health['error']}")
    print()
    
    # H5: FBP client configuration in FoKS
    print(">>> H5: FBP Client Configuration")
    fbp_env = {
        "FBP_TRANSPORT": os.getenv("FBP_TRANSPORT", "socket (default)"),
        "FBP_SOCKET_PATH": os.getenv("FBP_SOCKET_PATH", "/tmp/fbp.sock (default)"),
        "FBP_BACKEND_BASE_URL": os.getenv("FBP_BACKEND_BASE_URL", "http://localhost:8000 (default)"),
    }
    log_debug("H5", "debug_system_state.py:H5", "FBP client env check", fbp_env)
    print(f"  FBP_TRANSPORT: {fbp_env['FBP_TRANSPORT']}")
    print(f"  FBP_SOCKET_PATH: {fbp_env['FBP_SOCKET_PATH']}")
    print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    issues = []
    
    if not fbp_socket["listening"] and not fbp_port_9500["listening"]:
        issues.append("FBP is NOT running (neither socket nor port 9500)")
    # Note: Socket mode is the preferred production mode; health scripts have been updated
    # to support both socket and TCP modes. No issue if socket is working.
    
    if not log_dir["exists"]:
        issues.append("Log directory /Users/dnigga/Library/Logs/FoKS is MISSING")
    
    if not config_check.get("has_giovannini_origin"):
        issues.append("Cloudflare domains NOT in allowed_origins")
    
    if not foks_health["reachable"]:
        issues.append("FoKS is NOT running on port 8000")
    
    if issues:
        print("ISSUES DETECTED:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("✅ All checks passed!")
    
    log_debug("SUMMARY", "debug_system_state.py:summary", "Final summary", {
        "issues": issues,
        "issue_count": len(issues),
    })
    
    print()
    print(f"Debug logs written to: {DEBUG_LOG_PATH}")
    
    return 0 if not issues else 1

if __name__ == "__main__":
    sys.exit(main())

