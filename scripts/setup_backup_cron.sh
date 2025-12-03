#!/usr/bin/env bash
# Setup automatic database backups via cron

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/backup_database.sh"
CRON_JOB="0 2 * * * $BACKUP_SCRIPT >> $SCRIPT_DIR/../logs/backup.log 2>&1"

echo "[FoKS] Setting up automatic database backups..."

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "backup_database.sh"; then
    echo "[FoKS] Backup cron job already exists"
    crontab -l | grep "backup_database.sh"
else
    # Add cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "[FoKS] Backup cron job added:"
    echo "  $CRON_JOB"
    echo ""
    echo "[FoKS] Current crontab:"
    crontab -l
fi

echo ""
echo "[FoKS] ✅ Backup automation configured"
echo "[FoKS] Backups will run daily at 2:00 AM"

