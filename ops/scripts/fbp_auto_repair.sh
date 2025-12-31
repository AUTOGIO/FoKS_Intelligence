#!/usr/bin/env bash
################################################################################
# FBP Auto-Repair Script
# Automatically repairs and validates FBP backend setup
# 
# Capabilities:
# 1. Ensure venv exists at ~/.venvs/fbp
# 2. Install missing dependencies
# 3. Fix permissions
# 4. Validate FBP_Backend path
# 5. Start FBP and verify /tmp/fbp.sock
# 6. Print detailed diagnostics
#
# Behavior:
# - Non-destructive (only creates/fixes, never deletes)
# - Minimal output to stdout (detailed logs to file)
# - Uses set -euo pipefail for safety
################################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FBP_ROOT="/Users/dnigga/Documents/FBP_Backend"
VENV_BASE_DIR="$HOME/.venvs"
VENV_PATH="$VENV_BASE_DIR/fbp"
SOCKET_PATH="/tmp/fbp.sock"
OPS_LOG_DIR="$PROJECT_ROOT/ops/logs"
LOG_FILE="$OPS_LOG_DIR/fbp_auto_repair.log"
PID_FILE="$OPS_LOG_DIR/fbp_backend.pid"

mkdir -p "$OPS_LOG_DIR"

################################################################################
# Logging utility
################################################################################
log() {
    local level="$1"
    shift
    local msg="$*"
    local timestamp=$(date '+%Y-%m-%dT%H:%M:%S')
    echo "[$timestamp] [$level] $msg" | tee -a "$LOG_FILE"
}

log_info() { log "INFO" "$@"; }
log_warn() { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }
log_success() { log "SUCCESS" "$@"; }

################################################################################
# Step 1: Ensure venv exists
################################################################################
log_info "Step 1: Checking virtual environment..."

if [[ ! -d "$VENV_BASE_DIR" ]]; then
    log_info "Creating .venvs directory: $VENV_BASE_DIR"
    mkdir -p "$VENV_BASE_DIR"
fi

if [[ ! -d "$VENV_PATH" ]]; then
    log_info "Virtual environment not found. Creating: $VENV_PATH"
    python3 -m venv "$VENV_PATH" || {
        log_error "Failed to create virtual environment"
        exit 1
    }
    log_success "Virtual environment created: $VENV_PATH"
else
    log_info "Virtual environment found: $VENV_PATH"
fi

# Verify activation script exists
if [[ ! -f "$VENV_PATH/bin/activate" ]]; then
    log_error "Virtual environment activation script not found"
    exit 1
fi

# Activate venv
# shellcheck disable=SC1090
source "$VENV_PATH/bin/activate" || {
    log_error "Failed to activate virtual environment"
    exit 1
}

log_success "Virtual environment ready"

################################################################################
# Step 2: Install missing dependencies
################################################################################
log_info "Step 2: Checking and installing dependencies..."

cd "$FBP_ROOT" || {
    log_error "Cannot change to FBP root directory: $FBP_ROOT"
    exit 1
}

# Check for requirements.txt or pyproject.toml
REQUIREMENTS_FILE="$FBP_ROOT/requirements.txt"
PYPROJECT_FILE="$FBP_ROOT/pyproject.toml"

if [[ -f "$REQUIREMENTS_FILE" ]]; then
    log_info "Found requirements.txt: $REQUIREMENTS_FILE"
    
    # Check for key packages
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
        log_info "Missing packages detected: ${MISSING_PACKAGES[*]}"
        log_info "Installing requirements from $REQUIREMENTS_FILE..."
        
        pip install --upgrade pip >/dev/null 2>&1 || log_warn "pip upgrade failed, continuing..."
        pip install -r "$REQUIREMENTS_FILE" >>"$LOG_FILE" 2>&1 || {
            log_error "Failed to install requirements"
            exit 1
        }
        log_success "Requirements installed successfully"
    else
        log_info "All key packages are installed"
    fi
