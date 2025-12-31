#!/bin/bash
# Setup script for NFA Job automation
# Installs Playwright and browsers

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$BACKEND_DIR/.venv_foks"

echo "🔧 Setting up NFA Job automation..."

# Check if venv exists
if [[ ! -d "$VENV_DIR" ]]; then
    echo "❌ FoKS venv not found at $VENV_DIR"
    echo "   Please run: cd backend && python3 -m venv .venv_foks"
    exit 1
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Install Playwright
echo "📦 Installing Playwright..."
pip install -q playwright>=1.40.0

# Install Playwright browsers
echo "🌐 Installing Playwright browsers (Chromium)..."
playwright install chromium

echo "✅ NFA Job setup complete!"
echo ""
echo "To test the installation:"
echo "  python3 $SCRIPT_DIR/nfa_job.py --help"
echo ""
echo "To run a job:"
echo "  export NFA_USERNAME='your_username'"
echo "  export NFA_PASSWORD='your_password'"
echo "  python3 $SCRIPT_DIR/nfa_job.py --data-inicial 08/12/2025 --data-final 10/12/2025"
