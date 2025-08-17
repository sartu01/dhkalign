#!/bin/bash
#
# DHK Align Restore Script
# Production-grade restore system with safety checks and verification
#
# Usage:
#   ./restore.sh list                                    # List available backups
#   ./restore.sh database daily_20250118_143022         # Restore specific database backup
#   ./restore.sh csv weekly_20250115_091500              # Restore specific CSV backup
#   ./restore.sh full daily_20250118_143022              # Restore both database and CSV
#

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${PROJECT_ROOT}/data"
BACKUP_DIR="${PROJECT_ROOT}/backups"

# Current production files
DB_FILE="${DATA_DIR}/dhk_align.db"
CSV_FILE="${DATA_DIR}/combined_dataset_final_sequential.csv"

# Safety backup directory for current files
SAFETY_BACKUP_DIR="${BACKUP_DIR}/pre_restore_safety"

LOG_FILE="${BACKUP_DIR}/restore.log"

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
    exit 1
}

confirm_action() {
    local message="$1"
    echo "$message"
    read -p "Type 'yes' to continue: " response
    if [[ "$response" != "yes" ]]; then
        echo "Operation cancelled."
        exit 0
    fi
}

create_safety_backup() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    mkdir -p "$SAFETY_BACKUP_DIR"
    
    log "INFO" "Creating safety backup before restore"
    
    # Backup current database if it exists
    if [[ -f "$DB_FILE" ]]; then
        local safety_db="${SAFETY_BACKUP_DIR}/pre_restore_${timestamp}.db"
        cp "$DB_FILE" "$safety_db"
        gzip "$safety_db"
        log "INFO" "Current database backed up to: $(basename "$safety_db").gz"
    fi
    
    # Backup current CSV if it exists
    if [[ -f "$CSV_FILE" ]]; then
        local safety_csv="${SAFETY_BACKUP_DIR}/pre_restore_${timestamp}.csv"
        cp "$CSV_FILE" "$safety_csv"
        gzip "$safety_csv"
        log "INFO" "Current CSV backed up to: $(basename "$safety_csv").gz"
    fi
}

# =============================================================================
# RESTORE FUNCTIONS
# =============================================================================

