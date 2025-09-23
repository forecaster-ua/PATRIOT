"""
Order Executor - Исполнение торговых ордеров
==========================================

ИНТЕГРАЦИЯ В СУЩЕСТВУЮЩУЮ АРХИТЕКТУРУ:
ticker_monitor.py → signal_analyzer.py → [ЭТОТ МОДУЛЬ] → telegram_bot.py
                                               ↓
                                      websocket_monitor.py

Функции:
1. Получает сигнал от signal_analyzer
2. Рассчитывает размер позиции (2% от общего капитала)
3. Выставляет ордер на Binance
4. Передает ордер в websocket мониторинг
5. Отправляет уведомление в Telegram

Author: HEDGER
Version: 1.0 - MVP Integration
"""

from typing import Dict, Optional, Tuple, List
from decimal import Decimal, ROUND_UP, ROUND_HALF_UP
from datetime import datetime, timedelta
import time
import threading
import asyncio

# Локальные импорты
from utils import logger
from telegram_bot import telegram_bot
from symbol_cache import get_symbol_cache, round_price_for_symbol, round_quantity_for_symbol, calculate_leverage_for_symbol
from config import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET, MULTIPLE_ORDERS, MAX_CONCURRENT_ORDERS, RISK_PERCENT, FUTURES_LEVERAGE, FUTURES_MARGIN_TYPE

# Синхронизация заказов
try:
    from unified_sync import validate_signal_before_execution
    SYNC_AVAILABLE = True
    logger.info("✅ Orders Synchronizer подключен")
except ImportError:
    logger.warning("⚠️ Orders Synchronizer недоступен")
    SYNC_AVAILABLE = False
    def validate_signal_before_execution(symbol, side, quantity) -> Tuple[bool, str]:
        """Mock validation when synchronizer is not available"""
        return True, "Synchronizer недоступен"

# Binance
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Мониторинг ордеров через Orders Watchdog
try:
    from orders_watchdog import watchdog_api
    WATCHDOG_AVAILABLE = True
    logger.info("✅ Orders Watchdog API подключен")
except ImportError:
    logger.warning("⚠️ Orders Watchdog не доступен, используем старый мониторинг")
    WATCHDOG_AVAILABLE = False
    watchdog_api = None
    # Fallback к старому мониторингу
    try:
        from websocket_monitor import order_monitor
    except ImportError:
        logger.warning("⚠️ websocket_monitor тоже недоступен")
        order_monitor = None

# Теперь используем константы из config.py вместо локальных

