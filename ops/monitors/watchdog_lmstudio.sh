#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OPS_LOG_DIR="$PROJECT_ROOT/ops/logs"
LOG_FILE="$OPS_LOG_DIR/watchdog_lmstudio.log"
PID_FILE="$OPS_LOG_DIR/watchdog_lmstudio.pid"

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

notify() {
  local title="$1"
  local message="$2"
  if command -v osascript >/dev/null 2>&1; then
    /usr/bin/osascript -e "display notification \"${message}\" with title \"${title}\""
  else
    log "WARN" "osascript not available; cannot show macOS notification. Message: $title - $message"
  fi
}

echo "$$" >"$PID_FILE"

LMSTUDIO_URL="${LMSTUDIO_URL:-http://127.0.0.1:1234/v1/models}"
CHECK_INTERVAL="${CHECK_INTERVAL:-10}"

log "INFO" "Starting LM Studio watchdog (url: $LMSTUDIO_URL, interval: ${CHECK_INTERVAL}s)"

was_online=0

while true; do
  if curl --silent --fail --max-time 3 "$LMSTUDIO_URL" >/dev/null 2>&1; then
    if (( was_online == 0 )); then
      log "INFO" "LM Studio came ONLINE at $LMSTUDIO_URL"
      notify "LM Studio" "LM Studio is online at $LMSTUDIO_URL"
      was_online=1
    fi
  else
    if (( was_online == 1 )); then
      log "WARN" "LM Studio went OFFLINE at $LMSTUDIO_URL"
      notify "LM Studio" "LM Studio is offline or unreachable"
      was_online=0
    else
      log "WARN" "LM Studio still offline/unreachable at $LMSTUDIO_URL"
    fi
  fi

  sleep "$CHECK_INTERVAL"
done


