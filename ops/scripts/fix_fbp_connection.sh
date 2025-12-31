#!/usr/bin/env bash
################################################################################
# Quick Fix: Start FBP and Verify Connection
# One-command solution to start FBP backend and verify it's working
################################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOCKET_PATH="${FBP_SOCKET_PATH:-/tmp/fbp.sock}"
START_SCRIPT="$PROJECT_ROOT/ops/scripts/start_fbp_backend.sh"
CHECK_SCRIPT="$PROJECT_ROOT/ops/scripts/check_fbp_status.sh"
MAX_WAIT=30  # Maximum seconds to wait for socket

################################################################################
# Colors
################################################################################
RED=$'\033[31m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
CYAN=$'\033[36m'
RESET=$'\033[0m'

################################################################################
# Print status
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
# Check if socket exists and is working
################################################################################
socket_ready() {
  if [[ ! -S "$SOCKET_PATH" ]]; then
    return 1
  fi
  
  # Check if process is listening
  if ! lsof "$SOCKET_PATH" >/dev/null 2>&1; then
    return 1
  fi
  
  # Test connectivity
  if command -v curl >/dev/null 2>&1; then
    if curl --unix-socket "$SOCKET_PATH" --max-time 2 -s http://localhost/health >/dev/null 2>&1; then
      return 0
    fi
  fi
  
  return 1
}

################################################################################
# Wait for socket creation
################################################################################
wait_for_socket() {
  print_status "INFO" "Waiting for socket creation (max ${MAX_WAIT}s)..."
  
  local waited=0
  while [[ $waited -lt $MAX_WAIT ]]; do
    if socket_ready; then
      print_status "OK" "Socket is ready!"
      return 0
    fi
    
    sleep 1
    waited=$((waited + 1))
    
    # Show progress every 5 seconds
    if [[ $((waited % 5)) -eq 0 ]]; then
      echo "    Waiting... (${waited}s/${MAX_WAIT}s)"
    fi
  done
  
  print_status "ERROR" "Socket not ready after ${MAX_WAIT} seconds"
  return 1
}

################################################################################
# Main
################################################################################
main() {
  echo "=========================================="
  echo "FBP Connection Quick Fix"
  echo "=========================================="
  echo ""
  
  # Check current status
  print_status "INFO" "Checking current FBP status..."
  if socket_ready; then
    print_status "OK" "FBP backend is already running and ready"
    echo ""
    echo "Socket: $SOCKET_PATH"
    echo "Status: Ready"
    echo ""
    echo "You can now run NFA triggers."
    exit 0
  fi
  
  echo ""
  print_status "INFO" "FBP backend is not running, starting it..."
  echo ""
  
  # Check if start script exists
  if [[ ! -f "$START_SCRIPT" ]] || [[ ! -x "$START_SCRIPT" ]]; then
    print_status "ERROR" "Start script not found: $START_SCRIPT"
    exit 1
  fi
  
  # Start FBP in background
  print_status "INFO" "Starting FBP backend..."
  print_status "INFO" "Note: This will start FBP in foreground mode"
  print_status "INFO" "      For background operation, use launchd"
  echo ""
  
  # Check if we should run in background or foreground
  if [[ "${1:-}" == "--background" ]] || [[ "${1:-}" == "-b" ]]; then
    print_status "INFO" "Starting in background..."
    nohup "$START_SCRIPT" > /tmp/fbp_startup.log 2>&1 &
    local start_pid=$!
    echo "    Started with PID: $start_pid"
    echo "    Logs: /tmp/fbp_startup.log"
    echo ""
  else
    print_status "WARN" "Starting in foreground (will block)"
    print_status "INFO" "Use --background flag to start in background"
    print_status "INFO" "Or use launchd for proper service management"
    echo ""
    print_status "INFO" "Starting FBP backend (this may take a moment)..."
    echo ""
    
    # Start in background and wait
    "$START_SCRIPT" > /tmp/fbp_startup.log 2>&1 &
    local start_pid=$!
  fi
  
  # Wait for socket
  if wait_for_socket; then
    echo ""
    print_status "OK" "FBP backend is running and ready!"
    echo ""
    echo "Socket: $SOCKET_PATH"
    echo "Status: Connected"
    echo ""
    
    # Run status check
    if [[ -f "$CHECK_SCRIPT" ]] && [[ -x "$CHECK_SCRIPT" ]]; then
      echo "Running detailed status check..."
      echo ""
      "$CHECK_SCRIPT"
    fi
    
    echo ""
    print_status "OK" "You can now run NFA triggers:"
    echo "  bash $PROJECT_ROOT/ops/scripts/run_nfa_batch_now.sh"
    exit 0
  else
    echo ""
    print_status "ERROR" "Failed to start FBP backend"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check startup logs:"
    echo "     tail -50 /tmp/fbp_startup.log"
    echo ""
    echo "  2. Check FBP backend directory:"
    echo "     ls -la /Users/dnigga/Documents/FBP_Backend"
    echo ""
    echo "  3. Run diagnostic:"
    echo "     bash $CHECK_SCRIPT"
    echo ""
    echo "  4. Try manual start:"
    echo "     bash $START_SCRIPT"
    exit 1
  fi
}

main "$@"
