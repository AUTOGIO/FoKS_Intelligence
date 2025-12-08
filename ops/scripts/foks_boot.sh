#!/usr/bin/env bash
################################################################################
# FoKS Backend Bootstrap Script (M3 Optimized)
# Best practices:
#  - No daemonization; let launchd manage lifecycle
#  - Explicit logging via StandardOutPath/StandardErrorPath
#  - uvloop for improved async performance
#  - Single worker (1 process) + high async concurrency
#  - Proper PID tracking for watchdog
################################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
OPS_LOG_DIR="$PROJECT_ROOT/ops/logs"
PID_FILE="$OPS_LOG_DIR/foks_backend.pid"
LOG_FILE="$OPS_LOG_DIR/foks_boot.log"

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
if [[ ! -d "$BACKEND_DIR" ]]; then
  log "ERROR" "FoKS backend directory not found at $BACKEND_DIR"
  exit 1
fi

VENV_DIR="$BACKEND_DIR/.venv_foks"

if [[ ! -d "$VENV_DIR" ]]; then
  log "INFO" "Creating FoKS virtualenv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

################################################################################
# Install/upgrade dependencies
################################################################################
log "INFO" "Checking FoKS backend dependencies..."

if ! pip install --upgrade pip setuptools wheel >/dev/null 2>&1; then
  log "WARN" "Failed to upgrade pip; continuing"
fi

# Ensure uvloop is installed (for better async performance on M3)
if ! python -c "import uvloop" 2>/dev/null; then
  log "INFO" "Installing uvloop for improved async performance on M3"
  pip install uvloop >/dev/null 2>&1 || log "WARN" "uvloop install failed; FastAPI will use default event loop"
fi

if ! pip install -r "$BACKEND_DIR/requirements.txt" >/dev/null 2>&1; then
  log "WARN" "Failed to install/update FoKS requirements; proceeding"
fi

################################################################################
# Check for existing process
################################################################################
if [[ -f "$PID_FILE" ]]; then
  existing_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "${existing_pid:-}" ]] && ps -p "$existing_pid" >/dev/null 2>&1; then
    log "INFO" "FoKS backend already running with PID $existing_pid"
    exit 0
  else
    log "WARN" "Removing stale FoKS PID file at $PID_FILE"
    rm -f "$PID_FILE"
  fi
fi

################################################################################
# Environment setup
################################################################################
cd "$BACKEND_DIR"
export PYTHONPATH="$BACKEND_DIR:${PYTHONPATH:-}"

# M3 optimization hints
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Optional: tune uvicorn for M3 (single worker, high async concurrency)
# See: https://www.uvicorn.org/settings/
LOOP_TYPE="uvloop"  # Use uvloop if available (async improvements)
HTTP_TYPE="auto"    # Let uvicorn auto-detect httptools
WORKERS=1            # Single worker on local M3 (async handles concurrency)
WORKER_CLASS="uvicorn.workers.UvicornWorker"

log "INFO" "Starting FoKS backend with uvicorn on 0.0.0.0:8000"
log "INFO" "  - Workers: $WORKERS (single process, high async concurrency)"
log "INFO" "  - Loop: $LOOP_TYPE (Apple Silicon optimized)"
log "INFO" "  - HTTP: $HTTP_TYPE"

# Run in foreground (launchd will manage it)
# Note: We do NOT use nohup; let launchd handle process lifecycle
"$VENV_DIR/bin/python" -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers "$WORKERS" \
  --loop "$LOOP_TYPE" \
  --http "$HTTP_TYPE" \
  --timeout-keep-alive 5 \
  --timeout-notify 30 \
  --access-log

# If we reach here, the process exited; let launchd restart it
log "WARN" "FoKS backend process exited (launchd will restart if KeepAlive is enabled)"
exit 1
