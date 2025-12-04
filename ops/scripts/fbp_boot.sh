#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FBP_ROOT="${FBP_ROOT:-"$HOME/Documents/FBP_Backend"}"
OPS_LOG_DIR="$PROJECT_ROOT/ops/logs"
PID_FILE="$OPS_LOG_DIR/fbp_backend.pid"
LOG_FILE="$OPS_LOG_DIR/fbp_boot.log"

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

if [[ ! -d "$FBP_ROOT" ]]; then
  log "ERROR" "FBP backend directory not found at $FBP_ROOT"
  exit 1
fi

VENV_PATH="$HOME/Documents/.venvs/fbp"
if [[ ! -d "$VENV_PATH" ]]; then
  log "ERROR" "FBP virtualenv not found at $VENV_PATH"
  log "HINT" "Create it with: python3 -m venv \"$VENV_PATH\" && \"$VENV_PATH/bin/pip\" install -e '.[dev]' (run inside $FBP_ROOT)"
  exit 1
fi

# shellcheck disable=SC1090
source "$VENV_PATH/bin/activate"

export PYTHONPATH="$FBP_ROOT:${PYTHONPATH:-}"

if command -v playwright >/dev/null 2>&1; then
  pw_version="$(playwright --version 2>/dev/null || true)"
  log "INFO" "Playwright detected ($pw_version)"
else
  log "WARN" "Playwright CLI not found. Some NFA flows may fail. Run: \"$FBP_ROOT/scripts/setup_playwright.sh\""
fi

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

cd "$FBP_ROOT"

log "INFO" "Starting FBP backend with uvicorn on 0.0.0.0:8000"
nohup uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  >>"$OPS_LOG_DIR/fbp_backend.out" 2>&1 &

new_pid=$!
echo "$new_pid" >"$PID_FILE"
log "INFO" "FBP backend started with PID $new_pid (PID file: $PID_FILE)"

HEALTH_URL="http://127.0.0.1:8000/health"
attempts=0
max_attempts=30

while (( attempts < max_attempts )); do
  if curl --silent --fail --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
    log "INFO" "FBP health check passed at $HEALTH_URL"
    exit 0
  fi
  attempts=$((attempts + 1))
  sleep 1
done

log "WARN" "FBP health check did not succeed after ${max_attempts}s (URL: $HEALTH_URL)"


