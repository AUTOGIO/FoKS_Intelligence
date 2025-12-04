#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OPS_LOG_DIR="$PROJECT_ROOT/ops/logs"
LOG_FILE="$OPS_LOG_DIR/kill_all.log"

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
    *)     color=$'\033[0m'  ;;
  esac
  printf '%s [%s] %s%s%s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$level" "$color" "$msg" "$color_reset" | tee -a "$LOG_FILE"
}

stop_service() {
  local name="$1"
  local pid_file="$2"

  if [[ ! -f "$pid_file" ]]; then
    log "INFO" "No PID file for $name at $pid_file (nothing to stop)"
    return 0
  fi

  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [[ -z "${pid:-}" ]]; then
    log "WARN" "Empty PID in $pid_file for $name; removing file"
    rm -f "$pid_file"
    return 0
  fi

  if ! ps -p "$pid" >/dev/null 2>&1; then
    log "INFO" "Process $pid for $name is not running; removing stale PID file"
    rm -f "$pid_file"
    return 0
  fi

  log "INFO" "Stopping $name (PID $pid)"
  if ! kill "$pid" >/dev/null 2>&1; then
    log "WARN" "Failed to send SIGTERM to $name (PID $pid); attempting SIGKILL"
    kill -9 "$pid" >/dev/null 2>&1 || true
  fi

  sleep 1

  if ps -p "$pid" >/dev/null 2>&1; then
    log "WARN" "$name (PID $pid) still running after kill attempts"
  else
    log "INFO" "$name (PID $pid) stopped successfully"
    rm -f "$pid_file"
  fi
}

log "INFO" "Killing FoKS, FBP and watcher processes (safe mode)"

stop_service "FoKS backend" "$OPS_LOG_DIR/foks_backend.pid"
stop_service "FBP backend" "$OPS_LOG_DIR/fbp_backend.pid"
stop_service "LM Studio watcher" "$OPS_LOG_DIR/lmstudio_watch.pid"
stop_service "FoKS watchdog" "$OPS_LOG_DIR/watchdog_foks.pid"
stop_service "FBP watchdog" "$OPS_LOG_DIR/watchdog_fbp.pid"
stop_service "LM Studio watchdog" "$OPS_LOG_DIR/watchdog_lmstudio.pid"

log "INFO" "kill_all.sh completed"