class OrderExecutor:
    """Исполнитель торговых ордеров"""
    
    def __init__(self):
        """Инициализация исполнителя"""
        global order_lifecycle_manager
        
        self.binance_client = None
        self.symbol_cache = get_symbol_cache()
        self.order_lock = threading.Lock()  # 🔒 Thread-safe lock для проверки ордеров
        self._init_binance_client()
        
        # Создаем lifecycle manager после инициализации
        order_lifecycle_manager = OrderLifecycleManager(self)
        self.lifecycle_manager = order_lifecycle_manager
        
        logger.info(f"🎯 OrderExecutor initialized (Risk: {RISK_PERCENT}%, Leverage: {FUTURES_LEVERAGE}x)")
        logger.info(f"📋 Order Lifecycle Management активирован")
    
    def _init_binance_client(self) -> None:
        """Инициализация Binance клиента"""
        try:
            if not BINANCE_API_KEY or not BINANCE_API_SECRET:
                logger.error("❌ Binance API ключи не настроены")
                return
            
            logger.info(f"🔧 Подключение к Binance ({'TESTNET' if BINANCE_TESTNET else 'MAINNET'})...")
            
            self.binance_client = Client(
                api_key=BINANCE_API_KEY,
                api_secret=BINANCE_API_SECRET,
                testnet=BINANCE_TESTNET
            )
            
            # Проверяем подключение
            if BINANCE_TESTNET:
                account = self.binance_client.futures_account()
            else:
                account = self.binance_client.futures_account()
            
            logger.info("✅ Подключение к Binance успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Binance: {e}")
            self.binance_client = None
    
    def get_total_balance(self) -> float:
        """Получает общий баланс в USDT (не только доступный)"""
        if not self.binance_client:
            logger.error("❌ Binance клиент не инициализирован")
            return 0.0
        
        try:
            if BINANCE_TESTNET:
                account = self.binance_client.futures_account()
            else:
                account = self.binance_client.futures_account()
            
            total_balance = float(account['totalWalletBalance'])
            logger.info(f"💰 Общий баланс: {total_balance:.2f} USDT")
            return total_balance
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения баланса: {e}")
            return 0.0
    
    def check_open_position(self, symbol: str) -> tuple[bool, dict]:
        """
        Проверяет наличие открытой позиции по символу
        
        Returns:
            tuple: (has_position: bool, position_info: dict)
        """
        if not self.binance_client:
            logger.error("❌ Binance клиент не инициализирован")
            return False, {}
        
        try:
            # Получаем информацию о позициях
            positions = self.binance_client.futures_position_information(symbol=symbol)
            
            for position in positions:
                position_amt = float(position['positionAmt'])
                
                # Если количество позиции не равно 0, значит есть открытая позиция
                if abs(position_amt) > 0:
                    position_info = {
                        'symbol': position['symbol'],
                        'side': 'LONG' if position_amt > 0 else 'SHORT',
                        'size': abs(position_amt),
                        'entry_price': float(position['entryPrice']),
                        'unrealized_pnl': float(position['unRealizedProfit']),
                        'percentage': float(position['percentage']),
                        'notional': abs(float(position['notional']))
                    }
                    
                    logger.info(f"📊 Найдена открытая позиция {symbol}: {position_info['side']} {position_info['size']}")
                    return True, position_info
            
            return False, {}
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки позиции {symbol}: {e}")
            return False, {}
    
    def get_current_price(self, ticker: str) -> float:
        """Получает текущую рыночную цену"""
        if not self.binance_client:
            return 0.0
        
        try:
            # Используем ФЬЮЧЕРСНЫЕ цены, не спотовые!
            ticker_data = self.binance_client.futures_symbol_ticker(symbol=ticker)
            return float(ticker_data['price'])
        except Exception as e:
            logger.error(f"❌ Ошибка получения цены {ticker}: {e}")
            return 0.0
    
    def set_leverage(self, ticker: str, notional_value: Optional[float] = None) -> bool:
        """
        Устанавливает оптимальное плечо для символа
        
        Args:
            ticker: Торговый символ
            notional_value: Номинальная стоимость позиции (quantity * price)
                           Если не указана, используется дефолтное плечо
        """
        if not self.binance_client:
            return False
        
        try:
            # Рассчитываем оптимальное плечо
            if notional_value:
                optimal_leverage = calculate_leverage_for_symbol(ticker, notional_value, FUTURES_LEVERAGE)
            else:
                optimal_leverage = FUTURES_LEVERAGE
            
            result = self.binance_client.futures_change_leverage(
                symbol=ticker, 
                leverage=optimal_leverage
            )
            
            if optimal_leverage != FUTURES_LEVERAGE:
                logger.info(f"✅ Динамическое плечо {optimal_leverage}x установлено для {ticker} (позиция: ${notional_value:,.0f})")
            else:
                logger.info(f"✅ Плечо {optimal_leverage}x установлено для {ticker}")
            
            return True
        except Exception as e:
            logger.warning(f"⚠️ Не удалось установить плечо для {ticker}: {e}")
            return False
    
    def set_margin_type(self, ticker: str) -> bool:
        """Устанавливает режим маржи для символа"""
        if not self.binance_client:
            return False
        
        try:
            # Для фьючерсов: CROSS -> CROSSED, ISOLATED остается ISOLATED
            futures_margin_type = 'CROSSED' if FUTURES_MARGIN_TYPE == 'CROSS' else 'ISOLATED'
            
            # Устанавливаем режим маржи из конфигурации
            result = self.binance_client.futures_change_margin_type(
                symbol=ticker,
                marginType=futures_margin_type  # Используем marginType (camelCase) для Futures API
            )
            logger.info(f"✅ Режим маржи {futures_margin_type} установлен для {ticker}")
            return True
        except Exception as e:
            # Если режим уже установлен, это не ошибка
            error_msg = str(e).lower()
            if "no need to change margin type" in error_msg or "margin type is the same" in error_msg:
                futures_margin_type = 'CROSSED' if FUTURES_MARGIN_TYPE == 'CROSS' else 'ISOLATED'
                logger.info(f"✅ Режим маржи {futures_margin_type} уже установлен для {ticker}")
                return True
            else:
                logger.warning(f"⚠️ Не удалось установить режим маржи для {ticker}: {e}")
                return False

    def setup_symbol_settings(self, ticker: str) -> bool:
        """
        Настраивает все параметры символа: плечо и режим маржи
        
        Args:
            ticker: Торговая пара
            
        Returns:
            bool: True если все настройки применены успешно
        """
        logger.info(f"🔧 Настройка параметров символа {ticker}...")
        
        # Сначала устанавливаем режим маржи
        margin_ok = self.set_margin_type(ticker)
        
        # Затем устанавливаем плечо
        leverage_ok = self.set_leverage(ticker)
        
        if margin_ok and leverage_ok:
            logger.info(f"✅ Все параметры символа {ticker} настроены успешно")
            return True
        else:
            logger.warning(f"⚠️ Не все параметры символа {ticker} удалось настроить")
            return False
    
    def calculate_position_size(self, ticker: str, entry_price: float, stop_loss: float) -> Tuple[float, float, str]:
        """
        Рассчитывает размер позиции
        
        Args:
            ticker: Торговая пара
            entry_price: Цена входа
            stop_loss: Стоп-лосс
            
        Returns:
            (quantity, usdt_amount, error_msg): Размер позиции, сумма в USDT, ошибка
        """
        try:
            # Получаем общий баланс
            total_balance = self.get_total_balance()
            if total_balance <= 0:
                return 0.0, 0.0, "Не удалось получить баланс"
            
            # Рассчитываем сумму под риск (2% от общего капитала)
            risk_amount = total_balance * (RISK_PERCENT / 100)
            
            # Рассчитываем убыток при срабатывании стоп-лосса
            risk_per_unit = abs(entry_price - stop_loss)
            if risk_per_unit == 0:
                return 0.0, 0.0, "Стоп-лосс равен цене входа"
            
            # Базовый размер позиции без учета плеча
            base_quantity = risk_amount / risk_per_unit
            
            # С учетом плеча позиция может быть больше
            usdt_amount = base_quantity * entry_price
            
            # Округляем количество согласно фильтрам символа
            rounded_quantity = round_quantity_for_symbol(ticker, base_quantity)
            
            # Для увеличения позиции округляем в большую сторону
            if rounded_quantity < base_quantity:
                # Получаем step_size и добавляем один шаг
                symbol_info = self.symbol_cache.get_symbol_info(ticker)
                if symbol_info:
                    step_size = float(symbol_info.get('step_size', '0.001'))
                    rounded_quantity += step_size
                    # Округляем еще раз после добавления шага
                    rounded_quantity = round_quantity_for_symbol(ticker, rounded_quantity)
            final_usdt_amount = rounded_quantity * entry_price
            
            logger.info(
                f"📊 Расчет позиции {ticker}: "
                f"Баланс: {total_balance:.2f} USDT | "
                f"Риск: {risk_amount:.2f} USDT | "
                f"Количество: {rounded_quantity} | "
                f"Сумма: {final_usdt_amount:.2f} USDT"
            )
            
            return rounded_quantity, final_usdt_amount, ""
            
        except Exception as e:
            error_msg = f"Ошибка расчета позиции: {e}"
            logger.error(f"❌ {error_msg}")
            return 0.0, 0.0, error_msg
    
    def place_market_order(self, signal_data: Dict) -> Dict:
        """Размещает рыночный ордер с SL и TP"""
        if not self.binance_client:
            return {
                'success': False,
                'error': 'Binance клиент не инициализирован',
                'signal_data': signal_data
            }
        
        ticker = signal_data['ticker']
        signal_type = signal_data['signal']
        entry_price = float(signal_data['entry_price'])
        stop_loss = float(signal_data['stop_loss'])
        take_profit = float(signal_data['take_profit'])
        
        try:
            # � ВАЛИДАЦИЯ СИНХРОНИЗАЦИИ: Проверяем конфликты с Orders Watchdog
            if SYNC_AVAILABLE:
                side = "BUY" if signal_type == "LONG" else "SELL"
                quantity = 100.0  # Временное значение для валидации
                
                is_valid, validation_reason = validate_signal_before_execution(ticker, side, quantity)
                
                if not is_valid:
                    logger.warning(f"⚠️ Сигнал {ticker} отклонен синхронизатором: {validation_reason}")
                    self._send_synchronization_conflict_notification(ticker, signal_data, validation_reason)
                    return {
                        'success': False,
                        'error': f'Конфликт синхронизации: {validation_reason}',
                        'signal_data': signal_data,
                        'sync_validation': {'valid': False, 'reason': validation_reason}
                    }
                else:
                    logger.info(f"✅ Сигнал {ticker} прошел валидацию синхронизации: {validation_reason}")
            
            # �🔧 НОВАЯ ПРОВЕРКА: Проверяем открытые позиции
            has_position, position_info = self.check_open_position(ticker)
            
            if has_position:
                # Отправляем уведомление об открытой позиции
                self._send_position_exists_notification(ticker, position_info, signal_data)
                
                if not MULTIPLE_ORDERS:
                    # Запрещено открывать повторные ордера
                    self._send_multiple_orders_denied_notification(ticker, signal_data, position_info)
                    return {
                        'success': False,
                        'error': f'Повторное открытие ордеров запрещено для {ticker}',
                        'signal_data': signal_data,
                        'existing_position': position_info
                    }
                else:
                    # Разрешено открывать повторные ордера - проверяем лимит
                    self._send_multiple_orders_allowed_notification(ticker, signal_data, position_info)
                    
                    # 🔒 КРИТИЧЕСКАЯ СЕКЦИЯ: Thread-safe проверка лимита для символа
                    with self.order_lock:
                        positions_count, orders_count, total_active = self._count_active_positions_and_orders_for_symbol(ticker)
                        
                        if total_active >= MAX_CONCURRENT_ORDERS:
                            self._send_max_symbol_limit_notification(ticker, signal_data, positions_count, orders_count, total_active)
                            return {
                                'success': False,
                                'error': f'Достигнут лимит для {ticker}: {total_active}/{MAX_CONCURRENT_ORDERS} (позиций: {positions_count}, ордеров: {orders_count})',
                                'signal_data': signal_data,
                                'total_active': total_active,
                                'positions_count': positions_count,
                                'orders_count': orders_count
                            }
                        
                        # Проверяем качество цены (должна быть "even or better")
                        side = 'BUY' if signal_data['signal'] == 'LONG' else 'SELL'
                        entry_price = float(signal_data['entry_price'])
                        price_acceptable, price_reason = self._check_price_quality(ticker, side, entry_price)
                        
                        if not price_acceptable:
                            self._send_price_quality_notification(ticker, signal_data, price_reason)
                            return {
                                'success': False,
                                'error': f'Цена не соответствует требованию "even or better": {price_reason}',
                                'signal_data': signal_data,
                                'price_reason': price_reason
                            }
                    # 🔒 КОНЕЦ КРИТИЧЕСКОЙ СЕКЦИИ
                    
            # Настраиваем параметры символа (плечо и режим маржи)
            self.setup_symbol_settings(ticker)
            
            # Рассчитываем размер позиции
            quantity, usdt_amount, error_msg = self.calculate_position_size(
                ticker, entry_price, stop_loss
            )
            
            if quantity == 0:
                return {
                    'success': False,
                    'error': f'Не удалось рассчитать позицию: {error_msg}',
                    'signal_data': signal_data
                }
            
            # Размещаем лимитный ордер (НЕ MARKET!)
            side = 'BUY' if signal_type == 'LONG' else 'SELL'
            position_side = 'LONG' if signal_type == 'LONG' else 'SHORT'  # Для hedge mode
            entry_price_rounded = round_price_for_symbol(ticker, entry_price)
            
            logger.info(f"🎯 Размещаем LIMIT {side} ордер {ticker}: {quantity} по цене {entry_price_rounded} (~{usdt_amount:.2f} USDT) positionSide={position_side}")
            
            main_order = self.binance_client.futures_create_order(
                symbol=ticker,
                side=side,
                type='LIMIT',  # ИСПРАВЛЕНО: LIMIT вместо MARKET!
                quantity=quantity,
                price=str(entry_price_rounded),  # Цена обязательна для LIMIT
                timeInForce='GTC',  # Good Till Cancelled
                positionSide=position_side
            )
            
            logger.info(f"✅ Основной ордер исполнен: {main_order['orderId']}")
            
            # Размещаем Stop Loss (LIMIT вместо STOP_MARKET для лучшего контроля)
            sl_side = 'SELL' if signal_type == 'LONG' else 'BUY'
            sl_price = round_price_for_symbol(ticker, stop_loss)
            
            stop_order = self.binance_client.futures_create_order(
                symbol=ticker,
                side=sl_side,
                type='STOP',
                quantity=quantity,
                price=str(sl_price),  # Цена для лимитного исполнения
                stopPrice=str(sl_price),  # Цена срабатывания стопа
                timeInForce='GTC',
                positionSide=position_side  # Тот же positionSide!
            )
            
            logger.info(f"🛡️ Stop Loss размещен: {stop_order['orderId']} at {sl_price}")
            
            # Размещаем Take Profit
            tp_side = 'SELL' if signal_type == 'LONG' else 'BUY'
            tp_price = round_price_for_symbol(ticker, take_profit)
            
            tp_order = self.binance_client.futures_create_order(
                symbol=ticker,
                side=tp_side,
                type='TAKE_PROFIT_MARKET',
                quantity=quantity,
                stopPrice=str(tp_price),
                positionSide=position_side
            )
            
            logger.info(f"🎯 Take Profit размещен: {tp_order['orderId']} at {tp_price}")
            
            # Возвращаем результат
            return {
                'success': True,
                'main_order': main_order,
                'stop_order': stop_order,
                'tp_order': tp_order,
                'quantity': quantity,
                'usdt_amount': usdt_amount,
                'signal_data': signal_data
            }
            
        except BinanceAPIException as e:
            error_msg = f"Binance API ошибка: {e.message}"
            logger.error(f"❌ {error_msg}")
            
            # Специальная обработка для правил Binance
            if "Quantitative Rules violated" in str(e.message):
                logger.warning(f"⚠️ Binance ограничения для {ticker} - пропускаем торговлю")
                # Отправляем уведомление о временном блоке
                try:
                    message = f"""
🚨 <b>ОГРАНИЧЕНИЕ BINANCE</b> 🚨

📊 <b>Символ:</b> {ticker}
📈 <b>Сигнал:</b> {signal_data['signal_type']}
❌ <b>Ошибка:</b> Quantitative Rules Violation

⚠️ <b>Торговля временно заблокирована Binance</b>
🔄 <b>Попробуйте позже</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
                    telegram_bot.send_message(message)
                except:
                    pass
                    
            return {
                'success': False,
                'error': error_msg,
                'signal_data': signal_data
            }
        except Exception as e:
            error_msg = f"Неожиданная ошибка: {e}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'signal_data': signal_data
            }
    
    def execute_signal(self, signal_data: Dict) -> bool:
        """
        Главная функция - исполняет торговый сигнал через новый lifecycle manager
        
        Args:
            signal_data: Данные сигнала от signal_analyzer
            
        Returns:
            bool: True если основной ордер успешно размещен
        """
        ticker = signal_data.get('ticker', 'UNKNOWN')
        signal_type = signal_data.get('signal', 'UNKNOWN')
        
        logger.info(f"🎯 Исполняем сигнал {ticker}: {signal_type}")
        
        try:
            # Используем новый lifecycle manager для размещения ордера
            order_result = self.lifecycle_manager.place_main_limit_order(signal_data)
            
            if order_result['success']:
                logger.info(f"✅ === ЛИМИТНЫЙ ОРДЕР {ticker} РАЗМЕЩЕН ===")
                logger.info(f"📋 Order ID: {order_result['main_order_id']}")
                logger.info(f"📦 Количество: {order_result['quantity']:.6f}")
                logger.info(f"💰 Сумма: {order_result['usdt_amount']:.2f} USDT")
                logger.info(f"⏳ Ожидаем исполнения...")
                
                return True
            else:
                # Ошибка размещения - отправляем уведомление об ошибке
                self._send_error_notification(order_result['error'], signal_data)
                return False
                
        except Exception as e:
            error_msg = f"Критическая ошибка исполнения сигнала {ticker}: {e}"
            logger.error(f"❌ {error_msg}")
            self._send_error_notification(error_msg, signal_data)
            return False
    
    def _send_success_notification(self, order_result: Dict) -> None:
        """Отправляет уведомление об успешном размещении ордера"""
        try:
            signal_data = order_result['signal_data']
            ticker = signal_data['ticker']
            signal_type = signal_data['signal']
            quantity = order_result['quantity']
            usdt_amount = order_result['usdt_amount']
            
            main_order_id = order_result['main_order']['orderId']
            stop_order_id = order_result['stop_order']['orderId']
            tp_order_id = order_result['tp_order']['orderId']
            
            # Для корректного отображения типа маржи в уведомлении
            display_margin_type = 'CROSSED' if FUTURES_MARGIN_TYPE == 'CROSS' else 'ISOLATED'
            
            message = f"""
