#!/bin/bash
# Execute NFA Trigger Batch - Ready to Run
# This script will execute all 3 NFA triggers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BASE_URL="http://localhost:8000"
ENDPOINT="${BASE_URL}/tasks/nfa"
SOCKET_PATH="${FBP_SOCKET_PATH:-/tmp/fbp.sock}"
CHECK_SCRIPT="$PROJECT_ROOT/ops/scripts/check_fbp_status.sh"
FIX_SCRIPT="$PROJECT_ROOT/ops/scripts/fix_fbp_connection.sh"

################################################################################
# Colors
################################################################################
RED=$'\033[31m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
CYAN=$'\033[36m'
RESET=$'\033[0m'

################################################################################
# Check FBP socket
################################################################################
check_fbp_socket() {
    echo "Checking FBP backend connection..."
    
    # Check if socket exists and is accessible
    if [[ ! -S "$SOCKET_PATH" ]]; then
        echo ""
        echo "${RED}❌ ERROR: FBP socket not available!${RESET}"
        echo ""
        echo "The FBP backend must be running for NFA triggers to work."
        echo "Socket path: $SOCKET_PATH"
        echo ""
        echo "Quick fix options:"
        echo "  1. Auto-fix (recommended):"
        echo "     ${CYAN}bash $FIX_SCRIPT${RESET}"
        echo ""
        echo "  2. Check status:"
        echo "     ${CYAN}bash $CHECK_SCRIPT${RESET}"
        echo ""
        echo "  3. Manual start:"
        echo "     ${CYAN}bash $PROJECT_ROOT/ops/scripts/start_fbp_backend.sh${RESET}"
        echo ""
        
        # Offer to auto-fix
        if [[ "${AUTO_FIX:-}" == "1" ]] || [[ "${1:-}" == "--auto-fix" ]]; then
            echo "${YELLOW}Attempting to start FBP backend automatically...${RESET}"
            echo ""
            if bash "$FIX_SCRIPT" --background 2>&1 | head -20; then
                echo ""
                echo "Waiting for FBP to start..."
                sleep 5
                
                # Re-check
                if [[ -S "$SOCKET_PATH" ]] && lsof "$SOCKET_PATH" >/dev/null 2>&1; then
                    echo "${GREEN}✅ FBP backend started successfully${RESET}"
                    echo ""
                    return 0
                fi
            fi
            echo ""
            echo "${RED}Auto-start failed. Please start FBP manually.${RESET}"
        fi
        
        exit 1
    fi
    
    # Check if process is listening
    if ! lsof "$SOCKET_PATH" >/dev/null 2>&1; then
        echo ""
        echo "${YELLOW}⚠ WARNING: Socket exists but no process listening${RESET}"
        echo "  Socket: $SOCKET_PATH"
        echo "  This may indicate a stale socket file."
        echo ""
        echo "  Fix: Remove stale socket and restart FBP:"
        echo "    ${CYAN}rm -f $SOCKET_PATH${RESET}"
        echo "    ${CYAN}bash $FIX_SCRIPT${RESET}"
        echo ""
        exit 1
    fi
    
    # Test connectivity
    if command -v curl >/dev/null 2>&1; then
        if ! curl --unix-socket "$SOCKET_PATH" --max-time 2 -s http://localhost/health >/dev/null 2>&1; then
            echo ""
            echo "${YELLOW}⚠ WARNING: Socket exists but health check failed${RESET}"
            echo "  FBP backend may still be starting up..."
            echo "  Continuing anyway..."
            echo ""
        fi
    fi
    
    echo "${GREEN}✅ FBP backend is ready${RESET}"
    return 0
}

echo "=========================================="
echo "NFA TRIGGER BATCH EXECUTION"
echo "=========================================="
echo ""

# Check FoKS server
if ! curl -s "${BASE_URL}/health" > /dev/null 2>&1; then
    echo "${RED}❌ ERROR: FoKS server is not running!${RESET}"
    echo ""
    echo "Please start the server first:"
    echo "  cd backend"
    echo "  source .venv_foks/bin/activate  # or your venv"
    echo "  uvicorn app.main:app --host 127.0.0.1 --port 8000"
    echo ""
    exit 1
