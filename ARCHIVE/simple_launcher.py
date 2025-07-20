"""
Simple Launcher - Простой запуск торговой системы PATRIOT
========================================================

Минималистичный координатор системы:
- ticker_monitor (анализ и мониторинг)
- quick_test (интерактивное управление)

Модульная архитектура без сложного управления потоками.

Author: HEDGER
Version: 2.0 - Simplified
"""

import sys
import logging
from pathlib import Path

# Импорты проекта
from ticker_monitor import TickerMonitor
from utils import logger
import config

def check_environment():
    """Проверка готовности окружения"""
    print("🔍 Проверка системы...")
    
    # Проверяем API ключи
    if not hasattr(config, 'BINANCE_API_KEY') or not config.BINANCE_API_KEY:
        print(f"❌ Binance API ключи для {config.NETWORK_MODE} не настроены!")
        print(f"\n🔧 Установите переменные окружения для {config.NETWORK_MODE}:")
        if config.BINANCE_TESTNET:
            print("  BINANCE_TESTNET_API_KEY=your_testnet_api_key")
            print("  BINANCE_TESTNET_API_SECRET=your_testnet_api_secret")
        else:
            print("  BINANCE_MAINNET_API_KEY=your_production_api_key")
            print("  BINANCE_MAINNET_API_SECRET=your_production_api_secret")
        print("\nИли проверьте файл .env")
        return False
    
    # Проверяем файл тикеров
    tickers_file = Path(config.DEFAULT_TICKERS_FILE)
    if not tickers_file.exists():
        print(f"❌ Файл тикеров не найден: {tickers_file}")
        return False
    
    print(f"✅ Режим: {config.NETWORK_MODE}")
    print(f"✅ API ключи настроены")
    print(f"✅ Файл тикеров найден: {tickers_file}")
    return True

def show_menu():
    """Показывает главное меню"""
    print("\n" + "="*50)
    print("🚀 PATRIOT TRADING SYSTEM")
    print("="*50)
    print("1. 📊 Запустить мониторинг тикеров (ticker_monitor)")
    print("2. ⚡ Интерактивный режим (quick_test)")
    print("3. 🔧 Проверить систему")
    print("4. 📄 Показать статус")
    print("0. ❌ Выход")
    print("="*50)

def run_ticker_monitor():
    """Запуск мониторинга тикеров"""
    try:
        print("\n🎼 Запуск Ticker Monitor...")
        logger.info("Starting Ticker Monitor from launcher")
        
        monitor = TickerMonitor(
            tickers_file=config.DEFAULT_TICKERS_FILE,
            max_workers=config.MAX_WORKERS,
            ticker_delay=config.TICKER_DELAY
        )
        monitor.run()
        
    except KeyboardInterrupt:
        print("\n⏹️ Остановка мониторинга...")
        logger.info("Ticker Monitor stopped by user")
    except Exception as e:
        print(f"❌ Ошибка мониторинга: {e}")
        logger.error(f"Ticker Monitor error: {e}")

def run_quick_test():
    """Запуск интерактивного режима"""
    try:
        print("\n⚡ Запуск интерактивного режима...")
        import subprocess
        result = subprocess.run([sys.executable, "quick_test.py"], 
                              cwd=Path.cwd())
        if result.returncode != 0:
            print("❌ Ошибка запуска quick_test.py")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")

def show_status():
    """Показывает статус системы"""
    print("\n📊 СТАТУС СИСТЕМЫ:")
    print("-" * 30)
    print(f"🌐 Режим сети: {config.NETWORK_MODE}")
    print(f"📁 Файл тикеров: {config.DEFAULT_TICKERS_FILE}")
    print(f"👥 Макс. workers: {config.MAX_WORKERS}")
    print(f"⏱️ Задержка: {config.TICKER_DELAY}s")
    print(f"📋 Таймфреймы: {', '.join(config.TIMEFRAMES)}")
    
    # Показываем логи
    print(f"\n📝 Логи:")
    print(f"  Signals: {config.LOG_FILE}")
    print(f"  Binance: {config.BINANCE_LOG_FILE}")

def main():
    """Главная функция лаунчера"""
    try:
        print("🚀 Простой лаунчер PATRIOT")
        
        # Проверяем окружение
        if not check_environment():
            input("\nНажмите Enter для выхода...")
            return
        
        # Главный цикл меню
        while True:
            try:
                show_menu()
                choice = input("\nВыберите действие: ").strip()
                
                if choice == "1":
                    run_ticker_monitor()
                elif choice == "2":
                    run_quick_test()
                elif choice == "3":
                    check_environment()
                elif choice == "4":
                    show_status()
                elif choice == "0":
                    print("👋 До свидания!")
                    break
                else:
                    print("❌ Неверный выбор")
                    
            except KeyboardInterrupt:
                print("\n👋 Выход по Ctrl+C")
                break
            except Exception as e:
                print(f"❌ Ошибка меню: {e}")
                
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        logger.error(f"Critical launcher error: {e}")

if __name__ == "__main__":
    main()
