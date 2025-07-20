#!/usr/bin/env python3
"""
Initialize Symbol Cache - Инициализация кэша символов
====================================================

Этот скрипт загружает информацию о всех торговых символах 
из tickers.txt и создает кэш для быстрого доступа к фильтрам.

Запускайте этот скрипт:
1. При первом запуске системы
2. При добавлении новых символов в tickers.txt
3. Раз в день для обновления актуальной информации

Author: HEDGER
Version: 1.0
"""

from symbol_cache import SymbolCache
from utils import logger
import config

def initialize_symbol_cache():
    """Инициализирует и обновляет кэш символов"""
    logger.info("🚀 === ИНИЦИАЛИЗАЦИЯ КЭША СИМВОЛОВ ===")
    
    try:
        # Создаем экземпляр кэша
        cache = SymbolCache()
        
        # Показываем текущую статистику
        stats = cache.get_cache_stats()
        logger.info(f"📊 Текущее состояние кэша:")
        logger.info(f"   Символов в кэше: {stats['cached_symbols']}")
        logger.info(f"   Возраст кэша: {stats['cache_age']}")
        logger.info(f"   Кэш валиден: {stats['cache_valid']}")
        
        # Обновляем кэш (принудительно)
        logger.info("🔄 Обновление кэша символов...")
        success = cache.update_cache(force=True)
        
        if success:
            # Показываем обновленную статистику
            new_stats = cache.get_cache_stats()
            logger.info(f"✅ === КЭШ УСПЕШНО ОБНОВЛЕН ===")
            logger.info(f"   Символов загружено: {new_stats['cached_symbols']}")
            logger.info(f"   Файл кэша: {new_stats['cache_file']}")
            logger.info(f"   Время обновления: {new_stats['last_update']}")
            
            # Тестируем несколько символов для демонстрации
            test_symbols = ['BTCUSDT', 'ETHUSDT', 'NKNUSDT', 'SOLUSDT']
            test_price = 1000.123456
            test_quantity = 0.123456789
            
            logger.info(f"🧪 === ДЕМОНСТРАЦИЯ РАБОТЫ КЭША ===")
            
            for symbol in test_symbols:
                info = cache.get_symbol_info(symbol)
                if info:
                    rounded_price = cache.round_price(symbol, test_price)
                    rounded_qty = cache.round_quantity(symbol, test_quantity)
                    
                    logger.info(f"   {symbol}:")
                    logger.info(f"     Status: {info['status']}")
                    logger.info(f"     Tick Size: {info['tick_size']}")
                    logger.info(f"     Step Size: {info['step_size']}")
                    logger.info(f"     Price: {test_price:.6f} → {rounded_price:.6f}")
                    logger.info(f"     Quantity: {test_quantity:.9f} → {rounded_qty:.9f}")
                else:
                    logger.warning(f"   {symbol}: не найден в кэше")
            
            logger.info("🎉 === ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО ===")
            logger.info("💡 Кэш готов к использованию в торговой системе")
            
        else:
            logger.error("❌ === ОШИБКА ИНИЦИАЛИЗАЦИИ КЭША ===")
            logger.error("Проверьте подключение к Binance API и файл tickers.txt")
            
    except KeyboardInterrupt:
        logger.info("⌨️ Инициализация прервана пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка инициализации: {e}")

if __name__ == "__main__":
    logger.info(f"🌐 Режим: {'TESTNET' if config.BINANCE_TESTNET else 'MAINNET'}")
    initialize_symbol_cache()
