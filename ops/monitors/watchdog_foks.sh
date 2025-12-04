#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OPS_LOG_DIR="$PROJECT_ROOT/ops/logs"
LOG_FILE="$OPS_LOG_DIR/watchdog_foks.log"
PID_FILE="$OPS_LOG_DIR/watchdog_foks.pid"
FOKS_PID_FILE="$OPS_LOG_DIR/foks_backend.pid"

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

get_foks_pid() {
  if [[ -f "$FOKS_PID_FILE" ]]; then
    cat "$FOKS_PID_FILE" 2>/dev/null || true
  else
    echo ""
  fi
}

restart_foks() {
  log "WARN" "Restarting FoKS backend"
  if [[ -f "$FOKS_PID_FILE" ]]; then
    local pid
    pid="$(cat "$FOKS_PID_FILE" 2>/dev/null || true)"
    if [[ -n "${pid:-}" ]] && ps -p "$pid" >/dev/null 2>&1; then
      log "INFO" "Stopping FoKS backend PID $pid before restart"
      kill "$pid" >/dev/null 2>&1 || kill -9 "$pid" >/dev/null 2>&1 || true
      sleep 1
    fi
    rm -f "$FOKS_PID_FILE"
  fi

  bash "$PROJECT_ROOT/ops/scripts/foks_boot.sh" || log "ERROR" "Failed to restart FoKS via foks_boot.sh"
}

check_health() {
  if curl --silent --fail --max-time 3 "$HEALTH_URL" >/dev/null 2>&1; then
    consecutive_failures=0
    log "INFO" "FoKS /health OK at $HEALTH_URL"
  else
    consecutive_failures=$((consecutive_failures + 1))
    log "WARN" "FoKS /health FAILED (consecutive: $consecutive_failures)"
  fi

  if (( consecutive_failures >= 3 )); then
    log "WARN" "FoKS health failed 3+ times; triggering restart"
    restart_foks
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
    log "WARN" "FoKS PID $pid missing; restarting"
    restart_foks
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
    log "WARN" "FoKS PID $pid high CPU: ${cpu}% (accumulated ${high_cpu_seconds}s)"
  else
    high_cpu_seconds=0
  fi

  if (( high_cpu_seconds >= CPU_WINDOW_SECONDS )); then
    log "WARN" "FoKS CPU > ${CPU_THRESHOLD}% for ${CPU_WINDOW_SECONDS}s; restarting"
    restart_foks
    high_cpu_seconds=0
  fi
}

log "INFO" "Starting FoKS watchdog (health: $HEALTH_URL, interval: ${CHECK_INTERVAL}s)"

while true; do
  check_health
  foks_pid="$(get_foks_pid)"
  check_cpu "$foks_pid"
  sleep "$CHECK_INTERVAL"
done


