#!/usr/bin/env bash
#
# stop_nfa_all.sh - FoKS wrapper for NFA cleanup
#
# This script calls the main cleanup script in FBP_Backend if it exists,
# otherwise performs a standalone cleanup.
#
# Usage: ./ops/scripts/stop_nfa_all.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FOKS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# FBP Backend location
FBP_BACKEND="${HOME}/Documents/FBP_Backend"
FBP_STOP_SCRIPT="${FBP_BACKEND}/ops/stop_nfa_all.sh"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}[FoKS]${NC} NFA Cleanup Wrapper"
echo ""

# Check if FBP_Backend script exists and use it
if [[ -f "$FBP_STOP_SCRIPT" ]]; then
    echo -e "${GREEN}[FoKS]${NC} Found FBP cleanup script, delegating..."
    echo ""
    exec "$FBP_STOP_SCRIPT" "$@"
fi

# Fallback: standalone cleanup if FBP script not found
echo -e "${BLUE}[FoKS]${NC} FBP script not found, running standalone cleanup..."
echo ""

# Kill processes on ports 9500 and 8000
for port in 9500 8000; do
    pids=$(lsof -ti "tcp:$port" 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        for pid in $pids; do
            echo "  Stopping PID $pid on port $port"
            kill -TERM "$pid" 2>/dev/null || true
            sleep 0.5
            kill -KILL "$pid" 2>/dev/null || true
        done
    else
        echo "  Port $port: No process listening"
    fi
done

# Kill NFA browser processes
nfa_pids=$(pgrep -f "foks_atf_profile|ms-playwright|playwright" 2>/dev/null || true)
for pid in $nfa_pids; do
    cmdline=$(ps -p "$pid" -o command= 2>/dev/null || echo "")
    if echo "$cmdline" | grep -qiE "(chromium|chrome)" 2>/dev/null; then
        echo "  Stopping browser PID $pid"
        kill -TERM "$pid" 2>/dev/null || true
        sleep 0.3
        kill -KILL "$pid" 2>/dev/null || true
    fi
done

# Clean temp profiles
rm -rf /tmp/foks_atf_profile_* 2>/dev/null || true

echo ""
echo -e "${GREEN}[FoKS]${NC} Cleanup complete!"
echo ""

# Final status
echo "Port status:"
lsof -nP -iTCP:9500 -sTCP:LISTEN 2>/dev/null || echo "  Port 9500: FREE"
lsof -nP -iTCP:8000 -sTCP:LISTEN 2>/dev/null || echo "  Port 8000: FREE"

exit 0
