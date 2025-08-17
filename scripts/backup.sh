#!/bin/bash
#
# DHK Align Backup Automation Script
# Production-grade backup system with rotation, verification, and alerting
#
# Usage:
#   ./backup.sh daily    # Daily backup
#   ./backup.sh weekly   # Weekly backup
#   ./backup.sh manual   # Manual backup with custom suffix
#

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# =============================================================================
# CONFIGURATION - Modify paths for your environment
# =============================================================================

# Project directories
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${PROJECT_ROOT}/data"
BACKUP_DIR="${PROJECT_ROOT}/backups"
SCRIPTS_DIR="${PROJECT_ROOT}/scripts"

# Database and dataset files
DB_FILE="${DATA_DIR}/dhk_align.db"
CSV_FILE="${DATA_DIR}/combined_dataset_final_sequential.csv"

# Backup retention (number of backups to keep)
DAILY_RETENTION=7      # Keep 7 daily backups
WEEKLY_RETENTION=4     # Keep 4 weekly backups
MANUAL_RETENTION=10    # Keep 10 manual backups

# Notification settings (optional)
ENABLE_EMAIL_ALERTS=false
ALERT_EMAIL="admin@dhkalign.com"
LOG_FILE="${BACKUP_DIR}/backup.log"

# Cloud backup settings (optional - set to true to enable)
ENABLE_CLOUD_BACKUP=false
CLOUD_PROVIDER="s3"  # Options: s3, dropbox, gdrive
S3_BUCKET="dhk-align-backups"
S3_PREFIX="production"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR" "$1"
    send_alert "BACKUP FAILED" "$1"
    exit 1
}

send_alert() {
    local subject="$1"
    local message="$2"
    
    if [[ "$ENABLE_EMAIL_ALERTS" == "true" ]]; then
        echo "$message" | mail -s "DHK Align: $subject" "$ALERT_EMAIL" 2>/dev/null || true
    fi
    
    # macOS notification (if available)
    if command -v osascript >/dev/null 2>&1; then
        osascript -e "display notification \"$message\" with title \"DHK Align Backup\"" 2>/dev/null || true
    fi
}

# =============================================================================
# BACKUP FUNCTIONS
# =============================================================================

create_backup_dir() {
    mkdir -p "$BACKUP_DIR"
    if [[ ! -w "$BACKUP_DIR" ]]; then
        error_exit "Backup directory not writable: $BACKUP_DIR"
    fi
}

verify_source_files() {
    if [[ ! -f "$DB_FILE" ]]; then
        error_exit "Database file not found: $DB_FILE"
    fi
    
    if [[ ! -f "$CSV_FILE" ]]; then
        log "WARN" "CSV file not found: $CSV_FILE (skipping CSV backup)"
    fi
}

create_database_backup() {
    local backup_type="$1"
    local timestamp="$2"
    local backup_db="${BACKUP_DIR}/${backup_type}_${timestamp}.db"
    
    log "INFO" "Creating database backup: $(basename "$backup_db")"
    
    # Use SQLite's .backup command for consistency
    sqlite3 "$DB_FILE" ".backup '$backup_db'" || error_exit "Database backup failed"
    
    # Verify backup integrity
    sqlite3 "$backup_db" "PRAGMA integrity_check;" | grep -q "ok" || error_exit "Backup integrity check failed"
    
    # Compress backup (optional)
    gzip "$backup_db" || error_exit "Backup compression failed"
    
    log "INFO" "Database backup completed: $(basename "$backup_db").gz"
    echo "${backup_db}.gz"
}

create_csv_backup() {
    local backup_type="$1"
    local timestamp="$2"
    local backup_csv="${BACKUP_DIR}/${backup_type}_${timestamp}.csv"
    
    if [[ -f "$CSV_FILE" ]]; then
        log "INFO" "Creating CSV backup: $(basename "$backup_csv")"
        cp "$CSV_FILE" "$backup_csv" || error_exit "CSV backup failed"
        gzip "$backup_csv" || error_exit "CSV compression failed"
        log "INFO" "CSV backup completed: $(basename "$backup_csv").gz"
        echo "${backup_csv}.gz"
    fi
}

