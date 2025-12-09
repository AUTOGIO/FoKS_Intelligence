#!/usr/bin/env bash
# Health check script for FoKS Intelligence

set -euo pipefail

BASE_URL="${FOKS_BASE_URL:-http://localhost:8000}"
TIMEOUT=5

echo "🔍 Checking FoKS Intelligence health..."
echo ""

# Check if server is running
if curl -s --max-time $TIMEOUT "$BASE_URL/health" > /dev/null; then
    echo "✅ Server is running"

    # Get health details
    echo ""
    echo "📊 Health Details:"
    curl -s "$BASE_URL/health" | python3 -m json.tool

    # Get metrics
    echo ""
    echo "📈 Metrics:"
    curl -s "$BASE_URL/metrics" | python3 -m json.tool | head -30

    echo ""
    echo "✅ All checks passed!"
else
    echo "❌ Server is not responding"
    echo "   Check if backend is running: ./scripts/start_backend.sh"
    exit 1
fi

