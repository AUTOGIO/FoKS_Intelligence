#!/usr/bin/env bash
################################################################################
# FBP Backend Bootstrap Script (M3 Optimized, Best Practices)
# Best practices:
#  - No daemonization (no nohup); let launchd manage lifecycle
#  - Explicit logging via launchd StandardOutPath/StandardErrorPath
#  - uvloop for improved async performance on Apple Silicon
#  - Single worker (1 process) + high async concurrency
#  - Proper venv detection and setup
#  - Playwright validation
#  - Resource limits and monitoring hints
#  - Auto-creates venv if missing
#  - Validates requirements.txt
#  - Verifies socket creation
################################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FBP_ROOT="/Users/dnigga/Documents/FBP_Backend"
OPS_LOG_DIR="$PROJECT_ROOT/ops/logs"
PID_FILE="$OPS_LOG_DIR/fbp_backend.pid"
SOCKET_PATH="/tmp/fbp.sock"
VENV_BASE_DIR="$HOME/.venvs"
VENV_PATH="$VENV_BASE_DIR/fbp"

mkdir -p "$OPS_LOG_DIR"

################################################################################
# Logging utility (all output goes to launchd's StandardOutPath/StandardErrorPath)
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
# Validation: FBP Root Directory
################################################################################
log "INFO" "Validating FBP backend directory..."
if [[ ! -d "$FBP_ROOT" ]]; then
  log "ERROR" "FBP backend directory not found at $FBP_ROOT"
  log "HINT" "Expected path: $FBP_ROOT"
  exit 1
fi
log "INFO" "✓ FBP backend directory found: $FBP_ROOT"

################################################################################
# Virtual Environment Setup
################################################################################
log "INFO" "Checking virtual environment..."

# Create .venvs directory if it doesn't exist
if [[ ! -d "$VENV_BASE_DIR" ]]; then
  log "INFO" "Creating .venvs directory: $VENV_BASE_DIR"
  mkdir -p "$VENV_BASE_DIR"
fi

# Create venv if it doesn't exist
if [[ ! -d "$VENV_PATH" ]]; then
  log "INFO" "Virtual environment not found at $VENV_PATH"
  log "INFO" "Creating virtual environment..."
  python3 -m venv "$VENV_PATH" || {
    log "ERROR" "Failed to create virtual environment at $VENV_PATH"
    exit 1
  }
  log "INFO" "✓ Virtual environment created: $VENV_PATH"
else
  log "INFO" "✓ Virtual environment found: $VENV_PATH"
fi

# Activate venv safely
if [[ -f "$VENV_PATH/bin/activate" ]]; then
  # shellcheck disable=SC1090
  source "$VENV_PATH/bin/activate" || {
    log "ERROR" "Failed to activate virtual environment at $VENV_PATH"
    exit 1
  }
  log "INFO" "✓ Virtual environment activated"
else
  log "ERROR" "Virtual environment activation script not found: $VENV_PATH/bin/activate"
  exit 1
fi

# Verify Python is from venv
if [[ -z "${VIRTUAL_ENV:-}" ]] || [[ "$VIRTUAL_ENV" != "$VENV_PATH" ]]; then
  log "WARN" "Virtual environment may not be properly activated"
  log "HINT" "VIRTUAL_ENV=${VIRTUAL_ENV:-not set}, expected: $VENV_PATH"
fi

################################################################################
# Requirements Validation
################################################################################
log "INFO" "Validating FBP requirements..."

cd "$FBP_ROOT"

# Check for requirements.txt
REQUIREMENTS_FILE="$FBP_ROOT/requirements.txt"
if [[ -f "$REQUIREMENTS_FILE" ]]; then
  log "INFO" "Found requirements.txt: $REQUIREMENTS_FILE"
  
  # Check if key packages are installed
  MISSING_PACKAGES=()

