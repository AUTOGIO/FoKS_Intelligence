#!/usr/bin/env bash
################################################################################
# M3 Quick Setup & Verification Script
# Run this to verify all best-practices are in place
# macOS 26 Beta, iMac M3 (8 cores, 16 GB)
################################################################################
set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== M3 Best Practices Verification ===${NC}"
echo ""

# 1. Check uvloop
echo -e "${BLUE}1. Checking uvloop...${NC}"
if python3 -c "import uvloop; print(f'uvloop {uvloop.__version__}')" 2>/dev/null; then
  echo -e "${GREEN}✓ uvloop installed${NC}"
else
  echo -e "${RED}✗ uvloop NOT found${NC}"
  echo -e "${YELLOW}  Run: pip install uvloop (in each venv)${NC}"
fi
echo ""

# 2. Check launchd agents
echo -e "${BLUE}2. Checking launchd agents...${NC}"
if launchctl list | grep -q com.foks.bootstrap; then
  echo -e "${GREEN}✓ com.foks.bootstrap loaded${NC}"
else
  echo -e "${RED}✗ com.foks.bootstrap NOT loaded${NC}"
  echo -e "${YELLOW}  Run: launchctl load -w ~/Library/LaunchAgents/com.foks.bootstrap.plist${NC}"
fi

if launchctl list | grep -q com.fbp.bootstrap; then
  echo -e "${GREEN}✓ com.fbp.bootstrap loaded${NC}"
else
  echo -e "${RED}✗ com.fbp.bootstrap NOT loaded${NC}"
  echo -e "${YELLOW}  Run: launchctl load -w ~/Library/LaunchAgents/com.fbp.bootstrap.plist${NC}"
fi
echo ""

# 3. Check log directory
echo -e "${BLUE}3. Checking log directory...${NC}"
if [[ -d "$HOME/Library/Logs/FoKS" ]]; then
  echo -e "${GREEN}✓ ~/Library/Logs/FoKS exists${NC}"
  ls -lah "$HOME/Library/Logs/FoKS/" | tail -5
else
  echo -e "${RED}✗ ~/Library/Logs/FoKS NOT found${NC}"
  echo -e "${YELLOW}  Run: mkdir -p ~/Library/Logs/FoKS && chmod 700 ~/Library/Logs/FoKS${NC}"
fi
echo ""

# 4. Check M3 optimization module
echo -e "${BLUE}4. Checking M3 optimization module...${NC}"
M3_MODULE="$HOME/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/app/config/m3_optimization.py"
if [[ -f "$M3_MODULE" ]]; then
  echo -e "${GREEN}✓ m3_optimization.py exists${NC}"
  python3 "$M3_MODULE" 2>/dev/null | head -10
else
  echo -e "${RED}✗ m3_optimization.py NOT found${NC}"
fi
echo ""

# 5. Health check endpoints
echo -e "${BLUE}5. Checking service endpoints...${NC}"

echo -n "  FoKS /health: "
if curl -s --max-time 2 http://127.0.0.1:8001/health >/dev/null 2>&1; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${YELLOW}? (service may not be running)${NC}"
fi

echo -n "  FBP socket-health: "
FBP_TRANSPORT="${FBP_TRANSPORT:-socket}"
FBP_SOCKET_PATH="${FBP_SOCKET_PATH:-/tmp/fbp.sock}"
FBP_PORT="${FBP_PORT:-8000}"
if [[ "$FBP_TRANSPORT" == "socket" ]]; then
  if curl --unix-socket "$FBP_SOCKET_PATH" -s --max-time 2 http://localhost/socket-health >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
  else
    echo -e "${YELLOW}? (service may not be running)${NC}"
  fi
else
  if curl -s --max-time 2 "http://127.0.0.1:${FBP_PORT}/socket-health" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
  else
    echo -e "${YELLOW}? (service may not be running)${NC}"
  fi
fi

echo -n "  LM Studio /v1/models: "
if curl -s --max-time 2 http://127.0.0.1:1234/v1/models >/dev/null 2>&1; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${YELLOW}? (LM Studio not running)${NC}"
fi

echo ""

# 6. System resources
echo -e "${BLUE}6. System Resources (M3 iMac)...${NC}"
echo -n "  Total RAM: "
sysctl -n hw.memsize | awk '{printf "%.1f GB\n", $1 / 1024^3}'
echo -n "  Available RAM: "
vm_stat | grep 'Pages free' | awk '{printf "%.1f GB (est.)\n", $3 * 4096 / 1024^3}'
echo -n "  CPU Load: "
uptime | grep -o 'load average[^,]*'
echo ""

# 7. Process check
echo -e "${BLUE}7. Running Processes...${NC}"
echo -n "  FoKS: "
if pgrep -f 'uvicorn.*app.main' | head -1 | xargs -I {} sh -c 'ps -p {} -o comm= 2>/dev/null || echo "not found"' | grep -q .; then
  echo -e "${GREEN}✓ Running${NC}"
else
  echo -e "${RED}✗ Not running${NC}"
fi

echo -n "  LM Studio: "
if pgrep -i lmstudio >/dev/null 2>&1; then
  echo -e "${GREEN}✓ Running${NC}"
else
  echo -e "${YELLOW}? Not detected${NC}"
fi

echo ""

# 8. File permissions
echo -e "${BLUE}8. File Permissions...${NC}"
echo -n "  fbp_boot.sh: "
if [[ -x "$HOME/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/fbp_boot.sh" ]]; then
  echo -e "${GREEN}✓ executable${NC}"
else
  echo -e "${RED}✗ NOT executable${NC}"
  echo -e "${YELLOW}  Run: chmod +x ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/fbp_boot.sh${NC}"
fi

echo -n "  foks_boot.sh: "
if [[ -x "$HOME/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/foks_boot.sh" ]]; then
  echo -e "${GREEN}✓ executable${NC}"
else
  echo -e "${RED}✗ NOT executable${NC}"
  echo -e "${YELLOW}  Run: chmod +x ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/foks_boot.sh${NC}"
fi

echo ""
echo -e "${BLUE}=== Verification Complete ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Review: cat ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/docs/M3_OPTIMIZATION_GUIDE.md"
echo "  2. Start services: bash ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/scripts/m3_system_dashboard.sh"
echo "  3. Monitor logs: tail -f ~/Library/Logs/FoKS/com.foks.bootstrap.out.log"
echo ""
