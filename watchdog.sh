#!/bin/bash

# Запуск Orders Watchdog
# ====================
# 
# Этот скрипт запускает Orders Watchdog в фоне
# и обеспечивает автоматический перезапуск при сбое

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/orders_watchdog.py"
LOG_FILE="$SCRIPT_DIR/logs/orders_watchdog.log"
PID_FILE="$SCRIPT_DIR/orders_watchdog.pid"

# Создаем директорию для логов если не существует
mkdir -p "$SCRIPT_DIR/logs"

# Функция остановки
stop_watchdog() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "Останавливаем Orders Watchdog (PID: $PID)..."
            kill -TERM "$PID"
            sleep 3
            
            # Принудительная остановка если процесс не остановился
            if kill -0 "$PID" 2>/dev/null; then
                echo "Принудительная остановка..."
                kill -KILL "$PID"
            fi
        fi
        rm -f "$PID_FILE"
        echo "Orders Watchdog остановлен"
    else
        echo "PID файл не найден, возможно процесс уже остановлен"
    fi
}

# Функция интерактивной остановки
istop_watchdog() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "🛑 Интерактивная остановка Orders Watchdog (PID: $PID)..."
            echo "📋 Запускаем скрипт с подключенным терминалом для обработки активных ордеров..."
            
            # Останавливаем фоновый процесс
            kill -TERM "$PID"
            sleep 2
            
            # Запускаем интерактивную версию для обработки shutdown
            cd "$SCRIPT_DIR"
            /home/alexross/patriot/venv/bin/python -c "
import sys
sys.path.append('$SCRIPT_DIR')
from orders_watchdog import OrdersWatchdog

# Создаем экземпляр - автоматически загрузит состояние и подключится
print('🔄 Проверяем активные ордера и запускаем интерактивное управление...')
watchdog = OrdersWatchdog()

# Сразу вызываем shutdown для интерактивной обработки
watchdog.shutdown()
"
            
            # Убеждаемся что процесс остановлен
            if kill -0 "$PID" 2>/dev/null; then
                echo "Принудительная остановка фонового процесса..."
                kill -KILL "$PID"
            fi
        else
            echo "❌ Процесс не найден или уже остановлен"
        fi
        rm -f "$PID_FILE"
        echo "✅ Orders Watchdog остановлен"
    else
        echo "PID файл не найден, возможно процесс уже остановлен"
    fi
}

# Функция запуска
start_watchdog() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "Orders Watchdog уже запущен (PID: $PID)"
            return 0
        else
            # Удаляем старый PID файл
            rm -f "$PID_FILE"
        fi
    fi
    
    echo "Запускаем Orders Watchdog..."
    echo "Логи: $LOG_FILE"
    
    # Запускаем в фоне и записываем PID
    nohup /home/alexross/patriot/venv/bin/python "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"
    
    # Проверяем что процесс действительно запустился
    sleep 2
    if kill -0 "$PID" 2>/dev/null; then
        echo "✅ Orders Watchdog запущен (PID: $PID)"
    else
        echo "❌ Orders Watchdog не смог запуститься"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Функция проверки статуса
status_watchdog() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "✅ Orders Watchdog работает (PID: $PID)"
            
            # Показываем последние строки лога
            if [ -f "$LOG_FILE" ]; then
                echo "Последние записи в логе:"
                tail -5 "$LOG_FILE"
            fi
        else
            echo "❌ Orders Watchdog не работает (PID файл найден, но процесс не активен)"
            rm -f "$PID_FILE"
        fi
    else
        echo "❌ Orders Watchdog не запущен"
    fi
}

# Функция рестарта
restart_watchdog() {
    echo "Перезапускаем Orders Watchdog..."
    stop_watchdog
    sleep 1
    start_watchdog
}

# Функция просмотра логов
logs_watchdog() {
    if [ -f "$LOG_FILE" ]; then
        echo "Логи Orders Watchdog ($LOG_FILE):"
        echo "Нажмите Ctrl+C для выхода"
        tail -f "$LOG_FILE"
    else
        echo "Лог файл не найден: $LOG_FILE"
    fi
}

# Функция проверки синхронизации
check_sync() {
    echo "🔍 Проверяем синхронизацию с биржей..."
    cd "$SCRIPT_DIR"
    python3 sync_check.py --report
}

# Обработка аргументов
case "${1:-}" in
    start)
        start_watchdog
        ;;
    stop)
        stop_watchdog
        ;;
    istop)
        istop_watchdog
        ;;
    restart)
        restart_watchdog
        ;;
    status)
        status_watchdog
        ;;
    logs)
        logs_watchdog
        ;;
    check)
        check_sync
        ;;
    *)
        echo "Использование: $0 {start|stop|istop|restart|status|logs|check}"
        echo ""
        echo "Команды:"
        echo "  start   - Запустить Orders Watchdog в фоне"
        echo "  stop    - Остановить Orders Watchdog (без интерактивного управления ордерами)"
        echo "  istop   - Интерактивная остановка с управлением активными ордерами"
        echo "  restart - Перезапустить Orders Watchdog"
        echo "  status  - Проверить статус Orders Watchdog"
        echo "  logs    - Показать логи в реальном времени"
        echo "  check   - Проверить синхронизацию с биржей"
        exit 1
        ;;
esac
