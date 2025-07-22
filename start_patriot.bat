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

REM Запускаем систему
python ticker_monitor.py

echo.
echo System stopped.
pause
