"""
Enhanced Signal Processor - Улучшенный процессор сигналов
=========================================================

Интегрированный с архитектурой PATRIOT:
- Использует signal_analyzer для анализа
- Использует order_generator для исполнения
- Добавляет логику схождения таймфреймов
- MVP: Реальные ордера на Binance Testnet

Author: HEDGER
Version: 2.1 - MVP with Real Orders
"""

from typing import Dict, List, Set, Optional
from statistics import mean
import logging
import time
import threading
from binance.client import Client
from binance.exceptions import BinanceAPIException
from decimal import Decimal, ROUND_DOWN
import json
from datetime import datetime

# Импорты проекта
from signal_analyzer import SignalAnalyzer
from order_generator import process_trading_signal
from telegram_bot import telegram_bot
from utils import logger
import config

class OrderManager:
    """Менеджер ордеров для отслеживания и управления позициями"""
    
    def __init__(self, binance_client: Client, telegram_bot):
        self.client = binance_client
        self.telegram = telegram_bot
        self.active_orders: Dict[str, Dict] = {}  # {order_id: order_info}
        self.monitoring = False
        self.monitor_thread = None
        
    def add_order_group(self, entry_order: Dict, stop_order: Dict, take_order: Dict, signal_data: Dict):
        """Добавляет группу связанных ордеров для мониторинга"""
        group_id = f"group_{entry_order['orderId']}"
        
        order_group = {
            'group_id': group_id,
            'entry_order': entry_order,
            'stop_order': stop_order,
            'take_order': take_order,
            'signal_data': signal_data,
            'status': 'ACTIVE',
            'created_at': datetime.now().isoformat()
        }
        
        self.active_orders[group_id] = order_group
        logger.info(f"📋 Добавлена группа ордеров {group_id} для мониторинга")
        
        # Отправляем уведомление о создании ордеров
        self._send_order_created_notification(order_group)
        
    def _send_order_created_notification(self, order_group: Dict):
        """Отправляет уведомление о создании группы ордеров"""
        signal = order_group['signal_data']
        entry = order_group['entry_order']
        stop = order_group['stop_order']
        take = order_group['take_order']
        
        message = f"""
🚀 <b>ОРДЕРА ВЫСТАВЛЕНЫ</b>
        
📊 <b>Пара:</b> {signal['ticker']}
📈 <b>Направление:</b> {signal['signal']}
💰 <b>Размер позиции:</b> {entry.get('executedQty', entry.get('origQty', 'N/A'))}

📋 <b>ОРДЕРА:</b>
🎯 Entry (Market): #{entry['orderId']} - {entry['status']}
🛑 Stop Loss: #{stop['orderId']} - {stop['price']}
🎯 Take Profit: #{take['orderId']} - {take['price']}

⏰ <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}
🔍 <b>Таймфреймы:</b> {signal.get('timeframes_str', 'N/A')}
"""
        
        try:
            self.telegram.send_message(message)
            logger.info("📱 ✅ Уведомление об ордерах отправлено в Telegram")
        except Exception as e:
            logger.error(f"📱 ❌ Ошибка отправки уведомления: {e}")
    
    def start_monitoring(self):
        """Запускает мониторинг ордеров в отдельном потоке"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_orders, daemon=True)
        self.monitor_thread.start()
        logger.info("👁️ Запущен мониторинг ордеров")
    
    def stop_monitoring(self):
        """Останавливает мониторинг ордеров"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("⏹️ Мониторинг ордеров остановлен")
    
    def _monitor_orders(self):
        """Основной цикл мониторинга ордеров"""
        while self.monitoring:
            try:
                if not self.active_orders:
                    time.sleep(5)
                    continue
                
                # Проверяем каждую группу ордеров
                groups_to_remove = []
                
                for group_id, order_group in self.active_orders.items():
                    if order_group['status'] != 'ACTIVE':
                        continue
                        
                    # Проверяем статусы ордеров
                    updated = self._check_order_group_status(order_group)
                    
                    if updated:
                        # Если группа завершена, помечаем для удаления
                        if order_group['status'] in ['COMPLETED', 'CANCELLED']:
                            groups_to_remove.append(group_id)
                
                # Удаляем завершенные группы
                for group_id in groups_to_remove:
                    del self.active_orders[group_id]
                    logger.info(f"🗑️ Удалена завершенная группа ордеров {group_id}")
                
                time.sleep(2)  # Проверяем каждые 2 секунды
                
            except Exception as e:
                logger.error(f"❌ Ошибка мониторинга ордеров: {e}")
                time.sleep(5)
    
    def _check_order_group_status(self, order_group: Dict) -> bool:
        """Проверяет статус группы ордеров и обновляет их"""
        try:
            symbol = order_group['signal_data']['ticker']
            stop_order = order_group['stop_order']
            take_order = order_group['take_order']
            
            # Получаем текущие статусы ордеров
            if config.BINANCE_TESTNET:
                stop_status = self.client.futures_get_order(symbol=symbol, orderId=stop_order['orderId'])
                take_status = self.client.futures_get_order(symbol=symbol, orderId=take_order['orderId'])
            else:
                stop_status = self.client.get_order(symbol=symbol, orderId=stop_order['orderId'])
                take_status = self.client.get_order(symbol=symbol, orderId=take_order['orderId'])
            
            updated = False
            
            # Проверяем изменения статуса Stop Loss
            if stop_order['status'] != stop_status['status']:
                old_status = stop_order['status']
                stop_order['status'] = stop_status['status']
                logger.info(f"🛑 Stop Loss изменил статус: {old_status} → {stop_status['status']}")
                
                if stop_status['status'] == 'FILLED':
                    # Stop Loss исполнен - отменяем Take Profit
                    self._cancel_order(symbol, take_order['orderId'])
                    order_group['status'] = 'COMPLETED'
                    self._send_stop_filled_notification(order_group)
                    updated = True
            
            # Проверяем изменения статуса Take Profit
            if take_order['status'] != take_status['status']:
                old_status = take_order['status']
                take_order['status'] = take_status['status']
                logger.info(f"🎯 Take Profit изменил статус: {old_status} → {take_status['status']}")
                
                if take_status['status'] == 'FILLED':
                    # Take Profit исполнен - отменяем Stop Loss
                    self._cancel_order(symbol, stop_order['orderId'])
                    order_group['status'] = 'COMPLETED'
                    self._send_take_filled_notification(order_group)
                    updated = True
            
            return updated
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки статуса ордеров: {e}")
            return False
    
    def _cancel_order(self, symbol: str, order_id: int):
        """Отменяет ордер"""
        try:
            if config.BINANCE_TESTNET:
                result = self.client.futures_cancel_order(symbol=symbol, orderId=order_id)
            else:
                result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            logger.info(f"❌ Ордер #{order_id} отменен: {result['status']}")
            return result
        except Exception as e:
            logger.error(f"❌ Ошибка отмены ордера #{order_id}: {e}")
            return None
    
    def _send_stop_filled_notification(self, order_group: Dict):
        """Уведомление об исполнении Stop Loss"""
        signal = order_group['signal_data']
        stop_order = order_group['stop_order']
        
        message = f"""
🛑 <b>STOP LOSS ИСПОЛНЕН</b>

📊 <b>Пара:</b> {signal['ticker']}
📈 <b>Направление:</b> {signal['signal']}
💰 <b>Цена Stop:</b> {stop_order['price']}
📋 <b>Order ID:</b> #{stop_order['orderId']}

❌ Take Profit автоматически отменен
⏰ <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}
"""
        
        try:
            self.telegram.send_message(message)
            logger.info("📱 ✅ Уведомление о Stop Loss отправлено")
        except Exception as e:
            logger.error(f"📱 ❌ Ошибка отправки уведомления: {e}")
    
    def _send_take_filled_notification(self, order_group: Dict):
        """Уведомление об исполнении Take Profit"""
        signal = order_group['signal_data']
        take_order = order_group['take_order']
        
        message = f"""
🎯 <b>TAKE PROFIT ИСПОЛНЕН</b>

📊 <b>Пара:</b> {signal['ticker']}
📈 <b>Направление:</b> {signal['signal']}
💰 <b>Цена Take:</b> {take_order['price']}
📋 <b>Order ID:</b> #{take_order['orderId']}

❌ Stop Loss автоматически отменен
💰 <b>Прибыль зафиксирована!</b>
⏰ <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}
"""
        
        try:
            self.telegram.send_message(message)
            logger.info("📱 ✅ Уведомление о Take Profit отправлено")
        except Exception as e:
            logger.error(f"📱 ❌ Ошибка отправки уведомления: {e}")