list_backups() {
    echo "Available backups in $BACKUP_DIR:"
    echo
    
    # List database backups
    if compgen -G "$BACKUP_DIR/*.db.gz" > /dev/null; then
        echo "Database backups:"
        for backup in "$BACKUP_DIR"/*.db.gz; do
            local basename=$(basename "$backup" .db.gz)
            local size=$(ls -lh "$backup" | awk '{print $5}')
            local date=$(ls -l "$backup" | awk '{print $6, $7, $8}')
            echo "  $basename ($size, $date)"
        done
        echo
    else
        echo "No database backups found."
        echo
    fi
    
    # List CSV backups
    if compgen -G "$BACKUP_DIR/*.csv.gz" > /dev/null; then
        echo "CSV backups:"
        for backup in "$BACKUP_DIR"/*.csv.gz; do
            local basename=$(basename "$backup" .csv.gz)
            local size=$(ls -lh "$backup" | awk '{print $5}')
            local date=$(ls -l "$backup" | awk '{print $6, $7, $8}')
            echo "  $basename ($size, $date)"
        done
        echo
    else
        echo "No CSV backups found."
        echo
    fi
    
    # List metadata files
    if compgen -G "$BACKUP_DIR/*_metadata.json" > /dev/null; then
        echo "Metadata files available for detailed backup information."
        echo
    fi
}

show_backup_info() {
    local backup_id="$1"
    local metadata_file="${BACKUP_DIR}/${backup_id}_metadata.json"
    
    if [[ -f "$metadata_file" ]]; then
        echo "Backup Information for $backup_id:"
        echo "=================================="
        
        # Parse and display key information
        if command -v jq >/dev/null 2>&1; then
            jq -r '
                "Created: " + .created_at + 
                "\nHostname: " + .hostname + 
                "\nUser: " + .user + 
                "\nGit Commit: " + .git_commit +
                "\nDatabase Size: " + (.database.size_bytes | tostring) + " bytes" +
                "\nDataset Size: " + (.dataset.size_bytes | tostring) + " bytes"
            ' "$metadata_file"
        else
            cat "$metadata_file"
        fi
        echo
    else
        log "WARN" "No metadata file found for backup: $backup_id"
    fi
}

verify_backup_file() {
    local backup_file="$1"
    local file_type="$2"
    
    if [[ ! -f "$backup_file" ]]; then
        error_exit "Backup file not found: $backup_file"
    fi
    
    log "INFO" "Verifying backup file: $(basename "$backup_file")"
    
    # Verify the compressed file is valid
    if ! gzip -t "$backup_file" 2>/dev/null; then
        error_exit "Backup file is corrupted: $backup_file"
    fi
    
    # For database files, verify SQLite integrity after decompression
    if [[ "$file_type" == "database" ]]; then
        local temp_db=$(mktemp)
        gunzip -c "$backup_file" > "$temp_db"
        
        if ! sqlite3 "$temp_db" "PRAGMA integrity_check;" | grep -q "ok"; then
            rm -f "$temp_db"
            error_exit "Database backup integrity check failed: $backup_file"
        fi
        
        rm -f "$temp_db"
    fi
    
    log "INFO" "Backup file verification passed"
}

restore_database() {
    local backup_id="$1"
    local backup_file="${BACKUP_DIR}/${backup_id}.db.gz"
    
    log "INFO" "Starting database restore from: $backup_id"
    
    # Verify backup file
    verify_backup_file "$backup_file" "database"
    
    # Show backup information
    show_backup_info "$backup_id"
    
    # Confirm restore operation
    confirm_action "⚠️  This will replace the current database with backup: $backup_id"
    
    # Create safety backup
    create_safety_backup
    
    # Stop any running services (optional - uncomment if needed)
    # echo "Stopping DHK Align service..."
    # pkill -f "python.*main.py" || true
    # sleep 2
    
    # Restore database
    log "INFO" "Restoring database file"
    mkdir -p "$DATA_DIR"
    gunzip -c "$backup_file" > "$DB_FILE"
    
    # Verify restored database
    if sqlite3 "$DB_FILE" "PRAGMA integrity_check;" | grep -q "ok"; then
        log "INFO" "Database restore completed successfully"
        log "INFO" "Database file: $DB_FILE"
        
        # Show basic statistics
        local record_count=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM translations;" 2>/dev/null || echo "unknown")
        log "INFO" "Translation records: $record_count"
        
        echo
        echo "✅ Database restore completed successfully!"
        echo "📁 Restored file: $DB_FILE"
        echo "📊 Translation records: $record_count"
        echo
    else
        error_exit "Restored database failed integrity check"
    fi
}

restore_csv() {
    local backup_id="$1"
    local backup_file="${BACKUP_DIR}/${backup_id}.csv.gz"
    
    log "INFO" "Starting CSV restore from: $backup_id"
    
    # Verify backup file
    verify_backup_file "$backup_file" "csv"
    
    # Show backup information
    show_backup_info "$backup_id"
    
    # Confirm restore operation
    confirm_action "⚠️  This will replace the current CSV dataset with backup: $backup_id"
    
    # Create safety backup
    create_safety_backup
    
    # Restore CSV
    log "INFO" "Restoring CSV file"
    mkdir -p "$DATA_DIR"
    gunzip -c "$backup_file" > "$CSV_FILE"
    
    # Verify restored CSV
    if [[ -f "$CSV_FILE" ]] && [[ -s "$CSV_FILE" ]]; then
        log "INFO" "CSV restore completed successfully"
        log "INFO" "CSV file: $CSV_FILE"
        
        # Show basic statistics
        local line_count=$(wc -l < "$CSV_FILE" 2>/dev/null || echo "unknown")
        log "INFO" "CSV lines: $line_count"
        
        echo
        echo "✅ CSV restore completed successfully!"
        echo "📁 Restored file: $CSV_FILE"
        echo "📊 Lines: $line_count"
        echo
    else
        error_exit "CSV restore failed - file is empty or missing"
    fi
}

restore_full() {
    local backup_id="$1"
    local db_backup="${BACKUP_DIR}/${backup_id}.db.gz"
    local csv_backup="${BACKUP_DIR}/${backup_id}.csv.gz"
    
    log "INFO" "Starting full restore from: $backup_id"
    
    # Check if both files exist
    if [[ ! -f "$db_backup" ]]; then
        error_exit "Database backup not found: $db_backup"
    fi
    
    if [[ ! -f "$csv_backup" ]]; then
        log "WARN" "CSV backup not found: $csv_backup (will restore database only)"
        restore_database "$backup_id"
        return
    fi
    
    # Show backup information
    show_backup_info "$backup_id"
    
    # Confirm restore operation
    confirm_action "⚠️  This will replace BOTH database and CSV with backup: $backup_id"
    
    # Create safety backup
    create_safety_backup
    
    # Restore database
    log "INFO" "Restoring database file"
    verify_backup_file "$db_backup" "database"
    mkdir -p "$DATA_DIR"
    gunzip -c "$db_backup" > "$DB_FILE"
    
    # Restore CSV
    log "INFO" "Restoring CSV file"
    verify_backup_file "$csv_backup" "csv"
    gunzip -c "$csv_backup" > "$CSV_FILE"
    
    # Verify both files
    local db_ok=false
    local csv_ok=false
    
    if sqlite3 "$DB_FILE" "PRAGMA integrity_check;" | grep -q "ok"; then
        db_ok=true
        local record_count=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM translations;" 2>/dev/null || echo "unknown")
        log "INFO" "Database restored successfully ($record_count records)"
    else
        error_exit "Restored database failed integrity check"
    fi
    
    if [[ -f "$CSV_FILE" ]] && [[ -s "$CSV_FILE" ]]; then
        csv_ok=true
        local line_count=$(wc -l < "$CSV_FILE" 2>/dev/null || echo "unknown")
        log "INFO" "CSV restored successfully ($line_count lines)"
    else
        error_exit "CSV restore failed"
    fi
    
    if [[ "$db_ok" == true ]] && [[ "$csv_ok" == true ]]; then
        echo
        echo "✅ Full restore completed successfully!"
        echo "📁 Database: $DB_FILE ($record_count records)"
        echo "📁 CSV: $CSV_FILE ($line_count lines)"
        echo
        echo "💡 Tip: Restart your DHK Align service to load the restored data"
        echo
    fi
}

# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

main() {
    # Initialize log file
    touch "$LOG_FILE"
    
    case "${1:-}" in
        "list")
            list_backups
            ;;
        "database")
            if [[ -z "${2:-}" ]]; then
                error_exit "Missing backup ID. Usage: $0 database <backup_id>"
            fi
            restore_database "$2"
            ;;
        "csv")
            if [[ -z "${2:-}" ]]; then
                error_exit "Missing backup ID. Usage: $0 csv <backup_id>"
            fi
            restore_csv "$2"
            ;;
        "full")
            if [[ -z "${2:-}" ]]; then
                error_exit "Missing backup ID. Usage: $0 full <backup_id>"
            fi
            restore_full "$2"
            ;;
        "info")
            if [[ -z "${2:-}" ]]; then
                error_exit "Missing backup ID. Usage: $0 info <backup_id>"
            fi
            show_backup_info "$2"
            ;;
        "help"|"-h"|"--help")
            cat << EOF
DHK Align Restore Script

Usage:
  $0 list                           List all available backups
  $0 info <backup_id>               Show detailed backup information
  $0 database <backup_id>           Restore database only
  $0 csv <backup_id>                Restore CSV dataset only  
  $0 full <backup_id>               Restore both database and CSV
  $0 help                           Show this help message

Examples:
  $0 list                           # See all available backups
  $0 info daily_20250118_143022     # Show backup details
  $0 database daily_20250118_143022 # Restore database from daily backup
  $0 csv weekly_20250115_091500     # Restore CSV from weekly backup
  $0 full daily_20250118_143022     # Restore everything from daily backup

Safety Features:
  - Creates safety backup of current files before restore
  - Verifies backup integrity before restoration
  - Requires explicit confirmation for destructive operations
  - Comprehensive logging of all operations

Notes:
  - Backup IDs are the filename without extension (e.g., daily_20250118_143022)
  - Safety backups are stored in: $SAFETY_BACKUP_DIR
  - All operations are logged to: $LOG_FILE
  - Consider stopping DHK Align service before major restores

EOF
            ;;
        *)
            echo "Error: Invalid or missing argument"
            echo "Usage: $0 {list|info|database|csv|full|help} [backup_id]"
            echo "Run '$0 help' for more information"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"