elif [[ -f "$PYPROJECT_FILE" ]]; then
    log_info "Found pyproject.toml: $PYPROJECT_FILE"
    
    # Check if uv is available (modern approach)
    if command -v uv &>/dev/null; then
        log_info "Using uv to install dependencies..."
        uv pip install -e . >>"$LOG_FILE" 2>&1 || {
            log_warn "uv install failed, trying pip..."
            pip install -e . >>"$LOG_FILE" 2>&1 || {
                log_error "Failed to install from pyproject.toml"
                exit 1
            }
        }
        log_success "Dependencies installed via uv"
    else
        log_info "Installing from pyproject.toml with pip..."
        pip install -e . >>"$LOG_FILE" 2>&1 || {
            log_error "Failed to install from pyproject.toml"
            exit 1
        }
        log_success "Dependencies installed via pip"
    fi
else
    log_warn "No requirements.txt or pyproject.toml found"
    log_info "Installing minimal dependencies..."
    
    if ! python -c "import uvicorn" 2>/dev/null; then
        pip install uvicorn >>"$LOG_FILE" 2>&1 || {
            log_error "Failed to install uvicorn"
            exit 1
        }
    fi
    
    if ! python -c "import uvloop" 2>/dev/null; then
        pip install uvloop >>"$LOG_FILE" 2>&1 || {
            log_warn "uvloop install failed (non-critical)"
        }
    fi
    
    log_success "Minimal dependencies installed"
fi

################################################################################
# Step 3: Fix permissions
################################################################################
log_info "Step 3: Checking and fixing permissions..."

# Fix venv permissions if needed
if [[ -d "$VENV_PATH" ]]; then
    # Ensure venv is readable/executable
    chmod -R u+rX "$VENV_PATH" 2>/dev/null || log_warn "Could not fix venv permissions"
    log_info "Venv permissions verified"
fi

# Fix socket permissions if it exists
if [[ -e "$SOCKET_PATH" ]]; then
    # Socket should be readable/writable by user
    if [[ ! -r "$SOCKET_PATH" ]] || [[ ! -w "$SOCKET_PATH" ]]; then
        log_warn "Socket permissions may be incorrect"
        # Try to fix (may fail if owned by different user)
        chmod 660 "$SOCKET_PATH" 2>/dev/null || log_warn "Could not fix socket permissions"
    else
        log_info "Socket permissions OK"
    fi
fi

log_success "Permissions check completed"

################################################################################
# Step 4: Validate FBP_Backend path
################################################################################
log_info "Step 4: Validating FBP backend path..."

if [[ ! -d "$FBP_ROOT" ]]; then
    log_error "FBP backend directory not found: $FBP_ROOT"
    exit 1
fi

# Check for expected structure
EXPECTED_DIRS=("app")
MISSING_DIRS=()

for dir in "${EXPECTED_DIRS[@]}"; do
    if [[ ! -d "$FBP_ROOT/$dir" ]]; then
        MISSING_DIRS+=("$dir")
    fi
done