🚀 <b>ОРДЕР РАЗМЕЩЕН!</b> 🚀

📊 <b>Символ:</b> {ticker}
📈 <b>Направление:</b> {signal_type}
💰 <b>Объем:</b> {quantity}
💵 <b>Сумма:</b> {usdt_amount:.2f} USDT
⚡ <b>Плечо:</b> {FUTURES_LEVERAGE}x
🔧 <b>Режим маржи:</b> {display_margin_type}

🎯 <b>Цены:</b>
• Entry: {signal_data['entry_price']:.6f}
• Stop: {signal_data['stop_loss']:.6f}
• Target: {signal_data['take_profit']:.6f}

🆔 <b>Ордера:</b>
• Main: {main_order_id}
• Stop: {stop_order_id}  
• TP: {tp_order_id}

📊 <b>Схождение:</b> {signal_data.get('timeframes_str', 'N/A')}
🎯 <b>Уверенность:</b> {signal_data.get('confidence', 0):.1%}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление о размещении ордера {ticker} отправлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления об успехе: {e}")
    
    def _send_error_notification(self, error_msg: str, signal_data: Dict) -> None:
        """Отправляет уведомление об ошибке"""
        try:
            ticker = signal_data.get('ticker', 'UNKNOWN')
            signal_type = signal_data.get('signal', 'UNKNOWN')
            
            message = f"""
🚨 <b>ОШИБКА ОРДЕРА</b> 🚨

📊 <b>Символ:</b> {ticker}
📈 <b>Сигнал:</b> {signal_type}
❌ <b>Ошибка:</b> {error_msg}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление об ошибке {ticker} отправлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления об ошибке: {e}")
    
    def _send_position_exists_notification(self, ticker: str, position_info: dict, signal_data: Dict) -> None:
        """Отправляет уведомление о наличии открытой позиции"""
        try:
            signal_type = signal_data.get('signal', 'UNKNOWN')
            
            message = f"""
