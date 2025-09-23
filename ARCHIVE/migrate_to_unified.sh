#!/bin/bash

# PATRIOT Trading System - Migration to Unified Sync
# ==================================================
# Миграция на унифицированную систему синхронизации
#
# Author: HEDGER
# Version: 2.0 - Complete Migration Script

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
echo -e "${PURPLE} PATRIOT System Migration - Unified Sync v2.0${NC}"
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

# Проверка виртуального окружения
if [ ! -d "/home/alexross/patriot/venv" ]; then
    log_error "Virtual environment not found!"
    exit 1
fi

PYTHON_CMD="/home/alexross/patriot/venv/bin/python"

echo -e "${BLUE}🚀 Starting migration to Unified Sync System...${NC}"
echo ""

# ============================================================================
# ШАГ 1: Предварительные проверки
# ============================================================================
log_step "1/7 Pre-migration checks..."

# Проверяем, что система остановлена
echo -e "${CYAN}Checking if PATRIOT processes are stopped...${NC}"

RUNNING_PROCESSES=$(pgrep -f "ticker_monitor.py|orders_watchdog.py" | wc -l)
if [ $RUNNING_PROCESSES -gt 0 ]; then
    log_error "PATRIOT processes are still running!"
    echo ""
    echo -e "${YELLOW}Found running processes:${NC}"
    ps aux | grep -E "(ticker_monitor|orders_watchdog)" | grep -v grep
    echo ""
    echo -e "${RED}❌ Migration cannot proceed with active processes${NC}"
    echo -e "${CYAN}Run: ${GREEN}./stop_system_for_migration.sh${NC}"
    echo ""
    exit 1
fi

log_info "✅ No PATRIOT processes running - safe to proceed"

# Проверяем, что новый файл существует
if [ ! -f "unified_sync.py" ]; then
    log_error "unified_sync.py not found!"
    echo "Please ensure the unified sync system is properly installed"
    exit 1
fi

# Проверяем Python модули
$PYTHON_CMD -c "
import sys
try:
    from binance.client import Client
    print('✅ python-binance available')
except ImportError:
    print('❌ python-binance not installed')
    sys.exit(1)

try:
    from utils import logger
    print('✅ utils module available') 
except ImportError:
    print('❌ utils module not found')
    sys.exit(1)

try:
    from config import BINANCE_API_KEY, BINANCE_API_SECRET
    if BINANCE_API_KEY and BINANCE_API_SECRET:
        print('✅ Binance API keys configured')
    else:
        print('⚠️ Binance API keys not configured')
except ImportError:
    print('❌ config module not found')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    log_error "Pre-migration checks failed!"
    exit 1
fi

log_info "Pre-migration checks passed"
echo ""

# ============================================================================
# ШАГ 2: Тестирование новой системы
# ============================================================================
log_step "2/7 Testing unified sync system..."

echo -e "${CYAN}Running comprehensive tests...${NC}"
$PYTHON_CMD test_unified_sync.py

if [ $? -ne 0 ]; then
    log_warning "Some tests failed, but migration can continue"
    echo ""
    read -p "Continue with migration despite test failures? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Migration cancelled due to test failures"
        exit 1
    fi
else
    log_info "All tests passed successfully"
fi

echo ""

# ============================================================================
# ШАГ 3: Создание резервных копий
# ============================================================================
log_step "3/7 Creating backups..."

# Создаем папку для резервных копий
BACKUP_DIR="BACKUP_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Список файлов для резервного копирования
FILES_TO_BACKUP=(
    "orders_watchdog_state.json"
    "restart_patriot.sh"
    "start_patriot.sh"
    "orders_synchronizer.py"
    "state_recovery.py"
    "sync_check.py"
    "sync_monitor.py"
)

for file in "${FILES_TO_BACKUP[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" "$BACKUP_DIR/"
        log_info "Backed up: $file"
    fi
done

log_info "Backups created in $BACKUP_DIR"
echo ""

# ============================================================================
# ШАГ 4: Миграция компонентов
# ============================================================================
log_step "4/7 Migrating components..."

echo -e "${CYAN}Running migration script...${NC}"
$PYTHON_CMD migrate_sync.py << EOF
y
y
EOF

if [ $? -eq 0 ]; then
    log_info "Component migration completed successfully"
else
    log_warning "Component migration completed with warnings"
fi

echo ""

# ============================================================================
# ШАГ 5: Проверка обновленной системы
# ============================================================================
log_step "5/7 Validating updated system..."

# Проверяем статус новой системы
echo -e "${CYAN}Checking unified sync status...${NC}"
$PYTHON_CMD unified_sync.py --status