if [[ ${#MISSING_DIRS[@]} -gt 0 ]]; then
    log_warn "Missing expected directories: ${MISSING_DIRS[*]}"
    log_warn "FBP backend structure may be incomplete"
else
    log_info "FBP backend structure validated"
fi

# Check for main.py or app/main.py
if [[ -f "$FBP_ROOT/app/main.py" ]]; then
    log_info "Found FBP main application: $FBP_ROOT/app/main.py"
elif [[ -f "$FBP_ROOT/main.py" ]]; then
    log_info "Found FBP main application: $FBP_ROOT/main.py"
else
    log_warn "FBP main.py not found in expected locations"
fi

log_success "FBP backend path validated: $FBP_ROOT"

################################################################################
# Step 5: Start FBP and verify socket
################################################################################
log_info "Step 5: Starting FBP backend and verifying socket..."

# Check if FBP is already running
if [[ -f "$PID_FILE" ]]; then
    existing_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "${existing_pid:-}" ]] && ps -p "$existing_pid" >/dev/null 2>&1; then
        log_info "FBP backend already running with PID $existing_pid"
        
        # Verify socket exists
        if [[ -S "$SOCKET_PATH" ]]; then
            log_success "FBP backend is running and socket exists"
            log_info "Skipping startup (already running)"
        else
            log_warn "FBP process exists but socket not found"
            log_info "Removing stale PID file and restarting..."
            rm -f "$PID_FILE"
        fi
    else
        log_warn "Removing stale PID file"
        rm -f "$PID_FILE"
    fi
fi

# Start FBP if not running
if [[ ! -f "$PID_FILE" ]] || ! ps -p "$(cat "$PID_FILE" 2>/dev/null || echo '')" >/dev/null 2>&1; then
    log_info "Starting FBP backend..."
    
    # Remove stale socket if it exists
    if [[ -e "$SOCKET_PATH" ]] && [[ ! -S "$SOCKET_PATH" ]]; then
        log_warn "Removing stale socket file: $SOCKET_PATH"
        rm -f "$SOCKET_PATH"
    fi
    
    # Check for FBP's start script first
    FBP_START_SCRIPT="$FBP_ROOT/scripts/start.sh"
    if [[ -f "$FBP_START_SCRIPT" ]] && [[ -x "$FBP_START_SCRIPT" ]]; then
        log_info "Using FBP start script: $FBP_START_SCRIPT"
        # Start in background and capture PID
        cd "$FBP_ROOT"
        "$FBP_START_SCRIPT" >>"$LOG_FILE" 2>&1 &
        START_PID=$!
        echo "$START_PID" > "$PID_FILE"
        log_info "FBP start script launched (PID: $START_PID)"
    else
        # Fallback to uvicorn
        log_info "Using uvicorn directly"
        cd "$FBP_ROOT"
        export PYTHONPATH="$FBP_ROOT:${PYTHONPATH:-}"
        export PYTHONUNBUFFERED=1
        export PYTHONDONTWRITEBYTECODE=1
        
        "$VENV_PATH/bin/python" -m uvicorn app.main:app \
            --uds "$SOCKET_PATH" \
            --workers 1 \
            --loop uvloop \
            --http httptools \
            --log-level info >>"$LOG_FILE" 2>&1 &
        
        UVICORN_PID=$!
        echo "$UVICORN_PID" > "$PID_FILE"
        log_info "Uvicorn started (PID: $UVICORN_PID)"
    fi
    
    # Wait for socket creation (up to 15 seconds)
    log_info "Waiting for socket creation..."
    SOCKET_WAIT_COUNT=0
    SOCKET_CREATED=false
    
    while [[ $SOCKET_WAIT_COUNT -lt 15 ]]; do
        # Check if process is still running
        if [[ -f "$PID_FILE" ]]; then
            pid="$(cat "$PID_FILE" 2>/dev/null || true)"
            if [[ -n "$pid" ]] && ! ps -p "$pid" >/dev/null 2>&1; then
                log_error "FBP process exited before socket was created"
                log_error "Check logs: $LOG_FILE"
                exit 1
            fi
        fi
        
        # Check if socket exists
        if [[ -S "$SOCKET_PATH" ]]; then
            log_success "Socket created: $SOCKET_PATH"
            SOCKET_CREATED=true
            
            # Verify socket is accessible
            sleep 1
            if curl --unix-socket "$SOCKET_PATH" --max-time 2 http://localhost/health >/dev/null 2>&1; then
                log_success "FBP backend is healthy and responding"
            else
                log_warn "Socket exists but health check failed (may still be starting)"
            fi
            break
        fi
        
        sleep 1
        SOCKET_WAIT_COUNT=$((SOCKET_WAIT_COUNT + 1))
    done
    
    if [[ "$SOCKET_CREATED" == "false" ]]; then
        log_error "Socket not created within 15 seconds"
        log_error "Check logs: $LOG_FILE"
        exit 1
    fi
else
    log_success "FBP backend already running"
fi

sleep 1  # Allow UNIX socket stabilization

################################################################################
# Step 6: Print detailed diagnostics
################################################################################
log_info "Step 6: Running detailed diagnostics..."

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "FBP Auto-Repair Diagnostics Report"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Venv status
echo "📦 Virtual Environment:"
if [[ -d "$VENV_PATH" ]]; then
    echo "   ✓ Location: $VENV_PATH"
    if [[ -f "$VENV_PATH/bin/activate" ]]; then
        echo "   ✓ Activation script: OK"
    else
        echo "   ✗ Activation script: MISSING"
    fi
    
    # Check Python version
    if [[ -f "$VENV_PATH/bin/python" ]]; then
        PYTHON_VERSION=$("$VENV_PATH/bin/python" --version 2>&1 || echo "unknown")
        echo "   ✓ Python: $PYTHON_VERSION"
    fi
else
    echo "   ✗ NOT FOUND"
fi
echo ""

# Dependencies status
echo "📚 Dependencies:"
if python -c "import uvicorn" 2>/dev/null; then
    UVICORN_VERSION=$(python -c "import uvicorn; print(uvicorn.__version__)" 2>/dev/null || echo "installed")
    echo "   ✓ uvicorn: $UVICORN_VERSION"
else
    echo "   ✗ uvicorn: NOT INSTALLED"
fi

if python -c "import fastapi" 2>/dev/null; then
    FASTAPI_VERSION=$(python -c "import fastapi; print(fastapi.__version__)" 2>/dev/null || echo "installed")
    echo "   ✓ fastapi: $FASTAPI_VERSION"
else
    echo "   ✗ fastapi: NOT INSTALLED"
fi

if python -c "import uvloop" 2>/dev/null; then
    echo "   ✓ uvloop: installed"
else
    echo "   ⚠ uvloop: NOT INSTALLED (optional, but recommended)"
fi
echo ""

# FBP Backend path
echo "📁 FBP Backend Path:"
if [[ -d "$FBP_ROOT" ]]; then
    echo "   ✓ Location: $FBP_ROOT"
    
    if [[ -f "$FBP_ROOT/app/main.py" ]]; then
        echo "   ✓ Main application: $FBP_ROOT/app/main.py"
    elif [[ -f "$FBP_ROOT/main.py" ]]; then
        echo "   ✓ Main application: $FBP_ROOT/main.py"
    else
        echo "   ✗ Main application: NOT FOUND"
    fi
    
    if [[ -f "$FBP_ROOT/requirements.txt" ]]; then
        echo "   ✓ requirements.txt: found"
    elif [[ -f "$FBP_ROOT/pyproject.toml" ]]; then
        echo "   ✓ pyproject.toml: found"
    else
        echo "   ⚠ Dependency file: NOT FOUND"
    fi
else
    echo "   ✗ NOT FOUND: $FBP_ROOT"
fi
echo ""

# Socket status
echo "🔌 Socket Status:"
if [[ -S "$SOCKET_PATH" ]]; then
    echo "   ✓ Socket exists: $SOCKET_PATH"
    
    # Check permissions
    if [[ -r "$SOCKET_PATH" ]] && [[ -w "$SOCKET_PATH" ]]; then
        echo "   ✓ Permissions: OK (readable/writable)"
    else
        echo "   ⚠ Permissions: ISSUES DETECTED"
    fi
    
    # Test connectivity
    if curl --unix-socket "$SOCKET_PATH" --max-time 2 http://localhost/health >/dev/null 2>&1; then
        echo "   ✓ Connectivity: OK (health check passed)"
    else
        echo "   ⚠ Connectivity: Health check failed"
    fi
else
    echo "   ✗ Socket not found: $SOCKET_PATH"
fi
echo ""

# Process status
echo "🔄 Process Status:"
if [[ -f "$PID_FILE" ]]; then
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && ps -p "$pid" >/dev/null 2>&1; then
        echo "   ✓ FBP backend running (PID: $pid)"
        
        # Get process info
        if command -v ps >/dev/null 2>&1; then
            PROCESS_INFO=$(ps -p "$pid" -o command= 2>/dev/null | head -c 80 || echo "unknown")
            echo "   ℹ Command: ${PROCESS_INFO}..."
        fi
    else
        echo "   ✗ PID file exists but process not running"
    fi
else
    echo "   ✗ PID file not found (FBP may not be running)"
fi
echo ""

# Log file location
echo "📋 Logs:"
echo "   Location: $LOG_FILE"
if [[ -f "$LOG_FILE" ]]; then
    LOG_SIZE=$(wc -l < "$LOG_FILE" 2>/dev/null || echo "0")
    echo "   Lines: $LOG_SIZE"
fi
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo ""

# Final status
if [[ -S "$SOCKET_PATH" ]] && [[ -f "$PID_FILE" ]] && ps -p "$(cat "$PID_FILE" 2>/dev/null || echo '')" >/dev/null 2>&1; then
    log_success "FBP auto-repair completed successfully"
    echo "✅ FBP backend is READY"
    exit 0
else
    log_error "FBP auto-repair completed with issues"
    echo "❌ FBP backend has ISSUES - check logs: $LOG_FILE"
    exit 1
fi