📊 <b>ОТКРЫТАЯ ПОЗИЦИЯ ОБНАРУЖЕНА</b> 📊

💰 <b>Символ:</b> {ticker}
📈 <b>Направление:</b> {position_info['side']}
🔢 <b>Размер:</b> {position_info['size']}
💵 <b>Цена входа:</b> {position_info['entry_price']:.6f}
📊 <b>P&L:</b> {position_info['unrealized_pnl']:.2f} USDT ({position_info['percentage']:.2f}%)
💼 <b>Стоимость:</b> {position_info['notional']:.2f} USDT

🔔 <b>Новый сигнал:</b> {signal_type}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление об открытой позиции {ticker} отправлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления об открытой позиции: {e}")
    
    def _send_multiple_orders_denied_notification(self, ticker: str, signal_data: Dict, position_info: dict) -> None:
        """Отправляет уведомление о запрете повторных ордеров"""
        try:
            signal_type = signal_data.get('signal', 'UNKNOWN')
            entry_price = signal_data.get('entry_price', 0)
            
            message = f"""
🚫 <b>ПОВТОРНОЕ ОТКРЫТИЕ ЗАПРЕЩЕНО</b> 🚫

📊 <b>Символ:</b> {ticker}
🎯 <b>Сигнал:</b> {signal_type}
💵 <b>Цена сигнала:</b> {entry_price}

❌ <b>Ордер НЕ выставлен!</b>

📈 <b>Причина:</b> Есть открытая позиция {position_info['side']} {position_info['size']}
⚙️ <b>MULTIPLE_ORDERS = false</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление о запрете повторного ордера {ticker} отправлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления о запрете повторного ордера: {e}")
    
    def _send_multiple_orders_allowed_notification(self, ticker: str, signal_data: Dict, position_info: dict) -> None:
        """Отправляет уведомление о разрешении повторных ордеров"""
        try:
            signal_type = signal_data.get('signal', 'UNKNOWN')
            entry_price = signal_data.get('entry_price', 0)
            
            message = f"""
✅ <b>ПОВТОРНОЕ ОТКРЫТИЕ РАЗРЕШЕНО</b> ✅

📊 <b>Символ:</b> {ticker}
🎯 <b>Новый сигнал:</b> {signal_type}
💵 <b>Цена сигнала:</b> {entry_price}

📈 <b>Открытая позиция:</b> {position_info['side']} {position_info['size']}
⚙️ <b>MULTIPLE_ORDERS = true</b>

