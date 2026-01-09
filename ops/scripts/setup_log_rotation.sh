#!/usr/bin/env bash
# Setup automatic log rotation via launchd

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FOKS_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLIST_SOURCE="$FOKS_DIR/ops/launchd/com.foks.logrotation.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.foks.logrotation.plist"
SERVICE_LABEL="com.foks.logrotation"

echo "[FoKS] Setting up automatic log rotation..."

# Check if plist source exists
if [ ! -f "$PLIST_SOURCE" ]; then
    echo "[FoKS] ❌ Error: Plist source not found: $PLIST_SOURCE"
    exit 1
fi

# Check if service is already loaded
if launchctl list "$SERVICE_LABEL" &>/dev/null; then
    echo "[FoKS] Service already loaded. Unloading first..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Copy plist to LaunchAgents
echo "[FoKS] Copying plist to LaunchAgents..."
cp "$PLIST_SOURCE" "$PLIST_DEST"
echo "[FoKS] ✅ Plist copied to: $PLIST_DEST"

# Load the service
echo "[FoKS] Loading launchd service..."
if launchctl load "$PLIST_DEST"; then
    echo "[FoKS] ✅ Service loaded successfully"
else
    echo "[FoKS] ❌ Failed to load service"
    exit 1
fi

# Verify installation
echo ""
echo "[FoKS] Verifying installation..."
if launchctl list "$SERVICE_LABEL" &>/dev/null; then
    echo "[FoKS] ✅ Service is active"
    echo ""
    echo "[FoKS] Service status:"
    launchctl list "$SERVICE_LABEL" | head -5
else
    echo "[FoKS] ⚠️  Service may not be active yet (will activate at scheduled time)"
fi

echo ""
echo "[FoKS] ✅ Log rotation automation configured"
echo "[FoKS] Rotation will run daily at 23:30"
echo ""
echo "[FoKS] Logs will be written to:"
echo "  - Rotation log: /Users/dnigga/Library/Logs/FoKS/log_rotation.log"
echo "  - Service stdout: /Users/dnigga/Library/Logs/FoKS/com.foks.logrotation.out.log"
echo "  - Service stderr: /Users/dnigga/Library/Logs/FoKS/com.foks.logrotation.err.log"
echo ""
echo "[FoKS] To manage the service:"
echo "  - Check status: launchctl list $SERVICE_LABEL"
echo "  - Unload: launchctl unload $PLIST_DEST"
echo "  - Reload: launchctl unload $PLIST_DEST && launchctl load $PLIST_DEST"
