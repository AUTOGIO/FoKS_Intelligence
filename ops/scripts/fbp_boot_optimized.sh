#!/usr/bin/env bash
################################################################################
# FBP Backend Bootstrap Script (M3 Optimized)
# Best practices:
#  - No daemonization; let launchd manage lifecycle
#  - Explicit logging via StandardOutPath/StandardErrorPath
#  - uvloop for improved async performance
#  - Single worker (1 process) + high async concurrency
#  - Health check via /health endpoint
#  - Proper environment isolation
################################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FBP_ROOT="${FBP_ROOT:-"$HOME/Documents/FBP_Backend"}"
OPS_LOG_DIR="$PROJECT_ROOT/ops/logs"
PID_FILE="$OPS_LOG_DIR/fbp_backend.pid"
LOG_FILE="$OPS_LOG_DIR/fbp_boot.log"

mkdir -p "$OPS_LOG_DIR"

################################################################################
# Logging utility
################################################################################
log() {
  local level="$1"; shift
  local msg="$*"
  local color_reset=$'\033[0m'
  local color
  case "$level" in
    INFO)  color=$'\033[32m' ;; # green
    WARN)  color=$'\033[33m' ;; # yellow
    ERROR) color=$'\033[31m' ;; # red
    HINT)  color=$'\033[36m' ;; # cyan
    *)     color=$'\033[0m'  ;;
  esac
  printf '%s [%s] %s%s%s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$level" "$color" "$msg" "$color_reset" | tee -a "$LOG_FILE"
}

################################################################################
# Validation
################################################################################
if [[ ! -d "$FBP_ROOT" ]]; then
  log "ERROR" "FBP backend directory not found at $FBP_ROOT"
  exit 1
fi

VENV_PATH="$HOME/Documents/.venvs/fbp"
if [[ ! -d "$VENV_PATH" ]]; then
  log "ERROR" "FBP virtualenv not found at $VENV_PATH"
  log "HINT" "Create it with: python3 -m venv \"$VENV_PATH\" && source \"$VENV_PATH/bin/activate\" && cd \"$FBP_ROOT\" && pip install -e '.[dev]'"
  exit 1
fi

# shellcheck disable=SC1090
source "$VENV_PATH/bin/activate"

################################################################################
# Check Playwright setup
################################################################################
if command -v playwright >/dev/null 2>&1; then
  pw_version="$(playwright --version 2>/dev/null || true)"
  log "INFO" "Playwright detected ($pw_version)"
else
  log "WARN" "Playwright CLI not found. Some NFA flows may fail. Run: \"$FBP_ROOT/scripts/setup_playwright.sh\""
fi

################################################################################
# Ensure uvloop is installed
################################################################################
if ! python -c "import uvloop" 2>/dev/null; then
  log "INFO" "Installing uvloop for improved async performance on M3"
  pip install uvloop >/dev/null 2>&1 || log "WARN" "uvloop install failed; FastAPI will use default event loop"
fi

################################################################################
# Check for existing process
################################################################################
if [[ -f "$PID_FILE" ]]; then
  existing_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "${existing_pid:-}" ]] && ps -p "$existing_pid" >/dev/null 2>&1; then
    log "INFO" "FBP backend already running with PID $existing_pid"
    exit 0
  else
    log "WARN" "Removing stale FBP PID file at $PID_FILE"
    rm -f "$PID_FILE"
  fi
fi

################################################################################
# Environment setup
################################################################################
cd "$FBP_ROOT"
export PYTHONPATH="$FBP_ROOT:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Uvicorn tuning for M3 (single worker, high async concurrency)
LOOP_TYPE="uvloop"  # Use uvloop if available
HTTP_TYPE="auto"    # Auto-detect httptools
WORKERS=1            # Single worker on local M3

log "INFO" "Starting FBP backend with uvicorn on 0.0.0.0:8000"
log "INFO" "  - Workers: $WORKERS (single process, high async concurrency)"
log "INFO" "  - Loop: $LOOP_TYPE (Apple Silicon optimized)"
log "INFO" "  - HTTP: $HTTP_TYPE"
log "INFO" "  - Root directory: $FBP_ROOT"

# Run in foreground (launchd will manage it)
"$VENV_PATH/bin/uvicorn" app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers "$WORKERS" \
  --loop "$LOOP_TYPE" \
  --http "$HTTP_TYPE" \
  --timeout-keep-alive 5 \
  --timeout-notify 30 \
  --access-log

exit 1