class EnhancedSignalProcessor:
    """
    Улучшенный процессор сигналов с проверкой схождений
    Интегрирован с существующей архитектурой PATRIOT
    MVP: Выставляет реальные ордера на Binance Testnet
    """
    
    def __init__(self, ticker: str, price_threshold: float = 0.005, risk_percent: float = 5.0):
        self.ticker = ticker
        self.timeframes = config.TIMEFRAMES
        self.price_threshold = price_threshold
        self.min_matching_tfs = 2
        self.risk_percent = risk_percent  # 5% от капитала
        
        # Инициализация Binance клиента
        self.binance_client = None
        self._init_binance_client()
        
        # Инициализация менеджера ордеров
        self.order_manager = None
        if self.binance_client:
            self.order_manager = OrderManager(self.binance_client, telegram_bot)
            self.order_manager.start_monitoring()
        
        logger.info(f"📊 Enhanced Signal Processor initialized for {ticker} (Risk: {risk_percent}%)")
    
    def _init_binance_client(self):
        """Инициализация Binance клиента для тестнета"""
        try:
            # Проверяем наличие ключей
            if not config.BINANCE_API_KEY or not config.BINANCE_API_SECRET:
                logger.error(f"❌ Отсутствуют API ключи для {config.NETWORK_MODE}")
                logger.error(f"🔧 Проверьте .env файл и переменные BINANCE_{config.NETWORK_MODE}_API_KEY/SECRET")
                self.binance_client = None
                return
            
            logger.info(f"🔧 Инициализация Binance клиента...")
            logger.info(f"🌐 Режим: {config.NETWORK_MODE} (Testnet: {config.BINANCE_TESTNET})")
            logger.info(f"🔑 API Key: ...{config.BINANCE_API_KEY[-8:]}")
            
            self.binance_client = Client(
                api_key=config.BINANCE_API_KEY,
                api_secret=config.BINANCE_API_SECRET,
                testnet=config.BINANCE_TESTNET
            )
            
            # Проверяем подключение - используем правильный метод для каждого режима
            if config.BINANCE_TESTNET:
                # Для testnet используем фьючерсы
                account_info = self.binance_client.futures_account()
                logger.info(f"✅ Binance подключен (Testnet: {config.BINANCE_TESTNET})")
                logger.info(f"💰 Фьючерсный баланс: {account_info['totalWalletBalance']} USDT")
                logger.info(f"💵 Доступно: {account_info['availableBalance']} USDT")
            else:
                # Для mainnet используем спот аккаунт
                account_info = self.binance_client.get_account()
                logger.info(f"✅ Binance подключен (Testnet: {config.BINANCE_TESTNET})")
                logger.info(f"📊 Статус аккаунта: {account_info['accountType']}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Binance: {e}")
            logger.error(f"🔧 Проверьте API ключи в .env файле для режима {config.NETWORK_MODE}")
            self.binance_client = None
    
    def check_price_proximity(self, price1: float, price2: float) -> bool:
        """Проверяет близость цен в пределах threshold"""
        if None in (price1, price2) or price1 <= 0 or price2 <= 0:
            return False
        return abs(price1 - price2) / ((price1 + price2) / 2) <= self.price_threshold
    
    def analyze_convergence(self, signals: Dict[str, Dict]) -> Optional[Dict]:
        """
        Анализирует схождение сигналов по таймфреймам
        Возвращает усредненный сигнал если найдено схождение
        """
        if len(signals) < self.min_matching_tfs:
            logger.debug(f"Недостаточно сигналов для анализа: {len(signals)}")
            return None
        
        # Группируем по направлению
        long_signals = {tf: sig for tf, sig in signals.items() if sig.get('signal') == 'LONG'}
        short_signals = {tf: sig for tf, sig in signals.items() if sig.get('signal') == 'SHORT'}
        
        # Проверяем схождения для каждого направления
        for direction, direction_signals in [('LONG', long_signals), ('SHORT', short_signals)]:
            if len(direction_signals) < self.min_matching_tfs:
                continue
                
            # Проверяем близость цен входа
            converged_tfs = self._find_price_convergence(direction_signals)
            
            if len(converged_tfs) >= self.min_matching_tfs:
                logger.info(f"🎯 СХОЖДЕНИЕ НАЙДЕНО: {self.ticker} {direction} на {len(converged_tfs)} ТФ")
                return self._create_convergence_signal(direction, converged_tfs, direction_signals)
        
        logger.debug(f"Схождения не найдено для {self.ticker}")
        return None
    
    def _find_price_convergence(self, signals: Dict[str, Dict]) -> Set[str]:
        """Находит таймфреймы с близкими ценами входа"""
        converged_tfs = set()
        timeframes = list(signals.keys())
        
        # Проверяем все пары ТФ
        for i, tf1 in enumerate(timeframes):
            for tf2 in timeframes[i+1:]:
                price1 = signals[tf1].get('entry_price')
                price2 = signals[tf2].get('entry_price')
                
                if price1 is not None and price2 is not None and self.check_price_proximity(price1, price2):
                    converged_tfs.update([tf1, tf2])
                    logger.debug(f"Схождение цен: {tf1}={price1:.6f}, {tf2}={price2:.6f}")
        
        return converged_tfs
    
    def _create_convergence_signal(self, direction: str, timeframes: Set[str], signals: Dict) -> Dict:
        """Создает усредненный сигнал из схождений"""
        tf_list = list(timeframes)
        
        # Усредняем параметры
        entry_prices = [signals[tf]['entry_price'] for tf in tf_list]
        stop_losses = [signals[tf].get('stop_loss', 0) for tf in tf_list]
        take_profits = [signals[tf].get('take_profit', 0) for tf in tf_list]
        confidences = [signals[tf].get('confidence', 50) for tf in tf_list]
        
        converged_signal = {
            'ticker': self.ticker,
            'signal': direction,
            'timeframes': tf_list,
            'entry_price': round(mean(entry_prices), 6),
            'stop_loss': round(mean(stop_losses), 6) if any(stop_losses) else None,
            'take_profit': round(mean(take_profits), 6) if any(take_profits) else None,
            'confidence': mean(confidences) / 100,  # Конвертируем в 0.0-1.0
            'convergence_count': len(timeframes),
            'price_threshold': self.price_threshold,
            'timestamp': signals[tf_list[0]].get('timestamp')
        }
        
        logger.info(f"✅ Создан сигнал схождения: {direction} {converged_signal['entry_price']:.6f}")
        return converged_signal
    
    def get_symbol_info(self) -> Optional[Dict]:
        """Получает информацию о символе для определения точности"""
        if not self.binance_client:
            return None
            
        try:
            if config.BINANCE_TESTNET:
                exchange_info = self.binance_client.futures_exchange_info()
                symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == self.ticker), None)
            else:
                symbol_info = self.binance_client.get_symbol_info(self.ticker)
            return symbol_info
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о символе: {e}")
            return None
    
    def get_price_precision(self, symbol_info: Dict) -> int:
        """Определяет точность цены для символа"""
        try:
            price_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'), None)
            if price_filter:
                tick_size = float(price_filter['tickSize'])
                # Вычисляем количество знаков после запятой
                return len(str(tick_size).rstrip('0').split('.')[-1]) if '.' in str(tick_size) else 0
            return 2  # По умолчанию 2 знака
        except Exception as e:
            logger.error(f"❌ Ошибка определения точности цены: {e}")
            return 2
    
    def round_price(self, price: float, precision: int) -> float:
        """Округляет цену до указанной точности"""
        return round(price, precision)
    
    def get_account_balance(self) -> Dict[str, Dict[str, float]]:
        """Получает баланс аккаунта"""
        if not self.binance_client:
            return {}
        
        try:
            if config.BINANCE_TESTNET:
                # Для testnet используем фьючерсы
                account = self.binance_client.futures_account()
                # Создаем совместимый формат
                usdt_balance = float(account['availableBalance'])
                balances = {
                    'USDT': {
                        'free': usdt_balance,
                        'locked': float(account['totalWalletBalance']) - usdt_balance,
                        'total': float(account['totalWalletBalance'])
                    }
                }
                return balances
            else:
                # Для mainnet используем спот аккаунт
                account = self.binance_client.get_account()
                balances: Dict[str, Dict[str, float]] = {}
                
                for balance in account['balances']:
                    asset = balance['asset']
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    total = free + locked
                    
                    if total > 0:
                        balances[asset] = {
                            'free': free,
                            'locked': locked,
                            'total': total
                        }
                
                return balances
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения баланса: {e}")
            return {}
    
    def calculate_position_size(self, signal_data: Dict) -> Dict:
        """Рассчитывает размер позиции на основе риска"""
        if not self.binance_client:
            return {}
        
        try:
            # Получаем баланс USDT
            balances = self.get_account_balance()
            usdt_info = balances.get('USDT', {})
            usdt_balance = usdt_info.get('free', 0.0) if usdt_info else 0.0
            
            if usdt_balance <= 0:
                logger.error("❌ Недостаточно USDT на балансе")
                return {}
            
            # Рассчитываем сумму ордера (5% от баланса)
            order_amount_usdt = usdt_balance * (self.risk_percent / 100)
            
            # Получаем текущую цену
            current_price = float(signal_data['entry_price'])
            
            # Рассчитываем количество базовой валюты
            quantity = order_amount_usdt / current_price
            
            # Получаем информацию о символе для округления
            if config.BINANCE_TESTNET:
                exchange_info = self.binance_client.futures_exchange_info()
                symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == self.ticker), None)
            else:
                symbol_info = self.binance_client.get_symbol_info(self.ticker)
            
            if symbol_info:
                # Находим точность для количества
                lot_size_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
                if lot_size_filter:
                    step_size = float(lot_size_filter['stepSize'])
                    # Округляем количество вниз до допустимого шага
                    quantity = float(Decimal(str(quantity)).quantize(Decimal(str(step_size)), rounding=ROUND_DOWN))
            
            position_info = {
                'symbol': self.ticker,
                'quantity': quantity,
                'price': current_price,
                'order_amount_usdt': order_amount_usdt,
                'usdt_balance': usdt_balance,
                'risk_percent': self.risk_percent
            }
            
            logger.info(f"📊 Расчет позиции для {self.ticker}:")
            logger.info(f"  💰 Баланс USDT: {usdt_balance:.2f}")
            logger.info(f"  🎯 Размер ордера: {order_amount_usdt:.2f} USDT ({self.risk_percent}%)")
            logger.info(f"  📦 Количество: {quantity:.6f}")
            logger.info(f"  💲 Цена: {current_price:.6f}")
            
            return position_info
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета позиции: {e}")
            return {}
    
    def place_full_order_setup(self, signal_data: Dict) -> Dict:
        """Выставляет полную связку ордеров: Market Entry + Stop Loss + Take Profit"""
        if not self.binance_client:
            logger.error("❌ Binance клиент не инициализирован")
            return {}
        
        try:
            # Рассчитываем размер позиции
            position_info = self.calculate_position_size(signal_data)
            if not position_info:
                return {}
            
            # Получаем информацию о символе для правильного округления цен
            symbol_info = self.get_symbol_info()
            price_precision = 2  # По умолчанию
            if symbol_info:
                price_precision = self.get_price_precision(symbol_info)
                logger.info(f"📊 Точность цены для {self.ticker}: {price_precision} знаков")
            
            # Округляем цены до правильной точности
            stop_loss_price = self.round_price(float(signal_data['stop_loss']), price_precision)
            take_profit_price = self.round_price(float(signal_data['take_profit']), price_precision)
            
            logger.info(f"🔧 Округленные цены:")
            logger.info(f"  🛑 Stop Loss: {signal_data['stop_loss']:.6f} → {stop_loss_price}")
            logger.info(f"  🎯 Take Profit: {signal_data['take_profit']:.6f} → {take_profit_price}")
            
            # Настраиваем режим позиций для фьючерсов
            if config.BINANCE_TESTNET:
                try:
                    logger.info("🔧 Проверяем режим позиций...")
                    position_mode = self.binance_client.futures_get_position_mode()
                    logger.info(f"📊 Текущий режим позиций: {'Hedge' if position_mode['dualSidePosition'] else 'One-way'}")
                    
                    if not position_mode['dualSidePosition']:
                        logger.info("🔄 Переключаем в режим Hedge (двусторонние позиции)...")
                        self.binance_client.futures_change_position_mode(dualSidePosition=True)
                        logger.info("✅ Режим Hedge активирован")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось изменить режим позиций: {e}")
                    logger.info("💡 Попробуем в текущем режиме...")
            
            # Определяем сторону ордера
            side = Client.SIDE_BUY if signal_data['signal'] == 'LONG' else Client.SIDE_SELL
            position_side = 'LONG' if signal_data['signal'] == 'LONG' else 'SHORT'  # Для фьючерсов
            
            logger.info(f"🚀 === ВЫСТАВЛЯЕМ ПОЛНУЮ СВЯЗКУ ОРДЕРОВ ===")
            logger.info(f"📊 {side} ордер для {self.ticker}")
            logger.info(f"� Количество: {position_info['quantity']:.6f}")
            logger.info(f"🎯 Entry: Market")
            logger.info(f"🛑 Stop: {signal_data['stop_loss']:.6f}")
            logger.info(f"🎯 Take: {signal_data['take_profit']:.6f}")
            
            # 1. Выставляем Entry ордер (Market)
            if config.BINANCE_TESTNET:
                # Для testnet используем futures API с positionSide
                entry_order = self.binance_client.futures_create_order(
                    symbol=self.ticker,
                    side=side,
                    type=Client.ORDER_TYPE_MARKET,
                    quantity=position_info['quantity'],
                    positionSide=position_side
                )
            else:
                # Для mainnet используем spot API
                entry_order = self.binance_client.create_order(
                    symbol=self.ticker,
                    side=side,
                    type=Client.ORDER_TYPE_MARKET,
                    quantity=position_info['quantity']
                )
            
            logger.info(f"✅ Entry ордер выставлен: #{entry_order['orderId']}")
            
            # 2. Выставляем Stop Loss ордер
            stop_side = Client.SIDE_SELL if signal_data['signal'] == 'LONG' else Client.SIDE_BUY
            if config.BINANCE_TESTNET:
                stop_order = self.binance_client.futures_create_order(
                    symbol=self.ticker,
                    side=stop_side,
                    type='STOP_MARKET',
                    quantity=position_info['quantity'],
                    stopPrice=stop_loss_price,
                    positionSide=position_side
                )
            else:
                stop_order = self.binance_client.create_order(
                    symbol=self.ticker,
                    side=stop_side,
                    type=Client.ORDER_TYPE_STOP_LOSS,
                    quantity=position_info['quantity'],
                    stopPrice=stop_loss_price
                )
            
            logger.info(f"� Stop Loss выставлен: #{stop_order['orderId']} at {signal_data['stop_loss']:.6f}")
            
            # 3. Выставляем Take Profit ордер
            take_side = Client.SIDE_SELL if signal_data['signal'] == 'LONG' else Client.SIDE_BUY
            if config.BINANCE_TESTNET:
                take_order = self.binance_client.futures_create_order(
                    symbol=self.ticker,
                    side=take_side,
                    type=Client.ORDER_TYPE_LIMIT,
                    quantity=position_info['quantity'],
                    price=signal_data['take_profit'],
                    timeInForce=Client.TIME_IN_FORCE_GTC,
                    positionSide=position_side
                )
            else:
                take_order = self.binance_client.create_order(
                    symbol=self.ticker,
                    side=take_side,
                    type=Client.ORDER_TYPE_LIMIT,
                    quantity=position_info['quantity'],
                    price=signal_data['take_profit'],
                    timeInForce=Client.TIME_IN_FORCE_GTC
                )
            
            logger.info(f"🎯 Take Profit выставлен: #{take_order['orderId']} at {signal_data['take_profit']:.6f}")
            
            # Добавляем в менеджер ордеров для мониторинга
            if self.order_manager:
                self.order_manager.add_order_group(entry_order, stop_order, take_order, signal_data)
            
            order_result = {
                'entry_order': entry_order,
                'stop_order': stop_order,
                'take_order': take_order,
                'position_info': position_info,
                'signal_data': signal_data,
                'success': True
            }
            
            logger.info(f"✅ === ВСЕ ОРДЕРА УСПЕШНО ВЫСТАВЛЕНЫ ===")
            
            return order_result
            
        except BinanceAPIException as e:
            logger.error(f"❌ Binance API ошибка: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"❌ Ошибка выставления ордеров: {e}")
            return {'success': False, 'error': str(e)}
    
    def process_ticker(self) -> bool:
        """
        Основной метод обработки тикера
        MVP: Анализ + Telegram + Реальный ордер на Binance
        Возвращает True если сигнал найден и ордер выставлен
        """
        try:
            logger.info(f"🔍 === НАЧИНАЕМ АНАЛИЗ {self.ticker} ===")
            
            # 1. Используем SignalAnalyzer для получения сигналов
            analyzer = SignalAnalyzer(self.ticker)
            analysis_result = analyzer.analyze_ticker(stop_event=None)
            
            if not analysis_result:
                logger.info(f"📊 Сигналы не найдены для {self.ticker}")
                return False
            
            # SignalAnalyzer УЖЕ проверил схождения и вернул консолидированный сигнал!
            logger.info(f"🎯 СИГНАЛ НАЙДЕН для {self.ticker}:")
            logger.info(f"  📈 Направление: {analysis_result['signal']}")
            logger.info(f"  💰 Цена входа: {analysis_result['entry_price']:.6f}")
            logger.info(f"  🛑 Stop Loss: {analysis_result['stop_loss']:.6f}")
            logger.info(f"  🎯 Take Profit: {analysis_result['take_profit']:.6f}")
            logger.info(f"  ⏰ Таймфреймы: {analysis_result['timeframes_str']}")
            logger.info(f"  📊 Confidence: {analysis_result['confidence']:.3f}")
            
            # 2. Отправляем в Telegram
            try:
                telegram_bot.send_signal(analysis_result)
                logger.info(f"📱 ✅ Уведомление отправлено в Telegram")
            except Exception as e:
                logger.error(f"📱 ❌ Ошибка отправки в Telegram: {e}")
            
            # 3. MVP: Выставляем полную связку ордеров на Binance
            if self.binance_client:
                logger.info(f"🚀 Выставляем полную связку ордеров на Binance...")
                
                order_result = self.place_full_order_setup(analysis_result)
                
                if order_result.get('success'):
                    logger.info(f"✅ === ПОЛНАЯ СВЯЗКА ОРДЕРОВ ВЫСТАВЛЕНА ===")
                    logger.info(f"📋 Entry Order ID: {order_result['entry_order']['orderId']}")
                    logger.info(f"� Stop Order ID: {order_result['stop_order']['orderId']}")
                    logger.info(f"🎯 Take Order ID: {order_result['take_order']['orderId']}")
                    logger.info(f"�💰 Размер позиции: {order_result['position_info']['quantity']:.6f}")
                    logger.info(f"💵 Сумма ордера: {order_result['position_info']['order_amount_usdt']:.2f} USDT")
                    logger.info(f"👁️ Мониторинг ордеров активен")
                    return True
                else:
                    logger.error(f"❌ === ОШИБКА ВЫСТАВЛЕНИЯ ОРДЕРОВ ===")
                    logger.error(f"🔥 Причина: {order_result.get('error', 'Unknown error')}")
                    return False
            else:
                logger.warning(f"⚠️ Binance клиент недоступен - пропускаем выставление ордеров")
                return False
                
        except Exception as e:
            logger.error(f"❌ === КРИТИЧЕСКАЯ ОШИБКА ОБРАБОТКИ {self.ticker} ===")
            logger.error(f"🔥 Ошибка: {e}")
            return False
    
    def shutdown(self):
        """Корректное завершение работы с остановкой мониторинга"""
        if self.order_manager:
            self.order_manager.stop_monitoring()
            logger.info("🛑 Order Manager остановлен")


def process_multiple_tickers(tickers: List[str], price_threshold: float = 0.005) -> Dict[str, bool]:
    """
    Обрабатывает несколько тикеров с проверкой схождений
    
    Args:
        tickers: Список тикеров для анализа
        price_threshold: Порог близости цен (по умолчанию 0.5%)
    
    Returns:
        Словарь {ticker: success_status}
    """
    results = {}
    
    logger.info(f"🚀 Начинаем анализ схождений для {len(tickers)} тикеров")
    
    for ticker in tickers:
        processor = EnhancedSignalProcessor(ticker, price_threshold)
        results[ticker] = processor.process_ticker()
    
    successful = sum(results.values())
    logger.info(f"📊 Результат: {successful}/{len(tickers)} тикеров с найденными схождениями")
    
    return results


# Пример использования MVP с полным управлением ордерами
if __name__ == "__main__":
    logger.info("🚀 === ЗАПУСК ENHANCED SIGNAL PROCESSOR MVP v2.1 ===")
    logger.info("✨ Новые возможности:")
    logger.info("  🎯 Автоматические Stop Loss и Take Profit ордера")
    logger.info("  👁️ Мониторинг исполнения ордеров в реальном времени")
    logger.info("  📱 Уведомления в Telegram о всех изменениях")
    logger.info("  ❌ Автоотмена противоположного ордера при исполнении")
    
    # Проверяем настройки
    logger.info(f"🌐 Режим: {'TESTNET' if config.BINANCE_TESTNET else 'MAINNET'}")
    logger.info(f"🎯 Риск на сделку: 5%")
    
    # Тест одного тикера с полным управлением ордерами
    test_ticker = "BTCUSDT"
    processor = EnhancedSignalProcessor(test_ticker, risk_percent=5.0)
    
    try:
        # Показываем баланс перед торговлей
        balances = processor.get_account_balance()
        if balances:
            logger.info("💰 === ТЕКУЩИЙ БАЛАНС ===")
            for asset, balance in balances.items():
                if balance['total'] > 0:
                    logger.info(f"  {asset}: {balance['total']:.6f} (Free: {balance['free']:.6f})")
        
        # Запускаем анализ и торговлю
        success = processor.process_ticker()
        
        if success:
            logger.info("🎉 === MVP УСПЕШНО ЗАВЕРШЕН ===")
            logger.info("👁️ Мониторинг ордеров продолжает работать...")
            print("✅ Результат: SUCCESS - Сигнал найден и полная связка ордеров выставлена!")
            print("📱 Проверьте Telegram для уведомлений об исполнении ордеров")
            
            # Даем время на демонстрацию мониторинга
            logger.info("⏳ Демонстрация мониторинга (30 секунд)...")
            time.sleep(30)
            
        else:
            logger.info("📊 === MVP ЗАВЕРШЕН БЕЗ СИГНАЛА ===")
            print("📊 Результат: NO SIGNAL - Схождений не найдено или ошибка ордеров")
    
    except KeyboardInterrupt:
        logger.info("⌨️ Прерывание пользователем")
    
    finally:
        # Корректное завершение
        processor.shutdown()
        logger.info("🏁 === MVP ЗАВЕРШЕН ===")
    
    # # Раскомментируйте для тестирования нескольких тикеров
    # test_tickers = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    # logger.info(f"🔄 Тестируем {len(test_tickers)} тикеров...")
    # 
    # processors = []
    # try:
    #     for ticker in test_tickers:
    #         proc = EnhancedSignalProcessor(ticker, risk_percent=5.0)
    #         processors.append(proc)
    #         success = proc.process_ticker()
    #         logger.info(f"📊 {ticker}: {'SUCCESS' if success else 'NO SIGNAL'}")
    # 
    #     logger.info("⏳ Мониторинг всех ордеров (60 секунд)...")
    #     time.sleep(60)
    # 
    # finally:
    #     for proc in processors:
    #         proc.shutdown()
    #     logger.info("🏁 Все процессоры остановлены")
