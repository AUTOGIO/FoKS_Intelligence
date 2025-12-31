#!/usr/bin/env bash
################################################################################
# M3 System Dashboard & Health Monitor
# Monitors FoKS, FBP, and LM Studio health with resource usage
# macOS 26 Beta optimized
#
# SERVICE CLASSIFICATION:
# - FoKS (port 8000): REQUIRED - System unhealthy if down
# - LM Studio (port 1234): REQUIRED - System unhealthy if down
# - FBP (port 9500): ON-DEMAND - Optional service, not an error if stopped
################################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
OPS_LOG_DIR="$PROJECT_ROOT/ops/logs"
DASHBOARD_LOG="$OPS_LOG_DIR/system_dashboard.log"

mkdir -p "$OPS_LOG_DIR"

# Configuration: FBP is on-demand by default
FBP_ON_DEMAND="${FBP_ON_DEMAND:-true}"

# Output mode: human-readable (default) or JSON
OUTPUT_JSON=false
if [[ "${1:-}" == "--json" ]]; then
  OUTPUT_JSON=true
fi

# Colors (only used in human-readable mode)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

log() {
  local msg="$1"
  if [[ "$OUTPUT_JSON" == true ]]; then
    return 0  # Suppress log output in JSON mode
  fi
  local timestamp
  timestamp=$(date '+%Y-%m-%dT%H:%M:%S')
  printf '%s %s\n' "[$timestamp]" "$msg" | tee -a "$DASHBOARD_LOG"
}