🚀 <b>Размещаем дополнительный ордер...</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление о разрешении повторного ордера {ticker} отправлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления о разрешении повторного ордера: {e}")
    
    def _add_to_monitoring(self, order_result: Dict) -> None:
        """Добавляет ордер в мониторинг"""
        try:
            # Проверяем доступность старого мониторинга
            if order_monitor:
                # Добавляем группу ордеров в REST мониторинг
                order_monitor.add_order_group(order_result)
                
                ticker = order_result['signal_data']['ticker']
                logger.info(f"👁️ Ордера {ticker} переданы в REST API мониторинг")
            else:
                logger.warning("⚠️ Старый order_monitor недоступен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления в мониторинг: {e}")

    def _count_open_orders_for_symbol(self, symbol: str) -> int:
        """Подсчитывает количество открытых ордеров для символа"""
        try:
            if not self.binance_client:
                return 0
                
            open_orders = self.binance_client.futures_get_open_orders(symbol=symbol)
            return len(open_orders)
            
        except Exception as e:
            logger.error(f"❌ Ошибка подсчета ордеров для {symbol}: {e}")
            return 0
    
    def _count_active_positions_and_orders_for_symbol(self, symbol: str) -> Tuple[int, int, int]:
        """
        Подсчитывает РЕАЛЬНЫЕ открытые позиции (FILLED) и pending ордера для конкретного символа
        
        Returns:
            tuple: (filled_positions, pending_orders, total_for_limit_check) для символа
        """
        try:
            if not self.binance_client:
                return 0, 0, 0
            
            # Получаем реальные FILLED позиции для символа
            account_info = self.binance_client.futures_account()
            filled_positions = 0
            
            for position in account_info.get('positions', []):
                if position['symbol'] == symbol:
                    position_amt = float(position.get('positionAmt', 0))
                    if position_amt != 0:  # Реально открытая FILLED позиция
                        filled_positions += 1
                        break  # Для одного символа может быть максимум 1 позиция
            
            # Получаем pending ордера для символа  
            open_orders = self.binance_client.futures_get_open_orders(symbol=symbol)
            pending_orders = len(open_orders)
            
            # Для лимита считаем: реальные позиции + pending ордера
            total_for_limit = filled_positions + pending_orders
            
            logger.debug(f"📊 {symbol} status: {filled_positions} FILLED positions + {pending_orders} pending orders = {total_for_limit} total")
            
            return filled_positions, pending_orders, total_for_limit
            
        except Exception as e:
            logger.error(f"❌ Ошибка подсчета для {symbol}: {e}")
            return 0, 0, 0
            
    def _get_open_orders_with_prices(self, symbol: str, side: str) -> List[Dict]:
        """
        Получает открытые ордера с ценами для проверки качества цены
        
        Args:
            symbol: Торговый символ
            side: Сторона ордера (BUY/SELL)
            
        Returns:
            List[Dict]: Список ордеров с ценами
        """
        try:
            if not self.binance_client:
                return []
                
            open_orders = self.binance_client.futures_get_open_orders(symbol=symbol)
            
            # Фильтруем по стороне и типу ордера
            relevant_orders = []
            for order in open_orders:
                if order.get('side') == side and order.get('type') == 'LIMIT':
                    relevant_orders.append({
                        'orderId': order['orderId'],
                        'price': float(order['price']),
                        'side': order['side'],
                        'quantity': float(order['origQty'])
                    })
            
            return relevant_orders
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения ордеров с ценами для {symbol}: {e}")
            return []
            
    def _check_price_quality(self, symbol: str, side: str, new_price: float) -> Tuple[bool, str]:
        """
        Проверяет качество цены нового ордера согласно LONG/SHORT логике
        
        Args:
            symbol: Торговый символ  
            side: Сторона ордера (BUY/SELL)
            new_price: Цена нового ордера
            
        Returns:
            Tuple[is_acceptable: bool, reason: str]
        """
        try:
            # Получаем все релевантные цены (позиции + ордера)
            relevant_prices = []
            
            # 1. Проверяем открытые позиции 
            if self.binance_client:
                account_info = self.binance_client.futures_account()
                for position in account_info.get('positions', []):
                    if position['symbol'] == symbol:
                        position_amt = float(position.get('positionAmt', 0))
                        if position_amt != 0:
                            entry_price = float(position['entryPrice'])
                            relevant_prices.append(entry_price)
            
            # 2. Проверяем открытые ордера того же типа
            existing_orders = self._get_open_orders_with_prices(symbol, side)
            for order in existing_orders:
                relevant_prices.append(order['price'])
            
            if not relevant_prices:
                return True, "Нет существующих позиций или ордеров"
            
            # 3. Применяем логику для LONG/SHORT
            if side == 'BUY':  # LONG позиции
                # Для LONG: новая цена должна быть НИЖЕ лучшей существующей
                min_existing_price = min(relevant_prices)
                if new_price >= min_existing_price:
                    return False, f"LONG: новая цена {new_price} должна быть ниже лучшей {min_existing_price}"
            else:  # SELL / SHORT позиции  
                # Для SHORT: новая цена должна быть ВЫШЕ лучшей существующей
                max_existing_price = max(relevant_prices)
                if new_price <= max_existing_price:
                    return False, f"SHORT: новая цена {new_price} должна быть выше лучшей {max_existing_price}"
            
            return True, "Цена соответствует требованиям"
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки качества цены для {symbol}: {e}")
            return True, "Ошибка проверки, разрешаем"
    
    def _send_max_orders_limit_notification(self, ticker: str, signal_data: Dict, open_orders_count: int) -> None:
        """Уведомление о достижении лимита ордеров для символа (устаревший метод)"""
        try:
            signal_type = signal_data.get('signal', 'N/A')
            entry_price = signal_data.get('entry_price', 0)
            
            message = f"""
⚠️ <b>ЛИМИТ ОРДЕРОВ ДОСТИГНУТ</b> ⚠️

📊 <b>Символ:</b> {ticker}
🎯 <b>Сигнал (отклонен):</b> {signal_type}
💵 <b>Цена сигнала:</b> {entry_price}

📈 <b>Открытых ордеров:</b> {open_orders_count}/{MAX_CONCURRENT_ORDERS}
⚙️ <b>MAX_CONCURRENT_ORDERS = {MAX_CONCURRENT_ORDERS}</b>

❌ <b>Новый ордер НЕ размещен</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление о лимите ордеров для {ticker} отправлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о лимите: {e}")

    def _send_max_portfolio_limit_notification(self, ticker: str, signal_data: Dict, positions_count: int, orders_count: int, total_active: int) -> None:
        """Уведомление о достижении общего лимита портфеля (устаревший метод)"""
        try:
            signal_type = signal_data.get('signal', 'N/A')
            entry_price = signal_data.get('entry_price', 0)
            
            message = f"""
🚫 <b>ЛИМИТ ПОРТФЕЛЯ ДОСТИГНУТ</b> 🚫

📊 <b>Символ:</b> {ticker}
🎯 <b>Сигнал (отклонен):</b> {signal_type}
💵 <b>Цена сигнала:</b> {entry_price}

📈 <b>Текущий портфель:</b>
   • Активные позиции: {positions_count}
   • Открытые ордера: {orders_count}
   • Всего активно: {total_active}/{MAX_CONCURRENT_ORDERS}

⚙️ <b>MAX_CONCURRENT_ORDERS = {MAX_CONCURRENT_ORDERS}</b>

