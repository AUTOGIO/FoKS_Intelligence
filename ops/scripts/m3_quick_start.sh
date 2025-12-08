#!/usr/bin/env bash
################################################################################
# M3 Quick Start: Apply All Best Practices
# Run this ONCE after pulling the latest changes
# macOS 26 Beta, iMac M3
################################################################################
set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=== M3 Best Practices: Quick Start ===${NC}"
echo ""

# 1. Create log directory
echo -e "${BLUE}[1/6] Creating log directory...${NC}"
mkdir -p "$HOME/Library/Logs/FoKS"
chmod 700 "$HOME/Library/Logs/FoKS"
echo -e "${GREEN}✓ Created ~/Library/Logs/FoKS${NC}"
echo ""

# 2. Make scripts executable
echo -e "${BLUE}[2/6] Making scripts executable...${NC}"
chmod +x "$HOME/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/fbp_boot.sh" 2>/dev/null || echo -e "${YELLOW}Warning: fbp_boot.sh not found${NC}"
chmod +x "$HOME/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/m3_system_dashboard.sh" 2>/dev/null || echo -e "${YELLOW}Warning: m3_system_dashboard.sh not found${NC}"
chmod +x "$HOME/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/verify_m3_setup.sh" 2>/dev/null || echo -e "${YELLOW}Warning: verify_m3_setup.sh not found${NC}"
echo -e "${GREEN}✓ Scripts are now executable${NC}"
echo ""

# 3. Install uvloop (FoKS)
echo -e "${BLUE}[3/6] Installing uvloop in FoKS venv...${NC}"
FOKS_VENV="$HOME/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/.venv_foks"
if [[ -d "$FOKS_VENV" ]]; then
  source "$FOKS_VENV/bin/activate"
  if pip install uvloop >/dev/null 2>&1; then
    echo -e "${GREEN}✓ uvloop installed in FoKS${NC}"
  else
    echo -e "${YELLOW}Warning: Failed to install uvloop in FoKS${NC}"
  fi
  deactivate
else
  echo -e "${YELLOW}Warning: FoKS venv not found at $FOKS_VENV${NC}"
fi
echo ""

# 4. Install uvloop (FBP)
echo -e "${BLUE}[4/6] Installing uvloop in FBP venv...${NC}"
FBP_VENV="$HOME/Documents/.venvs/fbp"
if [[ -d "$FBP_VENV" ]]; then
  source "$FBP_VENV/bin/activate"
  if pip install uvloop >/dev/null 2>&1; then
    echo -e "${GREEN}✓ uvloop installed in FBP${NC}"
  else
    echo -e "${YELLOW}Warning: Failed to install uvloop in FBP${NC}"
  fi
  deactivate
else
  echo -e "${YELLOW}Warning: FBP venv not found at $FBP_VENV${NC}"
fi
echo ""

# 5. Register launchd agents
echo -e "${BLUE}[5/6] Registering launchd agents...${NC}"
FOKS_PLIST="$HOME/Library/LaunchAgents/com.foks.bootstrap.plist"
FBP_PLIST="$HOME/Library/LaunchAgents/com.fbp.bootstrap.plist"

cp "$HOME/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/launchd/com.foks.bootstrap.optimized.plist" "$FOKS_PLIST" 2>/dev/null || echo -e "${YELLOW}Warning: Could not copy FoKS plist${NC}"
cp "$HOME/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/launchd/com.fbp.bootstrap.optimized.plist" "$FBP_PLIST" 2>/dev/null || echo -e "${YELLOW}Warning: Could not copy FBP plist${NC}"

chmod 644 "$FOKS_PLIST" "$FBP_PLIST" 2>/dev/null || true

echo -e "${GREEN}✓ launchd plists registered${NC}"
echo ""

# 6. Load services
echo -e "${BLUE}[6/6] Loading launchd services (this may prompt for password)...${NC}"
echo ""

echo "Loading FoKS..."
if launchctl load -w "$FOKS_PLIST" 2>/dev/null; then
  echo -e "${GREEN}✓ FoKS loaded${NC}"
else
  echo -e "${YELLOW}Note: FoKS service loading returned status (may already be loaded)${NC}"
fi

echo "Loading FBP..."
if launchctl load -w "$FBP_PLIST" 2>/dev/null; then
  echo -e "${GREEN}✓ FBP loaded${NC}"
else
  echo -e "${YELLOW}Note: FBP service loading returned status (may already be loaded)${NC}"
fi

echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Verify setup:"
echo "     bash ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/verify_m3_setup.sh"
echo ""
echo "  2. View system health:"
echo "     bash ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/m3_system_dashboard.sh"
echo ""
echo "  3. Monitor logs:"
echo "     tail -f ~/Library/Logs/FoKS/com.foks.bootstrap.out.log"
echo "     tail -f ~/Library/Logs/FoKS/com.fbp.bootstrap.out.log"
echo ""
echo "  4. Read the full guide:"
echo "     cat ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/docs/M3_OPTIMIZATION_GUIDE.md"
echo ""
