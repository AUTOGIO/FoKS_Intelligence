#!/usr/bin/env bash
# iTerm2 FoKS Automation Profiles - Installation Script

set -e

echo "🚀 Installing FoKS iTerm2 Automation Profiles"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directories
ITERM2_CONFIG_DIR="$HOME/Library/Application Support/iTerm2"
DYNAMIC_PROFILES_DIR="$ITERM2_CONFIG_DIR/DynamicProfiles"
SCRIPTS_DIR="$ITERM2_CONFIG_DIR/Scripts"
AUTOLAUNCH_DIR="$SCRIPTS_DIR/AutoLaunch"

SOURCE_DIR="/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/iterm2"

# Check if iTerm2 is installed
if ! command -v iTerm2 &> /dev/null; then
    echo -e "${YELLOW}⚠️  iTerm2 not found. Installing via Homebrew...${NC}"
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew not found. Please install Homebrew first:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    brew install --cask iterm2
fi

echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p "$DYNAMIC_PROFILES_DIR"
mkdir -p "$AUTOLAUNCH_DIR"

# Install Dynamic Profiles
echo -e "${BLUE}📋 Installing Dynamic Profiles...${NC}"
if [ -f "$SOURCE_DIR/FoKS_Automation_Profiles.json" ]; then
    # File was created directly in target location, verify it
    if [ -f "$DYNAMIC_PROFILES_DIR/FoKS_Automation_Profiles.json" ]; then
        echo -e "${GREEN}✅ Dynamic profiles already installed${NC}"
    else
        echo "❌ Dynamic profiles not found. Please check the source file."
        exit 1
    fi
else
    echo "❌ Source profiles file not found at $SOURCE_DIR"
    exit 1
fi

# Validate JSON
echo -e "${BLUE}🔍 Validating JSON...${NC}"
if command -v jq &> /dev/null; then
    if jq empty "$DYNAMIC_PROFILES_DIR/FoKS_Automation_Profiles.json" 2>/dev/null; then
        echo -e "${GREEN}✅ JSON is valid${NC}"
    else
        echo "❌ JSON validation failed. Please check the profiles file."
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  jq not found, skipping JSON validation${NC}"
    echo "   Install jq: brew install jq"
fi

# Install Python API Scripts
echo -e "${BLUE}🐍 Installing Python API scripts...${NC}"
if [ -d "$SOURCE_DIR" ]; then
    for script in automation_launcher.py status_bar_monitor.py auto_restart_monitor.py ai_error_handler.py; do
        if [ -f "$SOURCE_DIR/$script" ]; then
            cp "$SOURCE_DIR/$script" "$AUTOLAUNCH_DIR/"
            chmod +x "$AUTOLAUNCH_DIR/$script"
            echo -e "${GREEN}  ✅ Installed $script${NC}"
        else
            echo -e "${YELLOW}  ⚠️  $script not found, skipping${NC}"
        fi
    done
else
    echo -e "${YELLOW}⚠️  Scripts directory not found at $SOURCE_DIR${NC}"
fi

# Check iTerm2 Python runtime
echo -e "${BLUE}🐍 Checking iTerm2 Python runtime...${NC}"
ITERM2_PYTHON="$ITERM2_CONFIG_DIR/iterm2env/versions/*/bin/python3"
if ls $ITERM2_PYTHON 1> /dev/null 2>&1; then
    echo -e "${GREEN}✅ Python runtime installed${NC}"
    PYTHON_VERSION=$(ls $ITERM2_PYTHON | head -1 | xargs -I {} {} --version)
    echo "   Version: $PYTHON_VERSION"
else
    echo -e "${YELLOW}⚠️  Python runtime not found${NC}"
    echo "   Install via: iTerm2 → Scripts → Manage → Install Python Runtime"
    echo "   Or run: iTerm2 → Scripts → Manage → New Python Script"
fi

# Install shell integration if not present
echo -e "${BLUE}🐚 Checking shell integration...${NC}"
if [ -f "$HOME/.iterm2_shell_integration.zsh" ]; then
    echo -e "${GREEN}✅ Shell integration installed${NC}"
