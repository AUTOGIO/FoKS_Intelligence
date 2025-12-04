#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OPS_LOG_DIR="$PROJECT_ROOT/ops/logs"
LOG_FILE="$OPS_LOG_DIR/lmstudio_watch.log"
PID_FILE="$OPS_LOG_DIR/lmstudio_watch.pid"

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

echo "$$" >"$PID_FILE"

INTERVAL_SECONDS="${INTERVAL_SECONDS:-5}"
LMSTUDIO_URL="${LMSTUDIO_URL:-http://127.0.0.1:1234/v1/models}"

log "INFO" "Starting LM Studio watcher (interval: ${INTERVAL_SECONDS}s, url: $LMSTUDIO_URL)"

while true; do
  if curl --silent --fail --max-time 2 "$LMSTUDIO_URL" >/dev/null 2>&1; then
    log "INFO" "LM Studio is online at $LMSTUDIO_URL"
  else
    log "WARN" "LM Studio is OFFLINE or unreachable at $LMSTUDIO_URL"
  fi
  sleep "$INTERVAL_SECONDS"
done


