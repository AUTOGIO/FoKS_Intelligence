#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OPS_LOG_DIR="$PROJECT_ROOT/ops/logs"
LOG_FILE="$OPS_LOG_DIR/system_dashboard.log"

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

print_section() {
  local title="$1"
  echo "===== $title ====="
}

cpu_usage() {
  if command -v top >/dev/null 2>&1; then
    top -l 1 -n 0 | grep "CPU usage" || echo "CPU usage: (top output unavailable)"
  else
    echo "CPU usage: 'top' command not available"
  fi
}

ram_usage() {
  if command -v vm_stat >/dev/null 2>&1; then
    local pages_free pages_active pages_speculative page_size total_used_gb
    page_size=$(vm_stat | awk '/page size of/ {print $8}')
    pages_free=$(vm_stat | awk '/Pages free/ {gsub("\\.", "", $3); print $3}')
    pages_active=$(vm_stat | awk '/Pages active/ {gsub("\\.", "", $3); print $3}')
    pages_speculative=$(vm_stat | awk '/Pages speculative/ {gsub("\\.", "", $3); print $3}')
    total_used_gb=$(( (pages_active + pages_speculative) * page_size / 1024 / 1024 / 1024 ))
    echo "RAM used (approx): ${total_used_gb} GB"
  else
    echo "RAM usage: 'vm_stat' command not available"
  fi
}

gpu_usage() {
  if command -v powermetrics >/dev/null 2>&1; then
    if [[ "$EUID" -ne 0 ]]; then
      echo "GPU/ANE usage: powermetrics available but requires sudo (run: sudo powermetrics --samplers smc -n 1)"
    else
      powermetrics --samplers smc -n 1 | grep -Ei 'GPU|ANE' || echo "GPU/ANE metrics not found in powermetrics output"
    fi
  else
    echo "GPU/ANE usage: 'powermetrics' not available"
  fi
}

active_pids() {
  echo "FoKS PID file: $OPS_LOG_DIR/foks_backend.pid"
  if [[ -f "$OPS_LOG_DIR/foks_backend.pid" ]]; then
    echo "FoKS PID: $(cat "$OPS_LOG_DIR/foks_backend.pid" 2>/dev/null || echo 'unknown')"
  else
    echo "FoKS PID: (no PID file)"
  fi

  echo "FBP PID file: $OPS_LOG_DIR/fbp_backend.pid"
  if [[ -f "$OPS_LOG_DIR/fbp_backend.pid" ]]; then
    echo "FBP PID: $(cat "$OPS_LOG_DIR/fbp_backend.pid" 2>/dev/null || echo 'unknown')"
  else
    echo "FBP PID: (no PID file)"
  fi
}

lmstudio_model() {
  local url="http://127.0.0.1:1234/v1/models"
  if ! command -v curl >/dev/null 2>&1; then
    echo "LM Studio: curl not available"
    return
  fi

  local json
  json="$(curl -s --max-time 3 "$url" || true)"
  if [[ -z "$json" ]]; then
    echo "LM Studio: offline or no response from $url"
    return
  fi

  local first_model
  first_model="$(printf '%s' "$json" | python3 - << 'PY'
import json, sys
try:
    data = json.loads(sys.stdin.read())
except Exception:
    print("")
    raise SystemExit(0)

models = data.get("data") or data.get("models") or []
if not isinstance(models, list) or not models:
    print("")
    raise SystemExit(0)

model = models[0]
mid = model.get("id") or model.get("name") or "unknown"
print(str(mid))
PY
)"

  if [[ -z "$first_model" ]]; then
    echo "LM Studio: models endpoint reachable but no models listed"
  else
    echo "LM Studio: first/active model -> $first_model"
  fi
}

fbp_request_rate() {
  local log_file="$OPS_LOG_DIR/fbp_backend.out"
  if [[ ! -f "$log_file" ]]; then
    echo "FBP request rate: log file not found at $log_file (start via fbp_boot.sh)"
    return
  fi

  local now_epoch start_epoch
  now_epoch=$(date +%s)
  start_epoch=$((now_epoch - 300))

  local count
  count=$(awk -v start="$start_epoch" '
    {
      # Expecting uvicorn-style timestamps: 2025-01-01 12:34:56
      if ($1 ~ /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/ && $2 ~ /^[0-9]{2}:[0-9]{2}:[0-9]{2}$/) {
        ts = $1 " " $2
        gsub(/[-:]/, " ", ts)
        split(ts, a, " ")
        # crude epoch approximation: rely on date -j -f via system
      }
    }
  ' "$log_file" 2>/dev/null | wc -l | awk '{print $1}')

  # Fallback simple heuristic: count lines with "HTTP/" in last 300s chunk
  if [[ "$count" -eq 0 ]]; then
    count=$(grep -c "HTTP/" "$log_file" 2>/dev/null || echo "0")
  fi

  echo "FBP request rate (approx, lifetime): ${count} requests logged (see $log_file)"
}

log "INFO" "Generating system dashboard snapshot"

print_section "CPU Usage"
cpu_usage

print_section "RAM Usage"
ram_usage

print_section "GPU / ANE (Apple M3) Utilization"
gpu_usage

print_section "Active PIDs"
active_pids

print_section "LM Studio Model"
lmstudio_model

print_section "FBP Request Rate"
fbp_request_rate