check_http_endpoint() {
  local name="$1"
  local url="$2"
  local timeout=2
  
  if curl --silent --fail --max-time "$timeout" "$url" >/dev/null 2>&1; then
    if [[ "$OUTPUT_JSON" == false ]]; then
      printf "${GREEN}✓${NC} %s" "$name"
    fi
    return 0
  else
    if [[ "$OUTPUT_JSON" == false ]]; then
      printf "${RED}✗${NC} %s" "$name"
    fi
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

# Health status tracking for JSON output
FOKS_HEALTH_OK="false"
FOKS_HEALTH_ERROR=""
FBP_HEALTH_OK="false"
FBP_HEALTH_EXPECTED="false"
FBP_HEALTH_ERROR=""
LMSTUDIO_HEALTH_OK="false"
LMSTUDIO_HEALTH_ERROR=""
SYSTEM_HEALTHY="true"

################################################################################
# Main health check
################################################################################

if [[ "$OUTPUT_JSON" == false ]]; then
  log "=== M3 System Dashboard (iMac M3, 16GB, macOS 26) ==="
  log ""
fi

# FoKS health (REQUIRED SERVICE)
if [[ "$OUTPUT_JSON" == false ]]; then
  log "FoKS Backend:"
fi
if check_http_endpoint "  Status" "http://127.0.0.1:8000/health" 2>/dev/null; then
  if [[ "$OUTPUT_JSON" == false ]]; then
    echo ""
    if check_http_endpoint "  Metrics" "http://127.0.0.1:8000/metrics" 2>/dev/null; then
      echo ""
    fi
  fi
  FOKS_HEALTH_OK="true"
else
  if [[ "$OUTPUT_JSON" == false ]]; then
    echo " (DOWN)" 
    if [[ -f "$PROJECT_ROOT/ops/logs/foks_backend.pid" ]]; then
      foks_pid=$(cat "$PROJECT_ROOT/ops/logs/foks_backend.pid" 2>/dev/null || echo "")
      if [[ -n "$foks_pid" ]]; then
        log "  PID: $foks_pid | Memory: $(get_process_memory "$foks_pid") | CPU: $(get_process_cpu "$foks_pid")"
      fi
    fi
  fi
  FOKS_HEALTH_OK="false"
  FOKS_HEALTH_ERROR="FoKS Backend is not responding on port 8000"
  SYSTEM_HEALTHY="false"
fi

if [[ "$OUTPUT_JSON" == false ]]; then
  log ""
fi

# FBP health (ON-DEMAND SERVICE)
FBP_PORT="${FBP_PORT:-9500}"
if [[ "$OUTPUT_JSON" == false ]]; then
  log "FBP Backend:"
fi
if check_http_endpoint "  Status" "http://127.0.0.1:${FBP_PORT}/health" 2>/dev/null; then
  if [[ "$OUTPUT_JSON" == false ]]; then
    echo ""
  fi
  FBP_HEALTH_OK="true"
  FBP_HEALTH_EXPECTED="true"
else
  # FBP is down - check if it's on-demand
  if [[ "$FBP_ON_DEMAND" == "true" ]]; then
    # On-demand service: down is expected, not an error
    FBP_HEALTH_OK="false"
    FBP_HEALTH_EXPECTED="false"
    if [[ "$OUTPUT_JSON" == false ]]; then
      printf "${WHITE}⚪${NC} On-demand (not running)\n"
    fi
    # System remains healthy even if FBP is down (on-demand)
  else
    # If FBP_ON_DEMAND=false, treat as required service
    FBP_HEALTH_OK="false"
    FBP_HEALTH_EXPECTED="true"
    FBP_HEALTH_ERROR="FBP Backend is not responding on port ${FBP_PORT}"
    SYSTEM_HEALTHY="false"
    if [[ "$OUTPUT_JSON" == false ]]; then
      echo " (DOWN)"
    fi
  fi
fi
if [[ -f "$PROJECT_ROOT/ops/logs/fbp_backend.pid" ]]; then
  fbp_pid=$(cat "$PROJECT_ROOT/ops/logs/fbp_backend.pid" 2>/dev/null || echo "")
  if [[ -n "$fbp_pid" && "$OUTPUT_JSON" == false ]]; then
    log "  PID: $fbp_pid | Memory: $(get_process_memory "$fbp_pid") | CPU: $(get_process_cpu "$fbp_pid")"
  fi
fi

if [[ "$OUTPUT_JSON" == false ]]; then
  log ""
fi

# LM Studio health (REQUIRED SERVICE)
if [[ "$OUTPUT_JSON" == false ]]; then
  log "LM Studio:"
fi
if check_http_endpoint "  Status" "http://127.0.0.1:1234/v1/models" 2>/dev/null; then
  if [[ "$OUTPUT_JSON" == false ]]; then
    echo " (models available)"
  fi
  LMSTUDIO_HEALTH_OK="true"
else
  if [[ "$OUTPUT_JSON" == false ]]; then
    echo " (DOWN or not responding on port 1234)"
  fi
  LMSTUDIO_HEALTH_OK="false"
  LMSTUDIO_HEALTH_ERROR="LM Studio is not responding on port 1234"
  SYSTEM_HEALTHY="false"
fi

if [[ "$OUTPUT_JSON" == false ]]; then
  log ""

  # System resource snapshot
  log "System Resources (M3 iMac):" 
  log "  Total Memory: $(sysctl -n hw.memsize | awk '{printf "%.1f GB", $1 / 1024^3}')"
  log "  Available Memory: $(vm_stat | grep 'Pages free' | awk '{printf "%.1f GB", $3 * 4096 / 1024^3}')"
  log "  CPU Load: $(uptime | grep -o 'load average[^,]*' || echo 'N/A')"

  log ""
  log "Full log: $DASHBOARD_LOG"
  log ""
fi

# JSON output for downstream tools (n8n, etc.)
if [[ "$OUTPUT_JSON" == true ]]; then
  # Get system resources for JSON
  TOTAL_MEM=$(sysctl -n hw.memsize 2>/dev/null | awk '{printf "%.1f", $1 / 1024^3}' || echo "N/A")
  FREE_MEM=$(vm_stat | grep 'Pages free' 2>/dev/null | awk '{printf "%.1f", $3 * 4096 / 1024^3}' || echo "N/A")
  CPU_LOAD=$(uptime | grep -o 'load average[^,]*' 2>/dev/null || echo "N/A")
  
  # Prepare error fields (null if empty)
  FOKS_ERROR_JSON="null"
  if [[ -n "${FOKS_HEALTH_ERROR:-}" ]]; then
    FOKS_ERROR_JSON=$(printf '%s' "$FOKS_HEALTH_ERROR" | jq -Rs . 2>/dev/null || echo "null")
  fi
  
  FBP_ERROR_JSON="null"
  if [[ -n "${FBP_HEALTH_ERROR:-}" ]]; then
    FBP_ERROR_JSON=$(printf '%s' "$FBP_HEALTH_ERROR" | jq -Rs . 2>/dev/null || echo "null")
  fi
  
  LMSTUDIO_ERROR_JSON="null"
  if [[ -n "${LMSTUDIO_HEALTH_ERROR:-}" ]]; then
    LMSTUDIO_ERROR_JSON=$(printf '%s' "$LMSTUDIO_HEALTH_ERROR" | jq -Rs . 2>/dev/null || echo "null")
  fi
  
  # Convert FBP_ON_DEMAND string to JSON boolean
  FBP_ON_DEMAND_JSON="false"
  if [[ "${FBP_ON_DEMAND}" == "true" ]]; then
    FBP_ON_DEMAND_JSON="true"
  fi
  
  cat <<EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "system": {
    "healthy": ${SYSTEM_HEALTHY},
    "resources": {
      "total_memory_gb": "${TOTAL_MEM}",
      "available_memory_gb": "${FREE_MEM}",
      "cpu_load": "${CPU_LOAD}"
    }
  },
  "services": {
    "foks": {
      "health": {
        "ok": ${FOKS_HEALTH_OK},
        "expected": true,
        "port": 8000,
        "error": ${FOKS_ERROR_JSON}
      }
    },
    "fbp": {
      "health": {
        "ok": ${FBP_HEALTH_OK},
        "expected": ${FBP_HEALTH_EXPECTED},
        "on_demand": ${FBP_ON_DEMAND_JSON},
        "port": ${FBP_PORT},
        "error": ${FBP_ERROR_JSON}
      }
    },
    "lmstudio": {
      "health": {
        "ok": ${LMSTUDIO_HEALTH_OK},
        "expected": true,
        "port": 1234,
        "error": ${LMSTUDIO_ERROR_JSON}
      }
    }
  }
}
EOF
fi

# Exit with error code if system is unhealthy (only for required services)
if [[ "$SYSTEM_HEALTHY" == "false" ]]; then
  exit 1
fi
exit 0
