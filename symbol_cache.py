#!/usr/bin/env python3
"""
Symbol Cache Manager - Система кэширования информации о торговых символах
===========================================================================

ФУНКЦИОНАЛ:
✅ Загрузка фильтров всех символов из Binance API
✅ Сохранение в JSON для быстрого доступа
✅ Автоматическое обновление кэша
✅ Быстрое получение tick_size и step_size
✅ Валидация и округление цен/количеств

Author: HEDGER
Version: 1.0
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from binance.client import Client
from binance.exceptions import BinanceAPIException

from utils import logger
import config

class SymbolCache:
    """Менеджер кэша информации о символах"""
    
    def __init__(self, cache_file: str = "symbol_filters.json", cache_duration_hours: int = 24):
        """
        Инициализация кэша символов
        
        Args:
            cache_file: Имя файла кэша
            cache_duration_hours: Время жизни кэша в часах (по умолчанию 24ч)
        """
        self.cache_file = cache_file
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.cache_data: Dict = {}
        self.binance_client = None
        
        # Инициализация Binance клиента
        self._init_binance_client()
        
        logger.info(f"📊 Symbol Cache initialized (cache: {cache_file}, duration: {cache_duration_hours}h)")
    
    def _init_binance_client(self):
        """Инициализация Binance клиента"""
        try:
            if not config.BINANCE_API_KEY or not config.BINANCE_API_SECRET:
                logger.error("❌ Отсутствуют API ключи Binance")
                return
            
            self.binance_client = Client(
                api_key=config.BINANCE_API_KEY,
                api_secret=config.BINANCE_API_SECRET,
                testnet=config.BINANCE_TESTNET
            )
            
            logger.info(f"✅ Binance клиент инициализирован ({'TESTNET' if config.BINANCE_TESTNET else 'MAINNET'})")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Binance: {e}")
    
    def _load_tickers_from_file(self) -> List[str]:
        """Загружает список тикеров из tickers.txt"""
        try:
            if not os.path.exists("tickers.txt"):
                logger.warning("⚠️ Файл tickers.txt не найден, используем тестовый список")
                return ["BTCUSDT", "ETHUSDT", "NKNUSDT"]
            
            with open("tickers.txt", "r", encoding="utf-8") as f:
                content = f.read()
            
            # Извлекаем символы из файла (поддерживает разные форматы)
            import re
            symbols = re.findall(r"'([A-Z]+USDT)'", content)
            
            if not symbols:
                # Пробуем другой формат
                symbols = re.findall(r'"([A-Z]+USDT)"', content)
            
            if not symbols:
                # Пробуем построчно
                lines = content.strip().split('\n')
                symbols = [line.strip().strip("'\"") for line in lines 
                          if line.strip() and not line.startswith('#') and 'USDT' in line]
            
            logger.info(f"📋 Загружено {len(symbols)} символов из tickers.txt")
            return symbols
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки tickers.txt: {e}")
            return ["BTCUSDT", "ETHUSDT", "NKNUSDT"]  # Fallback
    
    def _is_cache_valid(self) -> bool:
        """Проверяет актуальность кэша"""
        if not os.path.exists(self.cache_file):
            return False
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cache_time = datetime.fromisoformat(data.get('timestamp', '1970-01-01'))
            return datetime.now() - cache_time < self.cache_duration
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка проверки кэша: {e}")
            return False
    
    def _fetch_symbol_filters(self, symbols: List[str]) -> Dict:
        """Загружает фильтры символов с Binance API"""
        if not self.binance_client:
            logger.error("❌ Binance клиент недоступен")
            return {}
        
        try:
            logger.info("🔄 Загрузка фильтров символов с Binance...")
            
            # Получаем информацию о бирже
            exchange_info = self.binance_client.futures_exchange_info()
            
            filters_data = {
                'timestamp': datetime.now().isoformat(),
                'symbols': {}
            }
            
            # Обрабатываем каждый символ
            found_count = 0
            for symbol_info in exchange_info['symbols']:
                symbol = symbol_info['symbol']
                
                if symbol in symbols:
                    found_count += 1
                    
                    # Извлекаем важные фильтры
                    price_filter = None
                    lot_size_filter = None
                    
                    for filter_info in symbol_info['filters']:
                        if filter_info['filterType'] == 'PRICE_FILTER':
                            price_filter = filter_info
                        elif filter_info['filterType'] == 'LOT_SIZE':
                            lot_size_filter = filter_info
                    
                    # Сохраняем компактную информацию
                    filters_data['symbols'][symbol] = {
                        'status': symbol_info['status'],
                        'tick_size': price_filter['tickSize'] if price_filter else "0.01",
                        'min_price': price_filter['minPrice'] if price_filter else "0.0",
                        'max_price': price_filter['maxPrice'] if price_filter else "0.0",
                        'step_size': lot_size_filter['stepSize'] if lot_size_filter else "0.001",
                        'min_qty': lot_size_filter['minQty'] if lot_size_filter else "0.0",
                        'max_qty': lot_size_filter['maxQty'] if lot_size_filter else "0.0",
                        'precision_price': len(str(price_filter['tickSize']).split('.')[-1].rstrip('0')) if price_filter else 2,
                        'precision_qty': len(str(lot_size_filter['stepSize']).split('.')[-1].rstrip('0')) if lot_size_filter else 3
                    }
            
            logger.info(f"✅ Загружено фильтров для {found_count}/{len(symbols)} символов")
            return filters_data
            
        except BinanceAPIException as e:
            logger.error(f"❌ Binance API Error: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки фильтров: {e}")
            return {}
    
    def _save_cache(self, data: Dict):
        """Сохраняет кэш в файл"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Кэш сохранен в {self.cache_file}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения кэша: {e}")
    
    def _load_cache(self) -> Dict:
        """Загружает кэш из файла"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки кэша: {e}")
            return {}
    
    def update_cache(self, force: bool = False) -> bool:
        """
        Обновляет кэш символов
        
        Args:
            force: Принудительное обновление даже если кэш актуален
            
        Returns:
            bool: True если кэш успешно обновлен
        """
        try:
            if not force and self._is_cache_valid():
                logger.info("✅ Кэш актуален, обновление не требуется")
                self.cache_data = self._load_cache()
                return True
            
            logger.info("🔄 Обновление кэша символов...")
            
            # Загружаем список символов
            symbols = self._load_tickers_from_file()
            
            # Получаем фильтры
            filters_data = self._fetch_symbol_filters(symbols)
            
            if filters_data:
                # Сохраняем кэш
                self._save_cache(filters_data)
                self.cache_data = filters_data
                
                logger.info(f"✅ Кэш обновлен успешно ({len(filters_data.get('symbols', {}))} символов)")
                return True
            else:
                logger.error("❌ Не удалось получить данные для кэша")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления кэша: {e}")
            return False
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """
        Получает информацию о символе из кэша
        
        Args:
            symbol: Торговый символ (например 'BTCUSDT')
            
        Returns:
            Dict с информацией о символе или None если не найден
        """
        if not self.cache_data:
            if not self.update_cache():
                return None
        
        return self.cache_data.get('symbols', {}).get(symbol.upper())
    
    def round_price(self, symbol: str, price: float) -> float:
        """
        Округляет цену согласно tick_size символа
        
        Args:
            symbol: Торговый символ
            price: Цена для округления
            
        Returns:
            float: Округленная цена
        """
        info = self.get_symbol_info(symbol)
        if not info:
            # Fallback округление
            if 'BTC' in symbol:
                return round(price, 1)
            return round(price, 2)
        
        try:
            tick_size = Decimal(str(info['tick_size']))
            price_decimal = Decimal(str(price))
            rounded = (price_decimal / tick_size).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * tick_size
            return float(rounded)
        except:
            # Fallback если что-то пошло не так
            precision = info.get('precision_price', 2)
            return round(price, precision)
    
    def round_quantity(self, symbol: str, quantity: float) -> float:
        """
        Округляет количество согласно step_size символа
        
        Args:
            symbol: Торговый символ
            quantity: Количество для округления
            
        Returns:
            float: Округленное количество
        """
        info = self.get_symbol_info(symbol)
        if not info:
            # Fallback округление
            if 'BTC' in symbol:
                return round(quantity, 3)
            return round(quantity, 6)
        
        try:
            step_size = Decimal(str(info['step_size']))
            qty_decimal = Decimal(str(quantity))
            rounded = (qty_decimal / step_size).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * step_size
            return float(rounded)
        except:
            # Fallback если что-то пошло не так
            precision = info.get('precision_qty', 3)
            return round(quantity, precision)
    
    def validate_order_params(self, symbol: str, price: float, quantity: float) -> Tuple[float, float, bool]:
        """
        Валидирует и корректирует параметры ордера
        
        Args:
            symbol: Торговый символ
            price: Цена ордера
            quantity: Количество ордера
            
        Returns:
            Tuple[float, float, bool]: (округленная_цена, округленное_количество, валидность)
        """
        info = self.get_symbol_info(symbol)
        
        # Округляем параметры
        rounded_price = self.round_price(symbol, price)
        rounded_quantity = self.round_quantity(symbol, quantity)
        
        # Проверяем лимиты если есть информация
        if info:
            min_price = float(info['min_price']) if isinstance(info['min_price'], str) else info['min_price']
            max_price = float(info['max_price']) if isinstance(info['max_price'], str) else info['max_price']
            min_qty = float(info['min_qty']) if isinstance(info['min_qty'], str) else info['min_qty']
            max_qty = float(info['max_qty']) if isinstance(info['max_qty'], str) else info['max_qty']
            
            is_valid = (
                min_price <= rounded_price <= max_price and
                min_qty <= rounded_quantity <= max_qty
            )
        else:
            # Базовая проверка
            is_valid = rounded_price > 0 and rounded_quantity > 0
        
        return rounded_price, rounded_quantity, is_valid
    
    def get_cache_stats(self) -> Dict:
        """Получает статистику кэша"""
        if not self.cache_data:
            return {'cached_symbols': 0, 'cache_age': 'No cache', 'cache_valid': False}
        
        try:
            cache_time = datetime.fromisoformat(self.cache_data.get('timestamp', '1970-01-01'))
            age = datetime.now() - cache_time
            
            return {
                'cached_symbols': len(self.cache_data.get('symbols', {})),
                'cache_age': str(age),
                'cache_valid': age < self.cache_duration,
                'cache_file': self.cache_file,
                'last_update': self.cache_data.get('timestamp', 'Unknown')
            }
        except:
            return {'cached_symbols': 0, 'cache_age': 'Invalid', 'cache_valid': False}


# Глобальный экземпляр кэша (Singleton pattern)
_symbol_cache_instance = None

def get_symbol_cache() -> SymbolCache:
    """Получает глобальный экземпляр кэша символов (Singleton)"""
    global _symbol_cache_instance
    if _symbol_cache_instance is None:
        _symbol_cache_instance = SymbolCache()
    return _symbol_cache_instance


# Convenience функции для быстрого доступа
def round_price_for_symbol(symbol: str, price: float) -> float:
    """Быстрое округление цены для символа"""
    return get_symbol_cache().round_price(symbol, price)

def round_quantity_for_symbol(symbol: str, quantity: float) -> float:
    """Быстрое округление количества для символа"""
    return get_symbol_cache().round_quantity(symbol, quantity)

def validate_order_for_symbol(symbol: str, price: float, quantity: float) -> Tuple[float, float, bool]:
    """Быстрая валидация ордера для символа"""
    return get_symbol_cache().validate_order_params(symbol, price, quantity)


# Тест системы кэша
def test_symbol_cache():
    """Тестирует систему кэша символов"""
    logger.info("🧪 === ТЕСТ СИСТЕМЫ КЭША СИМВОЛОВ ===")
    
    try:
        # Создаем экземпляр кэша
        cache = SymbolCache()
        
        # Обновляем кэш
        logger.info("🔄 Обновление кэша...")
        success = cache.update_cache(force=True)
        
        if not success:
            logger.error("❌ Не удалось обновить кэш")
            return
        
        # Показываем статистику
        stats = cache.get_cache_stats()
        logger.info(f"📊 === СТАТИСТИКА КЭША ===")
        logger.info(f"   Символов в кэше: {stats['cached_symbols']}")
        logger.info(f"   Возраст кэша: {stats['cache_age']}")
        logger.info(f"   Кэш валиден: {stats['cache_valid']}")
        logger.info(f"   Файл: {stats['cache_file']}")
        
        # Тестируем несколько символов
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'NKNUSDT']
        test_price = 50000.12345
        test_quantity = 0.12345678
        
        logger.info(f"🧪 === ТЕСТ ОКРУГЛЕНИЯ ===")
        for symbol in test_symbols:
            info = cache.get_symbol_info(symbol)
            if info:
                rounded_price = cache.round_price(symbol, test_price)
                rounded_qty = cache.round_quantity(symbol, test_quantity)
                valid_price, valid_qty, is_valid = cache.validate_order_params(symbol, test_price, test_quantity)
                
                logger.info(f"   {symbol}:")
                logger.info(f"     Tick Size: {info['tick_size']}")
                logger.info(f"     Step Size: {info['step_size']}")
                logger.info(f"     {test_price:.8f} → {rounded_price:.8f}")
                logger.info(f"     {test_quantity:.8f} → {rounded_qty:.8f}")
                logger.info(f"     Валидность: {is_valid}")
            else:
                logger.warning(f"   {symbol}: информация не найдена")
        
        logger.info("✅ === ТЕСТ ЗАВЕРШЕН УСПЕШНО ===")
        
    except Exception as e:
        logger.error(f"❌ Ошибка теста: {e}")


if __name__ == "__main__":
    test_symbol_cache()
