@echo off
cls
echo ████████████████████████████████████████████████████████████
echo  PATRIOT Trading System - Production Launch v1.5
echo ████████████████████████████████████████████████████████████
echo.

REM Проверка актуальности версии
echo 🔍 Checking version synchronization...
python version_check.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo ⚠️  WARNING: Version out of sync or uncommitted changes detected!
    echo.
    choice /C YN /M "Continue anyway? (Y/N)"
    if %ERRORLEVEL% neq 1 (
        echo 🛑 Launch cancelled. Please sync your version first.
        echo 💡 Run: git pull origin main
        pause
        exit /b 1
    )
    echo.
    echo 🚀 Continuing with out-of-sync version...
)

echo.
echo ✅ Version check completed
echo.

REM Проверяем существование файла .env
if not exist .env (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and configure your API keys
    echo.
    pause
    exit /b 1
)

REM Проверяем существование файла tickers.txt
if not exist tickers.txt (
    echo ERROR: tickers.txt file not found!
    echo Please make sure tickers.txt exists in the current directory
    echo.
    pause
    exit /b 1
)

echo Starting PATRIOT Trading System...
echo ⏰ Start time: %date% %time%
echo.

REM Проверяем существование файла orders_watchdog.py
if not exist orders_watchdog.py (
    echo ERROR: orders_watchdog.py file not found!
    echo Please make sure orders_watchdog.py exists in the current directory
    echo.
    pause
    exit /b 1
)

echo.
echo ████████████████████████████████████████████████████████████
echo  PATRIOT Trading System - Dual Process Architecture
echo ████████████████████████████████████████████████████████████
echo.
echo 🔧 Process Architecture:
echo    1. TICKER MONITOR  - Signal detection and order placement
echo    2. ORDERS WATCHDOG - Order execution monitoring
echo.
echo 🚀 Starting PATRIOT Trading System...
echo ⏰ Start time: %date% %time%
echo.

REM Создаем временные файлы для PID процессов
set TICKER_PID_FILE=ticker_monitor.pid
set WATCHDOG_PID_FILE=orders_watchdog.pid

REM Функция очистки при выходе
set CLEANUP_DONE=0

REM Запускаем Orders Watchdog в фоне
echo 🐕 Starting Orders Watchdog...
start "Orders Watchdog" /MIN python orders_watchdog.py
echo ✅ Orders Watchdog started in background

REM Даем время на инициализацию
timeout /t 3 /nobreak >nul

REM Запускаем Ticker Monitor (основной процесс)
echo 🎼 Starting Ticker Monitor...
echo.
echo ════════════════════════════════════════════════════════════
echo  System is now running. Press Ctrl+C to stop both processes.
echo ════════════════════════════════════════════════════════════
echo.

REM Запускаем Ticker Monitor в основном окне (блокирующий вызов)
python ticker_monitor.py

REM Этот код выполнится когда ticker_monitor завершится
echo.
echo 🛑 Ticker Monitor stopped. Shutting down Orders Watchdog...

REM Останавливаем Orders Watchdog
taskkill /F /FI "WindowTitle eq Orders Watchdog" 2>nul

echo.
echo ✅ PATRIOT Trading System stopped.
echo ⏰ Stop time: %date% %time%
pause
