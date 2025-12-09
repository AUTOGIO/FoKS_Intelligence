#!/usr/bin/env bash
# FoKS Full System Diagnostic Script
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$BACKEND_DIR/.venv_foks"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
PASSED=0
WARNINGS=0
FAILURES=0
check() { local name="$1"; shift; printf "${CYAN}Checking: ${name}...${NC} "; if "$@" >/dev/null 2>&1; then echo -e "${GREEN}✓ PASSED${NC}"; ((PASSED++)); return 0; else echo -e "${RED}✗ FAILED${NC}"; ((FAILURES++)); return 1; fi; }
warn() { local name="$1"; local msg="$2"; echo -e "${CYAN}Checking: ${name}...${NC} ${YELLOW}⚠ WARNING: ${msg}${NC}"; ((WARNINGS++)); }
info() { echo -e "${CYAN}ℹ $*${NC}"; }
echo "=========================================="
echo "  FoKS Full System Diagnostic"
echo "=========================================="
echo ""
echo "=== 1. Virtual Environment ==="
if [[ -d "$VENV_DIR" ]]; then
    check test -d "$VENV_DIR"
    check test -f "$VENV_DIR/bin/python"
    info "Python: $("$VENV_DIR/bin/python" --version 2>&1)"
else
    warn "Virtualenv" "Not found at $VENV_DIR"
fi
echo ""
echo "=== 2. Python Dependencies ==="
if [[ -d "$VENV_DIR" ]]; then
    check "$VENV_DIR/bin/python" -c "import fastapi"
    check "$VENV_DIR/bin/python" -c "import uvicorn"
    check "$VENV_DIR/bin/python" -c "import httpx"
    check "$VENV_DIR/bin/python" -c "import pydantic"
    check "$VENV_DIR/bin/python" -c "import playwright" || warn "Playwright" "Not installed"
    info "Uvicorn: $("$VENV_DIR/bin/python" -m uvicorn --version 2>&1 || echo unknown)"
fi
echo ""
echo "=== 3. LM Studio Integration ==="
LMSTUDIO_URL="${LMSTUDIO_BASE_URL:-http://192.168.1.192:1234}"
LMSTUDIO_URL="${LMSTUDIO_URL%/v1}"
info "LM Studio URL: $LMSTUDIO_URL"
if check curl -s --max-time 5 "$LMSTUDIO_URL/v1/models"; then
    MODEL_COUNT=$(curl -s --max-time 5 "$LMSTUDIO_URL/v1/models" 2>/dev/null | grep -o id | wc -l || echo "0")
    info "Available models: $MODEL_COUNT"
else
    warn "LM Studio" "Cannot reach $LMSTUDIO_URL"
fi
echo ""
echo "=== 4. FoKS Backend ==="
if [[ -d "$BACKEND_DIR" ]]; then
    cd "$BACKEND_DIR"
    export PYTHONPATH="$BACKEND_DIR:${PYTHONPATH:-}"
    check "$VENV_DIR/bin/python" -c "from app.main import app" && info "FoKS app imports OK"
    if check "$VENV_DIR/bin/python" -c "from app.config import settings; print(settings.app_name)"; then
        LM_URL=$("$VENV_DIR/bin/python" -c "from app.config import settings; print(settings.lmstudio_base_url)" 2>/dev/null || echo "unknown")
        info "LM Studio URL in config: $LM_URL"
    fi
fi
echo ""
echo "=== 5. FBP Backend Integration ==="
FBP_TRANSPORT="${FBP_TRANSPORT:-socket}"
FBP_SOCKET_PATH="${FBP_SOCKET_PATH:-/tmp/fbp.sock}"
FBP_PORT="${FBP_PORT:-8000}"
FBP_URL="${FBP_URL:-http://localhost:${FBP_PORT}}"
if [[ "$FBP_TRANSPORT" == "socket" ]]; then
    if check curl --unix-socket "$FBP_SOCKET_PATH" -s --max-time 5 http://localhost/socket-health; then
        info "FBP health OK (UNIX socket)"
        check curl --unix-socket "$FBP_SOCKET_PATH" -s --max-time 5 http://localhost/api/nfa/test || warn "FBP NFA" "Endpoint may not be available"
    else
        warn "FBP" "Cannot reach UNIX socket at $FBP_SOCKET_PATH"
    fi
else
    if check curl -s --max-time 5 "$FBP_URL/socket-health"; then
        info "FBP health OK (TCP)"
        check curl -s --max-time 5 "$FBP_URL/api/nfa/test" || warn "FBP NFA" "Endpoint may not be available"
    else
        warn "FBP" "Cannot reach $FBP_URL"
    fi
fi
echo ""
echo "=== 6. Playwright Environment ==="
if [[ -d "$VENV_DIR" ]]; then
    if check "$VENV_DIR/bin/python" -c "import playwright"; then
        PLAYWRIGHT_VERSION=$("$VENV_DIR/bin/python" -c "import playwright; print(playwright.__version__)" 2>/dev/null || echo "unknown")
        info "Playwright version: $PLAYWRIGHT_VERSION"
        if "$VENV_DIR/bin/python" -c "from playwright.sync_api import sync_playwright; p = sync_playwright(); p.start(); p.chromium.launch(headless=True); p.stop()" >/dev/null 2>&1; then
            check true
        else
            warn "Playwright browsers" "Chromium not installed - run: $VENV_DIR/bin/python -m playwright install chromium"
        fi
    fi
fi
echo ""
echo "=== 7. Directory Permissions ==="
mkdir -p "$PROJECT_ROOT/output/nfa/screenshots" "$PROJECT_ROOT/output/nfa/results" "$PROJECT_ROOT/ops/logs"
check test -w "$PROJECT_ROOT/output/nfa/screenshots"
check test -w "$PROJECT_ROOT/output/nfa/results"
check test -w "$PROJECT_ROOT/ops/logs"
check test -r "$BACKEND_DIR"
echo ""
echo "=== 8. NFA Module Readiness ==="
if [[ -d "$BACKEND_DIR" ]]; then
    cd "$BACKEND_DIR"
    export PYTHONPATH="$BACKEND_DIR:${PYTHONPATH:-}"
    check curl -s --max-time 5 "$FBP_URL/api/nfa/test" || warn "FBP NFA" "Cannot verify"
    if [[ -f "$PROJECT_ROOT/../FBP_Backend/app/modules/nfa/screenshot_utils.py" ]]; then
        info "FBP screenshot_utils.py found"
    fi
fi
echo ""
echo "=========================================="
echo "  Diagnostic Summary"
echo "=========================================="
echo -e "${GREEN}✓ Passed: ${PASSED}${NC}"
echo -e "${YELLOW}⚠ Warnings: ${WARNINGS}${NC}"
echo -e "${RED}✗ Failures: ${FAILURES}${NC}"
echo ""
if [[ $FAILURES -eq 0 ]]; then
    if [[ $WARNINGS -eq 0 ]]; then
        echo -e "${GREEN}✅ ALL CHECKS PASSED - System ready for NFA${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ CHECKS PASSED WITH WARNINGS - Review warnings above${NC}"
        exit 0
    fi
else
    echo -e "${RED}❌ FAILURES DETECTED - Fix issues above before running NFA${NC}"
    exit 1
fi