if ! python -c "import uvicorn" 2>/dev/null; then
    MISSING_PACKAGES+=("uvicorn")
  fi
  
  if ! python -c "import fastapi" 2>/dev/null; then
    MISSING_PACKAGES+=("fastapi")
  fi
  
  if ! python -c "import uvloop" 2>/dev/null; then
    MISSING_PACKAGES+=("uvloop")
  fi
  
  if [[ ${#MISSING_PACKAGES[@]} -gt 0 ]]; then
    log "WARN" "Missing packages detected: ${MISSING_PACKAGES[*]}"
    log "INFO" "Installing requirements from $REQUIREMENTS_FILE..."
    pip install --upgrade pip >/dev/null 2>&1 || log "WARN" "pip upgrade failed, continuing..."
    pip install -r "$REQUIREMENTS_FILE" >/dev/null 2>&1 || {
      log "ERROR" "Failed to install requirements from $REQUIREMENTS_FILE"
      log "HINT" "Try running manually: pip install -r $REQUIREMENTS_FILE"
      exit 1
    }
    log "INFO" "✓ Requirements installed successfully"
  else
    log "INFO" "✓ All key packages are installed"
  fi
else
  log "WARN" "requirements.txt not found at $REQUIREMENTS_FILE"
  log "HINT" "Installing minimal dependencies..."
  
  # Install minimal dependencies if requirements.txt doesn't exist
  if ! python -c "import uvicorn" 2>/dev/null; then
    log "INFO" "Installing uvicorn..."
  pip install uvicorn >/dev/null 2>&1 || log "ERROR" "Failed to install uvicorn"
fi

if ! python -c "import uvloop" 2>/dev/null; then
  log "INFO" "Installing uvloop for improved async performance on M3"
  pip install uvloop >/dev/null 2>&1 || log "WARN" "uvloop install failed; FastAPI will use default event loop"
  fi
fi

# Verify Playwright (optional but recommended)
if command -v playwright >/dev/null 2>&1; then
  pw_version="$(playwright --version 2>/dev/null || true)"
  log "INFO" "✓ Playwright detected ($pw_version)"
else
  log "WARN" "Playwright CLI not found. Some NFA flows may fail."
  log "HINT" "Install with: \"$FBP_ROOT/scripts/setup_playwright.sh\" (if available)"
fi

################################################################################
# Check for existing process
################################################################################
if [[ -f "$PID_FILE" ]]; then
  existing_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "${existing_pid:-}" ]] && ps -p "$existing_pid" >/dev/null 2>&1; then
    log "INFO" "FBP backend already running with PID $existing_pid"
    exit 0
  else
    log "WARN" "Removing stale FBP PID file at $PID_FILE"
    rm -f "$PID_FILE"
  fi
fi

################################################################################
# Environment setup
################################################################################
cd "$FBP_ROOT"
export PYTHONPATH="$FBP_ROOT:${PYTHONPATH:-}"

# M3 optimization hints
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

################################################################################
# Start FBP Backend
################################################################################
log "INFO" "Starting FBP backend..."

# Check for FBP's start.sh script first
FBP_START_SCRIPT="$FBP_ROOT/scripts/start.sh"
if [[ -f "$FBP_START_SCRIPT" ]] && [[ -x "$FBP_START_SCRIPT" ]]; then
  log "INFO" "Found FBP start script: $FBP_START_SCRIPT"
  log "INFO" "Using FBP's start script to launch backend..."
  
  # Remove stale socket if it exists
  if [[ -S "$SOCKET_PATH" ]] || [[ -e "$SOCKET_PATH" ]]; then
    log "WARN" "Removing stale socket: $SOCKET_PATH"
    rm -f "$SOCKET_PATH"
  fi
  
  # Execute FBP's start script
  exec "$FBP_START_SCRIPT"
else
  # Fallback to uvicorn if start.sh doesn't exist
  log "INFO" "FBP start script not found, using uvicorn directly"
  log "INFO" "  - Socket: $SOCKET_PATH"
  log "INFO" "  - Workers: 1 (single process, high async concurrency)"
  log "INFO" "  - Loop: uvloop (Apple Silicon optimized)"
  log "INFO" "  - HTTP: httptools"
log "INFO" "  - Working directory: $FBP_ROOT"
log "INFO" "  - Logs: launchd StandardOutPath / StandardErrorPath (~/Library/Logs/FoKS/)"

  # Remove stale socket if it exists
  if [[ -S "$SOCKET_PATH" ]] || [[ -e "$SOCKET_PATH" ]]; then
    log "WARN" "Removing stale socket: $SOCKET_PATH"
    rm -f "$SOCKET_PATH"
  fi
  
  # Start uvicorn with UNIX socket
  log "INFO" "Starting uvicorn on UNIX socket: $SOCKET_PATH"
  
  # Start uvicorn in background to verify socket creation
"$VENV_PATH/bin/python" -m uvicorn app.main:app \
    --uds "$SOCKET_PATH" \
    --workers 1 \
    --loop uvloop \
    --http httptools \
  --timeout-keep-alive 5 \
  --timeout-notify 30 \
    --access-log &
  
  UVICORN_PID=$!
  echo "$UVICORN_PID" > "$PID_FILE"
  log "INFO" "Uvicorn started with PID: $UVICORN_PID"
  
  # Wait for socket creation (up to 10 seconds)
  log "INFO" "Waiting for socket creation..."
  SOCKET_WAIT_COUNT=0
  SOCKET_CREATED=false
  
  while [[ $SOCKET_WAIT_COUNT -lt 10 ]]; do
    # Check if process is still running
    if ! ps -p "$UVICORN_PID" >/dev/null 2>&1; then
      log "ERROR" "Uvicorn process exited before socket was created"
      exit 1
    fi
    
    # Check if socket exists
    if [[ -S "$SOCKET_PATH" ]]; then
      log "INFO" "✓ Socket created successfully: $SOCKET_PATH"
      SOCKET_CREATED=true
      
      # Verify socket is accessible (with timeout)
      sleep 1
      if curl --unix-socket "$SOCKET_PATH" --max-time 2 http://localhost/health >/dev/null 2>&1; then
        log "INFO" "✓ FBP backend is healthy and responding"
      else
        log "WARN" "Socket exists but health check failed (backend may still be starting)"
      fi
      break
    fi
    
    sleep 1
    SOCKET_WAIT_COUNT=$((SOCKET_WAIT_COUNT + 1))
  done
  
  if [[ "$SOCKET_CREATED" == "false" ]]; then
    log "ERROR" "Socket not created within 10 seconds"
    log "HINT" "Check uvicorn logs for errors"
    kill "$UVICORN_PID" 2>/dev/null || true
    exit 1
  fi
  
  # Socket verified, now wait for process in foreground (for launchd)
  log "INFO" "FBP backend is running. Waiting for process..."
  wait $UVICORN_PID || {
    EXIT_CODE=$?
    log "ERROR" "Uvicorn process exited with code $EXIT_CODE"
    exit $EXIT_CODE
  }
fi

# If we reach here, the process exited; let launchd restart it
log "WARN" "FBP backend process exited (launchd will restart if KeepAlive is enabled)"
exit 1
