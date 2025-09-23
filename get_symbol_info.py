#!/usr/bin/env python3
"""
Get Symbol Info - Получение информации о символах с использованием кэша
======================================================================

Этот скрипт показывает информацию о символах из кэша или загружает
её напрямую с Binance API для сравнения.

Author: HEDGER
Version: 2.0 - Updated to use Symbol Cache
"""

from binance.client import Client
from symbol_cache import get_symbol_cache
from utils import logger
import config

def get_leverage_brackets(client, symbol: str):
    """Получает информацию о leverage brackets для символа"""
    try:
        brackets = client.futures_leverage_bracket(symbol=symbol)
        return brackets
    except Exception as e:
        logger.error(f"❌ Ошибка получения leverage brackets для {symbol}: {e}")
        return None

def get_symbol_info_from_api(symbol: str):
    """Получает информацию о символе напрямую с Binance API"""
    try:
        client = Client(
            api_key=config.BINANCE_API_KEY,
            api_secret=config.BINANCE_API_SECRET,
            testnet=config.BINANCE_TESTNET
        )
        
        # Получаем информацию о символе
        exchange_info = client.futures_exchange_info()
        
        for symbol_info in exchange_info['symbols']:
            if symbol_info['symbol'] == symbol:
                print(f"📊 === ИНФОРМАЦИЯ О СИМВОЛЕ {symbol} (API) ===")
                print(f"   Status: {symbol_info['status']}")
                print(f"   Base Asset: {symbol_info['baseAsset']}")
                print(f"   Quote Asset: {symbol_info['quoteAsset']}")
                
                print(f"\n🔧 === ФИЛЬТРЫ ===")
                for filter_info in symbol_info['filters']:
                    if filter_info['filterType'] == 'PRICE_FILTER':
                        print(f"   PRICE_FILTER:")
                        print(f"     Min Price: {filter_info['minPrice']}")
                        print(f"     Max Price: {filter_info['maxPrice']}")
                        print(f"     Tick Size: {filter_info['tickSize']}")
                    elif filter_info['filterType'] == 'LOT_SIZE':
                        print(f"   LOT_SIZE:")
                        print(f"     Min Qty: {filter_info['minQty']}")
                        print(f"     Max Qty: {filter_info['maxQty']}")
                        print(f"     Step Size: {filter_info['stepSize']}")
                
                # Получаем информацию о leverage brackets
                print(f"\n⚡ === LEVERAGE BRACKETS ===")
                brackets = get_leverage_brackets(client, symbol)
                if brackets and len(brackets) > 0:
                    symbol_brackets = brackets[0].get('brackets', [])
                    if symbol_brackets:
                        min_leverage = min(bracket['initialLeverage'] for bracket in symbol_brackets)
                        max_leverage = max(bracket['initialLeverage'] for bracket in symbol_brackets)
                        print(f"   📊 Диапазон плеча: {min_leverage}x - {max_leverage}x")
                        print(f"   🎯 Текущее плечо в системе: {config.FUTURES_LEVERAGE}x")
                        
                        # Проверяем, можем ли использовать текущее плечо
                        if config.FUTURES_LEVERAGE > max_leverage:
                            print(f"   ⚠️  ВНИМАНИЕ: Текущее плечо {config.FUTURES_LEVERAGE}x превышает максимальное {max_leverage}x!")
                        elif config.FUTURES_LEVERAGE < min_leverage:
                            print(f"   ⚠️  ВНИМАНИЕ: Текущее плечо {config.FUTURES_LEVERAGE}x меньше минимального {min_leverage}x!")
                        else:
                            print(f"   ✅ Текущее плечо в допустимых пределах")
                        
                        print(f"\n   📋 Детальные уровни:")
                        prev_cap = 0
                        for i, bracket in enumerate(symbol_brackets[:5]):  # Показываем первые 5 уровней
                            notional_cap = float(bracket['notionalCap'])
                            initial_leverage = bracket['initialLeverage']
                            maint_margin_ratio = float(bracket['maintMarginRatio'])
                            
                            if notional_cap == 9223372036854775807:  # Максимальное значение
                                print(f"     💰 ${prev_cap:,.0f}+ → Max {initial_leverage}x (маржа: {maint_margin_ratio*100:.1f}%)")
                            else:
                                print(f"     💰 ${prev_cap:,.0f} - ${notional_cap:,.0f} → Max {initial_leverage}x (маржа: {maint_margin_ratio*100:.1f}%)")
                            prev_cap = notional_cap
                            
                        # Показываем практический пример
                        print(f"\n   💡 Практический пример:")
                        example_amounts = [1000, 5000, 10000, 50000]
                        for amount in example_amounts:
                            max_lev = max_leverage  # По умолчанию максимальное
                            for bracket in symbol_brackets:
                                if amount <= float(bracket['notionalCap']):
                                    max_lev = bracket['initialLeverage']
                                    break
                            print(f"     ${amount:,} позиция → Макс. плечо: {max_lev}x")
                    else:
                        print(f"   ❌ Нет данных о leverage brackets")
                else:
                    print(f"   ❌ Не удалось получить leverage brackets")
                break
        
    except Exception as e:
        print(f"❌ Ошибка API: {e}")

