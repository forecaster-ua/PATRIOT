#!/bin/bash

# PATRIOT Trading System - Ticker Monitor Launch
# ===============================================
# Запускает только Ticker Monitor
# Orders Watchdog работает как независимый сервис
#
# Author: HEDGER
# Version: 2.1 - Independent Watchdog Architecture

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
echo -e "${PURPLE} PATRIOT Trading System - Ticker Monitor v2.1${NC}"
echo -e "${PURPLE}████████████████████████████████████████████████████████████${NC}"
echo ""

# Функция логирования
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Проверка версии
echo -e "${BLUE}🔍 Checking version synchronization...${NC}"
python3 version_check.py
if [ $? -ne 0 ]; then
    echo ""
    log_warning "Version out of sync or uncommitted changes detected!"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Launch cancelled. Please sync your version first."
        echo "💡 Run: git pull origin main"
        exit 1
    fi
    echo ""
    log_info "Continuing with out-of-sync version..."
fi

log_info "Version check completed"
echo ""

# Проверяем файлы конфигурации
if [ ! -f .env ]; then
    log_error ".env file not found!"
    echo "Please copy .env.example to .env and configure your API keys"
    echo ""
    exit 1
fi

if [ ! -f tickers.txt ]; then
    log_error "tickers.txt file not found!"
    echo "Please make sure tickers.txt exists in the current directory"
    echo ""
    exit 1
fi

if [ ! -f orders_watchdog.py ]; then
    log_error "orders_watchdog.py file not found!"
    echo "Please make sure orders_watchdog.py exists in the current directory"
    echo ""
    exit 1
fi

# Проверяем статус Orders Watchdog
echo ""
echo -e "${BLUE}🐕 Checking Orders Watchdog status...${NC}"

WATCHDOG_PID_FILE="orders_watchdog.pid"
WATCHDOG_RUNNING=false

if [ -f "$WATCHDOG_PID_FILE" ]; then
    WATCHDOG_PID=$(cat "$WATCHDOG_PID_FILE")
    if kill -0 "$WATCHDOG_PID" 2>/dev/null; then
        WATCHDOG_RUNNING=true
        log_info "Orders Watchdog is running (PID: $WATCHDOG_PID)"
        echo -e "${GREEN}✅ Orders monitoring is active${NC}"
    else
        log_warning "Orders Watchdog PID file exists but process is dead"
        rm -f "$WATCHDOG_PID_FILE"
    fi
fi

if [ "$WATCHDOG_RUNNING" = false ]; then
    echo -e "${RED}❌ Orders Watchdog is NOT running${NC}"
    echo -e "${YELLOW}⚠️  Without Orders Watchdog:${NC}"
    echo -e "   • Placed orders won't be monitored"
    echo -e "   • SL/TP won't be automatically placed"
    echo -e "   • P&L calculations won't work"
    echo ""
    echo -e "${CYAN}💡 To start Orders Watchdog:${NC}"
    echo -e "   ${GREEN}./watchdog.sh start${NC}"
    echo ""
    read -p "Continue without Orders Watchdog? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Launch cancelled. Please start Orders Watchdog first."
        echo "Run: ./watchdog.sh start"
        exit 1
    fi
    echo ""
    log_warning "Continuing WITHOUT Orders Watchdog..."
fi

# Файлы для PID процессов
TICKER_PID_FILE="ticker_monitor.pid"

# Функция очистки при выходе
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down Ticker Monitor...${NC}"
    
    # Останавливаем только Ticker Monitor
    if [ -f "$TICKER_PID_FILE" ]; then
        TICKER_PID=$(cat "$TICKER_PID_FILE")
        if kill -0 "$TICKER_PID" 2>/dev/null; then
            echo -e "${YELLOW}🎼 Stopping Ticker Monitor (PID: $TICKER_PID)...${NC}"
            kill -TERM "$TICKER_PID" 2>/dev/null
        fi
        rm -f "$TICKER_PID_FILE"
    fi
    
    echo ""
    log_info "Ticker Monitor stopped."
    
    # Проверяем статус Orders Watchdog
    if [ "$WATCHDOG_RUNNING" = true ]; then
        echo -e "${GREEN}🐕 Orders Watchdog continues running independently${NC}"
        echo -e "${CYAN}   Monitoring existing orders and positions...${NC}"
    fi
    
    echo -e "${BLUE}⏰ Stop time: $(date)${NC}"
    echo ""
    echo -e "${YELLOW}💡 Orders Watchdog management:${NC}"
    echo -e "   ${GREEN}./watchdog.sh status${NC}  - check watchdog status"
    echo -e "   ${GREEN}./watchdog.sh stop${NC}    - stop watchdog"
    echo -e "   ${GREEN}./watchdog.sh logs${NC}    - view watchdog logs"
    echo ""
    exit 0
}

# Устанавливаем обработчик сигналов
trap cleanup SIGINT SIGTERM

echo ""
echo -e "${PURPLE}████████████████████████████████████████████████████████████${NC}"
echo -e "${PURPLE} PATRIOT Trading System - Independent Architecture${NC}"
echo -e "${PURPLE}████████████████████████████████████████████████████████████${NC}"
echo ""
echo -e "${CYAN}🔧 Process Architecture:${NC}"
echo -e "   ${GREEN}1. TICKER MONITOR${NC}   - Signal detection and order placement"
echo -e "   ${GREEN}2. ORDERS WATCHDOG${NC}  - Independent order monitoring service"
echo ""

if [ "$WATCHDOG_RUNNING" = true ]; then
    echo -e "${GREEN}🐕 Orders Watchdog: ✅ Running${NC}"
else
    echo -e "${YELLOW}🐕 Orders Watchdog: ⚠️  Not running${NC}"
fi

echo ""
echo -e "${BLUE}🚀 Starting Ticker Monitor...${NC}"
echo -e "${BLUE}⏰ Start time: $(date)${NC}"
echo ""

# Запускаем только Ticker Monitor (основной процесс)
echo -e "${CYAN}🎼 Initializing Ticker Monitor...${NC}"
echo ""

if [ "$WATCHDOG_RUNNING" = true ]; then
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN} Ticker Monitor is running. Orders Watchdog runs independently.${NC}"
    echo -e "${GREEN} Press Ctrl+C to stop only Ticker Monitor.${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
else
    echo -e "${YELLOW}════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW} WARNING: Running WITHOUT Orders Watchdog!${NC}"
    echo -e "${YELLOW} Orders will NOT be monitored automatically.${NC}"
    echo -e "${YELLOW}════════════════════════════════════════════════════════════${NC}"
fi
echo ""

# Запускаем Ticker Monitor в основном потоке
python3 ticker_monitor.py

# Этот код выполнится когда ticker_monitor завершится
cleanup
