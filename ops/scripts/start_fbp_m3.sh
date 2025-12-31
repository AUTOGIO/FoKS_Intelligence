#!/usr/bin/env bash
# Modern FBP Backend Startup (M3 Optimized)
# Uses uv for dependency management and modern Python practices
# Hardware: iMac (Mac15,5) - M3 Apple Silicon

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FBP_ROOT="/Users/dnigga/Documents/FBP_Backend"
SOCKET_PATH="${FBP_SOCKET_PATH:-/tmp/fbp.sock}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting FBP Backend (M3 Optimized)${NC}"
echo "Socket: $SOCKET_PATH"
echo ""

cd "$FBP_ROOT"

# Method 1: Try uv project management (modern, 2025 best practice)
if command -v uv &> /dev/null && [ -f "pyproject.toml" ]; then
    echo -e "${GREEN}📦 Using uv project management...${NC}"
    uv run uvicorn app.main:app \
        --uds "$SOCKET_PATH" \
        --workers 1 \
        --loop uvloop \
        --http httptools \
        --log-level info &
    echo $! > /tmp/fbp_server.pid
    echo -e "${GREEN}✓ FBP started with uv (PID: $(cat /tmp/fbp_server.pid))${NC}"
    
# Method 2: Fallback to venv (traditional, still valid)
elif [ -d "$HOME/Documents/.venvs/fbp" ]; then
    echo -e "${GREEN}📦 Using centralized venv...${NC}"
    source "$HOME/Documents/.venvs/fbp/bin/activate"
    
    # Remove stale socket
    rm -f "$SOCKET_PATH"
    
    # Start with M3 optimizations
    exec uvicorn app.main:app \
        --uds "$SOCKET_PATH" \
        --workers 1 \
        --loop uvloop \
        --http httptools \
        --log-level info

elif [ -d "$FBP_ROOT/venv" ]; then
    echo -e "${GREEN}📦 Using project venv...${NC}"
    source "$FBP_ROOT/venv/bin/activate"
    
    rm -f "$SOCKET_PATH"
    
    exec uvicorn app.main:app \
        --uds "$SOCKET_PATH" \
        --workers 1 \
        --loop uvloop \
        --http httptools \
        --log-level info

else
    echo -e "${YELLOW}❌ No virtual environment found${NC}"
    echo "Run: bash $SCRIPT_DIR/../setup_m3_modern.sh"
    exit 1
fi

# Wait for socket creation
for i in {1..10}; do
    if [ -S "$SOCKET_PATH" ]; then
        echo -e "${GREEN}✓ Socket ready: $SOCKET_PATH${NC}"
        
        # Verify health
        sleep 1
        if curl --unix-socket "$SOCKET_PATH" http://localhost/socket-health &>/dev/null; then
            echo -e "${GREEN}✓ FBP backend healthy${NC}"
        fi
        exit 0
    fi
    sleep 1
done

echo -e "${YELLOW}⚠️  Socket not created within 10 seconds${NC}"
echo "Check logs for errors"
exit 1
