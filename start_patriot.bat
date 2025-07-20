@echo off
echo ========================================
echo PATRIOT Trading System Launcher
echo ========================================
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
echo.

REM Запускаем систему
python main_launcher.py

echo.
echo System stopped.
pause
