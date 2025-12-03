#!/usr/bin/env bash
# Backup script for FoKS Intelligence database

set -e

PROJECT_ROOT="/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence"
DB_PATH="$PROJECT_ROOT/backend/data/conversations.db"
BACKUP_DIR="$PROJECT_ROOT/backend/data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/conversations_${TIMESTAMP}.db"

echo "[FoKS] Creating database backup..."

mkdir -p "$BACKUP_DIR"

if [ -f "$DB_PATH" ]; then
    cp "$DB_PATH" "$BACKUP_FILE"
    echo "[FoKS] Backup created: $BACKUP_FILE"

    # Keep only last 7 days of backups
    find "$BACKUP_DIR" -name "conversations_*.db" -mtime +7 -delete
    echo "[FoKS] Old backups cleaned up"
else
    echo "[FoKS] WARNING: Database file not found at $DB_PATH"
    exit 1
fi