def get_symbol_info_from_cache(symbol: str):
    """Получает информацию о символе из кэша"""
    try:
        cache = get_symbol_cache()
        info = cache.get_symbol_info(symbol)
        
        if info:
            print(f"💾 === ИНФОРМАЦИЯ О СИМВОЛЕ {symbol} (CACHE) ===")
            print(f"   Status: {info['status']}")
            print(f"   Tick Size: {info['tick_size']}")
            print(f"   Step Size: {info['step_size']}")
            print(f"   Min Price: {info['min_price']}")
            print(f"   Max Price: {info['max_price']}")
            print(f"   Min Qty: {info['min_qty']}")
            print(f"   Max Qty: {info['max_qty']}")
            print(f"   Price Precision: {info['precision_price']}")
            print(f"   Qty Precision: {info['precision_qty']}")
            
            # Демонстрация округления
            test_price = 50000.123456789
            test_qty = 0.123456789
            
            rounded_price = cache.round_price(symbol, test_price)
            rounded_qty = cache.round_quantity(symbol, test_qty)
            
            print(f"\n🧪 === ТЕСТ ОКРУГЛЕНИЯ ===")
            print(f"   Цена: {test_price:.9f} → {rounded_price:.9f}")
            print(f"   Количество: {test_qty:.9f} → {rounded_qty:.9f}")
            
            # Валидация ордера
            valid_price, valid_qty, is_valid = cache.validate_order_params(symbol, test_price, test_qty)
            print(f"\n✅ === ВАЛИДАЦИЯ ОРДЕРА ===")
            print(f"   Валидная цена: {valid_price:.9f}")
            print(f"   Валидное количество: {valid_qty:.9f}")
            print(f"   Ордер валиден: {is_valid}")
            
        else:
            print(f"❌ Символ {symbol} не найден в кэше")
            print("💡 Попробуйте запустить init_symbol_cache.py для обновления кэша")
        
    except Exception as e:
        print(f"❌ Ошибка кэша: {e}")

def compare_symbols(symbols: list):
    """Сравнивает несколько символов из кэша"""
    print(f"📊 === СРАВНЕНИЕ СИМВОЛОВ ===")
    cache = get_symbol_cache()
    
    print(f"{'Symbol':<12} {'Tick Size':<15} {'Step Size':<15} {'Status':<10}")
    print("-" * 65)
    
    for symbol in symbols:
        info = cache.get_symbol_info(symbol)
        if info:
            # Отображаем значения как они приходят с биржи (строки)
            tick_size = str(info['tick_size'])
            step_size = str(info['step_size'])
            print(f"{symbol:<12} {tick_size:<15} {step_size:<15} {info['status']:<10}")
        else:
            print(f"{symbol:<12} {'N/A':<15} {'N/A':<15} {'N/A':<10}")

def main():
    """Главная функция"""
    symbols_to_test = ['BTCUSDT', 'ETHUSDT', 'NKNUSDT', 'SOLUSDT', 'DOGEUSDT']
    
    print("🚀 === GET SYMBOL INFO V2.0 ===")
    print(f"🌐 Режим: {'TESTNET' if config.BINANCE_TESTNET else 'MAINNET'}")
    
    # Показываем статистику кэша
    cache = get_symbol_cache()
    stats = cache.get_cache_stats()
    print(f"\n💾 === СТАТИСТИКА КЭША ===")
    print(f"   Символов в кэше: {stats['cached_symbols']}")
    print(f"   Кэш валиден: {stats['cache_valid']}")
    print(f"   Возраст кэша: {stats['cache_age']}")
    
    # Сравниваем символы
    print()
    compare_symbols(symbols_to_test)
    
    # Подробная информация для первого символа
    test_symbol = 'NKNUSDT'
    print(f"\n📋 === ПОДРОБНАЯ ИНФОРМАЦИЯ ===")
    get_symbol_info_from_cache(test_symbol)
    
    # Опционально: сравнение с API (медленнее)
    print(f"\n🔍 Хотите сравнить с данными API? (медленно)")
    print(f"Раскомментируйте строку в коде для получения данных напрямую с API")
    get_symbol_info_from_api(test_symbol)

if __name__ == "__main__":
    main()
