#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
OPS_LOG_DIR="$PROJECT_ROOT/ops/logs"
PID_FILE="$OPS_LOG_DIR/foks_backend.pid"
LOG_FILE="$OPS_LOG_DIR/foks_boot.log"

mkdir -p "$OPS_LOG_DIR"

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

log "INFO" "Ensuring FoKS backend dependencies are installed"
if ! pip install --upgrade pip >/dev/null 2>&1; then
  log "WARN" "Failed to upgrade pip; continuing"
fi
if ! pip install -r "$BACKEND_DIR/requirements.txt" >/dev/null 2>&1; then
  log "WARN" "Failed to install FoKS requirements; backend may fail to start"
fi

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

cd "$BACKEND_DIR"
export PYTHONPATH="$BACKEND_DIR:${PYTHONPATH:-}"

log "INFO" "Starting FoKS backend with uvicorn on 0.0.0.0:8000"
nohup "$VENV_DIR/bin/python" -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  >>"$OPS_LOG_DIR/foks_backend.out" 2>&1 &

new_pid=$!
echo "$new_pid" >"$PID_FILE"
log "INFO" "FoKS backend started with PID $new_pid (PID file: $PID_FILE)"