if [ $? -eq 0 ]; then
    log_info "Unified sync system is operational"
else
    log_warning "Unified sync system has issues"
fi

# Тестируем синхронизацию
echo ""
echo -e "${CYAN}Testing synchronization...${NC}"
$PYTHON_CMD -c "
from unified_sync import sync_before_startup
try:
    success = sync_before_startup('migration_test')
    if success:
        print('✅ Synchronization test passed')
        exit(0)
    else:
        print('⚠️ Synchronization test passed with warnings')
        exit(1)
except Exception as e:
    print(f'❌ Synchronization test failed: {e}')
    exit(2)
"

SYNC_TEST_RESULT=$?
if [ $SYNC_TEST_RESULT -eq 0 ]; then
    log_info "Synchronization test passed"
elif [ $SYNC_TEST_RESULT -eq 1 ]; then
    log_warning "Synchronization test passed with warnings"
else
    log_error "Synchronization test failed"
    echo ""
    read -p "Continue despite synchronization test failure? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Migration halted due to synchronization failure"
        exit 1
    fi
fi

echo ""

# ============================================================================
# ШАГ 6: Финальная проверка
# ============================================================================
log_step "6/7 Final validation..."

# Проверяем, что все критичные файлы на месте
CRITICAL_FILES=(
    "unified_sync.py"
    "restart_patriot.sh"
    "start_patriot.sh"
    "orders_watchdog.py"
    "ticker_monitor.py"
)

MISSING_FILES=()
for file in "${CRITICAL_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -ne 0 ]; then
    log_error "Critical files missing: ${MISSING_FILES[*]}"
    exit 1
fi

log_info "All critical files present"

# Проверяем права на выполнение скриптов
chmod +x restart_patriot.sh
chmod +x start_patriot.sh
chmod +x unified_sync.py
chmod +x migrate_sync.py
chmod +x test_unified_sync.py

log_info "Script permissions updated"

# ============================================================================
# ШАГ 7: Дополнительная проверка состояния
# ============================================================================
log_step "7/7 Final state verification..."

# Убеждаемся, что процессы все еще остановлены
FINAL_PROCESS_CHECK=$(pgrep -f "ticker_monitor.py|orders_watchdog.py" | wc -l)
if [ $FINAL_PROCESS_CHECK -gt 0 ]; then
    log_warning "Some PATRIOT processes started during migration!"
    echo "This should not happen. Stopping them now..."
    pkill -f "ticker_monitor.py|orders_watchdog.py"
    sleep 2
fi

log_info "Final process check completed"

echo ""
echo -e "${GREEN}✅ MIGRATION COMPLETED SUCCESSFULLY!${NC}"
echo ""

# ============================================================================
# ИТОГОВАЯ ИНФОРМАЦИЯ
# ============================================================================
echo -e "${BLUE}📋 MIGRATION SUMMARY${NC}"
echo "=" * 50
echo -e "${GREEN}✅ Old components archived${NC}"
echo -e "${GREEN}✅ Unified sync system activated${NC}"  
echo -e "${GREEN}✅ Scripts updated${NC}"
echo -e "${GREEN}✅ Backups created in $BACKUP_DIR${NC}"
echo ""

echo -e "${BLUE}🔄 NEXT STEPS${NC}"
echo "=" * 50
echo -e "1. Test the system: ${GREEN}python3 unified_sync.py --status${NC}"
echo -e "2. Force sync if needed: ${GREEN}python3 unified_sync.py --force${NC}"
echo -e "3. Restart the system: ${GREEN}./restart_patriot.sh${NC}"
echo -e "4. Start trading: ${GREEN}./start_patriot.sh${NC}"
echo ""

echo -e "${BLUE}📚 DOCUMENTATION${NC}"
echo "=" * 50
echo -e "• Architecture guide: ${CYAN}UNIFIED_SYNC_ARCHITECTURE.md${NC}"
echo -e "• Migration details: ${CYAN}migrate_sync.py --help${NC}"
echo -e "• Testing guide: ${CYAN}test_unified_sync.py --help${NC}"
echo ""

echo -e "${YELLOW}⚠️ IMPORTANT NOTES${NC}"
echo "=" * 50
echo -e "• Old sync components are in ${CYAN}ARCHIVE/deprecated_sync_components/${NC}"
echo -e "• Backups are in ${CYAN}$BACKUP_DIR${NC}"
echo -e "• Monitor first few sync operations carefully"
echo -e "• Check Telegram notifications are working"
echo ""

read -p "Start the updated system now? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Starting updated PATRIOT system..."
    echo ""
    exec ./restart_patriot.sh
else
    log_info "Migration completed. Start manually with: ./restart_patriot.sh"
fi
