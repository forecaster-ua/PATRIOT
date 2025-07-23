#!/usr/bin/env python3
"""
🚨 ТЕСТ ВАЛИДАЦИИ ЦЕН ЛИМИТНЫХ ОРДЕРОВ
=====================================

Day 0 Task: Проверяем новую функцию validate_limit_order_price()
"""

from enhanced_signal_processor import AdvancedSignalProcessor
from utils import logger
import time

def test_price_validation():
    """Тестируем валидацию цен для разных сценариев"""
    logger.info("🧪 === ТЕСТ ВАЛИДАЦИИ ЦЕН ЛИМИТНЫХ ОРДЕРОВ ===")
    
    # Инициализируем процессор
    processor = AdvancedSignalProcessor("BTCUSDT", risk_percent=0.5)
    
    if not processor.binance_client:
        logger.error("❌ Binance клиент недоступен")
        return
    
    # Получаем текущую цену BTC
    current_price = processor.get_current_price()
    logger.info(f"📊 Текущая цена BTCUSDT: {current_price:.2f}")
    
    if current_price <= 0:
        logger.error("❌ Не удалось получить текущую цену")
        return
    
    # Тест 1: КОРРЕКТНЫЙ LONG (цена входа ниже текущей)
    logger.info("\n🧪 Тест 1: КОРРЕКТНЫЙ LONG")
    good_long_signal = {
        'ticker': 'BTCUSDT',
        'signal': 'LONG',
        'entry_price': current_price * 0.99,  # На 1% ниже текущей цены
        'stop_loss': current_price * 0.97,
        'take_profit': current_price * 1.03
    }
    
    valid, error_msg = processor.validate_limit_order_price(good_long_signal)
    logger.info(f"   Результат: {'✅ ВАЛИДЕН' if valid else f'❌ ОШИБКА: {error_msg}'}")
    
    # Тест 2: НЕКОРРЕКТНЫЙ LONG (цена входа выше текущей)
    logger.info("\n🧪 Тест 2: НЕКОРРЕКТНЫЙ LONG (должен выдать ошибку)")
    bad_long_signal = {
        'ticker': 'BTCUSDT',
        'signal': 'LONG',
        'entry_price': current_price * 1.01,  # На 1% выше текущей цены - ОШИБКА!
        'stop_loss': current_price * 0.97,
        'take_profit': current_price * 1.03
    }
    
    valid, error_msg = processor.validate_limit_order_price(bad_long_signal)
    logger.info(f"   Результат: {'✅ ВАЛИДЕН' if valid else f'❌ ОШИБКА (правильно!): {error_msg}'}")
    
    # Тест 3: КОРРЕКТНЫЙ SHORT (цена входа выше текущей)
    logger.info("\n🧪 Тест 3: КОРРЕКТНЫЙ SHORT")
    good_short_signal = {
        'ticker': 'BTCUSDT',
        'signal': 'SHORT',
        'entry_price': current_price * 1.01,  # На 1% выше текущей цены
        'stop_loss': current_price * 1.03,
        'take_profit': current_price * 0.97
    }
    
    valid, error_msg = processor.validate_limit_order_price(good_short_signal)
    logger.info(f"   Результат: {'✅ ВАЛИДЕН' if valid else f'❌ ОШИБКА: {error_msg}'}")
    
    # Тест 4: НЕКОРРЕКТНЫЙ SHORT (цена входа ниже текущей)
    logger.info("\n🧪 Тест 4: НЕКОРРЕКТНЫЙ SHORT (должен выдать ошибку)")
    bad_short_signal = {
        'ticker': 'BTCUSDT',
        'signal': 'SHORT',
        'entry_price': current_price * 0.99,  # На 1% ниже текущей цены - ОШИБКА!
        'stop_loss': current_price * 1.03,
        'take_profit': current_price * 0.97
    }
    
    valid, error_msg = processor.validate_limit_order_price(bad_short_signal)
    logger.info(f"   Результат: {'✅ ВАЛИДЕН' if valid else f'❌ ОШИБКА (правильно!): {error_msg}'}")
    
    # Тест 5: Проверим отправку ошибки в Telegram
    logger.info("\n🧪 Тест 5: Отправка ошибки в Telegram")
    try:
        # Попытка выставить некорректный лимитный ордер
        result = processor.place_limit_order_with_sl_tp(bad_long_signal)
        success_msg = "✅ Успех" if result['success'] else f"❌ Ошибка: {result['error']}"
        logger.info(f"   Результат ордера: {success_msg}")
        
        if not result['success']:
            logger.info("   📱 Проверьте Telegram - должно прийти уведомление об ошибке!")
    except Exception as e:
        logger.error(f"   Ошибка теста: {e}")
    
    logger.info("\n✅ === ТЕСТЫ ЗАВЕРШЕНЫ ===")
    logger.info("💡 Если все тесты прошли, валидация работает корректно!")

if __name__ == "__main__":
    test_price_validation()