create_metadata_file() {
    local backup_type="$1"
    local timestamp="$2"
    local metadata_file="${BACKUP_DIR}/${backup_type}_${timestamp}_metadata.json"
    
    # Get database statistics
    local db_size=$(stat -f%z "$DB_FILE" 2>/dev/null || stat -c%s "$DB_FILE" 2>/dev/null || echo "unknown")
    local csv_size="unknown"
    if [[ -f "$CSV_FILE" ]]; then
        csv_size=$(stat -f%z "$CSV_FILE" 2>/dev/null || stat -c%s "$CSV_FILE" 2>/dev/null || echo "unknown")
    fi
    
    # Create metadata JSON
    cat > "$metadata_file" << EOF
{
    "backup_type": "$backup_type",
    "timestamp": "$timestamp",
    "created_at": "$(date -Iseconds)",
    "hostname": "$(hostname)",
    "user": "$(whoami)",
    "project_root": "$PROJECT_ROOT",
    "database": {
        "file": "$DB_FILE",
        "size_bytes": $db_size,
        "backup_file": "${backup_type}_${timestamp}.db.gz"
    },
    "dataset": {
        "file": "$CSV_FILE",
        "size_bytes": $csv_size,
        "backup_file": "${backup_type}_${timestamp}.csv.gz"
    },
    "git_commit": "$(cd "$PROJECT_ROOT" && git rev-parse HEAD 2>/dev/null || echo 'not_a_git_repo')"
}
EOF
    
    log "INFO" "Metadata file created: $(basename "$metadata_file")"
    echo "$metadata_file"
}

upload_to_cloud() {
    local backup_files=("$@")
    
    if [[ "$ENABLE_CLOUD_BACKUP" != "true" ]]; then
        return 0
    fi
    
    log "INFO" "Uploading backups to cloud storage ($CLOUD_PROVIDER)"
    
    case "$CLOUD_PROVIDER" in
        "s3")
            for file in "${backup_files[@]}"; do
                local filename=$(basename "$file")
                aws s3 cp "$file" "s3://${S3_BUCKET}/${S3_PREFIX}/${filename}" || error_exit "S3 upload failed: $filename"
            done
            ;;
        "dropbox")
            # Requires dropbox_uploader.sh (https://github.com/andreafabrizi/Dropbox-Uploader)
            for file in "${backup_files[@]}"; do
                local filename=$(basename "$file")
                "$SCRIPTS_DIR/dropbox_uploader.sh" upload "$file" "dhk-align-backups/$filename" || error_exit "Dropbox upload failed: $filename"
            done
            ;;
        "gdrive")
            # Requires gdrive CLI tool
            for file in "${backup_files[@]}"; do
                gdrive upload --parent "dhk-align-backups-folder-id" "$file" || error_exit "Google Drive upload failed: $file"
            done
            ;;
        *)
            log "WARN" "Unknown cloud provider: $CLOUD_PROVIDER"
            ;;
    esac
    
    log "INFO" "Cloud upload completed"
}

cleanup_old_backups() {
    local backup_type="$1"
    local retention_count="$2"
    
    log "INFO" "Cleaning up old $backup_type backups (keeping $retention_count)"
    
    # Remove old database backups
    ls -t "${BACKUP_DIR}/${backup_type}_"*.db.gz 2>/dev/null | tail -n +$((retention_count + 1)) | xargs rm -f
    
    # Remove old CSV backups
    ls -t "${BACKUP_DIR}/${backup_type}_"*.csv.gz 2>/dev/null | tail -n +$((retention_count + 1)) | xargs rm -f
    
    # Remove old metadata files
    ls -t "${BACKUP_DIR}/${backup_type}_"*_metadata.json 2>/dev/null | tail -n +$((retention_count + 1)) | xargs rm -f
    
    log "INFO" "Cleanup completed for $backup_type backups"
}

# =============================================================================
# MAIN BACKUP FUNCTION
# =============================================================================

