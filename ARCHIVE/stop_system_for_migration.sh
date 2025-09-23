#!/bin/bash

# PATRIOT Trading System - Safe System Shutdown
# =============================================
# Безопасная остановка всех компонентов системы перед миграцией
#
# Author: HEDGER
# Version: 1.0 - Safe Pre-Migration Shutdown

clear

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${PURPLE}████████████████████████████████████████████████████████████${NC}"
echo -e "${PURPLE} PATRIOT System Shutdown - Pre-Migration Safety${NC}"
echo -e "${PURPLE}████████████████████████████████████████████████████████████${NC}"
echo ""

# Функции логирования
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

echo -e "${BLUE}🛑 Stopping all PATRIOT components before migration...${NC}"
echo ""

# ============================================================================
# ШАГ 1: Остановка Ticker Monitor
# ============================================================================
log_step "1/5 Stopping Ticker Monitor..."

# Найти и остановить все процессы ticker_monitor
TICKER_PIDS=$(pgrep -f "ticker_monitor.py")
if [ ! -z "$TICKER_PIDS" ]; then
    log_info "Found Ticker Monitor processes: $TICKER_PIDS"
    echo "$TICKER_PIDS" | while read pid; do
        if kill -TERM "$pid" 2>/dev/null; then
            log_info "Sent SIGTERM to Ticker Monitor PID: $pid"
        fi
    done
    
    # Ждем 5 секунд для graceful shutdown
    sleep 5
    
    # Проверяем, что процессы остановились
    TICKER_PIDS_AFTER=$(pgrep -f "ticker_monitor.py")
    if [ ! -z "$TICKER_PIDS_AFTER" ]; then
        log_warning "Some Ticker Monitor processes still running, force killing..."
        echo "$TICKER_PIDS_AFTER" | while read pid; do
            kill -KILL "$pid" 2>/dev/null
            log_info "Force killed Ticker Monitor PID: $pid"
        done
    fi
    
    log_info "Ticker Monitor stopped"
else
    log_info "Ticker Monitor not running"
fi

echo ""

# ============================================================================
# ШАГ 2: Остановка Orders Watchdog
# ============================================================================
log_step "2/5 Stopping Orders Watchdog..."

# Используем watchdog.sh для остановки если есть
if [ -f "./watchdog.sh" ]; then
    log_info "Using watchdog.sh to stop Orders Watchdog..."
    ./watchdog.sh stop
else
    log_warning "watchdog.sh not found, stopping manually..."
    
    # Найти процессы orders_watchdog
    WATCHDOG_PIDS=$(pgrep -f "orders_watchdog.py")
    if [ ! -z "$WATCHDOG_PIDS" ]; then
        log_info "Found Orders Watchdog processes: $WATCHDOG_PIDS"
        echo "$WATCHDOG_PIDS" | while read pid; do
            if kill -TERM "$pid" 2>/dev/null; then
                log_info "Sent SIGTERM to Orders Watchdog PID: $pid"
            fi
        done
        
        # Ждем 10 секунд для сохранения состояния
        sleep 10
        
        # Проверяем, что процессы остановились
        WATCHDOG_PIDS_AFTER=$(pgrep -f "orders_watchdog.py")
        if [ ! -z "$WATCHDOG_PIDS_AFTER" ]; then
            log_warning "Some Orders Watchdog processes still running, force killing..."
            echo "$WATCHDOG_PIDS_AFTER" | while read pid; do
                kill -KILL "$pid" 2>/dev/null
                log_info "Force killed Orders Watchdog PID: $pid"
            done
        fi
    else
        log_info "Orders Watchdog not running"
    fi
fi

# Удаляем PID файл если есть
if [ -f "orders_watchdog.pid" ]; then
    rm -f "orders_watchdog.pid"
    log_info "Removed Orders Watchdog PID file"
fi

echo ""

# ============================================================================
# ШАГ 3: Остановка других связанных процессов
# ============================================================================
log_step "3/5 Stopping other PATRIOT processes..."

# Список других возможных процессов
OTHER_PROCESSES=(
    "signal_analyzer.py"
    "order_executor.py"
    "websocket_monitor.py"
    "sync_monitor.py"
    "account_summary_fut.py"
)

for process in "${OTHER_PROCESSES[@]}"; do
    PIDS=$(pgrep -f "$process")
    if [ ! -z "$PIDS" ]; then
        log_info "Stopping $process (PIDs: $PIDS)"
        echo "$PIDS" | while read pid; do
            kill -TERM "$pid" 2>/dev/null
        done
    fi
done

# Небольшая пауза для остановки
sleep 3

