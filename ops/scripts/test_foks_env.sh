#!/usr/bin/env bash
# Quick Environment Test Script
# Run this to verify FoKS environment is correctly configured

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="$PROJECT_ROOT/backend/.venv_foks"
PYTHON_BIN="$VENV_DIR/bin/python"
UVICORN_BIN="$VENV_DIR/bin/uvicorn"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "🔍 FoKS Environment Test"
echo "======================="
echo ""

# Test 1: Venv exists
echo -n "Test 1: Virtualenv exists... "
if [[ -d "$VENV_DIR" ]]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  → Run: python3.11 -m venv $VENV_DIR"
    exit 1
fi

# Test 2: Python executable works
echo -n "Test 2: Venv Python works... "
if "$PYTHON_BIN" --version >/dev/null 2>&1; then
    version="$("$PYTHON_BIN" --version 2>&1)"
    echo -e "${GREEN}PASS${NC} ($version)"
else
    echo -e "${RED}FAIL${NC}"
    exit 1
fi

# Test 3: Uvicorn installed
echo -n "Test 3: Uvicorn installed... "
if "$PYTHON_BIN" -c "import uvicorn" 2>/dev/null; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  → Run: $VENV_DIR/bin/pip install uvicorn[standard]"
    exit 1
fi

# Test 4: Uvicorn executable
echo -n "Test 4: Uvicorn executable... "
if [[ -x "$UVICORN_BIN" ]]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    exit 1
fi

# Test 5: FastAPI installed
echo -n "Test 5: FastAPI installed... "
if "$PYTHON_BIN" -c "import fastapi" 2>/dev/null; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${YELLOW}WARN${NC}"
    echo "  → Run: $VENV_DIR/bin/pip install fastapi"
fi

# Test 6: Check for PATH conflicts
echo -n "Test 6: Check PATH conflicts... "
system_python="$(which python 2>/dev/null || echo 'none')"
if [[ "$system_python" == *"homebrew"* ]]; then
    echo -e "${YELLOW}WARN${NC}"
    echo "  → System python points to Homebrew: $system_python"
    echo "  → This is OK if scripts use absolute paths"
else
    echo -e "${GREEN}PASS${NC}"
fi

# Test 7: Check zshrc protection
echo -n "Test 7: Shell config protection... "
if grep -q "FoKS Intelligence - Venv Protection" "$HOME/.zshrc" 2>/dev/null; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${YELLOW}WARN${NC}"
    echo "  → Run: bash $PROJECT_ROOT/ops/scripts/foks_env_autofix.sh"
fi

# Test 8: Try importing app.main
echo -n "Test 8: FoKS app.main import... "
cd "$PROJECT_ROOT/backend"
if PYTHONPATH="$PROJECT_ROOT/backend" "$PYTHON_BIN" -c "import app.main" 2>/dev/null; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${YELLOW}WARN${NC}"
    echo "  → May need additional dependencies"
fi

echo ""
echo "======================="
echo -e "${GREEN}✅ Environment tests completed${NC}"
echo ""
echo "To start FoKS:"
echo "  $PROJECT_ROOT/ops/scripts/foks_boot.sh"
echo ""
echo "To verify health:"
echo "  curl http://localhost:8000/health"
echo ""