❌ <b>Новый ордер НЕ размещен</b>
💡 <b>Дождитесь закрытия позиций или ордеров</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.warning(f"🚫 ПОРТФЕЛЬ-ЛИМИТ: {ticker} отклонен - {total_active}/{MAX_CONCURRENT_ORDERS} активно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о лимите портфеля: {e}")

    def _send_max_symbol_limit_notification(self, ticker: str, signal_data: Dict, positions_count: int, orders_count: int, total_active: int) -> None:
        """Уведомление о достижении лимита для конкретного символа"""
        try:
            signal_type = signal_data.get('signal', 'N/A')
            entry_price = signal_data.get('entry_price', 0)
            
            message = f"""
🚫 <b>ЛИМИТ ДЛЯ {ticker} ДОСТИГНУТ</b> 🚫

📊 <b>Символ:</b> {ticker}
🎯 <b>Сигнал (отклонен):</b> {signal_type}
💵 <b>Цена сигнала:</b> {entry_price}

📈 <b>Текущее состояние {ticker}:</b>
   • Активные позиции: {positions_count}
   • Открытые ордера: {orders_count}
   • Всего активно: {total_active}/{MAX_CONCURRENT_ORDERS}

⚙️ <b>MAX_CONCURRENT_ORDERS = {MAX_CONCURRENT_ORDERS}</b>

❌ <b>Новый ордер НЕ размещен</b>
💡 <b>Дождитесь исполнения или закрытия ордеров по {ticker}</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.warning(f"🚫 СИМВОЛ-ЛИМИТ: {ticker} отклонен - {total_active}/{MAX_CONCURRENT_ORDERS} активно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о лимите символа: {e}")
            
    def _send_price_quality_notification(self, ticker: str, signal_data: Dict, price_reason: str) -> None:
        """Уведомление о неприемлемом качестве цены"""
        try:
            signal_type = signal_data.get('signal', 'N/A')
            entry_price = signal_data.get('entry_price', 0)
            
            message = f"""
⚠️ <b>ЦЕНА НЕ СООТВЕТСТВУЕТ ТРЕБОВАНИЮ</b> ⚠️

📊 <b>Символ:</b> {ticker}
🎯 <b>Сигнал (отклонен):</b> {signal_type}
💵 <b>Предлагаемая цена:</b> {entry_price}

❌ <b>Причина отклонения:</b> {price_reason}