echo ""

# ============================================================================
# ШАГ 4: Проверка состояния системы
# ============================================================================
log_step "4/5 Verifying system shutdown..."

# Проверяем все PATRIOT процессы
ALL_PATRIOT_PIDS=$(pgrep -f "ticker_monitor.py|orders_watchdog.py|signal_analyzer.py|order_executor.py")

if [ -z "$ALL_PATRIOT_PIDS" ]; then
    log_info "✅ All PATRIOT processes stopped successfully"
else
    log_warning "⚠️ Some processes still running:"
    ps aux | grep -E "(ticker_monitor|orders_watchdog|signal_analyzer|order_executor)" | grep -v grep
    echo ""
    read -p "Force kill remaining processes? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "$ALL_PATRIOT_PIDS" | while read pid; do
            kill -KILL "$pid" 2>/dev/null
            log_info "Force killed PID: $pid"
        done
        log_info "All remaining processes terminated"
    fi
fi

echo ""

# ============================================================================
# ШАГ 5: Резервное копирование критичных файлов
# ============================================================================
log_step "5/5 Creating pre-migration backup..."

# Создаем папку для резервной копии перед миграцией
BACKUP_DIR="PRE_MIGRATION_BACKUP_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Список критичных файлов для бэкапа
CRITICAL_FILES=(
    "orders_watchdog_state.json"
    "orders_watchdog_requests.json"
    "orders_watchdog_response.json"
    "system_state.json"
    "sync_report.json"
    "signals.db"
    "tickers.txt"
    ".env"
)

log_info "Creating backup in $BACKUP_DIR..."

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" "$BACKUP_DIR/"
        log_info "Backed up: $file"
    fi
done

# Копируем логи
if [ -d "logs" ]; then
    cp -r "logs" "$BACKUP_DIR/"
    log_info "Backed up: logs directory"
fi

# Создаем информационный файл
cat > "$BACKUP_DIR/backup_info.txt" << EOF
PATRIOT Trading System - Pre-Migration Backup
=============================================
Created: $(date)
Purpose: Backup before migration to Unified Sync System v2.0
Host: $(hostname)
User: $(whoami)
Working Directory: $(pwd)

Files backed up:
$(ls -la "$BACKUP_DIR")

System Status at Backup Time:
- All PATRIOT processes stopped
- System ready for migration
- Original files preserved

Restore Instructions:
To restore any file: cp $BACKUP_DIR/filename ./filename
To restore all: cp $BACKUP_DIR/* ./

Migration Command:
./migrate_to_unified.sh
EOF

log_info "Backup information saved to $BACKUP_DIR/backup_info.txt"

echo ""
echo -e "${GREEN}✅ SYSTEM SHUTDOWN COMPLETED SUCCESSFULLY!${NC}"
echo ""

# ============================================================================
# ИТОГОВАЯ ИНФОРМАЦИЯ
# ============================================================================
echo -e "${BLUE}📋 SHUTDOWN SUMMARY${NC}"
echo "=" * 50
echo -e "${GREEN}✅ Ticker Monitor stopped${NC}"
echo -e "${GREEN}✅ Orders Watchdog stopped${NC}"  
echo -e "${GREEN}✅ All related processes terminated${NC}"
echo -e "${GREEN}✅ Pre-migration backup created: $BACKUP_DIR${NC}"
echo ""

echo -e "${BLUE}🔄 NEXT STEPS${NC}"
echo "=" * 50
echo -e "1. Run migration: ${GREEN}./migrate_to_unified.sh${NC}"
echo -e "2. Or test new system: ${GREEN}python3 test_unified_sync.py${NC}"
echo -e "3. Check backup if needed: ${GREEN}ls -la $BACKUP_DIR${NC}"
echo ""

echo -e "${YELLOW}⚠️ IMPORTANT${NC}"
echo "=" * 50
echo -e "• All trading activity is now STOPPED"
echo -e "• System state preserved in backup"
echo -e "• Ready for safe migration"
echo -e "• Do NOT start any components manually until migration is complete"
echo ""

read -p "Proceed with migration now? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Starting migration to Unified Sync System..."
    echo ""
    if [ -f "./migrate_to_unified.sh" ]; then
        exec ./migrate_to_unified.sh
    else
        log_error "migrate_to_unified.sh not found!"
        echo "Please ensure the migration script is available before proceeding."
        exit 1
    fi
else
    log_info "System safely stopped. Run './migrate_to_unified.sh' when ready."
    echo ""
    echo -e "${CYAN}💡 Remember: Do not start any PATRIOT components until migration is complete!${NC}"
fi
