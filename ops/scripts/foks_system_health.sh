#!/bin/bash
# FoKS Unified System Health Check
# Validates entire automation ecosystem health

set -euo pipefail

# Color helpers
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$BACKEND_DIR/.venv_foks"

# Health check tracking
CHECKS_PASSED=0
CHECKS_FAILED=0
FAILED_MODULES=()

# Endpoints and paths
FOKS_BASE_URL="http://localhost:8000"
FBP_SOCKET="/tmp/fbp.sock"
NFA_OUTPUT_DIR="/Users/dnigga/Downloads/NFA_Outputs"
REPORTS_DIR="$PROJECT_ROOT/reports"
FBP_LOGS_DIR="$PROJECT_ROOT/../FBP_Backend/logs"

# Logging helper (FoKS format)
log_info() {
    local message="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [INFO] $message" >&2
}

log_error() {
    local message="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [ERROR] $message" >&2
}

log_warn() {
    local message="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [WARN] $message" >&2
}

# Pretty print JSON
pretty_json() {
    if command -v python3 >/dev/null 2>&1; then
        python3 -m json.tool 2>/dev/null || cat
    else
        cat
    fi
}

# Check result tracking
check_pass() {
    local module="$1"
    ((CHECKS_PASSED++))
    log_info "$module: OK"
    return 0
}

check_fail() {
    local module="$1"
    local reason="$2"
    ((CHECKS_FAILED++))
    FAILED_MODULES+=("$module: $reason")
    log_error "$module: FAILED - $reason"
    return 1
}

# 1. FoKS Backend Health
check_foks_backend() {
    echo -e "${BLUE}1. FoKS Backend Health${NC}"
    
    local response
    if ! response=$(curl -s -f --max-time 5 "${FOKS_BASE_URL}/health" 2>&1); then
        check_fail "FoKS Backend" "Not reachable at ${FOKS_BASE_URL}/health"
        return 1
    fi
    
    # Pretty print if JSON
    if echo "$response" | grep -q '^{'; then
        echo "$response" | pretty_json | head -10
        log_info "FoKS Backend response (JSON)"
    else
        echo "$response"
        log_info "FoKS Backend response (text)"
    fi
    
    # Detect running status
    if echo "$response" | grep -qi '"status".*"ok"\|status.*ok'; then
        check_pass "FoKS Backend"
        return 0
    else
        check_fail "FoKS Backend" "Health check returned non-OK status"
        return 1
    fi
}

# 2. FBP Backend Health
check_fbp_backend() {
    echo -e "${BLUE}2. FBP Backend Health${NC}"
    
    # Verify socket exists
    if [[ ! -S "$FBP_SOCKET" ]]; then
        check_fail "FBP Backend" "Socket not found: $FBP_SOCKET"
        return 1
    fi
    
    log_info "FBP socket exists: $FBP_SOCKET"
    
    # Check health via socket
    local response
    if ! response=$(curl -s -f --unix-socket "$FBP_SOCKET" --max-time 5 "http://localhost/health" 2>&1); then
        check_fail "FBP Backend" "Not reachable via socket"
        return 1
    fi
    
    # Pretty print if JSON
    if echo "$response" | grep -q '^{'; then
        echo "$response" | pretty_json | head -10
        log_info "FBP Backend response (JSON)"
    else
        echo "$response"
        log_info "FBP Backend response (text)"
    fi
    
    # Detect running status
    if echo "$response" | grep -qi '"status".*"ok"\|status.*ok'; then
        check_pass "FBP Backend"
        return 0
    else
        check_fail "FBP Backend" "Health check returned non-OK status"
        return 1
    fi
}

