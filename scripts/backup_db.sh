#!/bin/bash
set -euo pipefail

# SQLite online backup script with gzip compression and 14-day retention
# Usage: bash backup_db.sh [database_path] [backup_directory]

DB="${1:-./nets.db}"
BACKUP_DIR="${2:-./backups/}"

# Normalize paths
DB="$(cd "$(dirname "$DB")" && pwd)/$(basename "$DB")"
BACKUP_DIR="$(mkdir -p "$BACKUP_DIR" && cd "$BACKUP_DIR" && pwd)/"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Starting SQLite backup"
log "Database: $DB"
log "Backup directory: $BACKUP_DIR"

# Verify database file exists
if [[ ! -f "$DB" ]]; then
    log "ERROR: Database file not found: $DB"
    exit 1
fi

# Verify sqlite3 is available
if ! command -v sqlite3 &> /dev/null; then
    log "ERROR: sqlite3 command not found"
    exit 1
fi

# Create backup filename with timestamp
BACKUP_FILE="${BACKUP_DIR}nets-$(date +%Y%m%d-%H%M%S).db"

# Perform online backup
log "Creating backup: $BACKUP_FILE"
if sqlite3 "$DB" ".backup '$BACKUP_FILE'" 2>&1; then
    log "Backup created successfully"
else
    log "ERROR: Backup failed"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Verify backup file was created and has content
if [[ ! -f "$BACKUP_FILE" ]] || [[ ! -s "$BACKUP_FILE" ]]; then
    log "ERROR: Backup file is empty or missing"
    exit 1
fi

# Compress the backup
log "Compressing backup..."
if gzip -f "$BACKUP_FILE" 2>&1; then
    BACKUP_FILE="${BACKUP_FILE}.gz"
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Backup compressed: $BACKUP_FILE ($BACKUP_SIZE)"
else
    log "ERROR: Compression failed"
    exit 1
fi

# Clean up backups older than 14 days
log "Cleaning up backups older than 14 days..."
DELETED_COUNT=$(find "$BACKUP_DIR" -name "nets-*.db.gz" -mtime +14 -print -delete 2>/dev/null | wc -l | tr -d ' ')
log "Deleted $DELETED_COUNT old backup files"

log "Backup completed successfully"
