#!/usr/bin/env bash
################################################################################
# Apply M3 Optimization Changes
# 
# This script automates the migration from old boot scripts/plists to
# optimized versions for iMac M3 (8 cores: 4P+4E, 16 GB RAM, macOS 26 beta).
#
# What it does:
#  1. Backs up current launchd agents
#  2. Creates log directory
#  3. Unloads old agents
#  4. Makes new boot scripts executable
#  5. Installs new plists
#  6. Loads new agents
#  7. Verifies they're running
################################################################################
set -euo pipefail

echo "=" 
echo "= M3 Optimization Script"
echo "= iMac M3 (8 cores: 4P+4E, 16 GB RAM, macOS 26 beta)"
echo "="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/Library/Logs/FoKS"

################################################################################
# Color output
################################################################################
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
NC=$'\033[0m'  # No Color

echo_info() {
  echo -e "${BLUE}[INFO]${NC} $*"
}

echo_warn() {
  echo -e "${YELLOW}[WARN]${NC} $*"
}

echo_error() {
  echo -e "${RED}[ERROR]${NC} $*"
}

echo_success() {
  echo -e "${GREEN}[OK]${NC} $*"
}

################################################################################
# Step 1: Backup current launchd agents
################################################################################
echo_info "Step 1: Backing up current launchd agents..."

BACKUP_DIR="$LAUNCH_AGENTS/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [[ -f "$LAUNCH_AGENTS/com.foks.bootstrap.plist" ]]; then
  cp "$LAUNCH_AGENTS/com.foks.bootstrap.plist" "$BACKUP_DIR/"
  echo_success "Backed up com.foks.bootstrap.plist to $BACKUP_DIR"
else
  echo_warn "com.foks.bootstrap.plist not found (may not be installed)"
fi

if [[ -f "$LAUNCH_AGENTS/com.fbp.bootstrap.plist" ]]; then
  cp "$LAUNCH_AGENTS/com.fbp.bootstrap.plist" "$BACKUP_DIR/"
  echo_success "Backed up com.fbp.bootstrap.plist to $BACKUP_DIR"
else
  echo_warn "com.fbp.bootstrap.plist not found (may not be installed)"
fi

################################################################################
# Step 2: Create log directory
################################################################################
echo_info "Step 2: Creating log directory..."

mkdir -p "$LOG_DIR"
chmod 700 "$LOG_DIR"
echo_success "Log directory: $LOG_DIR"

################################################################################
# Step 3: Unload old agents
################################################################################
echo_info "Step 3: Unloading old launchd agents..."

if launchctl list | grep -q com.foks.bootstrap; then
  echo_warn "Unloading com.foks.bootstrap..."
  launchctl unload "$LAUNCH_AGENTS/com.foks.bootstrap.plist" || echo_warn "Could not unload (may be harmless)"
else
  echo_warn "com.foks.bootstrap not currently loaded"
fi

if launchctl list | grep -q com.fbp.bootstrap; then
  echo_warn "Unloading com.fbp.bootstrap..."
  launchctl unload "$LAUNCH_AGENTS/com.fbp.bootstrap.plist" || echo_warn "Could not unload (may be harmless)"
else
  echo_warn "com.fbp.bootstrap not currently loaded"
fi

sleep 2
echo_success "Agents unloaded"

################################################################################
# Step 4: Make boot scripts executable
################################################################################
echo_info "Step 4: Making boot scripts executable..."

chmod +x "$SCRIPT_DIR/foks_boot_optimized.sh"
chmod +x "$SCRIPT_DIR/fbp_boot_optimized.sh"
echo_success "Boot scripts are executable"

################################################################################
# Step 5: Copy optimized plists to LaunchAgents
################################################################################
echo_info "Step 5: Installing optimized launchd agents..."

cp "$PROJECT_ROOT/ops/launchd/com.foks.bootstrap.optimized.plist" \
   "$LAUNCH_AGENTS/com.foks.bootstrap.plist"
