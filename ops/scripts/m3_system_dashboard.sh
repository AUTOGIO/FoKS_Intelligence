#!/usr/bin/env bash
################################################################################
# M3 System Dashboard & Health Monitor
# Monitors FoKS, FBP, and LM Studio health with resource usage
# macOS 26 Beta optimized
################################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
OPS_LOG_DIR="$PROJECT_ROOT/ops/logs"
DASHBOARD_LOG="$OPS_LOG_DIR/system_dashboard.log"

mkdir -p "$OPS_LOG_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
  local msg="$1"
  local timestamp
  timestamp=$(date '+%Y-%m-%dT%H:%M:%S')
  printf '%s %s\n' "[$timestamp]" "$msg" | tee -a "$DASHBOARD_LOG"
}

check_http_endpoint() {
  local name="$1"
  local url="$2"
  local timeout=2
  
  if curl --silent --fail --max-time "$timeout" "$url" >/dev/null 2>&1; then
    printf "${GREEN}✓${NC} %s" "$name"
    return 0
  else
    printf "${RED}✗${NC} %s" "$name"
    return 1
  fi
}

get_process_memory() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    echo "N/A"
    return
  fi
  if ps -p "$pid" >/dev/null 2>&1; then
    # macOS ps: -o rss (in KB)
    ps -p "$pid" -o rss= | awk '{printf "%.1f MB", $1 / 1024}'
  else
    echo "N/A (dead)"
  fi
}

get_process_cpu() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    echo "N/A"
    return
  fi
  if ps -p "$pid" >/dev/null 2>&1; then
    # macOS ps: -o %cpu
    ps -p "$pid" -o %cpu= | awk '{printf "%.1f%%", $1}'
  else
    echo "N/A (dead)"
  fi
}

################################################################################
# Main health check
################################################################################

log "=== M3 System Dashboard (iMac M3, 16GB, macOS 26) ==="
log ""

# FoKS health
log "FoKS Backend:"
if check_http_endpoint "  Status" "http://127.0.0.1:8001/health" 2>/dev/null; then
  echo ""
  if check_http_endpoint "  Metrics" "http://127.0.0.1:8001/metrics" 2>/dev/null; then
    echo ""
  fi
else
  echo " (DOWN)" 
  if [[ -f "$PROJECT_ROOT/ops/logs/foks_backend.pid" ]]; then
    foks_pid=$(cat "$PROJECT_ROOT/ops/logs/foks_backend.pid" 2>/dev/null || echo "")
    if [[ -n "$foks_pid" ]]; then
      log "  PID: $foks_pid | Memory: $(get_process_memory "$foks_pid") | CPU: $(get_process_cpu "$foks_pid")"
    fi
  fi
fi

log ""

# FBP health
log "FBP Backend:"
FBP_TRANSPORT="${FBP_TRANSPORT:-socket}"
FBP_SOCKET_PATH="${FBP_SOCKET_PATH:-/tmp/fbp.sock}"
FBP_PORT="${FBP_PORT:-8000}"
if [[ "$FBP_TRANSPORT" == "socket" ]]; then
  if curl --unix-socket "$FBP_SOCKET_PATH" -fsS http://localhost/socket-health >/dev/null 2>&1; then
    log "  Status: OK (socket $FBP_SOCKET_PATH)"
    echo ""
  else
    echo " (DOWN)"
  fi
else
  if check_http_endpoint "  Status" "http://127.0.0.1:${FBP_PORT}/socket-health" 2>/dev/null; then
    echo ""
  else
    echo " (DOWN)"
  fi
fi
if [[ -f "$PROJECT_ROOT/ops/logs/fbp_backend.pid" ]]; then
  fbp_pid=$(cat "$PROJECT_ROOT/ops/logs/fbp_backend.pid" 2>/dev/null || echo "")
  if [[ -n "$fbp_pid" ]]; then
    log "  PID: $fbp_pid | Memory: $(get_process_memory "$fbp_pid") | CPU: $(get_process_cpu "$fbp_pid")"
  fi
fi

log ""

# LM Studio health
log "LM Studio:"
if check_http_endpoint "  Status" "http://127.0.0.1:1234/v1/models" 2>/dev/null; then
  echo " (models available)"
else
  echo " (DOWN or not responding on port 1234)"
fi

log ""

# System resource snapshot
log "System Resources (M3 iMac):" 
log "  Total Memory: $(sysctl -n hw.memsize | awk '{printf "%.1f GB", $1 / 1024^3}')"
log "  Available Memory: $(vm_stat | grep 'Pages free' | awk '{printf "%.1f GB", $3 * 4096 / 1024^3}')"
log "  CPU Load: $(uptime | grep -o 'load average[^,]*' || echo 'N/A')"

log ""
log "Full log: $DASHBOARD_LOG"
log ""
