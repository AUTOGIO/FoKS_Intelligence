#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OPS_LOG_DIR="$PROJECT_ROOT/ops/logs"
LOG_FILE="$OPS_LOG_DIR/watchdog_fbp.log"
PID_FILE="$OPS_LOG_DIR/watchdog_fbp.pid"
FBP_PID_FILE="$OPS_LOG_DIR/fbp_backend.pid"

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

echo "$$" >"$PID_FILE"

HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/health}"
CHECK_INTERVAL="${CHECK_INTERVAL:-10}"
CPU_THRESHOLD="${CPU_THRESHOLD:-95}"
CPU_WINDOW_SECONDS="${CPU_WINDOW_SECONDS:-30}"

consecutive_failures=0
high_cpu_seconds=0

get_fbp_pid() {
  if [[ -f "$FBP_PID_FILE" ]]; then
    cat "$FBP_PID_FILE" 2>/dev/null || true
  else
    echo ""
  fi
}

restart_fbp() {
  log "WARN" "Restarting FBP backend"
  if [[ -f "$FBP_PID_FILE" ]]; then
    local pid
    pid="$(cat "$FBP_PID_FILE" 2>/dev/null || true)"
    if [[ -n "${pid:-}" ]] && ps -p "$pid" >/dev/null 2>&1; then
      log "INFO" "Stopping FBP backend PID $pid before restart"
      kill "$pid" >/dev/null 2>&1 || kill -9 "$pid" >/dev/null 2>&1 || true
      sleep 1
    fi
    rm -f "$FBP_PID_FILE"
  fi

  bash "$PROJECT_ROOT/ops/scripts/fbp_boot.sh" || log "ERROR" "Failed to restart FBP via fbp_boot.sh"
}

has_google_error_marker() {
  local text="$1"
  local lowered
  lowered="$(printf '%s' "$text" | tr '[:upper:]' '[:lower:]')"
  if printf '%s' "$lowered" | grep -Eq 'google|gmail|oauth2|oauthlib|google-api-python-client|google\.auth'; then
    return 0
  fi
  return 1
}

check_health() {
  local body
  body="$(curl --silent --show-error --max-time 5 "$HEALTH_URL" 2>&1 || true)"
  if printf '%s' "$body" | grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"'; then
    consecutive_failures=0
    log "INFO" "FBP /health OK at $HEALTH_URL"
    return 0
  fi

  if has_google_error_marker "$body"; then
    consecutive_failures=$((consecutive_failures + 1))
    log "WARN" "FBP /health suggests Google/Gmail package issues (consecutive: $consecutive_failures)"
    log "HINT" "Activate FBP venv and run: pip install -r requirements.txt"
  else
    consecutive_failures=$((consecutive_failures + 1))
    log "WARN" "FBP /health FAILED (consecutive: $consecutive_failures)"
  fi

  if (( consecutive_failures >= 3 )); then
    log "WARN" "FBP health failed 3+ times; triggering restart"
    restart_fbp
    consecutive_failures=0
    high_cpu_seconds=0
  fi
}

check_cpu() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    high_cpu_seconds=0
    return 0
  fi

  if ! ps -p "$pid" >/dev/null 2>&1; then
    log "WARN" "FBP PID $pid missing; restarting"
    restart_fbp
    high_cpu_seconds=0
    return 0
  fi

  local cpu
  cpu="$(ps -p "$pid" -o %cpu= 2>/dev/null | tr -d '[:space:]' || echo "0")"

  if [[ -z "$cpu" ]]; then
    high_cpu_seconds=0
    return 0
  fi

  cpu_int="${cpu%.*}"
  if (( cpu_int > CPU_THRESHOLD )); then
    high_cpu_seconds=$((high_cpu_seconds + CHECK_INTERVAL))
    log "WARN" "FBP PID $pid high CPU: ${cpu}% (accumulated ${high_cpu_seconds}s)"
  else
    high_cpu_seconds=0
  fi

  if (( high_cpu_seconds >= CPU_WINDOW_SECONDS )); then
    log "WARN" "FBP CPU > ${CPU_THRESHOLD}% for ${CPU_WINDOW_SECONDS}s; restarting"
    restart_fbp
    high_cpu_seconds=0
  fi
}

log "INFO" "Starting FBP watchdog (health: $HEALTH_URL, interval: ${CHECK_INTERVAL}s)"

while true; do
  check_health
  fbp_pid="$(get_fbp_pid)"
  check_cpu "$fbp_pid"
  sleep "$CHECK_INTERVAL"
done