chmod 644 "$LAUNCH_AGENTS/com.foks.bootstrap.plist"
echo_success "Installed com.foks.bootstrap.plist"

cp "$PROJECT_ROOT/ops/launchd/com.fbp.bootstrap.optimized.plist" \
   "$LAUNCH_AGENTS/com.fbp.bootstrap.plist"
chmod 644 "$LAUNCH_AGENTS/com.fbp.bootstrap.plist"
echo_success "Installed com.fbp.bootstrap.plist"

################################################################################
# Step 6: Load new agents
################################################################################
echo_info "Step 6: Loading new launchd agents..."

launchctl load "$LAUNCH_AGENTS/com.foks.bootstrap.plist"
echo_success "Loaded com.foks.bootstrap.plist"

launchctl load "$LAUNCH_AGENTS/com.fbp.bootstrap.plist"
echo_success "Loaded com.fbp.bootstrap.plist"

sleep 3

################################################################################
# Step 7: Verify agents are loaded and running
################################################################################
echo_info "Step 7: Verifying agents..."

echo ""
echo "=== Loaded Launch Agents ==="
launchctl list | grep -E "com\.foks|com\.fbp" || echo_warn "No FoKS/FBP agents found in launchctl list"

echo ""
echo "=== FoKS Backend Health ==="
if curl --silent --max-time 2 http://127.0.0.1:8000/health >/dev/null 2>&1; then
  echo_success "FoKS backend is responding on port 8000"
  curl --silent http://127.0.0.1:8000/health | jq . 2>/dev/null || echo "(health endpoint returned data)"
else
  echo_warn "FoKS backend not yet responding on port 8000 (may still be starting)"
fi

echo ""
echo "=== FBP Backend Health ==="
if curl --silent --max-time 2 http://127.0.0.1:8001/health >/dev/null 2>&1; then
  echo_success "FBP backend is responding on port 8001"
  curl --silent http://127.0.0.1:8001/health | jq . 2>/dev/null || echo "(health endpoint returned data)"
else
  echo_warn "FBP backend not yet responding on port 8001 (may still be starting or on port 8000)"
fi

echo ""
echo "=== Log Files ==="
if [[ -f "$LOG_DIR/com.foks.bootstrap.out.log" ]]; then
  echo_success "FoKS stdout log: $LOG_DIR/com.foks.bootstrap.out.log"
  echo "  Last 5 lines:"
  tail -5 "$LOG_DIR/com.foks.bootstrap.out.log" | sed 's/^/    /'
else
  echo_warn "FoKS stdout log not yet created"
fi

echo ""
echo "=== Memory Usage ==="
top -l 1 | grep PhysMem

################################################################################
# Final summary
################################################################################
echo ""
echo "==============================================================================="
echo "M3 Optimization Migration Complete!"
echo "==============================================================================="
echo ""
echo "What changed:"
echo "  1. Boot scripts: now use uvloop, single worker, M3-optimized"
echo "  2. Launch agents: follow Apple macOS 15+ best practices"
echo "  3. Logging: goes to ~/Library/Logs/FoKS/ (not in project)"
echo "  4. Resource limits: soft limits on memory/files in launchd"
echo ""
echo "Next steps:"
echo "  1. Check logs: tail -f $LOG_DIR/com.foks.bootstrap.out.log"
echo "  2. Monitor memory in Activity Monitor.app"
echo "  3. Verify LM Studio is using MLX backend"
echo "  4. Test with a chat request: curl http://127.0.0.1:8000/chat"
echo ""
echo "Troubleshooting:"
echo "  - View launchd status: launchctl list | grep com.foks"
echo "  - Reload agent: launchctl unload $LAUNCH_AGENTS/com.foks.bootstrap.plist && launchctl load $LAUNCH_AGENTS/com.foks.bootstrap.plist"
echo "  - Full logs: cat $LOG_DIR/com.foks.bootstrap.out.log"
echo ""
echo "==============================================================================="
