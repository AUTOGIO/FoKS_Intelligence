
#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# FoKS / FBP Unified System Bootstrap
#
# - Validates local environment (Python, LM Studio, FoKS import)
# - Activates the FoKS virtualenv (if present)
# - Starts FoKS backend and (optionally) FBP backend via nohup
# - Spawns health-check watchers for FoKS / FBP / LM Studio
# - Runs non-fatal smoke tests for LMStudio and FBP clients
#
# This script only creates/uses system resources (processes, logs, env vars).
# It does NOT modify any Python source code.
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FOKS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$FOKS_DIR/backend"
LOG_DIR="$FOKS_DIR/logs"
FBP_DIR="${FBP_DIR:-"$HOME/Documents/FBP_Backend"}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_ts() {
  date '+%Y-%m-%d %H:%M:%S'
}

log_info() {
  printf "%b[INFO ] %s - %s%b\n" "$GREEN" "$(log_ts)" "$*" "$NC"
}

log_warn() {
  printf "%b[WARN ] %s - %s%b\n" "$YELLOW" "$(log_ts)" "$*" "$NC"
}

log_error() {
  printf "%b[ERROR] %s - %s%b\n" "$RED" "$(log_ts)" "$*" "$NC" >&2
}

log_section() {
  printf "\n%b=====================================================\n" "$BLUE"
  printf "%b%s%b\n" "$BLUE" "$*" "$NC"
  printf "%b=====================================================%b\n\n" "$BLUE" "$NC"
}

ensure_directories() {
  log_section "Ensuring workspace directories"
  mkdir -p "$FOKS_DIR" "$BACKEND_DIR" "$LOG_DIR"
  log_info "FoKS directory: $FOKS_DIR"
  log_info "Backend directory: $BACKEND_DIR"
  log_info "Logs directory: $LOG_DIR"
}

PYTHON_BIN=""

detect_python() {
  log_section "Detecting Python interpreter (preferring 3.11)"
  if command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3.11)"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  else
    log_error "No python3 interpreter found (expected python3.11 or python3)."
    exit 1
  fi
  log_info "Using Python interpreter: $PYTHON_BIN"
}

activate_venv() {
  log_section "Activating FoKS virtual environment (if present)"
  local venv1="$BACKEND_DIR/.venv/bin/activate"
  local venv2="$BACKEND_DIR/.venv_foks/bin/activate"

  if [[ -f "$venv1" ]]; then
    log_info "Sourcing virtualenv: $venv1"
    # shellcheck disable=SC1090
    source "$venv1"
  elif [[ -f "$venv2" ]]; then
    log_info "Sourcing alternate virtualenv: $venv2"
    # shellcheck disable=SC1090
    source "$venv2"
  else
    log_warn "No .venv or .venv_foks found under $BACKEND_DIR; continuing without activation."
  fi
}

configure_environment() {
  log_section "Configuring environment variables"

  export FOKS_PORT="${FOKS_PORT:-8080}"
  export FBP_PORT="${FBP_PORT:-9500}"
  export LMSTUDIO_PORT="${LMSTUDIO_PORT:-1234}"

  # Prepend FoKS backend to PYTHONPATH for app.main imports
  if [[ -n "${PYTHONPATH-}" ]]; then
    export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"
  else
    export PYTHONPATH="$BACKEND_DIR"
  fi

  log_info "FOKS_PORT     = $FOKS_PORT"
  log_info "FBP_PORT      = $FBP_PORT"
  log_info "LMSTUDIO_PORT = $LMSTUDIO_PORT"
  log_info "PYTHONPATH    = $PYTHONPATH"
}

check_lmstudio() {
  log_section "Checking LM Studio availability"
  local url="http://localhost:${LMSTUDIO_PORT}/v1/models"
  log_info "Probing $url"
  if curl -fsS "$url" >/dev/null 2>&1; then
    log_info "LM Studio is reachable at $url"
  else
    log_warn "LM Studio is not reachable at $url. Continue, but FoKS LM features may not work."
  fi
}

check_foks_import() {
  log_section "Checking FoKS backend import (app.main)"
  (
    cd "$FOKS_DIR"
    if "$PYTHON_BIN" - <<'EOF'
import sys
sys.path.insert(0, "backend")
try:
    import app.main  # noqa: F401
except Exception as exc:
    import traceback
    print("FoKS import failed:", repr(exc))
    traceback.print_exc()
    raise
EOF
    then
      log_info "FoKS app.main imported successfully."
    else
      log_warn "FoKS backend (app.main) could not be imported. Check virtualenv and dependencies."
    fi
  )
}

start_foks() {
  log_section "Starting FoKS backend"

  if [[ -f "$LOG_DIR/foks_server.pid" ]]; then
    local existing_pid
    existing_pid="$(cat "$LOG_DIR/foks_server.pid" || true)"
    if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" 2>/dev/null; then
      log_info "FoKS server already running (PID $existing_pid)"
      return 0
    fi
  fi

  log_info "Launching FoKS on port $FOKS_PORT"
  (
    cd "$BACKEND_DIR"
    nohup "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port "$FOKS_PORT" --reload \
      >>"$LOG_DIR/foks_server.log" 2>&1 &
    echo $! >"$LOG_DIR/foks_server.pid"
  )
  log_info "FoKS server started (PID $(cat "$LOG_DIR/foks_server.pid" 2>/dev/null || echo 'unknown')). Logs: $LOG_DIR/foks_server.log"
}

