#!/bin/bash
# Hedge Scheduler Service Control Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HEDGE_SCRIPT="$SCRIPT_DIR/get_hedge.py"
PID_FILE="$SCRIPT_DIR/hedge_scheduler.pid"
LOG_FILE="$SCRIPT_DIR/hedge_scheduler.log"

case "$1" in
    start)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "🟢 Hedge Scheduler уже запущен (PID: $PID)"
                exit 1
            else
                echo "🧹 Удаляем устаревший PID файл"
                rm "$PID_FILE"
            fi
        fi
        
        echo "🚀 Запуск Hedge Scheduler..."
        echo "📂 Рабочая директория: $SCRIPT_DIR"
        echo "📄 Лог файл: $LOG_FILE"
        
        # Запускаем в фоне с интервалом 15 минут
        # Логирование управляется внутри Python скрипта
        nohup python3 "$HEDGE_SCRIPT" 15 >/dev/null 2>&1 &
        PID=$!
        echo "$PID" > "$PID_FILE"
        
        echo "✅ Hedge Scheduler запущен (PID: $PID)"
        echo "📋 Для просмотра логов: tail -f $LOG_FILE"
        echo "🛑 Для остановки: $0 stop"
        ;;
        
    stop)
        if [ ! -f "$PID_FILE" ]; then
            echo "❌ Hedge Scheduler не запущен (PID файл не найден)"
            exit 1
        fi
        
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "🛑 Остановка Hedge Scheduler (PID: $PID)..."
            kill -TERM "$PID"
            
            # Ждем корректного завершения
            for i in {1..10}; do
                if ! ps -p "$PID" > /dev/null 2>&1; then
                    break
                fi
                sleep 1
            done
            
            # Принудительное завершение если не остановился
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "⚠️ Принудительное завершение..."
                kill -KILL "$PID"
            fi
            
            rm -f "$PID_FILE"
            echo "✅ Hedge Scheduler остановлен"
        else
            echo "❌ Процесс с PID $PID не найден"
            rm -f "$PID_FILE"
        fi
        ;;
        
    status)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "🟢 Hedge Scheduler работает (PID: $PID)"
                echo "📊 Процесс: $(ps -p $PID -o pid,ppid,etime,cmd --no-headers)"
            else
                echo "🔴 Hedge Scheduler не работает (PID файл есть, но процесс мертв)"
                rm -f "$PID_FILE"
            fi
        else
            echo "🔴 Hedge Scheduler не работает"
        fi
        ;;
        
    logs)
        if [ -f "$LOG_FILE" ]; then
            echo "📋 Последние логи Hedge Scheduler:"
            echo "================================"
            tail -20 "$LOG_FILE"
        else
            echo "❌ Лог файл не найден: $LOG_FILE"
        fi
        ;;
        
    restart)
        echo "🔄 Перезапуск Hedge Scheduler..."
        $0 stop
        sleep 2
        $0 start
        ;;
        
    *)
        echo "Hedge Scheduler Control Script"
        echo "============================="
        echo "Использование: $0 {start|stop|status|logs|restart}"
        echo ""
        echo "Команды:"
        echo "  start   - Запуск планировщика (каждые 15 минут)"
        echo "  stop    - Остановка планировщика"
        echo "  status  - Проверка статуса"
        echo "  logs    - Показать последние логи"
        echo "  restart - Перезапуск планировщика"
        echo ""
        echo "📂 Рабочая директория: $SCRIPT_DIR"
        echo "📄 Лог файл: $LOG_FILE"
        exit 1
        ;;
esac