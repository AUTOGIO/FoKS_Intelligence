#!/usr/bin/env bash
################################################################################
# Start FBP Backend Script
# Starts FBP backend and verifies socket creation
################################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FBP_ROOT="/Users/dnigga/Documents/FBP_Backend"
SOCKET_PATH="/tmp/fbp.sock"
OPS_LOG_DIR="$PROJECT_ROOT/ops/logs"
PID_FILE="$OPS_LOG_DIR/fbp_backend.pid"

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
  printf '%s [%s] %s%s%s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$level" "$color" "$msg" "$color_reset"
}

################################################################################
# Check if FBP is already running
################################################################################
check_running() {
  # Check PID file
  if [[ -f "$PID_FILE" ]]; then
    local existing_pid
    existing_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "${existing_pid:-}" ]] && ps -p "$existing_pid" >/dev/null 2>&1; then
      log "INFO" "FBP backend already running with PID $existing_pid"
      
      # Verify socket exists
      if [[ -S "$SOCKET_PATH" ]]; then
        log "INFO" "✓ Socket exists: $SOCKET_PATH"
        return 0
      else
        log "WARN" "Process running but socket not found, removing stale PID file"
        rm -f "$PID_FILE"
        return 1
      fi
    else
      log "WARN" "Removing stale PID file at $PID_FILE"
      rm -f "$PID_FILE"
    fi
  fi
  
  # Check socket directly
  if [[ -S "$SOCKET_PATH" ]]; then
    # Check if process is listening on socket
    if lsof "$SOCKET_PATH" >/dev/null 2>&1; then
      log "INFO" "FBP backend appears to be running (socket exists and has listener)"
      return 0
    else
      log "WARN" "Socket exists but no process listening, removing stale socket"
      rm -f "$SOCKET_PATH"
    fi
  fi
  
  return 1
}

################################################################################
# Validate FBP directory
################################################################################
validate_fbp() {
  if [[ ! -d "$FBP_ROOT" ]]; then
    log "ERROR" "FBP backend directory not found at $FBP_ROOT"
    log "HINT" "Expected path: $FBP_ROOT"
    return 1
  fi
  log "INFO" "✓ FBP backend directory found: $FBP_ROOT"
  return 0
}

################################################################################
# Start FBP backend
################################################################################
start_fbp() {
  log "INFO" "Starting FBP backend..."
  
  # Use existing boot script if available
  FBP_BOOT_SCRIPT="$PROJECT_ROOT/ops/scripts/fbp_boot.sh"
  if [[ -f "$FBP_BOOT_SCRIPT" ]] && [[ -x "$FBP_BOOT_SCRIPT" ]]; then
    log "INFO" "Using FBP boot script: $FBP_BOOT_SCRIPT"
    log "INFO" "Note: This script will start FBP in foreground (use launchd for background)"
    
    # Execute boot script (will handle venv, requirements, etc.)
    exec "$FBP_BOOT_SCRIPT"
  else
    log "ERROR" "FBP boot script not found: $FBP_BOOT_SCRIPT"
    log "HINT" "Expected script at: $FBP_BOOT_SCRIPT"
    return 1
  fi
}

################################################################################
# Main
################################################################################
main() {
  log "INFO" "=========================================="
  log "INFO" "FBP Backend Startup"
  log "INFO" "=========================================="
  log "INFO" ""
  
  # Check if already running
  if check_running; then
    log "INFO" "FBP backend is already running"
    exit 0
  fi
  
  # Validate FBP directory
  if ! validate_fbp; then
    exit 1
  fi
  
  # Start FBP
  start_fbp
}

main "$@"
