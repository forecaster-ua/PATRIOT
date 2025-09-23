#!/bin/bash
# PATRIOT System Cleanup Script
# Version: 1.0
# Date: $(date)
# Description: Automated cleanup of unused files in PATRIOT trading system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="BACKUP_CLEANUP_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="cleanup_log_$(date +%Y%m%d_%H%M%S).txt"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_FILE"
}

# Error handling
error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    log "ERROR: $1"
    exit 1
}

# Success message
success() {
    echo -e "${GREEN}✅ $1${NC}"
    log "SUCCESS: $1"
}

# Warning message
warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    log "WARNING: $1"
}

# Info message
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
    log "INFO: $1"
}

# File size calculator
get_size() {
    if [[ -f "$1" ]]; then
        du -sh "$1" 2>/dev/null | cut -f1
    elif [[ -d "$1" ]]; then
        du -sh "$1" 2>/dev/null | cut -f1
    else
        echo "0B"
    fi
}

# Safe remove with backup
safe_remove() {
    local file="$1"
    local category="$2"

    if [[ -e "$file" ]]; then
        local size=$(get_size "$file")
        log "Removing $category: $file ($size)"

        # Create backup
        mkdir -p "$BACKUP_DIR"
        if [[ -f "$file" ]]; then
            cp "$file" "$BACKUP_DIR/" 2>/dev/null || warning "Failed to backup file: $file"
        elif [[ -d "$file" ]]; then
            cp -r "$file" "$BACKUP_DIR/" 2>/dev/null || warning "Failed to backup directory: $file"
        fi

        # Remove file
        rm -rf "$file" 2>/dev/null && success "Removed: $file" || warning "Failed to remove: $file"
    else
        warning "File not found: $file"
    fi
}

# Main cleanup function
main() {
    echo "🧹 PATRIOT Trading System Cleanup"
    echo "=================================="
    echo "Backup directory: $BACKUP_DIR"
    echo "Log file: $LOG_FILE"
    echo ""

    log "Starting PATRIOT system cleanup"
    log "Backup directory: $BACKUP_DIR"

    # Create backup directory
    mkdir -p "$BACKUP_DIR" || error "Failed to create backup directory"

    # Calculate initial size
    initial_size=$(du -sh . 2>/dev/null | cut -f1)
    log "Initial project size: $initial_size"

    info "Phase 1: Creating comprehensive backup..."
    # Backup entire project before cleanup
    tar -czf "${BACKUP_DIR}/full_backup.tar.gz" . --exclude="$BACKUP_DIR" --exclude="logs" 2>/dev/null || warning "Full backup failed"

    info "Phase 2: Removing test files..."
    safe_remove "test_max_concurrent_orders.py" "test file"
    safe_remove "test_new_features.py" "test file"
    safe_remove "test_watchdog_lifecycle.py" "test file"

    info "Phase 3: Removing empty/placeholder files..."
    safe_remove "get_full_json.py" "empty file"
    safe_remove "signal_to_order_workflow.txt" "empty file"
    safe_remove "signal_to_order_workflow_addendum.txt" "empty file"

    info "Phase 4: Removing demo/example files..."
    safe_remove "current_data_examp.json" "demo file"
    safe_remove "current_data_examp_15m.json" "demo file"
    safe_remove "fetch_signal_example.py" "demo script"
    safe_remove "simple_signal_fetch.py" "demo script"

    info "Phase 5: Removing web interface files..."
    safe_remove "price_monitor.html" "web interface"
    safe_remove "price_monitor_direct.html" "web interface"
    safe_remove "websocket_price_server.py" "web interface"
    safe_remove "websocket_test.html" "web interface"
    safe_remove "start_price_monitor.py" "web interface"
    safe_remove "PRICE_MONITOR_README.md" "web interface docs"

    info "Phase 6: Removing duplicate documentation..."
    safe_remove "21-08-NEW_FEATURES_SUMMARY.md" "duplicate docs"
    safe_remove "NEW_FEATURES_SUMMARY.md" "duplicate docs"
    safe_remove "PATRIOT_PROJECT_MAP.md" "duplicate docs"
    safe_remove "PATRIOT.txt" "duplicate docs"

    info "Phase 7: Removing utility scripts..."
    safe_remove "clean_old_orders.py" "utility script"
    safe_remove "exchange_sync_cleanup.py" "utility script"
    safe_remove "sync_orders_data.py" "utility script"
    safe_remove "init_symbol_cache.py" "utility script"

    # info "Phase 8: Removing temporary files..."
    # safe_remove "markdown.md" "temporary file"
    # safe_remove "bot.log" "temporary log"

    info "Phase 9: Removing Python cache..."
    safe_remove "__pycache__/" "Python cache"

    info "Phase 10: Removing old backups..."
    # Remove old backup files (but keep recent ones)
    find . -name "orders_watchdog_state_backup_*.json" -type f -mtime +7 -exec bash -c 'safe_remove "$1" "old backup"' _ {} \;

    info "Phase 11: Removing alternative ticker lists..."
    safe_remove "tickers_full_copy.txt" "alternative ticker list"
    safe_remove "tickers_max.txt" "alternative ticker list"

    # Calculate final size
    final_size=$(du -sh . 2>/dev/null | cut -f1)
    log "Final project size: $final_size"

    # Summary
    echo ""
    echo "🎉 CLEANUP COMPLETED!"
    echo "===================="
    success "Cleanup completed successfully"
    info "Backup location: $BACKUP_DIR"
    info "Log file: $LOG_FILE"
    info "Initial size: $initial_size"
    info "Final size: $final_size"
    echo ""
    warning "Review backup directory before deleting it"
    warning "Check log file for any warnings or errors"
    echo ""
    echo "📋 Files you may want to review from backup:"
    echo "  - Web interface files (if you need price monitoring)"
    echo "  - Utility scripts (if you need manual maintenance)"
    echo "  - Demo files (if you need examples)"
    echo ""
    success "PATRIOT system cleanup completed!"
}

# Run main function
main "$@"