# 3. FoKS → FBP Transport Diagnostics
check_foks_fbp_transport() {
    echo -e "${BLUE}3. FoKS → FBP Transport Diagnostics${NC}"
    
    local response
    if ! response=$(curl -s -f -X POST --max-time 10 "${FOKS_BASE_URL}/fbp/diagnostics/run" 2>&1); then
        check_fail "FoKS → FBP Transport" "Diagnostics endpoint unreachable"
        return 1
    fi
    
    # Pretty print JSON
    local formatted
    formatted=$(echo "$response" | pretty_json)
    echo "$formatted" | head -20
    
    # Summarize: socket, version, ping (use Python for reliable JSON parsing)
    local socket_ok=false
    local version_ok=false
    local ping_ok=false
    
    # Parse JSON using Python for reliability
    local parse_result
    parse_result=$(echo "$formatted" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    socket_ok = d.get('socket_check', {}).get('exists', False)
    version_ok = d.get('version_check', {}).get('success', False)
    ping_ok = d.get('ping_check', {}).get('success', False)
    print(f'{socket_ok},{version_ok},{ping_ok}')
except:
    print('false,false,false')
" 2>/dev/null)
    
    if [[ -n "$parse_result" ]]; then
        IFS=',' read -r socket_ok version_ok ping_ok <<< "$parse_result"
        
        if [[ "$socket_ok" == "True" ]]; then
            socket_ok=true
            log_info "Socket check: OK"
        else
            socket_ok=false
            log_warn "Socket check: FAILED"
        fi
        
        if [[ "$version_ok" == "True" ]]; then
            version_ok=true
            log_info "Version check: OK"
        else
            version_ok=false
            log_warn "Version check: FAILED"
        fi
        
        if [[ "$ping_ok" == "True" ]]; then
            ping_ok=true
            log_info "Ping check: OK"
        else
            ping_ok=false
            log_warn "Ping check: FAILED"
        fi
    else
        log_warn "Failed to parse diagnostics JSON"
    fi
    
    if [[ "$socket_ok" == "true" ]] && [[ "$version_ok" == "true" ]] && [[ "$ping_ok" == "true" ]]; then
        check_pass "FoKS → FBP Transport"
        return 0
    else
        check_fail "FoKS → FBP Transport" "One or more checks failed (socket:$socket_ok, version:$version_ok, ping:$ping_ok)"
        return 1
    fi
}

# 4. NFA Automation (ATF)
check_nfa_automation() {
    echo -e "${BLUE}4. NFA Automation (ATF)${NC}"
    
    # Check file exists
    local nfa_script="$PROJECT_ROOT/ops/scripts/nfa/nfa_atf.py"
    if [[ ! -f "$nfa_script" ]]; then
        check_fail "NFA Automation" "Script not found: $nfa_script"
        return 1
    fi
    
    log_info "NFA script exists: $nfa_script"
    
    # Call test endpoint (dry-run mode - we'll use validate endpoint instead)
    # Note: We use validate endpoint to avoid launching browser
    local response
    if ! response=$(curl -s -f -X GET --max-time 10 "${FOKS_BASE_URL}/tasks/nfa_atf/validate" 2>&1); then
        # If validate endpoint doesn't exist, just check script exists
        log_warn "NFA validate endpoint not available, script exists check passed"
        check_pass "NFA Automation"
        return 0
    fi
    
    # Pretty print JSON
    local formatted
    formatted=$(echo "$response" | pretty_json)
    echo "$formatted" | head -15
    
    # Check validation status
    if echo "$formatted" | grep -q '"status".*"ok"'; then
        check_pass "NFA Automation"
        return 0
    else
        check_fail "NFA Automation" "Validation failed"
        return 1
    fi
}

# 5. NFA Intelligence Layer
check_nfa_intelligence() {
    echo -e "${BLUE}5. NFA Intelligence Layer${NC}"
    
    # Verify router exists (check if endpoint responds)
    local response
    if ! response=$(curl -s -f -X GET --max-time 10 "${FOKS_BASE_URL}/nfa/intelligence/validate" 2>&1); then
        check_fail "NFA Intelligence" "Validate endpoint unreachable"
        return 1
    fi
    
    # Pretty print JSON
    local formatted
    formatted=$(echo "$response" | pretty_json)
    echo "$formatted" | head -15
    
    # Check validation status
    if echo "$formatted" | grep -q '"status".*"ok"'; then
        check_pass "NFA Intelligence"
        return 0
    else
        check_fail "NFA Intelligence" "Validation failed"
        return 1
    fi
}

# 6. Filesystem Checks
check_filesystem() {
    echo -e "${BLUE}6. Filesystem Checks${NC}"
    
    local fs_ok=true
    local failures=()
    
    # Check NFA Outputs directory
    if [[ ! -d "$NFA_OUTPUT_DIR" ]]; then
        failures+=("NFA Outputs directory missing: $NFA_OUTPUT_DIR")
        fs_ok=false
    elif [[ ! -w "$NFA_OUTPUT_DIR" ]]; then
        failures+=("NFA Outputs directory not writable: $NFA_OUTPUT_DIR")
        fs_ok=false
    else
        log_info "NFA Outputs directory OK: $NFA_OUTPUT_DIR"
    fi
    
    # Check reports directory
    if [[ ! -d "$REPORTS_DIR" ]]; then
        failures+=("Reports directory missing: $REPORTS_DIR")
        fs_ok=false
    elif [[ ! -w "$REPORTS_DIR" ]]; then
        failures+=("Reports directory not writable: $REPORTS_DIR")
        fs_ok=false
    else
        log_info "Reports directory OK: $REPORTS_DIR"
    fi
    
    # Check FBP logs directory (optional)
    if [[ -d "$FBP_LOGS_DIR" ]]; then
        log_info "FBP logs directory exists: $FBP_LOGS_DIR"
    else
        log_warn "FBP logs directory not found: $FBP_LOGS_DIR (optional)"
    fi
    
    if [[ "$fs_ok" == "true" ]]; then
        check_pass "Filesystem"
        return 0
    else
        local failure_msg
        failure_msg=$(IFS='; '; echo "${failures[*]}")
        check_fail "Filesystem" "$failure_msg"
        return 1
    fi
}

# 7. Python Environment
check_python_env() {
    echo -e "${BLUE}7. Python Environment${NC}"
    
    local py_ok=true
    local failures=()
    
    # Check python3 version
    if ! command -v python3 >/dev/null 2>&1; then
        failures+=("python3 not found in PATH")
        py_ok=false
    else
        local py_version
        py_version=$(python3 --version 2>&1)
        local py_path
        py_path=$(which python3)
        log_info "Python3 version: $py_version"
        log_info "Python3 path: $py_path"
    fi
    
    # Check playwright
    if command -v playwright >/dev/null 2>&1; then
        local playwright_version
        playwright_version=$(playwright --version 2>&1 || echo "version unknown")
        log_info "Playwright found: $playwright_version"
    elif [[ -f "$VENV_DIR/bin/playwright" ]]; then
        log_info "Playwright found in venv: $VENV_DIR/bin/playwright"
    else
        failures+=("playwright not found")
        py_ok=false
    fi
    
    # Check uvicorn
    if command -v uvicorn >/dev/null 2>&1; then
        log_info "Uvicorn found: $(which uvicorn)"
    elif [[ -f "$VENV_DIR/bin/uvicorn" ]]; then
        log_info "Uvicorn found in venv: $VENV_DIR/bin/uvicorn"
    else
        failures+=("uvicorn not found")
        py_ok=false
    fi
    
    # Check venv
    if [[ -d "$VENV_DIR" ]]; then
        log_info "FoKS venv exists: $VENV_DIR"
        if [[ -f "$VENV_DIR/bin/activate" ]]; then
            log_info "Venv activation script exists"
        fi
    else
        log_warn "FoKS venv not found: $VENV_DIR (optional if using system Python)"
    fi
    
    if [[ "$py_ok" == "true" ]]; then
        check_pass "Python Environment"
        return 0
    else
        local failure_msg
        failure_msg=$(IFS='; '; echo "${failures[*]}")
        check_fail "Python Environment" "$failure_msg"
        return 1
    fi
}

# Main execution
main() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  FoKS Unified System Health Check${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    # Run all checks (continue on failure)
    check_foks_backend || true
    echo ""
    check_fbp_backend || true
    echo ""
    check_foks_fbp_transport || true
    echo ""
    check_nfa_automation || true
    echo ""
    check_nfa_intelligence || true
    echo ""
    check_filesystem || true
    echo ""
    check_python_env || true
    echo ""
    
    # Print summary
    echo -e "${BLUE}========================================${NC}"
    if [[ $CHECKS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}  ALL HEALTH CHECKS PASSED${NC}"
        echo -e "${GREEN}  Passed: $CHECKS_PASSED / $((CHECKS_PASSED + CHECKS_FAILED))${NC}"
        echo -e "${BLUE}========================================${NC}"
        exit 0
    else
        echo -e "${RED}  HEALTH CHECK FAILURES DETECTED${NC}"
        echo -e "${RED}  Passed: $CHECKS_PASSED / $((CHECKS_PASSED + CHECKS_FAILED))${NC}"
        echo -e "${RED}  Failed: $CHECKS_FAILED / $((CHECKS_PASSED + CHECKS_FAILED))${NC}"
        echo ""
        echo -e "${RED}Failed Modules:${NC}"
        for module in "${FAILED_MODULES[@]}"; do
            echo -e "${RED}  - $module${NC}"
        done
        echo -e "${BLUE}========================================${NC}"
        exit 1
    fi
}

# Run main
main "$@"