fi

echo "${GREEN}✅ FoKS server is running${RESET}"
echo ""

# Check FBP socket (pre-flight check)
if ! check_fbp_socket "$@"; then
    exit 1
fi

echo ""

# Execute requests
declare -a results=()

echo "1️⃣  SP228 - CPF: 228.240.248-01"
response1=$(curl -s -w "\n%{http_code}" -X POST "${ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d '{"cpf": "228.240.248-01", "test": false}')
http1=$(echo "$response1" | tail -n1)
body1=$(echo "$response1" | sed '$d')
success1=$(echo "$body1" | grep -o '"success":[^,}]*' | cut -d':' -f2 | tr -d ' ' || echo "false")
message1=$(echo "$body1" | grep -o '"message":"[^"]*"' | cut -d'"' -f4 || echo "No message")
if [ "$http1" = "200" ] && [ "$success1" = "true" ]; then
    echo "   ✅ SUCCESS: $message1"
    results+=("✅ SP228: SUCCESS")
else
    echo "   ❌ FAILED: $message1 (HTTP $http1)"
    results+=("❌ SP228: FAILED")
fi
echo ""

echo "2️⃣  SP233 - CPF: 113.684.248.99"
echo "   ⚠️  Note: Format might need to be 113.684.248-99"
response2=$(curl -s -w "\n%{http_code}" -X POST "${ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d '{"cpf": "113.684.248.99", "test": false}')
http2=$(echo "$response2" | tail -n1)
body2=$(echo "$response2" | sed '$d')
success2=$(echo "$body2" | grep -o '"success":[^,}]*' | cut -d':' -f2 | tr -d ' ' || echo "false")
message2=$(echo "$body2" | grep -o '"message":"[^"]*"' | cut -d'"' -f4 || echo "No message")
if [ "$http2" = "200" ] && [ "$success2" = "true" ]; then
    echo "   ✅ SUCCESS: $message2"
    results+=("✅ SP233: SUCCESS")
else
    echo "   ❌ FAILED: $message2 (HTTP $http2)"
    results+=("❌ SP233: FAILED")
    # Try with corrected format
    echo "   🔄 Retrying with corrected format: 113.684.248-99"
    response2b=$(curl -s -w "\n%{http_code}" -X POST "${ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d '{"cpf": "113.684.248-99", "test": false}')
    http2b=$(echo "$response2b" | tail -n1)
    body2b=$(echo "$response2b" | sed '$d')
    success2b=$(echo "$body2b" | grep -o '"success":[^,}]*' | cut -d':' -f2 | tr -d ' ' || echo "false")
    message2b=$(echo "$body2b" | grep -o '"message":"[^"]*"' | cut -d'"' -f4 || echo "No message")
    if [ "$http2b" = "200" ] && [ "$success2b" = "true" ]; then
        echo "   ✅ SUCCESS (retry): $message2b"
        results+=("✅ SP233: SUCCESS (retry)")
    else
        echo "   ❌ FAILED (retry): $message2b (HTTP $http2b)"
    fi
fi
echo ""

echo "3️⃣  SP242 - CPF: 512.810.178-92"
response3=$(curl -s -w "\n%{http_code}" -X POST "${ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d '{"cpf": "512.810.178-92", "test": false}')
http3=$(echo "$response3" | tail -n1)
body3=$(echo "$response3" | sed '$d')
success3=$(echo "$body3" | grep -o '"success":[^,}]*' | cut -d':' -f2 | tr -d ' ' || echo "false")
message3=$(echo "$body3" | grep -o '"message":"[^"]*"' | cut -d'"' -f4 || echo "No message")
if [ "$http3" = "200" ] && [ "$success3" = "true" ]; then
    echo "   ✅ SUCCESS: $message3"
    results+=("✅ SP242: SUCCESS")
else
    echo "   ❌ FAILED: $message3 (HTTP $http3)"
    results+=("❌ SP242: FAILED")
fi
echo ""

echo "=========================================="
echo "SUMMARY"
echo "=========================================="
for result in "${results[@]}"; do
    echo "$result"
done
echo "=========================================="