perform_backup() {
    local backup_type="$1"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_files=()
    
    log "INFO" "Starting $backup_type backup (timestamp: $timestamp)"
    
    # Create backup directory
    create_backup_dir
    
    # Verify source files exist
    verify_source_files
    
    # Create database backup
    local db_backup
    db_backup=$(create_database_backup "$backup_type" "$timestamp")
    backup_files+=("$db_backup")
    
    # Create CSV backup (if file exists)
    local csv_backup
    csv_backup=$(create_csv_backup "$backup_type" "$timestamp")
    if [[ -n "$csv_backup" ]]; then
        backup_files+=("$csv_backup")
    fi
    
    # Create metadata file
    local metadata_file
    metadata_file=$(create_metadata_file "$backup_type" "$timestamp")
    backup_files+=("$metadata_file")
    
    # Upload to cloud (if enabled)
    upload_to_cloud "${backup_files[@]}"
    
    # Cleanup old backups based on type
    case "$backup_type" in
        "daily")
            cleanup_old_backups "$backup_type" "$DAILY_RETENTION"
            ;;
        "weekly")
            cleanup_old_backups "$backup_type" "$WEEKLY_RETENTION"
            ;;
        "manual")
            cleanup_old_backups "$backup_type" "$MANUAL_RETENTION"
            ;;
    esac
    
    log "INFO" "$backup_type backup completed successfully"
    send_alert "BACKUP SUCCESS" "$backup_type backup completed at $timestamp"
    
    # Display backup summary
    echo
    echo "=== BACKUP SUMMARY ==="
    echo "Type: $backup_type"
    echo "Timestamp: $timestamp"
    echo "Files created:"
    for file in "${backup_files[@]}"; do
        echo "  - $(basename "$file")"
    done
    echo "Location: $BACKUP_DIR"
    echo
}

# =============================================================================
# RESTORE FUNCTIONS
# =============================================================================

list_backups() {
    echo "Available backups in $BACKUP_DIR:"
    echo
    
    if [[ -n "$(ls "$BACKUP_DIR"/*.db.gz 2>/dev/null)" ]]; then
        echo "Database backups:"
        ls -lh "$BACKUP_DIR"/*.db.gz | awk '{print "  " $9 " (" $5 ", " $6 " " $7 ")"}'
        echo
    fi
    
    if [[ -n "$(ls "$BACKUP_DIR"/*.csv.gz 2>/dev/null)" ]]; then
        echo "CSV backups:"
        ls -lh "$BACKUP_DIR"/*.csv.gz | awk '{print "  " $9 " (" $5 ", " $6 " " $7 ")"}'
        echo
    fi
    
    if [[ -n "$(ls "$BACKUP_DIR"/*_metadata.json 2>/dev/null)" ]]; then
        echo "Metadata files:"
        ls -lh "$BACKUP_DIR"/*_metadata.json | awk '{print "  " $9 " (" $5 ", " $6 " " $7 ")"}'
    fi
}

# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

main() {
    # Initialize log file
    touch "$LOG_FILE"
    
    case "${1:-}" in
        "daily")
            perform_backup "daily"
            ;;
        "weekly")
            perform_backup "weekly"
            ;;
        "manual")
            perform_backup "manual"
            ;;
        "list")
            list_backups
            ;;
        "help"|"-h"|"--help")
            cat << EOF
DHK Align Backup Automation Script

Usage:
  $0 daily              Create daily backup
  $0 weekly             Create weekly backup  
  $0 manual             Create manual backup
  $0 list               List available backups
  $0 help               Show this help message

Configuration:
  Edit the CONFIGURATION section at the top of this script to customize:
  - Backup directories and file paths
  - Retention policies
  - Cloud storage settings
  - Email alert settings

Examples:
  $0 daily              # Run daily backup
  $0 weekly             # Run weekly backup
  $0 list               # See all available backups

Automation:
  Add to crontab for automatic backups:
  # Daily backup at 2 AM
  0 2 * * * $PWD/$0 daily
  
  # Weekly backup on Sunday at 3 AM  
  0 3 * * 0 $PWD/$0 weekly

EOF
            ;;
        *)
            echo "Error: Invalid or missing argument"
            echo "Usage: $0 {daily|weekly|manual|list|help}"
            echo "Run '$0 help' for more information"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"