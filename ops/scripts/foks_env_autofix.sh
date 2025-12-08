#!/usr/bin/env bash
# FoKS Environment Auto-Healing Script
# Detects and fixes PATH conflicts, venv issues, and missing dependencies
# Run this automatically before starting FoKS services

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="$PROJECT_ROOT/backend/.venv_foks"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"
LOG_FILE="$PROJECT_ROOT/ops/logs/foks_env_autofix.log"

mkdir -p "$PROJECT_ROOT/ops/logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    local level="$1"; shift
    local msg="$*"
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[$timestamp] [$level] $msg" | tee -a "$LOG_FILE"
}

log_color() {
    local color="$1"; shift
    local msg="$*"
    echo -e "${color}${msg}${NC}"
    log "INFO" "$msg"
}

# ============================================================================
# PHASE 1: Virtualenv Verification
# ============================================================================

check_venv() {
    log_color "$BLUE" "========================================="
    log_color "$BLUE" "PHASE 1: Virtualenv Verification"
    log_color "$BLUE" "========================================="
    
    if [[ ! -d "$VENV_DIR" ]]; then
        log_color "$YELLOW" "⚠️  Virtualenv not found at $VENV_DIR"
        log_color "$GREEN" "✅ Creating virtualenv..."
        /opt/homebrew/bin/python3.11 -m venv "$VENV_DIR"
        log_color "$GREEN" "✅ Virtualenv created"
    else
        log_color "$GREEN" "✅ Virtualenv exists at $VENV_DIR"
    fi
    
    # Verify Python executable
    if [[ ! -x "$PYTHON_BIN" ]]; then
        log_color "$RED" "❌ Python executable not found or not executable: $PYTHON_BIN"
        return 1
    fi
    
    local python_version="$("$PYTHON_BIN" --version 2>&1)"
    log_color "$GREEN" "✅ Python version: $python_version"
    
    # Check if python3.11 symlink points to Homebrew (this is the problem!)
    local python_target="$(readlink "$VENV_DIR/bin/python3.11" 2>/dev/null || echo 'not a symlink')"
    if [[ "$python_target" == */homebrew/* ]]; then
        log_color "$YELLOW" "⚠️  Venv python3.11 symlink points to Homebrew: $python_target"
        log_color "$YELLOW" "⚠️  This is a known issue with python3 -m venv when Homebrew Python is in PATH"
        log_color "$GREEN" "✅ This is actually OK - the venv will work, but we need to use absolute paths"
    fi
}

# ============================================================================
# PHASE 2: Dependencies Installation
# ============================================================================

install_dependencies() {
    log_color "$BLUE" "========================================="
    log_color "$BLUE" "PHASE 2: Dependencies Installation"
    log_color "$BLUE" "========================================="
    
    log_color "$GREEN" "✅ Upgrading pip..."
    "$PIP_BIN" install --upgrade pip --quiet
    
    log_color "$GREEN" "✅ Installing/verifying requirements..."
    if [[ -f "$PROJECT_ROOT/backend/requirements.txt" ]]; then
        "$PIP_BIN" install -r "$PROJECT_ROOT/backend/requirements.txt" --quiet
    else
        log_color "$YELLOW" "⚠️  requirements.txt not found, installing critical packages..."
        "$PIP_BIN" install fastapi uvicorn[standard] pydantic sqlalchemy httpx --quiet
    fi
    
    # Verify critical packages
    log_color "$GREEN" "✅ Verifying critical packages..."
    local missing_packages=()
    
    for pkg in uvicorn fastapi pydantic sqlalchemy httpx; do
        if ! "$PYTHON_BIN" -c "import $pkg" 2>/dev/null; then
            missing_packages+=("$pkg")
        fi
    done
    
    if [[ ${#missing_packages[@]} -gt 0 ]]; then
        log_color "$RED" "❌ Missing packages: ${missing_packages[*]}"
        log_color "$GREEN" "✅ Installing missing packages..."
        "$PIP_BIN" install "${missing_packages[@]}"
    else
        log_color "$GREEN" "✅ All critical packages installed"
    fi
    
    # Show installed versions
    log_color "$GREEN" "📦 Installed versions:"
    "$PIP_BIN" list | grep -E "(fastapi|uvicorn|pydantic|sqlalchemy|httpx)" || true
}

# ============================================================================
# PHASE 3: PATH Conflict Detection
# ============================================================================

detect_path_conflicts() {
    log_color "$BLUE" "========================================="
    log_color "$BLUE" "PHASE 3: PATH Conflict Detection"
    log_color "$BLUE" "========================================="
    
    # Check if system python would override venv
    local system_python="$(which python 2>/dev/null || echo 'not found')"
    local system_python3="$(which python3 2>/dev/null || echo 'not found')"
    
    log_color "$GREEN" "Current PATH python: $system_python"
    log_color "$GREEN" "Current PATH python3: $system_python3"
    
    # Check for problematic aliases in zshrc
    if [[ -f "$HOME/.zshrc" ]]; then
        local has_python_alias=$(grep -c "alias python.*homebrew" "$HOME/.zshrc" 2>/dev/null || echo "0")
        if [[ "$has_python_alias" -gt 0 ]]; then
            log_color "$YELLOW" "⚠️  Found Python aliases in ~/.zshrc that may override venv"
            log_color "$YELLOW" "⚠️  Aliases detected: $(grep "alias python" "$HOME/.zshrc" | head -3)"
            log_color "$GREEN" "✅ SOLUTION: Always use absolute path to venv Python"
        fi
    fi
    
    # Check if VIRTUAL_ENV is set (means venv is activated)
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        log_color "$GREEN" "✅ VIRTUAL_ENV is set: $VIRTUAL_ENV"
        if [[ "$VIRTUAL_ENV" != "$VENV_DIR" ]]; then
            log_color "$YELLOW" "⚠️  Wrong venv activated: $VIRTUAL_ENV"
            log_color "$YELLOW" "⚠️  Expected: $VENV_DIR"
        fi
    else
        log_color "$YELLOW" "⚠️  VIRTUAL_ENV not set (venv not activated)"
        log_color "$GREEN" "✅ This is OK - we use absolute paths"
    fi
}

# ============================================================================
# PHASE 4: Fix Shell Configuration
# ============================================================================

fix_shell_config() {
    log_color "$BLUE" "========================================="
    log_color "$BLUE" "PHASE 4: Shell Configuration Fix"
    log_color "$BLUE" "========================================="
    
    local zshrc="$HOME/.zshrc"
    local marker="# FoKS Intelligence - Venv Protection"
    
    if [[ -f "$zshrc" ]] && ! grep -q "$marker" "$zshrc" 2>/dev/null; then
        log_color "$GREEN" "✅ Adding venv protection to ~/.zshrc..."
        
        cat >> "$zshrc" << 'EOF'

# FoKS Intelligence - Venv Protection
# This ensures virtualenv activation is not overridden by aliases
# Only set Homebrew Python aliases if NOT inside a virtualenv
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -x "/opt/homebrew/bin/python3.11" ]; then
        alias python="/opt/homebrew/bin/python3.11"
        alias python3="/opt/homebrew/bin/python3.11"
    fi
else
    # Inside venv - unset any conflicting aliases
    unalias python 2>/dev/null || true
    unalias python3 2>/dev/null || true
fi
EOF
        
        log_color "$GREEN" "✅ ~/.zshrc updated with venv protection"
        log_color "$YELLOW" "⚠️  Run 'source ~/.zshrc' or restart terminal for changes to take effect"
    else
        log_color "$GREEN" "✅ ~/.zshrc already has venv protection"
    fi
}

# ============================================================================
# PHASE 5: Verify Uvicorn Availability
# ============================================================================

verify_uvicorn() {
    log_color "$BLUE" "========================================="
    log_color "$BLUE" "PHASE 5: Uvicorn Verification"
    log_color "$BLUE" "========================================="
    
    # Test uvicorn import
    if "$PYTHON_BIN" -c "import uvicorn" 2>/dev/null; then
        log_color "$GREEN" "✅ Uvicorn importable in venv Python"
    else
        log_color "$RED" "❌ Uvicorn NOT importable"
        log_color "$GREEN" "✅ Installing uvicorn..."
        "$PIP_BIN" install "uvicorn[standard]"
    fi
    
    # Test uvicorn executable
    local uvicorn_bin="$VENV_DIR/bin/uvicorn"
    if [[ -x "$uvicorn_bin" ]]; then
        local uvicorn_version="$("$uvicorn_bin" --version 2>&1 | head -1 || echo 'unknown')"
        log_color "$GREEN" "✅ Uvicorn executable found: $uvicorn_version"
    else
        log_color "$RED" "❌ Uvicorn executable not found at $uvicorn_bin"
        return 1
    fi
}

# ============================================================================
# PHASE 6: Port Unification Check
# ============================================================================

check_port_unification() {
    log_color "$BLUE" "========================================="
    log_color "$BLUE" "PHASE 6: Port Unification Check"
    log_color "$BLUE" "========================================="
    
    log_color "$GREEN" "✅ Checking for port inconsistencies in scripts..."
    
    local port_8000_scripts=$(grep -r "port 8000" "$PROJECT_ROOT/ops/scripts" 2>/dev/null | wc -l | tr -d ' ')
    local port_8080_scripts=$(grep -r "port 8080" "$PROJECT_ROOT/scripts" 2>/dev/null | wc -l | tr -d ' ')
    
    log_color "$GREEN" "   Scripts using port 8000: $port_8000_scripts"
    log_color "$GREEN" "   Scripts using port 8080: $port_8080_scripts"
    
    if [[ "$port_8080_scripts" -gt 0 ]]; then
        log_color "$YELLOW" "⚠️  Found scripts using port 8080"
        log_color "$YELLOW" "⚠️  Standard FoKS port is 8000"
    else
        log_color "$GREEN" "✅ All scripts use consistent port 8000"
    fi
}

# ============================================================================
# PHASE 7: Final Health Check
# ============================================================================

final_health_check() {
    log_color "$BLUE" "========================================="
    log_color "$BLUE" "PHASE 7: Final Health Check"
    log_color "$BLUE" "========================================="
    
    local all_ok=true
    
    # Check 1: Venv Python works
    if "$PYTHON_BIN" --version >/dev/null 2>&1; then
        log_color "$GREEN" "✅ Venv Python executable works"
    else
        log_color "$RED" "❌ Venv Python executable FAILED"
        all_ok=false
    fi
    
    # Check 2: FastAPI import works
    if "$PYTHON_BIN" -c "import fastapi" 2>/dev/null; then
        log_color "$GREEN" "✅ FastAPI importable"
    else
        log_color "$RED" "❌ FastAPI NOT importable"
        all_ok=false
    fi
    
    # Check 3: Uvicorn import works
    if "$PYTHON_BIN" -c "import uvicorn" 2>/dev/null; then
        log_color "$GREEN" "✅ Uvicorn importable"
    else
        log_color "$RED" "❌ Uvicorn NOT importable"
        all_ok=false
    fi
    
    # Check 4: App import works (if app exists)
    if [[ -f "$PROJECT_ROOT/backend/app/main.py" ]]; then
        cd "$PROJECT_ROOT/backend"
        if PYTHONPATH="$PROJECT_ROOT/backend" "$PYTHON_BIN" -c "import app.main" 2>/dev/null; then
            log_color "$GREEN" "✅ FoKS app.main importable"
        else
            log_color "$YELLOW" "⚠️  FoKS app.main import failed (may need additional deps)"
        fi
        cd "$PROJECT_ROOT"
    fi
    
    if [[ "$all_ok" == "true" ]]; then
        log_color "$GREEN" "==========================================="
        log_color "$GREEN" "✅ ALL HEALTH CHECKS PASSED"
        log_color "$GREEN" "==========================================="
        return 0
    else
        log_color "$RED" "==========================================="
        log_color "$RED" "❌ SOME HEALTH CHECKS FAILED"
        log_color "$RED" "==========================================="
        return 1
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    log_color "$GREEN" "========================================="
    log_color "$GREEN" "🔧 FoKS Environment Auto-Healing"
    log_color "$GREEN" "========================================="
    log_color "$GREEN" "Project Root: $PROJECT_ROOT"
    log_color "$GREEN" "Venv Dir: $VENV_DIR"
    log_color "$GREEN" "Log File: $LOG_FILE"
    echo ""
    
    check_venv || { log_color "$RED" "Fatal: Venv check failed"; exit 1; }
    echo ""
    
    install_dependencies || { log_color "$RED" "Fatal: Dependencies installation failed"; exit 1; }
    echo ""
    
    detect_path_conflicts
    echo ""
    
    fix_shell_config
    echo ""
    
    verify_uvicorn || { log_color "$RED" "Fatal: Uvicorn verification failed"; exit 1; }
    echo ""
    
    check_port_unification
    echo ""
    
    final_health_check
    exit_code=$?
    echo ""
    
    if [[ $exit_code -eq 0 ]]; then
        log_color "$GREEN" "========================================="
        log_color "$GREEN" "✅ FoKS ENVIRONMENT READY"
        log_color "$GREEN" "========================================="
        log_color "$GREEN" ""
        log_color "$GREEN" "To start FoKS backend:"
        log_color "$GREEN" "  $PROJECT_ROOT/ops/scripts/foks_boot.sh"
        log_color "$GREEN" ""
        log_color "$GREEN" "To verify health:"
        log_color "$GREEN" "  curl http://localhost:8000/health"
        log_color "$GREEN" ""
    else
        log_color "$RED" "========================================="
        log_color "$RED" "❌ ENVIRONMENT ISSUES DETECTED"
        log_color "$RED" "========================================="
        log_color "$RED" "Check log file: $LOG_FILE"
    fi
    
    return $exit_code
}

main "$@"
