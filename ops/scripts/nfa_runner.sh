#!/usr/bin/env bash
# NFA Runner Setup Script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$BACKEND_DIR/.venv_foks"
VENV_PYTHON="$VENV_DIR/bin/python"
LOG_DIR="$PROJECT_ROOT/logs"
FBP_DIR="/Users/dnigga/Documents/FBP_Backend"
FBP_TRANSPORT="${FBP_TRANSPORT:-socket}"
FBP_SOCKET_PATH="${FBP_SOCKET_PATH:-/tmp/fbp.sock}"
FBP_PORT="${FBP_PORT:-8000}"

log() {
  local level="$1"; shift
  local msg="$*"
  local color_reset=$'[0m'
  local color
  case "$level" in
    INFO)  color=$'[32m' ;;
    WARN)  color=$'[33m' ;;
    ERROR) color=$'[31m' ;;
    *)     color=$'[0m'  ;;
  esac
  printf '%s [%s] %s%s%s
' "$(date '+%Y-%m-%dT%H:%M:%S')" "$level" "$color" "$msg" "$color_reset"
}

log "INFO" "NFA Runner Setup"
log "INFO" "Project Root: $PROJECT_ROOT"
mkdir -p "$LOG_DIR"

if [[ ! -f "$VENV_PYTHON" ]]; then
  log "ERROR" "FoKS venv Python not found at $VENV_PYTHON"
  log "INFO" "Run ./ops/scripts/foks_boot.sh first to create venv"
  exit 1
fi

log "INFO" "Activating FoKS venv: $VENV_DIR"
source "$VENV_DIR/bin/activate"

log "INFO" "Starting FoKS backend..."
if [[ -f "$LOG_DIR/foks_backend.pid" ]]; then
  existing_pid="$(cat "$LOG_DIR/foks_backend.pid" 2>/dev/null || true)"
  if [[ -n "${existing_pid:-}" ]] && ps -p "$existing_pid" >/dev/null 2>&1; then
    log "INFO" "FoKS backend already running (PID $existing_pid)"
  else
    log "WARN" "Stale PID file found, removing..."
    rm -f "$LOG_DIR/foks_backend.pid"
    bash "$PROJECT_ROOT/ops/scripts/foks_boot.sh"
  fi
else
  bash "$PROJECT_ROOT/ops/scripts/foks_boot.sh"
fi

log "INFO" "Waiting for FoKS backend to be healthy..."
for i in {1..30}; do
  if curl -fsS --max-time 2 "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    log "INFO" "FoKS backend is healthy"
    break
  fi
  if [[ $i -eq 30 ]]; then
    log "WARN" "FoKS backend health check timed out (may still be starting)"
  else
    sleep 1
  fi
done

log "INFO" "Checking FBP backend..."
if [[ -d "$FBP_DIR" ]]; then
  if [[ "$FBP_TRANSPORT" == "socket" ]]; then
    if curl --unix-socket "$FBP_SOCKET_PATH" -fsS http://localhost/socket-health >/dev/null 2>&1; then
      log "INFO" "FBP backend is reachable via UNIX socket ($FBP_SOCKET_PATH)"
    else
      log "INFO" "FBP backend not reachable via UNIX socket (optional)"
    fi
  else
    FBP_URL="http://127.0.0.1:${FBP_PORT}/socket-health"
    if curl -fsS --max-time 2 "$FBP_URL" >/dev/null 2>&1; then
      log "INFO" "FBP backend is already running"
    else
      log "INFO" "FBP backend not running (optional)"
    fi
  fi
else
  log "WARN" "FBP directory not found at $FBP_DIR (optional)"
fi

log "INFO" "Validating LM Studio..."
LMSTUDIO_BASE_URL="${LMSTUDIO_BASE_URL:-http://192.168.1.192:1234}"
LMSTUDIO_URL="${LMSTUDIO_BASE_URL}/v1/models"
if curl -fsS --max-time 3 "$LMSTUDIO_URL" >/dev/null 2>&1; then
  MODEL_COUNT=$(curl -fsS --max-time 3 "$LMSTUDIO_URL" 2>/dev/null | grep -o '"id"' | wc -l || echo "0")
  if [[ "$MODEL_COUNT" -gt 0 ]]; then
    log "INFO" "LM Studio validated ($MODEL_COUNT models available)"
  else
    log "WARN" "LM Studio reachable but no models found"
  fi
else
  log "WARN" "LM Studio not reachable at $LMSTUDIO_BASE_URL"
fi

mkdir -p "$PROJECT_ROOT/output/nfa/screenshots"
mkdir -p "$PROJECT_ROOT/output/nfa/results"

log "INFO" "NFA Runner setup complete!"
log "INFO" "FoKS backend: http://127.0.0.1:8000"
if [[ "$FBP_TRANSPORT" == "socket" ]]; then
  log "INFO" "FBP backend: unix socket $FBP_SOCKET_PATH (if running)"
else
  log "INFO" "FBP backend: http://127.0.0.1:${FBP_PORT} (if running)"
fi
log "INFO" "LM Studio: $LMSTUDIO_BASE_URL"
