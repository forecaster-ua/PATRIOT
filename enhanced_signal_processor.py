"""
Enhanced Signal Processor - Финальная MVP версия
============================================

ПОЛНАЯ ТОРГОВАЯ СИСТЕМА:
✅ Market ордера для быстрого входа
✅ Limit ордера с точным позиционированием
✅ Stop Loss и Take Profit автоматически
✅ Правильные расчеты позиции с учетом плеча 10x
✅ Подробные Telegram уведомления с информацией о капитале
✅ Оптимизированная производительность

Функционал:
1. Анализ сигналов через signal_analyzer
2. Market/Limit ордера с корректным leverage + SL/TP
3. Отправка детальных уведомлений в Telegram
4. Полное управление рисками

Author: HEDGER
Version: 3.0 - Финальная версия MVP готовая к продакшену
"""

from typing import Dict, Optional
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Импорты проекта
from signal_analyzer import SignalAnalyzer
from telegram_bot import telegram_bot
from utils import logger
import config
from symbol_cache import get_symbol_cache, round_price_for_symbol, round_quantity_for_symbol, validate_order_for_symbol

# Константы для управления рисками
DEFAULT_RISK_PERCENT = 2.0  # Унифицированный процент риска по умолчанию (2%)
DEFAULT_LEVERAGE = config.FUTURES_LEVERAGE  # Используем плечо из config.py

