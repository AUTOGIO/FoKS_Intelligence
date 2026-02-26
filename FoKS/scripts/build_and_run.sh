#!/bin/bash
# FoKS Intelligence — Build & Run via Cursor
# Usage: ./scripts/build_and_run.sh [--build-only | --run-only]
set -euo pipefail

FOKS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BINARY="${FOKS_DIR}/.build/debug/foks-app"
PF_DIR="/Users/dnigga/Documents/Active_Projects/PromptForge_Personal"

echo "━━━ FoKS Intelligence — Build & Run ━━━"
echo "Package: ${FOKS_DIR}"
echo "Binary:  ${BINARY}"
echo ""

build() {
    echo "▸ Building FoKS Swift app..."
    cd "${FOKS_DIR}"
    swift build 2>&1
    echo ""
    echo "✅ Build complete"
}

run_app() {
    echo "▸ Launching FoKS app..."
    # Kill existing instance if running
    pkill -f foks-app 2>/dev/null || true
    sleep 0.5
    "${BINARY}" &
    APP_PID=$!
    echo "✅ FoKS app running (PID: ${APP_PID})"
    echo ""

    # Wait for HTTP server to be ready
    echo "▸ Waiting for HTTP server on port 3000..."
    for i in $(seq 1 10); do
        if curl -sf http://127.0.0.1:3000/health > /dev/null 2>&1; then
            echo "✅ HTTP server healthy"
            curl -s http://127.0.0.1:3000/health | python3 -m json.tool 2>/dev/null || true
            break
        fi
        sleep 1
    done
}

health_check() {
    echo ""
    echo "▸ Integration health check..."
    if [ -f "${PF_DIR}/.build/debug/promptforge-personal" ]; then
        "${PF_DIR}/.build/debug/promptforge-personal" integration status 2>/dev/null || echo "  (PromptForge not built — run 'swift build' in PromptForge_Personal)"
    else
        echo "  Checking FoKS directly..."
        curl -sf http://127.0.0.1:3000/health | python3 -m json.tool 2>/dev/null && echo "  FoKS: ✅" || echo "  FoKS: ❌"
        curl -sf http://127.0.0.1:8000/health | python3 -m json.tool 2>/dev/null && echo "  FBP:  ✅" || echo "  FBP:  ❌"
    fi
}

case "${1:-}" in
    --build-only) build ;;
    --run-only)   run_app; health_check ;;
    *)            build; run_app; health_check ;;
esac

echo ""
echo "━━━ Done ━━━"