💡 <b>Требование:</b> Новый ордер должен иметь цену "equal or better" чем существующие ордера

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.warning(f"⚠️ ЦЕНА ОТКЛОНЕНА: {ticker} - {price_reason}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о качестве цены: {e}")
    
    def _send_synchronization_conflict_notification(self, ticker: str, signal_data: Dict, validation_reason: str) -> None:
        """Уведомление о конфликте синхронизации"""
        try:
            signal_type = signal_data.get('signal', 'N/A')
            entry_price = signal_data.get('entry_price', 0)
            timeframe = signal_data.get('timeframe', 'N/A')
            
            message = f"""
🔄 <b>КОНФЛИКТ СИНХРОНИЗАЦИИ</b> 🔄

📊 <b>Символ:</b> {ticker}
🎯 <b>Сигнал (отклонен):</b> {signal_type}
💵 <b>Цена сигнала:</b> {entry_price}
⌚ <b>Таймфрейм:</b> {timeframe}

⚠️ <b>Причина отклонения:</b>
{validation_reason}

🐕 <b>Orders Watchdog обнаружил конфликт</b>
❌ <b>Новый ордер НЕ размещен для безопасности</b>

💡 <b>Рекомендация:</b> Проверьте состояние существующих ордеров и позиций

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление о конфликте синхронизации для {ticker} отправлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о конфликте синхронизации: {e}")


class OrderLifecycleManager:
    """
    Управляет жизненным циклом ордеров: LIMIT -> мониторинг -> STOP_MARKET + LIMIT
    """
    
    def __init__(self, order_executor_instance):
        self.executor = order_executor_instance
        self.pending_orders = {}  # {ticker: {'main_order_id': ..., 'signal_data': ..., 'created_at': ...}}
        self.timeout_minutes = 60  # Таймаут ожидания исполнения
        self.lock = threading.Lock()
        
        logger.info("📋 OrderLifecycleManager initialized")
    
    def place_main_limit_order(self, signal_data: Dict) -> Dict:
        """
        Размещает только основной лимитный ордер и запускает мониторинг
        """
        ticker = signal_data['ticker']
        signal_type = signal_data['signal']
        entry_price = float(signal_data['entry_price'])
        stop_loss = float(signal_data['stop_loss'])
        take_profit = float(signal_data['take_profit'])
        
        try:
            # Проверяем открытые позиции
            has_position, position_info = self.executor.check_open_position(ticker)
            
            if has_position:
                self.executor._send_position_exists_notification(ticker, position_info, signal_data)
                
                if not MULTIPLE_ORDERS:
                    self.executor._send_multiple_orders_denied_notification(ticker, signal_data, position_info)
                    return {
                        'success': False,
                        'error': f'Повторное открытие ордеров запрещено для {ticker}',
                        'signal_data': signal_data
                    }
                else:
                    self.executor._send_multiple_orders_allowed_notification(ticker, signal_data, position_info)
            
            # Отменяем предыдущий ордер если есть
            self._cancel_pending_order(ticker)
            
            # Настраиваем параметры символа (базовые)
            self.executor.setup_symbol_settings(ticker)
            
            # Рассчитываем размер позиции
            quantity, usdt_amount, error_msg = self.executor.calculate_position_size(
                ticker, entry_price, stop_loss
            )
            
            if quantity == 0:
                return {
                    'success': False,
                    'error': f'Не удалось рассчитать позицию: {error_msg}',
                    'signal_data': signal_data
                }
            
            # Рассчитываем номинальную стоимость позиции для динамического плеча
            notional_value = quantity * entry_price
            
            # Устанавливаем оптимальное плечо на основе размера позиции
            logger.info(f"📊 Рассчитываем оптимальное плечо для {ticker} (позиция: ${notional_value:,.2f})")
            leverage_ok = self.executor.set_leverage(ticker, notional_value)
            
            if not leverage_ok:
                logger.warning(f"⚠️ Не удалось установить плечо для {ticker}, используем существующее")
            
            # Размещаем ТОЛЬКО основной лимитный ордер
            side = 'BUY' if signal_type == 'LONG' else 'SELL'
            position_side = 'LONG' if signal_type == 'LONG' else 'SHORT'
            entry_price_rounded = round_price_for_symbol(ticker, entry_price)
            
            logger.info(f"🎯 Размещаем LIMIT {side} ордер {ticker}: {quantity} по цене {entry_price_rounded}")
            
            main_order = self.executor.binance_client.futures_create_order(
                symbol=ticker,
                side=side,
                type='LIMIT',
                quantity=quantity,
                price=str(entry_price_rounded),
                timeInForce='GTC',
                positionSide=position_side
            )
            
            logger.info(f"✅ Основной ордер размещен: {main_order['orderId']}")
            
            # Сохраняем информацию для мониторинга
            order_info = {
                'main_order_id': main_order['orderId'],
                'signal_data': signal_data,
                'quantity': quantity,
                'usdt_amount': usdt_amount,
                'created_at': datetime.now(),
                'entry_price_rounded': entry_price_rounded,
                'side': side,
                'position_side': position_side
            }
            
            with self.lock:
                self.pending_orders[ticker] = order_info
            
            # Отправляем уведомление о размещении
            self._send_main_order_placed_notification(order_info)
            
            # Добавляем ордер в Orders Watchdog для мониторинга
            self._add_to_watchdog_monitoring(order_info)
            
            return {
                'success': True,
                'main_order_id': main_order['orderId'],
                'order_data': main_order,
                'quantity': quantity,
                'usdt_amount': usdt_amount,
                'signal_data': signal_data,
                'stage': 'MAIN_ORDER_PLACED'
            }
            
        except BinanceAPIException as e:
            error_msg = f"Binance API ошибка: {e.message}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'signal_data': signal_data
            }
        except Exception as e:
            error_msg = f"Неожиданная ошибка: {e}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'signal_data': signal_data
            }
    
    def on_main_order_filled(self, ticker: str, order_id: str, fill_data: Dict):
        """
        Callback при исполнении основного ордера - размещаем SL/TP
        """
        logger.info(f"🎉 Основной ордер {ticker} исполнен: {order_id}")
        
        with self.lock:
            if ticker not in self.pending_orders:
                logger.warning(f"⚠️ Не найдена информация о ордере {ticker}")
                return
            
            order_info = self.pending_orders.pop(ticker)
        
        try:
            signal_data = order_info['signal_data']
            quantity = order_info['quantity']
            position_side = order_info['position_side']
            signal_type = signal_data['signal']
            
            stop_loss = float(signal_data['stop_loss'])
            take_profit = float(signal_data['take_profit'])
            
            # Размещаем Stop Loss (STOP_MARKET)
            sl_side = 'SELL' if signal_type == 'LONG' else 'BUY'
            sl_price = round_price_for_symbol(ticker, stop_loss)
            
            logger.info(f"🛡️ Размещаем STOP_MARKET {sl_side} для {ticker}: {quantity} at {sl_price}")
            
            stop_order = self.executor.binance_client.futures_create_order(
                symbol=ticker,
                side=sl_side,
                type='STOP_MARKET',  # ИСПРАВЛЕНО: STOP_MARKET вместо STOP
                quantity=quantity,
                stopPrice=str(sl_price),
                timeInForce='GTC',
                positionSide=position_side
            )
            
            logger.info(f"✅ Stop Loss размещен: {stop_order['orderId']}")
            
            # Размещаем Take Profit (LIMIT)
            tp_side = 'SELL' if signal_type == 'LONG' else 'BUY'
            tp_price = round_price_for_symbol(ticker, take_profit)
            
            logger.info(f"🎯 Размещаем TAKE_PROFIT {tp_side} для {ticker}: {quantity} at {tp_price}")
            
            tp_order = self.executor.binance_client.futures_create_order(
                symbol=ticker,
                side=tp_side,
                type='LIMIT',  # Take Profit как LIMIT ордер
                quantity=quantity,
                price=str(tp_price),
                timeInForce='GTC',
                positionSide=position_side
            )
            
            logger.info(f"✅ Take Profit размещен: {tp_order['orderId']}")
            
            # Создаем полный результат для мониторинга и уведомлений
            complete_order_result = {
                'success': True,
                'main_order': {'orderId': order_id},
                'stop_order': stop_order,
                'tp_order': tp_order,
                'quantity': quantity,
                'usdt_amount': order_info['usdt_amount'],
                'signal_data': signal_data
            }
            
            # Отправляем финальное уведомление об успехе
            self.executor._send_success_notification(complete_order_result)
            
            # Передаем в мониторинг
            self.executor._add_to_monitoring(complete_order_result)
            
            logger.info(f"🎉 Полная торговая позиция {ticker} открыта успешно!")
            
        except Exception as e:
            error_msg = f"Ошибка размещения SL/TP для {ticker}: {e}"
            logger.error(f"❌ {error_msg}")
            self.executor._send_error_notification(error_msg, order_info['signal_data'])
    
    def on_main_order_cancelled(self, ticker: str, order_id: str):
        """
        Callback при отмене основного ордера
        """
        logger.info(f"🚫 Основной ордер {ticker} отменен: {order_id}")
        
        with self.lock:
            if ticker in self.pending_orders:
                order_info = self.pending_orders.pop(ticker)
                self._send_main_order_cancelled_notification(ticker, order_info)
    
    def _cancel_pending_order(self, ticker: str):
        """
        Отменяет предыдущий ордер если есть
        """
        with self.lock:
            if ticker in self.pending_orders:
                old_order = self.pending_orders[ticker]
                old_order_id = old_order['main_order_id']
                
                try:
                    # Отменяем старый ордер
                    cancel_result = self.executor.binance_client.futures_cancel_order(
                        symbol=ticker,
                        orderId=old_order_id
                    )
                    logger.info(f"🚫 Предыдущий ордер {ticker} отменен: {old_order_id}")
                    self._send_previous_order_cancelled_notification(ticker, old_order)
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось отменить предыдущий ордер {ticker}: {e}")
                
                # Удаляем из отслеживания
                del self.pending_orders[ticker]
    
    def _add_to_watchdog_monitoring(self, order_info: Dict):
        """Добавляет ордер в Orders Watchdog для мониторинга"""
        try:
            if not WATCHDOG_AVAILABLE:
                logger.warning("⚠️ Orders Watchdog недоступен, используем старый мониторинг")
                # Fallback к старому мониторингу
                self._start_order_monitoring_fallback(order_info)
                return
            
            signal_data = order_info['signal_data']
            
            # Подготавливаем данные для watchdog
            watchdog_data = {
                'symbol': signal_data['ticker'],
                'order_id': order_info['main_order_id'],
                'side': order_info['side'],
                'position_side': order_info['position_side'],
                'quantity': order_info['quantity'],
                'price': order_info['entry_price_rounded'],
                'signal_type': signal_data['signal'],
                'stop_loss': signal_data['stop_loss'],
                'take_profit': signal_data['take_profit']
            }
            
            # Отправляем в Orders Watchdog
            if watchdog_api and watchdog_api.add_order_for_monitoring(watchdog_data):
                logger.info(f"🐕 Ордер {signal_data['ticker']} добавлен в Orders Watchdog")
            else:
                logger.error(f"❌ Не удалось добавить ордер {signal_data['ticker']} в Orders Watchdog")
                # Fallback к старому мониторингу
                self._start_order_monitoring_fallback(order_info)
                
        except Exception as e:
            logger.error(f"❌ Ошибка добавления в Orders Watchdog: {e}")
            # Fallback к старому мониторингу
            self._start_order_monitoring_fallback(order_info)
    
    def _start_order_monitoring_fallback(self, order_info: Dict):
        """Fallback к старому мониторингу если Orders Watchdog недоступен"""
        try:
            ticker = order_info['signal_data']['ticker']
            order_id = order_info['main_order_id']
            
            logger.info(f"🔄 Используем fallback мониторинг для {ticker} ордера {order_id}")
            self._start_timeout_timer(ticker, order_id)
            
        except Exception as e:
            logger.error(f"❌ Ошибка fallback мониторинга: {e}")
    
    def _start_order_monitoring(self, ticker: str, order_id: str):
        """
        Запускает WebSocket мониторинг для ордера
        """
        try:
            # Мониторинг через REST API в order_monitor (периодические проверки)
            logger.info(f"👁️ Мониторинг запущен для {ticker} ордера {order_id}")
            logger.info(f"� Используется REST API мониторинг (websocket_monitor.py)")
            
            # Запускаем таймер для timeout
            self._start_timeout_timer(ticker, order_id)
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска мониторинга для {ticker}: {e}")
    
    def _start_timeout_timer(self, ticker: str, order_id: str):
        """
        Запускает таймер для отмены ордера по timeout
        """
        def timeout_handler():
            time.sleep(self.timeout_minutes * 60)  # 60 минут
            
            with self.lock:
                if ticker in self.pending_orders:
                    order_info = self.pending_orders[ticker]
                    if order_info['main_order_id'] == order_id:
                        try:
                            # Отменяем ордер по timeout
                            cancel_result = self.executor.binance_client.futures_cancel_order(
                                symbol=ticker,
                                orderId=order_id
                            )
                            logger.info(f"⏰ Ордер {ticker} отменен по timeout: {order_id}")
                            self._send_timeout_cancellation_notification(ticker, order_info)
                            
                            del self.pending_orders[ticker]
                        except Exception as e:
                            logger.error(f"❌ Ошибка отмены ордера по timeout {ticker}: {e}")
        
        # Запускаем в отдельном потоке
        timeout_thread = threading.Thread(target=timeout_handler, daemon=True)
        timeout_thread.start()
    
    def _send_main_order_placed_notification(self, order_info: Dict):
        """Уведомление о размещении основного ордера"""
        try:
            signal_data = order_info['signal_data']
            ticker = signal_data['ticker']
            
            message = f"""
