"""
Main Launcher - Запуск всей торговой системы PATRIOT
=====================================================

Координирует работу всех компонентов системы:
- ticker_monitor (анализ сигналов)
- order_generator (создание уведомлений)
- binance_factory (реальные ордера)

Author: HEDGER
Version: 1.0
"""

import asyncio
import logging
import logging.config
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# Импорты модулей проекта
from ticker_monitor import TickerMonitor
from binance_factory import BinanceFactory
from order_generator import set_binance_factory
import config

# Настройка логирования с UTF-8
logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)

class PatriotLauncher:
    """Главный координатор всей торговой системы"""
    
    def __init__(self):
        """Инициализация всех компонентов системы"""
        self.ticker_monitor = None
        self.binance_factory = None
        self.binance_thread = None
        self.stop_event = threading.Event()
        
        logger.info("Starting PATRIOT Trading System...")
        
        # Инициализируем компоненты
        self._initialize_components()
        
    def _initialize_components(self):
        """Инициализация всех компонентов"""
        try:
            # 1. Инициализируем Binance Factory с проверкой подключения
            logger.info("Initializing Binance Factory...")
            print("🔄 Подключение к Binance API...")
            
            try:
                self.binance_factory = BinanceFactory()
                print("✅ Binance Factory успешно инициализирован")
            except ConnectionError as e:
                error_msg = f"❌ ОШИБКА ПОДКЛЮЧЕНИЯ К BINANCE: {e}"
                print(error_msg)
                logger.error(error_msg)
                print("\n🛑 ПРОГРАММА ОСТАНОВЛЕНА из-за ошибки подключения к Binance API")
                print("Проверьте:")
                print("1. Правильность API ключей в .env файле")
                print("2. Подключение к интернету")
                print("3. Статус серверов Binance")
                sys.exit(1)
            except ValueError as e:
                error_msg = f"❌ ОШИБКА КОНФИГУРАЦИИ: {e}"
                print(error_msg)
                logger.error(error_msg)
                print("\n🛑 ПРОГРАММА ОСТАНОВЛЕНА из-за ошибки конфигурации")
                print("Проверьте настройки API ключей в .env файле")
                sys.exit(1)
            except Exception as e:
                error_msg = f"❌ НЕОЖИДАННАЯ ОШИБКА BINANCE: {e}"
                print(error_msg)
                logger.error(error_msg)
                print("\n🛑 ПРОГРАММА ОСТАНОВЛЕНА из-за критической ошибки")
                sys.exit(1)
            
            # 2. Связываем order_generator с binance_factory
            logger.info("Connecting Order Generator with Binance Factory...")
            set_binance_factory(self.binance_factory)
            
            # 3. Инициализируем Ticker Monitor
            logger.info("Initializing Ticker Monitor...")
            self.ticker_monitor = TickerMonitor(
                tickers_file=config.DEFAULT_TICKERS_FILE,
                max_workers=config.MAX_WORKERS,
                ticker_delay=config.TICKER_DELAY
            )
            
            logger.info("All components initialized successfully")
            print("✅ Все компоненты системы успешно инициализированы")
            
        except Exception as e:
            error_msg = f"Failed to initialize components: {e}"
            logger.error(error_msg)
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА ИНИЦИАЛИЗАЦИИ: {e}")
            raise
    
    def start_binance_factory(self):
        """Запуск Binance Factory в отдельном потоке"""
        def run_binance_factory():
            try:
                logger.info("Starting Binance Factory...")
                if self.binance_factory is not None:
                    asyncio.run(self.binance_factory.run())
                else:
                    logger.error("Binance Factory is not initialized")
            except Exception as e:
                logger.error(f"Binance Factory error: {e}")
        
        self.binance_thread = threading.Thread(
            target=run_binance_factory,
            name="BinanceFactory",
            daemon=True
        )
        self.binance_thread.start()
        logger.info("Binance Factory started in background")
    
    def run(self):
        """Главный цикл работы системы"""
        try:
            logger.info("Starting PATRIOT Trading Orchestra...")
            
            # Запускаем Binance Factory в фоновом режиме
            self.start_binance_factory()
            
            # Даем время на инициализацию Binance Factory
            time.sleep(2)
            
            # Запускаем Ticker Monitor в главном потоке
            logger.info("Starting Ticker Monitor...")
            if self.ticker_monitor is not None:
                self.ticker_monitor.run()
            else:
                logger.error("Ticker Monitor is not initialized")
            
        except KeyboardInterrupt:
            logger.info("Graceful shutdown requested...")
            self.shutdown()
        except Exception as e:
            logger.error(f"Critical error in main launcher: {e}")
            self.shutdown()
    
    def shutdown(self):
        """Корректное завершение работы всех компонентов"""
        logger.info("Shutting down PATRIOT Trading System...")
        
        # Останавливаем Ticker Monitor
        if self.ticker_monitor:
            self.ticker_monitor.shutdown()
        
        # Останавливаем Binance Factory
        if self.binance_factory:
            self.binance_factory.stop()
        
        # Ждем завершения потока Binance Factory
        if self.binance_thread and self.binance_thread.is_alive():
            self.binance_thread.join(timeout=5)
        
        logger.info("PATRIOT Trading System shutdown complete")

def main():
    """Точка входа в приложение"""
    try:
        print("🚀 Запуск торговой системы PATRIOT...")
        
        # Проверяем наличие конфигурации
        if not hasattr(config, 'BINANCE_API_KEY') or not config.BINANCE_API_KEY:
            error_msg = f"❌ Binance API ключи для {config.NETWORK_MODE} не настроены!"
            logger.error(error_msg)
            print(error_msg)
            print(f"\n🔧 Пожалуйста, установите переменные окружения для {config.NETWORK_MODE}:")
            if config.BINANCE_TESTNET:
                print("set BINANCE_TESTNET_API_KEY=your_testnet_api_key")
                print("set BINANCE_TESTNET_API_SECRET=your_testnet_api_secret")
                print("set BINANCE_TESTNET=true")
            else:
                print("set BINANCE_MAINNET_API_KEY=your_production_api_key")
                print("set BINANCE_MAINNET_API_SECRET=your_production_api_secret")
                print("set BINANCE_TESTNET=false")
            print("\nИли проверьте файл .env")
            return
        
        # Проверяем наличие файла тикеров
        tickers_file = Path(config.DEFAULT_TICKERS_FILE)
        if not tickers_file.exists():
            error_msg = f"❌ Файл тикеров не найден: {tickers_file}"
            logger.error(error_msg)
            print(error_msg)
            return
        
        # Запускаем систему
        try:
            launcher = PatriotLauncher()
            launcher.run()
        except SystemExit:
            # Корректный выход из программы
            pass
        except Exception as e:
            error_msg = f"❌ КРИТИЧЕСКАЯ ОШИБКА ЗАПУСКА: {e}"
            print(error_msg)
            logger.error(error_msg)
            return
        
    except KeyboardInterrupt:
        print("\n👋 Завершение работы по запросу пользователя")
        logger.info("Shutdown requested by user")
    except Exception as e:
        error_msg = f"💥 ФАТАЛЬНАЯ ОШИБКА: {e}"
        print(error_msg)
        logger.error(error_msg)
        import traceback
        logger.debug(traceback.format_exc())

if __name__ == "__main__":
    main()
