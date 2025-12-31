#!/usr/bin/env bash
################################################################################
# FBP Status Diagnostic Script
# Checks FBP socket, process, and connectivity
################################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOCKET_PATH="${FBP_SOCKET_PATH:-/tmp/fbp.sock}"
FBP_ROOT="/Users/dnigga/Documents/FBP_Backend"
OPS_LOG_DIR="$PROJECT_ROOT/ops/logs"
PID_FILE="$OPS_LOG_DIR/fbp_backend.pid"

################################################################################
# Colors
################################################################################
RED=$'\033[31m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
CYAN=$'\033[36m'
RESET=$'\033[0m'

################################################################################
# Print status with color
################################################################################
print_status() {
  local status="$1"
  local message="$2"
  case "$status" in
    OK)    echo "${GREEN}✓${RESET} $message" ;;
    ERROR) echo "${RED}✗${RESET} $message" ;;
    WARN)  echo "${YELLOW}⚠${RESET} $message" ;;
    INFO)  echo "${CYAN}ℹ${RESET} $message" ;;
    *)     echo "  $message" ;;
  esac
}

################################################################################
# Check socket existence
################################################################################
check_socket() {
  echo ""
  echo "Socket Check:"
  echo "  Path: $SOCKET_PATH"
  
  if [[ ! -e "$SOCKET_PATH" ]]; then
    print_status "ERROR" "Socket does not exist"
    return 1
  fi
  
  if [[ ! -S "$SOCKET_PATH" ]]; then
    print_status "ERROR" "Path exists but is not a socket file"
    return 1
  fi
  
  print_status "OK" "Socket file exists"
  
  # Check permissions
  if [[ -r "$SOCKET_PATH" ]] && [[ -w "$SOCKET_PATH" ]]; then
    print_status "OK" "Socket has read/write permissions"
  else
    print_status "WARN" "Socket lacks read/write permissions"
    echo "    Fix: chmod 666 $SOCKET_PATH"
  fi
  
  # Check if process is listening
  if lsof "$SOCKET_PATH" >/dev/null 2>&1; then
    local listener_pid
    listener_pid=$(lsof -t "$SOCKET_PATH" 2>/dev/null | head -1 || echo "")
    if [[ -n "$listener_pid" ]]; then
      print_status "OK" "Process listening on socket (PID: $listener_pid)"
      return 0
    fi
  else
    print_status "WARN" "No process listening on socket"
    return 1
  fi
  
  return 0
}

################################################################################
# Check FBP process
################################################################################
check_process() {
  echo ""
  echo "Process Check:"
  
  # Check PID file
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && ps -p "$pid" >/dev/null 2>&1; then
      print_status "OK" "FBP process running (PID: $pid from $PID_FILE)"
      
      # Show process info
      if command -v ps >/dev/null 2>&1; then
        echo "    Process details:"
        ps -p "$pid" -o pid,command --no-headers 2>/dev/null | sed 's/^/    /' || true
      fi
      return 0
    else
      print_status "WARN" "PID file exists but process not running (stale PID file)"
      echo "    Fix: rm -f $PID_FILE"
    fi
  else
    print_status "INFO" "No PID file found at $PID_FILE"
  fi
  
  # Check for FBP processes by name
  local fbp_procs
  fbp_procs=$(ps aux | grep -i "[f]bp\|[u]vicorn.*fbp\|[p]ython.*fbp" || true)
  if [[ -n "$fbp_procs" ]]; then
    print_status "INFO" "Found potential FBP processes:"
    echo "$fbp_procs" | sed 's/^/    /'
    return 0
  else
    print_status "ERROR" "No FBP backend process found"
    return 1
  fi
}

