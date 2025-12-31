#!/usr/bin/env bash
# Install FoKS M3-Optimized iTerm2 Profile
# For MacBook Air 15" M3 (fanless) - macOS 26.0 (Tahoe)

set -euo pipefail

echo "🚀 Installing FoKS M3-Optimized iTerm2 Profile"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE_JSON="${SCRIPT_DIR}/FoKS_M3_Optimized.json"
ITERM2_DIR="$HOME/Library/Application Support/iTerm2"
DYNAMIC_PROFILES_DIR="$ITERM2_DIR/DynamicProfiles"

# Check if profile exists
if [ ! -f "$PROFILE_JSON" ]; then
    echo -e "${RED}❌ Profile JSON not found: $PROFILE_JSON${NC}"
    exit 1
fi

# Create DynamicProfiles directory
echo -e "${BLUE}📁 Creating DynamicProfiles directory...${NC}"
mkdir -p "$DYNAMIC_PROFILES_DIR"

# Copy profile
echo -e "${BLUE}📋 Installing profile...${NC}"
cp "$PROFILE_JSON" "$DYNAMIC_PROFILES_DIR/FoKS_M3_Optimized.json"
echo -e "${GREEN}✅ Profile copied${NC}"

# Validate JSON
if command -v jq &> /dev/null; then
    echo -e "${BLUE}🔍 Validating JSON...${NC}"
    if jq empty "$DYNAMIC_PROFILES_DIR/FoKS_M3_Optimized.json" 2>/dev/null; then
        echo -e "${GREEN}✅ JSON is valid${NC}"
    else
        echo -e "${RED}❌ JSON validation failed${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  jq not found, skipping validation (install: brew install jq)${NC}"
fi

echo ""
echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""
echo "📝 Next steps:"
echo "1. Open iTerm2"
echo "2. Go to Preferences (⌘,) → Profiles"
echo "3. The 'FoKS Intelligence — M3 Optimized' profile should appear automatically"
echo "4. Select it and click 'Other Actions...' → 'Set as Default' (optional)"
echo ""
echo "🔧 M3 Optimizations to enable manually:"
echo "   Preferences → General → Magic:"
echo "   ✅ Enable 'GPU Rendering' (Metal)"
echo "   ✅ Enable 'Disable GPU renderer when disconnected from power'"
echo "   ✅ Enable 'Maximize Throughput' (reduces GPU load by ~40%)"
echo ""
echo "💡 The profile will:"
echo "   • Auto-activate backend/.venv_foks"
echo "   • Auto-cd to FoKS directory"
echo "   • Set PYTHONPATH correctly"
echo "   • Show status bar with CPU/Memory/Network"
echo "   • Use 50k scrollback buffer (M3-optimized)"
echo "   • Apply Catppuccin Mocha color scheme"
echo ""