start_fbp() {
  log_section "Starting FBP backend (optional)"

  if [[ ! -d "$FBP_DIR" ]]; then
    log_warn "FBP directory not found at $FBP_DIR. Skipping FBP startup."
    return 0
  fi

  if [[ -f "$LOG_DIR/fbp_server.pid" ]]; then
    local existing_pid
    existing_pid="$(cat "$LOG_DIR/fbp_server.pid" || true)"
    if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" 2>/dev/null; then
      log_info "FBP server already running (PID $existing_pid)"
      return 0
    fi
  fi

  log_info "Launching FBP on port $FBP_PORT"
  (
    cd "$FBP_DIR"
    if [[ -f ".venv/bin/activate" ]]; then
      # shellcheck disable=SC1091
      source ".venv/bin/activate"
      log_info "Activated FBP virtualenv at $FBP_DIR/.venv"
    else
      log_warn "FBP virtualenv not found at $FBP_DIR/.venv; using system python."
    fi

    local fbp_python=""
    if command -v python3.11 >/dev/null 2>&1; then
      fbp_python="$(command -v python3.11)"
    elif command -v python3 >/dev/null 2>&1; then
      fbp_python="$(command -v python3)"
    fi

    if [[ -z "$fbp_python" ]]; then
      log_warn "No python3 interpreter found for FBP; skipping FBP start."
      exit 0
    fi

    nohup "$fbp_python" -m uvicorn app.main:app --host 0.0.0.0 --port "$FBP_PORT" --reload \
      >>"$LOG_DIR/fbp_server.log" 2>&1 &
    echo $! >"$LOG_DIR/fbp_server.pid"
  )
  log_info "FBP server start attempted (PID $(cat "$LOG_DIR/fbp_server.pid" 2>/dev/null || echo 'unknown')). Logs: $LOG_DIR/fbp_server.log"
}

start_health_watcher() {
  local name="$1"
  local url="$2"
  local logfile="$3"
  local pidfile="$4"

  if [[ -f "$pidfile" ]]; then
    local existing_pid
    existing_pid="$(cat "$pidfile" || true)"
    if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" 2>/dev/null; then
      log_info "Health watcher for $name already running (PID $existing_pid)"
      return 0
    fi
  fi

  log_info "Starting health watcher for $name at $url"

  env WATCH_NAME="$name" WATCH_URL="$url" bash -c '
    while true; do
      ts="$(date "+%Y-%m-%d %H:%M:%S")"
      echo "[$ts] Checking ${WATCH_NAME} at ${WATCH_URL}"
      if ! curl -fsS "${WATCH_URL}" >/dev/null 2>&1; then
        echo "[$ts] ${WATCH_NAME} health check FAILED"
      fi
      sleep 10
    done
  ' >>"$logfile" 2>&1 &

  echo $! >"$pidfile"
}

start_health_watchers() {
  log_section "Spawning health monitor watchers"

  start_health_watcher "FoKS" "http://localhost:${FOKS_PORT}/health" \
    "$LOG_DIR/watch_foks_health.log" "$LOG_DIR/watch_foks_health.pid"

  start_health_watcher "FBP" "http://localhost:${FBP_PORT}/health" \
    "$LOG_DIR/watch_fbp_health.log" "$LOG_DIR/watch_fbp_health.pid"

  start_health_watcher "LMStudio" "http://localhost:${LMSTUDIO_PORT}/v1/health" \
    "$LOG_DIR/watch_lmstudio_health.log" "$LOG_DIR/watch_lmstudio_health.pid"
}

run_smoke_tests() {
  log_section "Running non-fatal smoke tests (LMStudio & FBP clients)"

  (
    cd "$FOKS_DIR"
    export PYTHONPATH="$BACKEND_DIR:${PYTHONPATH-}"

    if "$PYTHON_BIN" -m pytest -q backend/tests/test_lmstudio_client.py \
      >>"$LOG_DIR/smoke_lmstudio_client.log" 2>&1; then
      log_info "LMStudio client smoke tests PASSED (see $LOG_DIR/smoke_lmstudio_client.log)"
    else
      log_warn "LMStudio client smoke tests FAILED (see $LOG_DIR/smoke_lmstudio_client.log)"
    fi

    if "$PYTHON_BIN" -m pytest -q backend/tests/test_fbp_client.py \
      >>"$LOG_DIR/smoke_fbp_client.log" 2>&1; then
      log_info "FBP client smoke tests PASSED (see $LOG_DIR/smoke_fbp_client.log)"
    else
      log_warn "FBP client smoke tests FAILED (see $LOG_DIR/smoke_fbp_client.log)"
    fi
  )
}

final_message() {
  cat <<EOF

=====================================================
FoKS Unified System Bootstrap Complete
Logs at: $LOG_DIR
=====================================================

EOF
}

main() {
  ensure_directories
  detect_python
  activate_venv
  configure_environment
  check_lmstudio
  check_foks_import
  start_foks
  start_fbp
  start_health_watchers
  run_smoke_tests || true
  final_message
}

main "$@"