################################################################################
# Test socket connectivity
################################################################################
test_connectivity() {
  echo ""
  echo "Connectivity Test:"
  
  if [[ ! -S "$SOCKET_PATH" ]]; then
    print_status "ERROR" "Cannot test: socket does not exist"
    return 1
  fi
  
  # Test health endpoint via socket
  if command -v curl >/dev/null 2>&1; then
    local response
    if response=$(curl --unix-socket "$SOCKET_PATH" --max-time 2 -s -w "\n%{http_code}" http://localhost/health 2>&1); then
      local http_code
      http_code=$(echo "$response" | tail -n1)
      local body
      body=$(echo "$response" | sed '$d')
      
      if [[ "$http_code" == "200" ]]; then
        print_status "OK" "Health check successful (HTTP $http_code)"
        if echo "$body" | grep -q "status"; then
          echo "    Response: $body" | head -c 100
          echo ""
        fi
        return 0
      else
        print_status "WARN" "Health check returned HTTP $http_code"
        return 1
      fi
    else
      print_status "ERROR" "Failed to connect to socket"
      echo "    Error: $response"
      return 1
    fi
  else
    print_status "WARN" "curl not available, skipping connectivity test"
    return 1
  fi
}

################################################################################
# Check configuration
################################################################################
check_config() {
  echo ""
  echo "Configuration:"
  
  # Check FoKS config for FBP settings
  local foks_config
  foks_config="$PROJECT_ROOT/backend/app/config.py"
  if [[ -f "$foks_config" ]]; then
    echo "  FoKS Config: $foks_config"
    
    # Extract FBP settings (if visible in config)
    if grep -q "fbp_socket_path\|FBP_SOCKET_PATH" "$foks_config" 2>/dev/null; then
      local socket_config
      socket_config=$(grep -E "fbp_socket_path|FBP_SOCKET_PATH" "$foks_config" | head -1 || echo "")
      if [[ -n "$socket_config" ]]; then
        echo "    $socket_config" | sed 's/^/    /'
      fi
    fi
  fi
  
  # Environment variables
  echo "  Environment:"
  if [[ -n "${FBP_SOCKET_PATH:-}" ]]; then
    echo "    FBP_SOCKET_PATH=$FBP_SOCKET_PATH"
  else
    echo "    FBP_SOCKET_PATH (not set, using default: /tmp/fbp.sock)"
  fi
  
  if [[ -n "${FBP_TRANSPORT:-}" ]]; then
    echo "    FBP_TRANSPORT=$FBP_TRANSPORT"
  else
    echo "    FBP_TRANSPORT (not set, using default: socket)"
  fi
}

################################################################################
# Provide next steps
################################################################################
show_next_steps() {
  echo ""
  echo "=========================================="
  echo "Next Steps:"
  echo "=========================================="
  
  local socket_ok=false
  local process_ok=false
  
  # Check socket: exists, is socket file, and has listener
  if [[ -S "$SOCKET_PATH" ]] && lsof "$SOCKET_PATH" >/dev/null 2>&1; then
    socket_ok=true
  fi
  
  # Check PID file (optional - process may be running without PID file)
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && ps -p "$pid" >/dev/null 2>&1; then
      process_ok=true
    fi
  fi
  
  # Socket is the primary indicator - if socket exists and has listener, FBP is running
  if [[ "$socket_ok" == "true" ]]; then
    print_status "OK" "FBP backend is running and ready"
    echo ""
    echo "Socket: $SOCKET_PATH"
    if [[ "$process_ok" == "true" ]]; then
      echo "PID file: $PID_FILE (verified)"
    else
      echo "PID file: Not found (process running without PID file)"
    fi
    echo ""
    echo "You can now run NFA triggers:"
    echo "  bash $PROJECT_ROOT/ops/scripts/run_nfa_batch_now.sh"
  else
    print_status "ERROR" "FBP backend is not running"
    echo ""
    echo "To start FBP backend:"
    echo "  1. Quick fix:"
    echo "     bash $PROJECT_ROOT/ops/scripts/fix_fbp_connection.sh"
    echo ""
    echo "  2. Manual start:"
    echo "     bash $PROJECT_ROOT/ops/scripts/start_fbp_backend.sh"
    echo ""
    echo "  3. Using launchd (if configured):"
    echo "     launchctl load ~/Library/LaunchAgents/com.fbp.bootstrap.optimized.plist"
  fi
  echo ""
}

################################################################################
# Main
################################################################################
main() {
  echo "=========================================="
  echo "FBP Backend Status Diagnostic"
  echo "=========================================="
  echo ""
  echo "Checking FBP backend status..."
  echo ""
  
  local socket_status=0
  local process_status=0
  local connectivity_status=0
  
  check_config
  check_socket || socket_status=1
  check_process || process_status=1
  
  # Only test connectivity if socket exists
  if [[ $socket_status -eq 0 ]]; then
    test_connectivity || connectivity_status=1
  fi
  
  show_next_steps
  
  # Exit code: 0 if all OK, 1 if any issue
  if [[ $socket_status -eq 0 ]] && [[ $process_status -eq 0 ]] && [[ $connectivity_status -eq 0 ]]; then
    exit 0
  else
    exit 1
  fi
}

main "$@"
