#!/bin/bash
set -euo pipefail

# SQLite restore script with integrity verification and pre-restore safety copy
# Usage: bash restore_db.sh <backup_file> [target_db_path]

if [[ $# -lt 1 ]]; then
    echo "Usage: bash restore_db.sh <backup_file> [target_db_path]"
    exit 1
fi

BACKUP_FILE="$1"
TARGET_DB="${2:-./nets.db}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Starting SQLite restore"
log "Backup file: $BACKUP_FILE"
log "Target database: $TARGET_DB"

# Verify backup file exists
if [[ ! -f "$BACKUP_FILE" ]]; then
    log "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Verify sqlite3 is available
if ! command -v sqlite3 &> /dev/null; then
    log "ERROR: sqlite3 command not found"
    exit 1
fi

# Create target directory if it doesn't exist
TARGET_DIR="$(dirname "$TARGET_DB")"
mkdir -p "$TARGET_DIR"

# Handle gzipped backup
TEMP_BACKUP="$BACKUP_FILE"
if [[ "$BACKUP_FILE" == *.gz ]]; then
    log "Decompressing gzipped backup..."
    TEMP_BACKUP="${TARGET_DIR}/.restore_temp_$(date +%s).db"
    if ! gunzip -c "$BACKUP_FILE" > "$TEMP_BACKUP" 2>&1; then
        log "ERROR: Failed to decompress backup file"
        rm -f "$TEMP_BACKUP"
        exit 1
    fi
    log "Decompressed to temporary file: $TEMP_BACKUP"
fi

# Create safety copy if target exists
if [[ -f "$TARGET_DB" ]]; then
    SAFETY_COPY="${TARGET_DB}.pre-restore-$(date +%s)"
    log "Target database exists, creating safety copy: $SAFETY_COPY"
    if ! cp "$TARGET_DB" "$SAFETY_COPY" 2>&1; then
        log "ERROR: Failed to create safety copy"
        rm -f "$TEMP_BACKUP"
        exit 1
    fi
    log "Safety copy created successfully"
fi

# Copy or move backup into place
log "Restoring backup to target location..."
if ! cp "$TEMP_BACKUP" "$TARGET_DB" 2>&1; then
    log "ERROR: Failed to restore backup"
    rm -f "$TEMP_BACKUP"
    exit 1
fi

# Clean up temporary file if it was created
if [[ "$TEMP_BACKUP" != "$BACKUP_FILE" ]]; then
    rm -f "$TEMP_BACKUP"
fi

log "Restore file copied to target"

# Verify database integrity
log "Verifying database integrity..."
INTEGRITY_CHECK=$(sqlite3 "$TARGET_DB" "PRAGMA integrity_check" 2>&1)
if [[ "$INTEGRITY_CHECK" == "ok" ]]; then
    log "Integrity check PASSED"
    log "Restore completed successfully"
else
    log "ERROR: Integrity check FAILED"
    log "Integrity check output: $INTEGRITY_CHECK"
    if [[ -f "${TARGET_DB}.pre-restore-"* ]]; then
        LATEST_SAFETY=$(ls -t "${TARGET_DB}.pre-restore-"* 2>/dev/null | head -1)
        log "Safety copy available at: $LATEST_SAFETY"
    fi
    exit 1
fi
