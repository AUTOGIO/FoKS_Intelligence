#!/usr/bin/env bash
# FoKS Intelligence - Log Backup Script
# Backs up important log files

set -e

PROJECT_ROOT="/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence"
LOG_DIR="$PROJECT_ROOT/logs"
BACKUP_DIR="$PROJECT_ROOT/backups/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "📦 Backing up logs..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup current log file
if [ -f "$LOG_DIR/app.log" ]; then
    cp "$LOG_DIR/app.log" "$BACKUP_DIR/app_${TIMESTAMP}.log"
    echo "✅ Backed up app.log"
fi

# Backup log history
if [ -d "$LOG_DIR/history" ]; then
    tar -czf "$BACKUP_DIR/history_${TIMESTAMP}.tar.gz" -C "$LOG_DIR" history/
    echo "✅ Backed up log history"
fi

# Backup deploy logs
if [ -f "$LOG_DIR/deploy.log" ]; then
    cp "$LOG_DIR/deploy.log" "$BACKUP_DIR/deploy_${TIMESTAMP}.log"
    echo "✅ Backed up deploy.log"
fi

# Clean old backups (keep last 30 days)
find "$BACKUP_DIR" -name "*.log" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo "✅ Log backup completed"
echo "Backup location: $BACKUP_DIR"

