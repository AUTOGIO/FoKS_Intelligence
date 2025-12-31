#!/usr/bin/env bash
# Modern M3 iMac Setup Script (2025 Best Practices)
# Hardware: iMac (Mac15,5) - M3 Apple Silicon
# macOS: 26.2+
# Python: 3.12+ (recommended for M3 optimizations)

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🍎 Modern M3 Setup for FoKS Intelligence${NC}"
echo "Hardware: iMac (Mac15,5) - M3 Apple Silicon"
echo "macOS: $(sw_vers -productVersion)"
echo ""

# Check if running on Apple Silicon
ARCH=$(uname -m)
if [[ "$ARCH" != "arm64" ]]; then
    echo -e "${YELLOW}⚠️  Warning: Not running on Apple Silicon (current: $ARCH)${NC}"
fi

# 1. Install uv (modern Python package manager, 10-100x faster than pip)
if ! command -v uv &> /dev/null; then
    echo -e "${GREEN}📦 Installing uv (modern Python package manager)...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    source "$HOME/.zshrc" 2>/dev/null || source "$HOME/.bash_profile" 2>/dev/null || true
else
    echo -e "${GREEN}✓ uv already installed${NC}"
fi

# 2. Install Python 3.12+ (better M3 performance than 3.9)
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
echo -e "${GREEN}🐍 Setting up Python ${PYTHON_VERSION} with uv...${NC}"

# Install Python via uv (manages versions automatically)
uv python install "$PYTHON_VERSION" || {
    echo -e "${YELLOW}⚠️  Python ${PYTHON_VERSION} installation skipped (may already exist)${NC}"
}

# 3. Setup FoKS backend with uv
FOKS_ROOT="/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence"
FOKS_BACKEND="$FOKS_ROOT/backend"

echo -e "${GREEN}🚀 Setting up FoKS backend...${NC}"
cd "$FOKS_BACKEND"

# Use uv to sync dependencies (reads pyproject.toml)
if [ -f "pyproject.toml" ]; then
    echo -e "${GREEN}📋 Syncing dependencies with uv...${NC}"
    uv sync --python "$PYTHON_VERSION" || {
        echo -e "${YELLOW}⚠️  Using fallback: pip install${NC}"
        "$HOME/.cargo/bin/uv" venv --python "$PYTHON_VERSION" .venv_foks
        source .venv_foks/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
    }
else
    echo -e "${YELLOW}⚠️  pyproject.toml not found, using requirements.txt${NC}"
    "$HOME/.cargo/bin/uv" venv --python "$PYTHON_VERSION" .venv_foks
    source .venv_foks/bin/activate
    uv pip install --upgrade pip
    uv pip install -r requirements.txt
fi

echo -e "${GREEN}✓ FoKS backend ready${NC}"

# 4. Setup FBP backend with uv (modern approach)
FBP_ROOT="/Users/dnigga/Documents/FBP_Backend"
FBP_VENV="$HOME/.local/share/uv/projects/fbp"  # uv managed project

echo -e "${GREEN}🔧 Setting up FBP backend...${NC}"

if [ -d "$FBP_ROOT" ]; then
    cd "$FBP_ROOT"
    
    # Use uv project management (preferred) or create venv
    if [ -f "pyproject.toml" ]; then
        echo -e "${GREEN}📋 Syncing FBP dependencies with uv...${NC}"
        uv sync --python "$PYTHON_VERSION" || {
            echo -e "${YELLOW}⚠️  Using fallback venv approach${NC}"
            mkdir -p "$HOME/Documents/.venvs"
            "$HOME/.cargo/bin/uv" venv --python "$PYTHON_VERSION" "$HOME/Documents/.venvs/fbp"
            source "$HOME/Documents/.venvs/fbp/bin/activate"
            uv pip install -r requirements.txt || uv pip install -e .
        }
    else
        # Create centralized venv using uv
        echo -e "${GREEN}📦 Creating FBP virtual environment with uv...${NC}"
        mkdir -p "$HOME/Documents/.venvs"
        "$HOME/.cargo/bin/uv" venv --python "$PYTHON_VERSION" "$HOME/Documents/.venvs/fbp"
        source "$HOME/Documents/.venvs/fbp/bin/activate"
        uv pip install --upgrade pip
        if [ -f "requirements.txt" ]; then
            uv pip install -r requirements.txt
        elif [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
            uv pip install -e .
        fi
    fi
    
    echo -e "${GREEN}✓ FBP backend ready${NC}"
else
    echo -e "${YELLOW}⚠️  FBP backend not found at $FBP_ROOT${NC}"
fi

# 5. Verify socket permissions (macOS 26.2 best practices)
SOCKET_PATH="/tmp/fbp.sock"
echo -e "${GREEN}🔐 Configuring socket permissions...${NC}"

# Create socket directory if needed
sudo mkdir -p "$(dirname "$SOCKET_PATH")" 2>/dev/null || true

# Set proper permissions (user writable, readable by group)
# macOS 26.2: sockets inherit from umask, ensure proper defaults
if [ -e "$SOCKET_PATH" ]; then
    chmod 660 "$SOCKET_PATH" 2>/dev/null || true
    echo -e "${GREEN}✓ Socket permissions configured${NC}"
fi

# 6. Verify M3 optimizations
echo -e "${GREEN}⚡ Verifying M3 optimizations...${NC}"

# Check for uvloop (async performance)
cd "$FOKS_BACKEND"
if source .venv_foks/bin/activate 2>/dev/null || source "$HOME/Documents/.venvs/fbp/bin/activate" 2>/dev/null; then
    python3 -c "
import sys
print(f'Python: {sys.version}')
try:
    import uvloop
    print('✓ uvloop available (M3 async optimization)')
except ImportError:
    print('⚠️  uvloop not installed (recommended for M3)')

try:
    import httptools
    print('✓ httptools available (fast HTTP parsing)')
except ImportError:
    print('⚠️  httptools not installed (recommended)')
" || true
fi

# 7. Summary
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Modern M3 setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Set NFA environment variables:"
echo "     export NFA_USERNAME='your_username'"
echo "     export NFA_PASSWORD='your_password'"
echo "     export NFA_EMITENTE_CNPJ='your_cnpj'"
echo ""
echo "  2. Start FBP backend:"
echo "     cd $FBP_ROOT"
echo "     source ~/Documents/.venvs/fbp/bin/activate  # or: uv run"
echo "     ./scripts/start.sh"
echo ""
echo "  3. Start FoKS backend:"
echo "     cd $FOKS_BACKEND"
echo "     source .venv_foks/bin/activate  # or: uv run"
echo "     uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