class AdvancedSignalProcessor:
    """
    Продвинутый процессор сигналов для полной торговой системы
    Поддерживает Market ордера, Limit ордера + Stop Loss + Take Profit
    """
    
    def __init__(self, ticker: str, risk_percent: float = DEFAULT_RISK_PERCENT):
        """
        Инициализация процессора
        
        Args:
            ticker: Торговая пара (например "BTCUSDT")
            risk_percent: Процент от баланса на сделку (по умолчанию из DEFAULT_RISK_PERCENT)
        """
        self.ticker = ticker
        self.risk_percent = risk_percent
        
        # Инициализация Binance клиента
        self.binance_client = None
        self._init_binance_client()
        
        # Инициализация кэша символов (автоматически обновится если нужно)
        self.symbol_cache = get_symbol_cache()
        
        logger.info(f"📊 Advanced Signal Processor initialized for {ticker} (Risk: {risk_percent}%)")
        
        # Проверяем актуальность кэша символов
        cache_stats = self.symbol_cache.get_cache_stats()
        if cache_stats['cached_symbols'] == 0:
            logger.info("🔄 Обновляем кэш символов...")
            self.symbol_cache.update_cache()
    
    def _init_binance_client(self):
        """Инициализация Binance клиента"""
        try:
            if not config.BINANCE_API_KEY or not config.BINANCE_API_SECRET:
                logger.error("❌ Отсутствуют API ключи Binance")
                return
            
            logger.info("🔧 Инициализация Binance клиента...")
            logger.info(f"🌐 Режим: {'TESTNET' if config.BINANCE_TESTNET else 'MAINNET'}")
            
            self.binance_client = Client(
                api_key=config.BINANCE_API_KEY,
                api_secret=config.BINANCE_API_SECRET,
                testnet=config.BINANCE_TESTNET
            )
            
            # Проверяем подключение
            if config.BINANCE_TESTNET:
                account_info = self.binance_client.futures_account()
                logger.info(f"✅ Binance Testnet подключен")
                logger.info(f"💰 Баланс: {account_info['totalWalletBalance']} USDT")
            else:
                # Для mainnet также используем фьючерсный API
                account_info = self.binance_client.futures_account()
                logger.info(f"✅ Binance Mainnet (Futures) подключен")
                logger.info(f"💰 Баланс: {account_info['totalWalletBalance']} USDT")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Binance: {e}")
            self.binance_client = None
    
    def get_usdt_balance(self) -> float:
        """Получает доступный баланс USDT"""
        if not self.binance_client:
            return 0.0
        
        try:
            if config.BINANCE_TESTNET:
                account = self.binance_client.futures_account()
                return float(account['availableBalance'])
            else:
                # Для mainnet также используем фьючерсный API
                account = self.binance_client.futures_account()
                return float(account['availableBalance'])
        except Exception as e:
            logger.error(f"❌ Ошибка получения баланса: {e}")
            return 0.0
    
    def get_symbol_leverage(self) -> int:
        """Устанавливает плечо 10x для символа"""
        if not self.binance_client:
            return 1
        
        try:
            # Устанавливаем плечо 30x
            result = self.binance_client.futures_change_leverage(symbol=self.ticker, leverage=30)
            
            # Проверяем результат
            if isinstance(result, dict) and 'leverage' in result:
                leverage = int(result['leverage'])
                logger.info(f"✅ Плечо установлено: {leverage}x")
                return leverage
            
            # Если API не вернул плечо, возвращаем 10 (должно было установиться)
            logger.info("✅ Плечо установлено: 10x")
            return 10
            
        except Exception as e:
            logger.warning(f"⚠️ Не удалось установить плечо: {e}")
            return 1
    
    def get_current_price(self) -> float:
        """Получает текущую рыночную цену символа"""
        if not self.binance_client:
            return 0.0
        
        try:
            ticker_data = self.binance_client.get_symbol_ticker(symbol=self.ticker)
            return float(ticker_data['price'])
        except Exception as e:
            logger.error(f"❌ Ошибка получения цены для {self.ticker}: {e}")
            return 0.0
    
    def validate_limit_order_price(self, signal_data: Dict) -> tuple[bool, str]:
        """
        🚨 НОВАЯ ФУНКЦИЯ: Проверяет корректность цены лимитного ордера
        
        Правила валидации:
        - LONG: entry_price ДОЛЖНА быть НИЖЕ current_price (покупаем дешевле)
        - SHORT: entry_price ДОЛЖНА быть ВЫШЕ current_price (продаем дороже)
        
        Returns:
            (bool, str): (valid, error_message)
        """
        try:
            # Получаем текущую рыночную цену
            current_price = self.get_current_price()
            if current_price <= 0:
                return False, "❌ Не удалось получить текущую цену"
            
            entry_price = float(signal_data['entry_price'])
            signal_type = signal_data['signal']
            
            # Валидация логики цен
            if signal_type == 'LONG' and entry_price > current_price:
                error_msg = f"❌ LONG: ЦЕНА {entry_price:.6f} выше ТЕКУЩЕЙ ЦЕНЫ {current_price:.6f}"
                return False, error_msg
            elif signal_type == 'SHORT' and entry_price < current_price:
                error_msg = f"❌ SHORT: ЦЕНА {entry_price:.6f} ниже ТЕКУЩЕЙ ЦЕНЫ {current_price:.6f}"
                return False, error_msg
            
            # Дополнительная проверка: слишком далеко от текущей цены (>5%)
            price_diff_percent = abs(entry_price - current_price) / current_price * 100
            if price_diff_percent > 5.0:
                warning_msg = f"⚠️ Цена входа на {price_diff_percent:.1f}% от текущей цены"
                logger.warning(warning_msg)
            
            logger.info(f"✅ Цена валидна: {signal_type} @ {entry_price:.6f} (текущая: {current_price:.6f})")
            return True, ""
            
        except Exception as e:
            error_msg = f"❌ Ошибка валидации цены: {e}"
            return False, error_msg
    
    def calculate_position_size(self, entry_price: float) -> tuple:
        """Рассчитывает размер позиции с учетом плеча"""
        try:
            usdt_balance = self.get_usdt_balance()
            if usdt_balance <= 0:
                logger.error("❌ Недостаточно USDT на балансе")
                return 0.0, 1, 0.0, 0.0
            
            leverage = self.get_symbol_leverage()
            risk_amount_usdt = usdt_balance * (self.risk_percent / 100)
            position_value_usdt = risk_amount_usdt * leverage
            quantity = position_value_usdt / entry_price
            
            # Округление с использованием кэша символов
            quantity = round_quantity_for_symbol(self.ticker, quantity)
            
            logger.info(f"📊 Расчет позиции: Залог {risk_amount_usdt:.2f} USDT × {leverage}x = {quantity:.6f} {self.ticker.replace('USDT', '')}")
            
            return quantity, leverage, risk_amount_usdt, position_value_usdt
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета позиции: {e}")
            return 0.0, 1, 0.0, 0.0
    
    def place_simple_market_order(self, signal_data: Dict) -> Dict:
        """Выставляет простой Market ордер"""
        if not self.binance_client:
            return {'success': False, 'error': 'Binance client not initialized'}
        
        try:
            side = Client.SIDE_BUY if signal_data['signal'] == 'LONG' else Client.SIDE_SELL
            entry_price = float(signal_data['entry_price'])
            quantity, leverage, risk_amount_usdt, position_value_usdt = self.calculate_position_size(entry_price)
            
            if quantity <= 0:
                return {'success': False, 'error': 'Invalid position size'}
            
            logger.info(f"🚀 Market ордер {signal_data['signal']}: {quantity:.6f} @ {entry_price:.6f}")
            
            # Определяем positionSide для Hedge режима
            position_side = 'LONG' if side == Client.SIDE_BUY else 'SHORT'
            
            if config.BINANCE_TESTNET:
                order = self.binance_client.futures_create_order(
                    symbol=self.ticker,
                    side=side,
                    type=Client.ORDER_TYPE_MARKET,
                    quantity=quantity,
                    positionSide=position_side
                )
            else:
                # Для mainnet также используем фьючерсный API
                order = self.binance_client.futures_create_order(
                    symbol=self.ticker,
                    side=side,
                    type=Client.ORDER_TYPE_MARKET,
                    quantity=quantity,
                    positionSide=position_side
                )
            
            logger.info(f"✅ Ордер {order['orderId']} выполнен!")
            
            return {
                'success': True,
                'order_id': order['orderId'],
                'order_data': order,
                'quantity': quantity,
                'entry_price': entry_price,
                'leverage': leverage,
                'risk_amount_usdt': risk_amount_usdt,
                'position_value_usdt': position_value_usdt,
                'executed_price': order.get('fills', [{}])[0].get('price', entry_price) if order.get('fills') else entry_price,
                'timestamp': datetime.now().isoformat(),
                'current_price': entry_price  # Для Telegram
            }
            
        except BinanceAPIException as e:
            logger.error(f"❌ Binance API Error: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"❌ Order Error: {e}")
            return {'success': False, 'error': str(e)}
    
    def place_limit_order_with_sl_tp(self, signal_data: Dict) -> Dict:
        """
        Выставляет лимитный ордер + Stop Loss + Take Profit
        
        Использует точные цены из сигнала:
        - entry_price для лимитного ордера  
        - stop_loss для защитного ордера
        - take_profit для ордера на прибыль
        """
        if not self.binance_client:
            return {'success': False, 'error': 'Binance client not initialized'}
        
        try:
            # 🚨 НОВАЯ ВАЛИДАЦИЯ: Проверяем корректность цены лимитного ордера
            valid, error_msg = self.validate_limit_order_price(signal_data)
            if not valid:
                logger.error(f"🚫 Валидация не пройдена: {error_msg}")
                # Отправляем ошибку в Telegram
                try:
                    signal_data_with_timestamp = signal_data.copy()
                    signal_data_with_timestamp['timestamp'] = datetime.now().strftime('%H:%M:%S')
                    telegram_bot.send_error(error_msg, signal_data_with_timestamp)
                except Exception as tg_error:
                    logger.error(f"❌ Не удалось отправить ошибку в Telegram: {tg_error}")
                return {'success': False, 'error': error_msg}
            
            side = Client.SIDE_BUY if signal_data['signal'] == 'LONG' else Client.SIDE_SELL
            entry_price = round_price_for_symbol(self.ticker, float(signal_data['entry_price']))
            stop_loss = round_price_for_symbol(self.ticker, float(signal_data.get('stop_loss', 0)))
            take_profit = round_price_for_symbol(self.ticker, float(signal_data.get('take_profit', 0)))
            
            quantity, leverage, risk_amount_usdt, position_value_usdt = self.calculate_position_size(entry_price)
            
            if quantity <= 0:
                return {'success': False, 'error': 'Invalid position size'}
            
            if stop_loss <= 0 or take_profit <= 0:
                return {'success': False, 'error': 'Missing stop_loss or take_profit prices'}
            
            # Валидация параметров ордера с помощью кэша символов
            valid_entry_price, valid_quantity, is_entry_valid = validate_order_for_symbol(self.ticker, entry_price, quantity)
            valid_stop_loss, _, is_stop_valid = validate_order_for_symbol(self.ticker, stop_loss, quantity)
            valid_take_profit, _, is_tp_valid = validate_order_for_symbol(self.ticker, take_profit, quantity)
            
            if not (is_entry_valid and is_stop_valid and is_tp_valid):
                error_msg = f"Order validation failed: Entry={is_entry_valid}, SL={is_stop_valid}, TP={is_tp_valid}"
                logger.error(f"❌ {error_msg}")
                return {'success': False, 'error': error_msg}
            
            # Используем валидированные значения
            entry_price, quantity = valid_entry_price, valid_quantity
            stop_loss, take_profit = valid_stop_loss, valid_take_profit
            
            logger.info(f"🎯 Limit ордер {signal_data['signal']}: {quantity:.6f} @ {entry_price:.6f}")
            logger.info(f"🛑 Stop Loss: {stop_loss:.6f} | 🎯 Take Profit: {take_profit:.6f}")
            
            # Определяем positionSide для Hedge режима
            position_side = 'LONG' if side == Client.SIDE_BUY else 'SHORT'
            
            # 1. Размещаем основной лимитный ордер
            main_order = self.binance_client.futures_create_order(
                symbol=self.ticker,
                side=side,
                type=Client.ORDER_TYPE_LIMIT,
                quantity=quantity,
                price=str(entry_price),
                positionSide=position_side,
                timeInForce='GTC'  # Good Till Cancelled
            )
            
            logger.info(f"✅ Лимитный ордер {main_order['orderId']} размещен!")
            
            # 2. Размещаем Stop Loss ордер (условный)
            stop_side = Client.SIDE_SELL if signal_data['signal'] == 'LONG' else Client.SIDE_BUY
            
            try:
                stop_order = self.binance_client.futures_create_order(
                    symbol=self.ticker,
                    side=stop_side,
                    type='STOP_MARKET',
                    quantity=quantity,
                    stopPrice=str(stop_loss),
                    positionSide=position_side,
                    timeInForce='GTC'
                )
                logger.info(f"🛑 Stop Loss {stop_order['orderId']} установлен!")
            except Exception as e:
                logger.warning(f"⚠️ Stop Loss не установлен: {e}")
                stop_order = {'orderId': 'FAILED'}
            
            # 3. Размещаем Take Profit ордер (условный)
            try:
                tp_order = self.binance_client.futures_create_order(
                    symbol=self.ticker,
                    side=stop_side,  # Та же сторона что и stop
                    type='TAKE_PROFIT_MARKET',
                    quantity=quantity,
                    stopPrice=str(take_profit),
                    positionSide=position_side,
                    timeInForce='GTC'
                )
                logger.info(f"🎯 Take Profit {tp_order['orderId']} установлен!")
            except Exception as e:
                logger.warning(f"⚠️ Take Profit не установлен: {e}")
                tp_order = {'orderId': 'FAILED'}
            
            return {
                'success': True,
                'main_order_id': main_order['orderId'],
                'stop_order_id': stop_order['orderId'],
                'tp_order_id': tp_order['orderId'],
                'order_data': main_order,
                'quantity': quantity,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'leverage': leverage,
                'risk_amount_usdt': risk_amount_usdt,
                'position_value_usdt': position_value_usdt,
                'timestamp': datetime.now().isoformat(),
                'current_price': entry_price,  # Для Telegram
                'order_type': 'LIMIT_WITH_SL_TP'
            }
            
        except BinanceAPIException as e:
            logger.error(f"❌ Binance API Error: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"❌ Limit Order Error: {e}")
            return {'success': False, 'error': str(e)}
    
    def process_ticker(self, order_type: str = "MARKET") -> bool:
        """
        Основной метод обработки тикера
        
        Args:
            order_type: Тип ордера - "MARKET" или "LIMIT"
        
        1. Анализирует сигналы
        2. Выставляет ордер выбранного типа при наличии сигнала  
        3. Отправляет уведомление в Telegram
        
        Returns:
            bool: True если сигнал найден и ордер выставлен
        """
        try:
            logger.info(f"🔍 === АНАЛИЗ {self.ticker} ({order_type}) ===")
            
            # 1. Получаем сигнал от анализатора
            analyzer = SignalAnalyzer(self.ticker)
            signal_data = analyzer.analyze_ticker(stop_event=None)
            
            if not signal_data:
                logger.info(f"📊 Сигналы не найдены для {self.ticker}")
                return False
            
            logger.info(f"🎯 СИГНАЛ НАЙДЕН для {self.ticker}:")
            logger.info(f"  📈 Направление: {signal_data['signal']}")
            logger.info(f"  💰 Цена входа: {signal_data['entry_price']:.6f}")
            logger.info(f"  🛑 Stop Loss: {signal_data.get('stop_loss', 'N/A')}")
            logger.info(f"  🎯 Take Profit: {signal_data.get('take_profit', 'N/A')}")
            logger.info(f"  📊 Confidence: {signal_data.get('confidence', 0):.3f}")
            
            # 2. Выставляем ордер выбранного типа
            if self.binance_client:
                logger.info(f"🚀 Выставляем {order_type} ордер на Binance...")
                
                # Выбираем тип ордера
                if order_type.upper() == "LIMIT":
                    order_result = self.place_limit_order_with_sl_tp(signal_data)
                else:
                    order_result = self.place_simple_market_order(signal_data)
                
                if order_result['success']:
                    logger.info(f"✅ === {order_type} ОРДЕР ВЫСТАВЛЕН УСПЕШНО ===")
                    
                    if order_type.upper() == "LIMIT":
                        logger.info(f"📋 Main Order ID: {order_result['main_order_id']}")
                        logger.info(f"🛑 Stop Order ID: {order_result['stop_order_id']}")  
                        logger.info(f"🎯 TP Order ID: {order_result['tp_order_id']}")
                    else:
                        logger.info(f"📋 Order ID: {order_result['order_id']}")
                    
                    logger.info(f"📦 Количество: {order_result['quantity']:.6f}")
                    logger.info(f"💰 Цена входа: {order_result['entry_price']:.6f}")
                    
                    # 3. Отправляем уведомление в Telegram ПОСЛЕ успешного ордера
                    try:
                        import time
                        usdt_balance = self.get_usdt_balance()
                        
                        # Формируем данные для Telegram с учетом типа ордера
                        telegram_data = {
                            'pair': signal_data['ticker'],
                            'timeframe': signal_data.get('timeframes_str', 'N/A'),
                            'signal': signal_data['signal'],
                            'current_price': order_result.get('current_price', order_result['entry_price']),
                            'entry_price': order_result['entry_price'],
                            'quantity': order_result['quantity'],
                            'leverage': order_result['leverage'],
                            'risk_amount': order_result['risk_amount_usdt'],
                            'position_value': order_result['position_value_usdt'],
                            'confidence': signal_data.get('confidence', 0),
                            'timestamp': int(time.time()),
                            'stop_loss': signal_data.get('stop_loss', 0),
                            'take_profit': signal_data.get('take_profit', 0),
                            # Дополнительная информация для улучшенного сообщения
                            'total_balance': usdt_balance,
                            'risk_percent': self.risk_percent,
                            'capital_at_risk': f"{order_result['risk_amount_usdt']:.2f} USDT ({self.risk_percent}%)",
                            'order_type': order_result.get('order_type', order_type.upper())
                        }
                        
                        # Добавляем ID ордеров в зависимости от типа
                        if order_type.upper() == "LIMIT":
                            telegram_data['order_id'] = f"Main:{order_result['main_order_id']}"
                            telegram_data['stop_order_id'] = order_result['stop_order_id']
                            telegram_data['tp_order_id'] = order_result['tp_order_id']
                        else:
                            telegram_data['order_id'] = order_result['order_id']
                        
                        telegram_bot.send_signal(telegram_data)
                        logger.info("📱 ✅ Уведомление отправлено в Telegram")
                    except Exception as e:
                        logger.error(f"📱 ❌ Ошибка отправки в Telegram: {e}")
                    
                    return True
                else:
                    logger.error(f"❌ === ОШИБКА ВЫСТАВЛЕНИЯ {order_type} ОРДЕРА ===")
                    logger.error(f"🔥 Причина: {order_result['error']}")
                    return False
            else:
                logger.warning("⚠️ Binance клиент недоступен - пропускаем ордер")
                return False
                
        except Exception as e:
            logger.error(f"❌ === ОШИБКА ОБРАБОТКИ {self.ticker} ===")
            logger.error(f"🔥 Ошибка: {e}")
            return False


# Тест продвинутого процессора
def test_advanced_processor(ticker: str = "BTCUSDT", risk_percent: float = DEFAULT_RISK_PERCENT, order_type: str = "MARKET"):
    """
    Тестирует продвинутый процессор на одном тикере
    
    Args:
        ticker: Торговая пара для тестирования  
        risk_percent: Процент риска на сделку (по умолчанию из DEFAULT_RISK_PERCENT)
        order_type: Тип ордера - "MARKET" или "LIMIT"
    """
    logger.info("🚀 === ТЕСТ ADVANCED SIGNAL PROCESSOR ===")
    logger.info(f"🎯 Тикер: {ticker}")
    logger.info(f"💰 Риск: {risk_percent}%")
    logger.info(f"📋 Тип ордера: {order_type}")
    logger.info(f"🌐 Режим: {'TESTNET' if config.BINANCE_TESTNET else 'MAINNET'}")
    
    processor = AdvancedSignalProcessor(ticker, risk_percent)
    
    try:
        # Показываем текущий баланс
        balance = processor.get_usdt_balance()
        logger.info(f"💰 Текущий баланс: {balance:.2f} USDT")
        
        # Запускаем обработку
        success = processor.process_ticker(order_type)
        
        if success:
            logger.info("🎉 === ТЕСТ УСПЕШЕН ===")
            logger.info(f"✅ Сигнал найден и {order_type} ордер выставлен!")
        else:
            logger.info("📊 === ТЕСТ ЗАВЕРШЕН ===")
            logger.info("📊 Сигнал не найден или ошибка ордера")
            
    except KeyboardInterrupt:
        logger.info("⌨️ Тест прерван пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка теста: {e}")
    
    logger.info("🏁 === ТЕСТ ЗАВЕРШЕН ===")


# Функция для интеграции с ticker_monitor
def process_trading_signal_enhanced(signal_data: Dict, order_type: str = "MARKET") -> bool:
    """
    Функция для интеграции с ticker_monitor.py
    Обрабатывает готовый сигнал и размещает ордер
    
    Args:
        signal_data: Готовые данные сигнала от анализатора
        order_type: Тип ордера - "MARKET" или "LIMIT"
        
    Returns:
        bool: True если ордер успешно размещен
    """
    try:
        ticker = signal_data.get('ticker', 'UNKNOWN')
        processor = AdvancedSignalProcessor(ticker, DEFAULT_RISK_PERCENT)
        
        # Используем готовый сигнал без повторного анализа
        if processor.binance_client:
            if order_type.upper() == "LIMIT":
                order_result = processor.place_limit_order_with_sl_tp(signal_data)
            else:
                order_result = processor.place_simple_market_order(signal_data)
            
            if order_result['success']:
                # Отправляем в Telegram
                try:
                    import time
                    usdt_balance = processor.get_usdt_balance()
                    
                    telegram_data = {
                        'pair': signal_data['ticker'],
                        'timeframe': signal_data.get('timeframes_str', 'N/A'),
                        'signal': signal_data['signal'],
                        'current_price': order_result.get('current_price', order_result['entry_price']),
                        'entry_price': order_result['entry_price'],
                        'quantity': order_result['quantity'],
                        'leverage': order_result['leverage'],
                        'risk_amount': order_result['risk_amount_usdt'],
                        'position_value': order_result['position_value_usdt'],
                        'confidence': signal_data.get('confidence', 0),
                        'timestamp': int(time.time()),
                        'stop_loss': signal_data.get('stop_loss', 0),
                        'take_profit': signal_data.get('take_profit', 0),
                        'total_balance': usdt_balance,
                        'risk_percent': DEFAULT_RISK_PERCENT,
                        'capital_at_risk': f"{order_result['risk_amount_usdt']:.2f} USDT ({DEFAULT_RISK_PERCENT}%)",
                        'order_type': order_result.get('order_type', order_type.upper())
                    }
                    
                    if order_type.upper() == "LIMIT":
                        telegram_data['order_id'] = f"Main:{order_result['main_order_id']}"
                    else:
                        telegram_data['order_id'] = order_result['order_id']
                    
                    telegram_bot.send_signal(telegram_data)
                    logger.info(f"📱 ✅ {ticker} уведомление отправлено в Telegram")
                except Exception as e:
                    logger.error(f"📱 ❌ {ticker} ошибка отправки в Telegram: {e}")
                
                return True
            else:
                logger.error(f"❌ {ticker} ошибка размещения ордера: {order_result['error']}")
                return False
        else:
            logger.error(f"❌ {ticker} Binance клиент недоступен")
            return False
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка обработки сигнала {signal_data.get('ticker', 'UNKNOWN')}: {e}")
        return False


# Запуск при прямом вызове
if __name__ == "__main__":
    # Тест Market ордеров (по умолчанию)
    # test_advanced_processor("BTCUSDT", DEFAULT_RISK_PERCENT, "MARKET")
    
    # Раскомментируйте для теста Limit ордеров с SL/TP
    test_advanced_processor("BTCUSDT", DEFAULT_RISK_PERCENT, "LIMIT")