� <b>ОРДЕР РАЗМЕЩЕН!</b> �

📊 <b>Символ:</b> {ticker}
📈 <b>Направление:</b> {signal_data['signal']}
💰 <b>Объем:</b> {order_info['quantity']}
💵 <b>Сумма:</b> {order_info['usdt_amount']:.2f} USDT
⚡ <b>Плечо:</b> {FUTURES_LEVERAGE}x

🎯 <b>Orders:</b>
• Limit: {order_info['entry_price_rounded']:.6f}
• Stop: {signal_data['stop_loss']:.6f}
• Target: {signal_data['take_profit']:.6f}

📊 <b>Схождение:</b> {signal_data.get('timeframes_str', 'N/A')}
🎯 <b>Уверенность:</b> {signal_data.get('confidence', 0):.1%}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление о размещении лимитного ордера {ticker} отправлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о размещении: {e}")
    
    def _send_main_order_cancelled_notification(self, ticker: str, order_info: Dict):
        """Уведомление об отмене основного ордера"""
        try:
            message = f"""
🚫 <b>ОРДЕР ОТМЕНЕН</b> 🚫

📊 <b>Символ:</b> {ticker}
🆔 <b>Ордер:</b> {order_info['main_order_id']}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление об отмене ордера {ticker} отправлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления об отмене: {e}")
    
    def _send_previous_order_cancelled_notification(self, ticker: str, old_order_info: Dict):
        """Уведомление об отмене предыдущего ордера"""
        try:
            message = f"""
🔄 <b>ПРЕДЫДУЩИЙ ОРДЕР ОТМЕНЕН</b> 🔄

📊 <b>Символ:</b> {ticker}
🆔 <b>Старый ордер:</b> {old_order_info['main_order_id']}

🔔 <b>Причина:</b> Поступил новый сигнал

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о замене ордера: {e}")
    
    def _send_timeout_cancellation_notification(self, ticker: str, order_info: Dict):
        """Уведомление об отмене ордера по timeout"""
        try:
            message = f"""
⏰ <b>ОРДЕР ОТМЕНЕН ПО TIMEOUT</b> ⏰

📊 <b>Символ:</b> {ticker}
🆔 <b>Ордер:</b> {order_info['main_order_id']}
⏳ <b>Timeout:</b> {self.timeout_minutes} минут

💡 <b>Ордер не был исполнен за отведенное время</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о timeout: {e}")


# Создаем глобальный экземпляр lifecycle manager  
order_lifecycle_manager = None


# Глобальный экземпляр для использования в ticker_monitor
order_executor = OrderExecutor()


def execute_trading_signal(signal_data: Dict) -> bool:
    """
    Функция-адаптер для интеграции с ticker_monitor.py
    
    Заменяет process_trading_signal из order_generator.py
    
    Args:
        signal_data: Данные торгового сигнала
        
    Returns:
        bool: True если ордер успешно размещен
    """
    return order_executor.execute_signal(signal_data)


# Для совместимости с существующим кодом
process_trading_signal = execute_trading_signal


if __name__ == "__main__":
    """Тест исполнителя ордеров"""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Тестовый сигнал
    test_signal = {
        'ticker': 'BTCUSDT',
        'signal': 'LONG',
        'entry_price': 45000.0,
        'stop_loss': 44000.0,
        'take_profit': 47000.0,
        'confidence': 0.85,
        'timeframes_str': '1H, 4H'
    }
    
    logger.info("🧪 Тестируем OrderExecutor...")
    
    # Тестируем расчет позиции (без реального ордера)
    executor = OrderExecutor()
    if executor.binance_client:
        quantity, usdt_amount, error = executor.calculate_position_size(
            test_signal['ticker'],
            test_signal['entry_price'], 
            test_signal['stop_loss']
        )
        
        if error:
            logger.error(f"❌ Ошибка расчета: {error}")
        else:
            logger.info(f"✅ Расчет позиции: {quantity} ({usdt_amount:.2f} USDT)")
    else:
        logger.error("❌ Binance клиент не инициализирован")
