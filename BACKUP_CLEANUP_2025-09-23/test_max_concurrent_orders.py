#!/usr/bin/env python3
"""
Тест для проверки логики MAX_CONCURRENT_ORDERS
============================================

Проверяет корректность ограничения:
1. Подсчет активных позиций + открытых ордеров для символа
2. Проверка качества цены (equal or better)

Author: HEDGER
Version: 1.0
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from order_executor import OrderExecutor
from config import MAX_CONCURRENT_ORDERS
from utils import logger

def test_count_positions_and_orders():
    """Тест подсчета позиций и ордеров"""
    logger.info("🧪 Тестируем подсчет позиций и ордеров...")
    
    executor = OrderExecutor()
    
    # Тестируем с реальными данными
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    
    for symbol in test_symbols:
        try:
            positions, orders, total = executor._count_active_positions_and_orders_for_symbol(symbol)
            logger.info(f"📊 {symbol}: {positions} позиций + {orders} ордеров = {total} всего")
            
            if total >= MAX_CONCURRENT_ORDERS:
                logger.warning(f"⚠️ {symbol} достиг лимита: {total}/{MAX_CONCURRENT_ORDERS}")
            else:
                logger.info(f"✅ {symbol} в пределах лимита: {total}/{MAX_CONCURRENT_ORDERS}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования {symbol}: {e}")


def test_price_quality():
    """Тест проверки качества цены"""
    logger.info("🧪 Тестируем проверку качества цены...")
    
    executor = OrderExecutor()
    
    # Тестируем с реальными данными
    test_cases = [
        ('BTCUSDT', 'BUY', 60000.0),
        ('BTCUSDT', 'SELL', 65000.0),
        ('ETHUSDT', 'BUY', 2500.0),
        ('ETHUSDT', 'SELL', 2600.0),
    ]
    
    for symbol, side, price in test_cases:
        try:
            acceptable, reason = executor._check_price_quality(symbol, side, price)
            
            if acceptable:
                logger.info(f"✅ {symbol} {side} @ {price}: {reason}")
            else:
                logger.warning(f"⚠️ {symbol} {side} @ {price}: {reason}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования цены {symbol}: {e}")


def main():
    """Главная функция теста"""
    try:
        logger.info("🚀 Запуск тестов MAX_CONCURRENT_ORDERS")
        logger.info(f"⚙️ Текущий лимит: {MAX_CONCURRENT_ORDERS}")
        logger.info("=" * 50)
        
        # Тест 1: Подсчет позиций и ордеров
        test_count_positions_and_orders()
        
        logger.info("=" * 50)
        
        # Тест 2: Проверка качества цены
        test_price_quality()
        
        logger.info("=" * 50)
        logger.info("✅ Тесты завершены")
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в тестах: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