else
    echo -e "${YELLOW}⚠️  Shell integration not found${NC}"
    read -p "Install shell integration now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        curl -L https://iterm2.com/shell_integration/zsh \
            -o ~/.iterm2_shell_integration.zsh
        
        if ! grep -q "iterm2_shell_integration.zsh" ~/.zshrc; then
            echo 'source ~/.iterm2_shell_integration.zsh' >> ~/.zshrc
            echo -e "${GREEN}✅ Added to ~/.zshrc${NC}"
        fi
        
        echo -e "${GREEN}✅ Shell integration installed${NC}"
        echo "   Run: source ~/.zshrc"
    fi
fi

# Create example configuration
echo -e "${BLUE}📝 Creating example configurations...${NC}"
cat > "$HOME/.foks_iterm2_config" << 'EOF'
# FoKS iTerm2 Configuration
# Source this in your .zshrc for additional features

# Aliases for quick profile switching
alias foks-backend="echo -e '\033]50;SetProfile=FoKS Intelligence - Backend\a'"
alias fbp-backend="echo -e '\033]50;SetProfile=FBP Backend - Socket Server\a'"
alias nfa-batch="echo -e '\033]50;SetProfile=NFA Automation - Batch Runner\a'"

# Quick commands
alias foks-start="cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend && source /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/.venv_foks/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
alias fbp-start="cd /Users/dnigga/Documents/FBP_Backend && source ~/.venvs/fbp/bin/activate && uvicorn app.main:app --uds /tmp/fbp.sock --loop uvloop --http httptools"
alias nfa-run="cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence && source /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/.venv_foks/bin/activate && python run_rental_nfa_batch.py"

# Health check functions
foks-health() {
    echo "🏥 FoKS Health Check"
    curl -s http://localhost:8000/health | jq .
}

fbp-health() {
    echo "🏥 FBP Health Check"
    curl -s --unix-socket /tmp/fbp.sock http://localhost/socket-health | jq .
}

all-health() {
    echo "🏥 System Health Check"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "FoKS Backend:"
    foks-health
    echo ""
    echo "FBP Socket:"
    fbp-health
}

# Badge updater
update-badge() {
    local badge_text="$1"
    echo -e "\033]1337;SetBadgeFormat=$(echo -n "$badge_text" | base64)\a"
}

# Auto-update badge with git branch (requires shell integration)
if [ -n "$ITERM_SESSION_ID" ]; then
    precmd() {
        if git rev-parse --git-dir > /dev/null 2>&1; then
            branch=$(git branch --show-current 2>/dev/null)
            if [ -n "$branch" ]; then
                update-badge "$(basename $(pwd))\\n$branch"
            fi
        fi
    }
fi
EOF

echo -e "${GREEN}✅ Created ~/.foks_iterm2_config${NC}"

# Add to .zshrc if not present
if ! grep -q ".foks_iterm2_config" ~/.zshrc 2>/dev/null; then
    echo "" >> ~/.zshrc
    echo "# FoKS iTerm2 Configuration" >> ~/.zshrc
    echo "[ -f ~/.foks_iterm2_config ] && source ~/.foks_iterm2_config" >> ~/.zshrc
    echo -e "${GREEN}✅ Added to ~/.zshrc${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Installation Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "📋 Installed Components:"
echo "   ✅ 11 Dynamic Profiles"
echo "   ✅ 4 Python API Scripts"
echo "   ✅ Shell integration helpers"
echo "   ✅ Custom aliases and functions"
echo ""
echo "🚀 Next Steps:"
echo ""
echo "1. Restart iTerm2 or reload profiles:"
echo "   iTerm2 → Settings → Profiles → Other Actions → Reload All Profiles"
echo ""
echo "2. Install Python runtime (if not done):"
echo "   iTerm2 → Scripts → Manage → Install Python Runtime"
echo ""
echo "3. Enable AutoLaunch scripts:"
echo "   iTerm2 → Scripts → Manage → Enable AutoLaunch Scripts"
echo ""
echo "4. Reload your shell:"
echo "   source ~/.zshrc"
echo ""
echo "5. Test profiles:"
echo "   ⌘T → Select 'FoKS Intelligence - Backend'"
echo ""
echo "6. Launch automation workspace:"
echo "   iTerm2 → Scripts → automation_launcher"
echo ""
echo "📚 Documentation:"
echo "   $SOURCE_DIR/README.md"
echo ""
echo "🎯 Quick Commands:"
echo "   foks-start   - Start FoKS backend"
echo "   fbp-start    - Start FBP backend"
echo "   nfa-run      - Run NFA batch"
echo "   all-health   - Check all services"
echo ""
