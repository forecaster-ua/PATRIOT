#!/bin/bash

# PATRIOT Trading System - Complete Restart & Synchronization
# ============================================================
# Полный перезапуск системы с синхронизацией состояния
# ============================================================================
# ШАГ 6: Финальная проверка состояния
# ============================================================================
log_step "6/6 Final state validation..."

echo -e "${CYAN}Running final state validation...${NC}"
$PYTHON_CMD -c "
from unified_sync import unified_sync
unified_sync.print_status()
": HEDGER
# Version: 1.0 - Complete System Restart

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
echo -e "${PURPLE} PATRIOT System Restart & Synchronization${NC}"
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

echo -e "${BLUE}🔄 Starting complete system restart...${NC}"
echo ""

# ============================================================================
# ШАГ 1: Остановка всех компонентов
# ============================================================================
log_step "1/6 Stopping all PATRIOT components..."

# Остановить Ticker Monitor
TICKER_PIDS=$(pgrep -f "ticker_monitor.py")
if [ ! -z "$TICKER_PIDS" ]; then
    log_info "Stopping Ticker Monitor processes: $TICKER_PIDS"
    pkill -f "ticker_monitor.py"
    sleep 2
else
    log_info "Ticker Monitor not running"
fi

# Остановить Orders Watchdog
log_info "Stopping Orders Watchdog..."
./watchdog.sh stop
sleep 2

echo ""

# ============================================================================
# ШАГ 2: Полная синхронизация состояния
# ============================================================================
log_step "2/6 System state synchronization..."

echo -e "${CYAN}Running state synchronization with exchange...${NC}"
$PYTHON_CMD -c "
from unified_sync import sync_before_startup
success = sync_before_startup('restart')
if success:
    print('✅ State synchronized successfully')
    exit(0)
else:
    print('⚠️ State synchronization completed with warnings')
    exit(1)
"

SYNC_STATUS=$?
if [ $SYNC_STATUS -eq 1 ]; then
    log_warning "State synchronization completed with warnings"
    echo ""
    read -p "Continue with restart? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Restart cancelled due to synchronization issues"
        exit 1
    fi
else
    log_info "State synchronization completed successfully"
fi

echo ""

# ============================================================================
# ШАГ 3: Проверка состояния на бирже
# ============================================================================
log_step "3/6 Checking exchange status..."

echo -e "${CYAN}Checking Binance connection and account status...${NC}"
$PYTHON_CMD emergency_stop.py --status

if [ $? -ne 0 ]; then
    log_error "Failed to connect to Binance!"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Restart cancelled"
        exit 1
    fi
fi

echo ""

# ============================================================================
# ШАГ 4: Восстановление состояния (опционально)
# ============================================================================
log_step "4/6 State recovery options..."

echo -e "${YELLOW}State recovery options:${NC}"
echo -e "  ${GREEN}1.${NC} Skip recovery (fast start)"
echo -e "  ${GREEN}2.${NC} Full state recovery from exchange"
echo -e "  ${GREEN}3.${NC} Manual state check"
echo ""

read -p "Select option (1-3): " -n 1 -r
echo ""

case $REPLY in
    2)
        log_info "Running full state recovery..."
        $PYTHON_CMD state_recovery.py
        ;;
    3)
        log_info "Manual state check..."
        $PYTHON_CMD -c "
from state_recovery import StateRecovery
recovery = StateRecovery()
print('=== EXCHANGE POSITIONS ===')
recovery.print_exchange_state()
print('=== SUMMARY ===')
recovery.print_recovery_summary()
        "
        echo ""
        read -p "Continue with startup? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "Restart cancelled"
            exit 1
        fi
        ;;
    *)
        log_info "Skipping state recovery"
        ;;
esac

echo ""

# ============================================================================
# ШАГ 5: Запуск Orders Watchdog
# ============================================================================
log_step "5/6 Starting Orders Watchdog..."

./watchdog.sh start

if [ $? -eq 0 ]; then
    log_info "Orders Watchdog started successfully"
    sleep 3
    
    # Проверяем статус
    ./watchdog.sh status
else
    log_error "Failed to start Orders Watchdog!"
    exit 1
fi

echo ""

# ============================================================================
# ШАГ 6: Финальная проверка синхронизации
# ============================================================================
log_step "6/6 Final state validation..."

echo -e "${CYAN}Running final state validation...${NC}"
$PYTHON_CMD -c "
from state_synchronizer import state_sync
state_sync.print_sync_status()
"

echo ""
echo -e "${GREEN}✅ System restart completed successfully!${NC}"
echo ""
echo -e "${BLUE}Next step: Launch Ticker Monitor${NC}"
echo -e "${CYAN}Run: ${GREEN}./start_patriot.sh${NC}"
echo ""

# Опция автоматического запуска
read -p "Start Ticker Monitor now? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Starting Ticker Monitor..."
    echo ""
    exec ./start_patriot.sh
else
    log_info "Manual startup. Run './start_patriot.sh' when ready."
fi
