"""
Orders Watchdog - Независимый мониторинг ордеров
===============================================

Отдельный сервис для отслеживания исполнения ордеров:
- Мониторит все открытые лимитные ордера
- При исполнении основного ордера автоматически ставит SL/TP
- Отправляет уведомления в Telegram
- Работает независимо от ticker_monitor

Архитектура:
ticker_monitor.py (поиск сигналов) → order_executor.py (размещение лимитных ордеров) 
                                                    ↓
orders_watchdog.py (мониторинг исполнения) → telegram уведомления + SL/TP

Author: HEDGER
Version: 1.0 - Independent Order Monitoring
"""

import time
import signal
import sys
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

# Локальные импорты
from config import (
    BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET, 
    FUTURES_LEVERAGE, FUTURES_MARGIN_TYPE
)
from utils import logger
from telegram_bot import telegram_bot
from symbol_cache import round_price_for_symbol, round_quantity_for_symbol

# Binance - создаем типы для правильной работы с Pylance
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from binance.client import Client as BinanceClient
    from binance.exceptions import BinanceAPIException as BinanceError
else:
    try:
        from binance.client import Client as BinanceClient
        from binance.exceptions import BinanceAPIException as BinanceError
        BINANCE_AVAILABLE = True
    except ImportError:
        logger.error("❌ python-binance not installed")
        BINANCE_AVAILABLE = False
        
        # Создаем заглушки с правильными type hints
        class BinanceClient:
            def __init__(self, *args: Any, **kwargs: Any) -> None: pass
            def futures_account(self) -> Dict[str, Any]: return {}
            def futures_get_order(self, **kwargs: Any) -> Dict[str, Any]: return {}
            def futures_get_open_orders(self) -> List[Dict[str, Any]]: return []
            def futures_position_information(self) -> List[Dict[str, Any]]: return []
            def futures_create_order(self, **kwargs: Any) -> Dict[str, Any]: return {}
            def futures_cancel_order(self, **kwargs: Any) -> None: pass
        
        class BinanceError(Exception): pass

# Устанавливаем BINANCE_AVAILABLE если он не был установлен в except блоке
if 'BINANCE_AVAILABLE' not in locals():
    BINANCE_AVAILABLE = True


class OrderStatus(Enum):
    """Статусы ордеров для отслеживания"""
    PENDING = "PENDING"           # Ожидает исполнения
    FILLED = "FILLED"             # Исполнен
    CANCELLED = "CANCELLED"       # Отменен
    SL_TP_PLACED = "SL_TP_PLACED" # SL/TP размещены
    SL_TP_ERROR = "SL_TP_ERROR"   # Ошибка размещения SL/TP
    COMPLETED = "COMPLETED"       # Полностью завершен


@dataclass
class WatchedOrder:
    """Отслеживаемый ордер"""
    symbol: str
    order_id: str
    side: str  # BUY/SELL
    position_side: str  # LONG/SHORT
    quantity: float
    price: float
    signal_type: str  # LONG/SHORT
    stop_loss: float
    take_profit: float
    status: OrderStatus
    created_at: datetime
    filled_at: Optional[datetime] = None
    sl_order_id: Optional[str] = None
    tp_order_id: Optional[str] = None
    sl_tp_attempts: int = 0  # Счетчик попыток размещения SL/TP
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для JSON"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['filled_at'] = self.filled_at.isoformat() if self.filled_at else None
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WatchedOrder':
        """Создание из словаря"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['filled_at'] = datetime.fromisoformat(data['filled_at']) if data['filled_at'] else None
        data['status'] = OrderStatus(data['status'])
        
        # Обеспечиваем обратную совместимость для sl_tp_attempts
        if 'sl_tp_attempts' not in data:
            data['sl_tp_attempts'] = 0
            
        return cls(**data)


class OrdersWatchdog:
    """Независимый мониторинг ордеров"""
    
    def __init__(self):
        self.client: Optional[BinanceClient] = None
        self.watched_orders: Dict[str, WatchedOrder] = {}  # order_id -> WatchedOrder
        self.stop_event = threading.Event()
        self.check_interval = 5  # Проверяем каждые 5 секунд
        self.persistence_file = Path('orders_watchdog_state.json')
        self.requests_file = Path('orders_watchdog_requests.json')  # Файл для входящих запросов
        self.lock = threading.Lock()
        
        # Инициализация
        self._init_client()
        self._load_persistent_state()
        self._setup_signal_handlers()
        
        logger.info("🐕 Orders Watchdog initialized")
    
    def _init_client(self) -> None:
        """Инициализация Binance клиента"""
        if not BINANCE_AVAILABLE:
            logger.error("❌ Binance library not available")
            return
            
        if not BINANCE_API_KEY or not BINANCE_API_SECRET:
            logger.error("❌ Binance API ключи не настроены")
            return
        
        try:
            logger.info(f"🔧 Подключение к Binance ({'TESTNET' if BINANCE_TESTNET else 'MAINNET'})...")
            
            self.client = BinanceClient(
                api_key=BINANCE_API_KEY,
                api_secret=BINANCE_API_SECRET,
                testnet=BINANCE_TESTNET
            )
            
            # Тест подключения
            if self.client:
                self.client.futures_account()
            logger.info("✅ Подключение к Binance успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Binance: {e}")
            self.client = None
    
    def _setup_signal_handlers(self) -> None:
        """Настройка graceful shutdown"""
        def signal_handler(signum: int, frame: Any) -> None:
            signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
            logger.info(f"🛑 Received {signal_name} - shutting down Orders Watchdog...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _load_persistent_state(self) -> None:
        """Загружает состояние из файла"""
        try:
            if self.persistence_file.exists():
                with open(self.persistence_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for order_data in data.get('watched_orders', []):
                    order = WatchedOrder.from_dict(order_data)
                    self.watched_orders[order.order_id] = order
                
                logger.info(f"📂 Загружено {len(self.watched_orders)} отслеживаемых ордеров")
            else:
                logger.info("📂 Файл состояния не найден, начинаем с пустого состояния")
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки состояния: {e}")
    
    def _save_persistent_state(self) -> None:
        """Сохраняет состояние в файл"""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'watched_orders': [order.to_dict() for order in self.watched_orders.values()]
            }
            
            with open(self.persistence_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения состояния: {e}")
    
    def add_order_to_watch(self, order_data: Dict[str, Any]) -> bool:
        """
        Добавляет ордер для отслеживания
        
        Args:
            order_data: {
                'symbol': 'BTCUSDT',
                'order_id': '12345',
                'side': 'BUY',
                'position_side': 'LONG',
                'quantity': 0.001,
                'price': 45000.0,
                'signal_type': 'LONG',
                'stop_loss': 44000.0,
                'take_profit': 47000.0
            }
        """
        try:
            order = WatchedOrder(
                symbol=order_data['symbol'],
                order_id=str(order_data['order_id']),
                side=order_data['side'],
                position_side=order_data['position_side'],
                quantity=float(order_data['quantity']),
                price=float(order_data['price']),
                signal_type=order_data['signal_type'],
                stop_loss=float(order_data['stop_loss']),
                take_profit=float(order_data['take_profit']),
                status=OrderStatus.PENDING,
                created_at=datetime.now()
            )
            
            with self.lock:
                self.watched_orders[order.order_id] = order
                self._save_persistent_state()
            
            logger.info(f"👁️ Добавлен в отслеживание: {order.symbol} ордер {order.order_id}")
            self._send_watchdog_notification(f"👁️ Начал отслеживание ордера {order.symbol} #{order.order_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления ордера в отслеживание: {e}")
            return False
    
    def remove_order_from_watch(self, order_id: str) -> bool:
        """Удаляет ордер из отслеживания"""
        try:
            with self.lock:
                if order_id in self.watched_orders:
                    order = self.watched_orders.pop(order_id)
                    self._save_persistent_state()
                    logger.info(f"👁️ Убран из отслеживания: {order.symbol} ордер {order_id}")
                    return True
                else:
                    logger.warning(f"⚠️ Ордер {order_id} не найден в отслеживании")
                    return False
        except Exception as e:
            logger.error(f"❌ Ошибка удаления ордера из отслеживания: {e}")
            return False
    
    def _process_incoming_requests(self) -> None:
        """Обрабатывает входящие запросы на добавление ордеров"""
        try:
            if not self.requests_file.exists():
                return
            
            # Читаем запросы
            with open(self.requests_file, 'r', encoding='utf-8') as f:
                requests_data = json.load(f)
            
            if not requests_data:
                return
            
            # Обрабатываем каждый запрос
            processed_requests = []
            for request in requests_data:
                try:
                    if request['action'] == 'add_order':
                        if self.add_order_to_watch(request['data']):
                            logger.info(f"📥 Обработан запрос на добавление ордера")
                        else:
                            logger.error(f"❌ Не удалось обработать запрос")
                    
                    processed_requests.append(request)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки запроса: {e}")
            
            # Очищаем файл после обработки
            if processed_requests:
                with open(self.requests_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки входящих запросов: {e}")
    
    def check_orders_status(self) -> None:
        """Проверяет статус всех отслеживаемых ордеров"""
        if not self.client:
            return
        
        with self.lock:
            orders_to_check = list(self.watched_orders.values())
        
        if not orders_to_check:
            return
        
        logger.debug(f"🔍 Проверяем {len(orders_to_check)} ордеров...")
        
        for order in orders_to_check:
            if order.status == OrderStatus.PENDING:
                self._check_single_order(order)
            elif order.status == OrderStatus.FILLED:
                self._handle_filled_order(order)
            elif order.status == OrderStatus.SL_TP_PLACED:
                self._check_sl_tp_orders(order)
            elif order.status == OrderStatus.SL_TP_ERROR:
                # Игнорируем ордера с ошибками SL/TP
                continue
    
    def _check_single_order(self, order: WatchedOrder) -> None:
        """Проверяет статус одного ордера"""
        if not self.client:
            return
            
        try:
            # Получаем информацию об ордере
            order_info = self.client.futures_get_order(
                symbol=order.symbol,
                orderId=order.order_id
            )
            
            status = order_info['status']
            
            if status == 'FILLED':
                logger.info(f"🎉 Ордер {order.symbol} #{order.order_id} ИСПОЛНЕН!")
                
                # Обновляем статус
                with self.lock:
                    order.status = OrderStatus.FILLED
                    order.filled_at = datetime.now()
                    self._save_persistent_state()
                
                # Отправляем уведомление об исполнении
                self._send_order_filled_notification(order, order_info)
                
            elif status in ['CANCELED', 'REJECTED', 'EXPIRED']:
                logger.info(f"🚫 Ордер {order.symbol} #{order.order_id} отменен/отклонен: {status}")
                
                # Обновляем статус и удаляем из отслеживания
                with self.lock:
                    order.status = OrderStatus.CANCELLED
                    self._save_persistent_state()
                
                # Отправляем уведомление об отмене
                self._send_order_cancelled_notification(order, status)
                
                # Удаляем из отслеживания
                self.remove_order_from_watch(order.order_id)
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки ордера {order.order_id}: {e}")
    
    def _handle_filled_order(self, order: WatchedOrder) -> None:
        """Обрабатывает исполненный ордер - размещает SL/TP"""
        if order.status != OrderStatus.FILLED:
            return
        
        # Защита от повторных попыток
        if order.sl_tp_attempts >= 3:
            logger.warning(f"⚠️ Максимум попыток размещения SL/TP для {order.symbol} исчерпан")
            with self.lock:
                order.status = OrderStatus.SL_TP_ERROR
                self._save_persistent_state()
            return
            
        try:
            # Увеличиваем счетчик попыток
            with self.lock:
                order.sl_tp_attempts += 1
                self._save_persistent_state()
            
            logger.info(f"🛡️ Размещаем SL/TP для {order.symbol} (попытка {order.sl_tp_attempts}/3)...")
            
            # Размещаем Stop Loss
            sl_success, sl_order_id = self._place_stop_loss(order)
            
            # Размещаем Take Profit
            tp_success, tp_order_id = self._place_take_profit(order)
            
            if sl_success and tp_success:
                # Обновляем статус (проверяем что order_id не None)
                if sl_order_id and tp_order_id:
                    with self.lock:
                        order.status = OrderStatus.SL_TP_PLACED
                        order.sl_order_id = sl_order_id
                        order.tp_order_id = tp_order_id
                        self._save_persistent_state()
                    
                    logger.info(f"✅ SL/TP размещены для {order.symbol}: SL={sl_order_id}, TP={tp_order_id}")
                    
                    # Отправляем уведомление о полном открытии позиции
                    self._send_position_opened_notification(order, sl_order_id, tp_order_id)
                    
                    # НЕ удаляем из отслеживания - продолжаем мониторить SL/TP ордера
                    logger.info(f"👁️ Продолжаем отслеживание SL/TP для {order.symbol}")
                else:
                    logger.error(f"❌ Получены пустые ID для SL/TP ордеров")
                    with self.lock:
                        order.status = OrderStatus.SL_TP_ERROR
                        self._save_persistent_state()
                    self._send_sl_tp_error_notification(order)
                
            else:
                logger.error(f"❌ Не удалось разместить SL/TP для {order.symbol}")
                if order.sl_tp_attempts >= 3:
                    with self.lock:
                        order.status = OrderStatus.SL_TP_ERROR
                        self._save_persistent_state()
                    self._send_sl_tp_error_notification(order)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки исполненного ордера {order.order_id}: {e}")
            if order.sl_tp_attempts >= 3:
                with self.lock:
                    order.status = OrderStatus.SL_TP_ERROR
                    self._save_persistent_state()
                self._send_sl_tp_error_notification(order)
    
    def _check_sl_tp_orders(self, order: WatchedOrder) -> None:
        """Проверяет статус SL/TP ордеров для расчета P&L"""
        if not self.client or order.status != OrderStatus.SL_TP_PLACED:
            return
            
        try:
            sl_filled = False
            tp_filled = False
            sl_cancelled = False
            tp_cancelled = False
            filled_order_info = None
            
            # Проверяем Stop Loss ордер
            if order.sl_order_id:
                try:
                    sl_info = self.client.futures_get_order(
                        symbol=order.symbol,
                        orderId=order.sl_order_id
                    )
                    
                    if sl_info['status'] == 'FILLED':
                        sl_filled = True
                        filled_order_info = sl_info
                        logger.info(f"🛑 Stop Loss исполнен для {order.symbol}")
                    elif sl_info['status'] == 'CANCELED':
                        sl_cancelled = True
                        logger.warning(f"🚫 Stop Loss отменен для {order.symbol}")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка проверки SL ордера {order.sl_order_id}: {e}")
            
            # Проверяем Take Profit ордер (только если SL не исполнен)
            if not sl_filled and order.tp_order_id:
                try:
                    tp_info = self.client.futures_get_order(
                        symbol=order.symbol,
                        orderId=order.tp_order_id
                    )
                    
                    if tp_info['status'] == 'FILLED':
                        tp_filled = True
                        filled_order_info = tp_info
                        logger.info(f"🎯 Take Profit исполнен для {order.symbol}")
                    elif tp_info['status'] == 'CANCELED':
                        tp_cancelled = True
                        logger.warning(f"🚫 Take Profit отменен для {order.symbol}")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка проверки TP ордера {order.tp_order_id}: {e}")
            
            # Если один из ордеров исполнен - рассчитываем P&L
            if (sl_filled or tp_filled) and filled_order_info:
                self._handle_sl_tp_filled(order, filled_order_info, is_stop_loss=sl_filled)
            
            # Если оба ордера отменены - проверяем позицию и удаляем из отслеживания
            elif sl_cancelled and tp_cancelled:
                logger.warning(f"⚠️ Оба ордера (SL/TP) отменены для {order.symbol} - проверяем позицию")
                self._handle_both_orders_cancelled(order)
            
            # Если SL отменен, но есть активный TP - пытаемся восстановить SL
            elif sl_cancelled and not tp_filled and not tp_cancelled:
                logger.warning(f"⚠️ SL отменен для {order.symbol}, но TP активен - требуется восстановление SL")
                self._handle_cancelled_sl_order(order)
            
            # Если TP отменен, но есть активный SL - пытаемся восстановить TP
            elif tp_cancelled and not sl_filled and not sl_cancelled:
                logger.warning(f"⚠️ TP отменен для {order.symbol}, но SL активен - требуется восстановление TP")
                self._handle_cancelled_tp_order(order)
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки SL/TP ордеров для {order.order_id}: {e}")
    
    def _handle_sl_tp_filled(self, order: WatchedOrder, filled_order_info: Dict[str, Any], is_stop_loss: bool) -> None:
        """Обрабатывает исполнение SL или TP ордера с расчетом P&L"""
        try:
            # Рассчитываем прибыль/убыток
            pnl = self._calculate_pnl(order, filled_order_info, is_stop_loss)
            
            # Отменяем оставшийся ордер (SL или TP)
            self._cancel_remaining_order(order, is_stop_loss)
            
            # Отправляем уведомление с P&L
            if is_stop_loss:
                self._send_stop_loss_filled_notification(order, filled_order_info, pnl)
            else:
                self._send_take_profit_filled_notification(order, filled_order_info, pnl)
            
            # Помечаем как завершенный и удаляем из отслеживания
            with self.lock:
                order.status = OrderStatus.COMPLETED
                self._save_persistent_state()
            
            self.remove_order_from_watch(order.order_id)
            logger.info(f"✅ Позиция {order.symbol} полностью закрыта, P&L: {pnl:.2f} USDT")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки исполнения SL/TP: {e}")
    
    def _handle_cancelled_sl_order(self, order: WatchedOrder) -> None:
        """Обрабатывает отмененный SL ордер - пытается восстановить защиту"""
        if not self.client:
            return
            
        try:
            logger.warning(f"🔧 Попытка восстановления SL для {order.symbol}...")
            
            # Проверяем, что позиция еще открыта
            positions = self.client.futures_position_information(symbol=order.symbol)
            position_open = False
            for pos in positions:
                if pos['positionSide'] == order.position_side and float(pos['positionAmt']) != 0:
                    position_open = True
                    break
            
            if not position_open:
                logger.info(f"📍 Позиция {order.symbol} закрыта, удаляем из отслеживания")
                # Отменяем TP ордер если он еще активен
                if order.tp_order_id:
                    try:
                        self.client.futures_cancel_order(
                            symbol=order.symbol,
                            orderId=order.tp_order_id
                        )
                        logger.info(f"🚫 TP ордер {order.tp_order_id} отменен")
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось отменить TP: {e}")
                
                # Удаляем из отслеживания
                self.remove_order_from_watch(order.order_id)
                self._send_position_closed_externally_notification(order)
                return
            
            # Позиция открыта - пытаемся восстановить SL
            if order.sl_tp_attempts < 3:
                logger.info(f"🛡️ Восстанавливаем SL для {order.symbol} (попытка {order.sl_tp_attempts + 1}/3)")
                
                # Увеличиваем счетчик попыток
                with self.lock:
                    order.sl_tp_attempts += 1
                    self._save_persistent_state()
                
                # Пытаемся разместить новый SL
                sl_success, new_sl_order_id = self._place_stop_loss(order)
                
                if sl_success and new_sl_order_id:
                    # Обновляем ID SL ордера
                    with self.lock:
                        order.sl_order_id = new_sl_order_id
                        self._save_persistent_state()
                    
                    logger.info(f"✅ SL восстановлен для {order.symbol}: {new_sl_order_id}")
                    self._send_sl_restored_notification(order, new_sl_order_id)
                else:
                    logger.error(f"❌ Не удалось восстановить SL для {order.symbol}")
                    if order.sl_tp_attempts >= 3:
                        # Максимум попыток исчерпан - помечаем как ошибку
                        with self.lock:
                            order.status = OrderStatus.SL_TP_ERROR
                            self._save_persistent_state()
                        self._send_sl_restore_failed_notification(order)
            else:
                logger.error(f"❌ Максимум попыток восстановления SL для {order.symbol} исчерпан")
                with self.lock:
                    order.status = OrderStatus.SL_TP_ERROR
                    self._save_persistent_state()
                self._send_sl_restore_failed_notification(order)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки отмененного SL: {e}")
    
    def _handle_both_orders_cancelled(self, order: WatchedOrder) -> None:
        """Обрабатывает случай когда оба ордера (SL/TP) отменены"""
        if not self.client:
            return
            
        try:
            logger.warning(f"🔧 Оба ордера отменены для {order.symbol} - проверяем позицию...")
            
            # Проверяем, что позиция еще открыта
            positions = self.client.futures_position_information(symbol=order.symbol)
            position_open = False
            for pos in positions:
                if pos['positionSide'] == order.position_side and float(pos['positionAmt']) != 0:
                    position_open = True
                    break
            
            if not position_open:
                logger.info(f"📍 Позиция {order.symbol} закрыта, удаляем из отслеживания")
                # Удаляем из отслеживания
                self.remove_order_from_watch(order.order_id)
                self._send_position_closed_externally_notification(order)
                return
            
            # Позиция все еще открыта - пытаемся восстановить SL/TP
            if order.sl_tp_attempts < 3:
                logger.info(f"🛡️ Восстанавливаем SL/TP для {order.symbol} (попытка {order.sl_tp_attempts + 1}/3)")
                
                # Увеличиваем счетчик попыток
                with self.lock:
                    order.sl_tp_attempts += 1
                    self._save_persistent_state()
                
                # Пытаемся разместить новые SL/TP
                sl_success, new_sl_order_id = self._place_stop_loss(order)
                tp_success, new_tp_order_id = self._place_take_profit(order)
                
                if sl_success and tp_success and new_sl_order_id and new_tp_order_id:
                    # Обновляем ID ордеров
                    with self.lock:
                        order.sl_order_id = new_sl_order_id
                        order.tp_order_id = new_tp_order_id
                        self._save_persistent_state()
                    
                    logger.info(f"✅ SL/TP восстановлены для {order.symbol}: SL={new_sl_order_id}, TP={new_tp_order_id}")
                    self._send_sl_tp_restored_notification(order, new_sl_order_id, new_tp_order_id)
                else:
                    logger.error(f"❌ Не удалось восстановить SL/TP для {order.symbol}")
                    # Помечаем как ошибку
                    with self.lock:
                        order.status = OrderStatus.SL_TP_ERROR
                        self._save_persistent_state()
                    self._send_sl_tp_error_notification(order)
            else:
                logger.error(f"❌ Максимум попыток восстановления SL/TP для {order.symbol} исчерпан")
                with self.lock:
                    order.status = OrderStatus.SL_TP_ERROR
                    self._save_persistent_state()
                self._send_sl_tp_error_notification(order)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки отмененных SL/TP: {e}")
    
    def _handle_cancelled_tp_order(self, order: WatchedOrder) -> None:
        """Обрабатывает отмененный TP ордер - пытается восстановить"""
        if not self.client:
            return
            
        try:
            logger.warning(f"🔧 Попытка восстановления TP для {order.symbol}...")
            
            # Проверяем, что позиция еще открыта
            positions = self.client.futures_position_information(symbol=order.symbol)
            position_open = False
            for pos in positions:
                if pos['positionSide'] == order.position_side and float(pos['positionAmt']) != 0:
                    position_open = True
                    break
            
            if not position_open:
                logger.info(f"📍 Позиция {order.symbol} закрыта, удаляем из отслеживания")
                # Отменяем SL ордер если он еще активен
                if order.sl_order_id:
                    try:
                        self.client.futures_cancel_order(
                            symbol=order.symbol,
                            orderId=order.sl_order_id
                        )
                        logger.info(f"🚫 SL ордер {order.sl_order_id} отменен")
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось отменить SL: {e}")
                
                # Удаляем из отслеживания
                self.remove_order_from_watch(order.order_id)
                self._send_position_closed_externally_notification(order)
                return
            
            # Позиция открыта - пытаемся восстановить TP
            if order.sl_tp_attempts < 3:
                logger.info(f"🎯 Восстанавливаем TP для {order.symbol} (попытка {order.sl_tp_attempts + 1}/3)")
                
                # Увеличиваем счетчик попыток
                with self.lock:
                    order.sl_tp_attempts += 1
                    self._save_persistent_state()
                
                # Пытаемся разместить новый TP
                tp_success, new_tp_order_id = self._place_take_profit(order)
                
                if tp_success and new_tp_order_id:
                    # Обновляем ID TP ордера
                    with self.lock:
                        order.tp_order_id = new_tp_order_id
                        self._save_persistent_state()
                    
                    logger.info(f"✅ TP восстановлен для {order.symbol}: {new_tp_order_id}")
                    self._send_tp_restored_notification(order, new_tp_order_id)
                else:
                    logger.error(f"❌ Не удалось восстановить TP для {order.symbol}")
                    if order.sl_tp_attempts >= 3:
                        # Максимум попыток исчерпан - помечаем как ошибку
                        with self.lock:
                            order.status = OrderStatus.SL_TP_ERROR
                            self._save_persistent_state()
                        self._send_tp_restore_failed_notification(order)
            else:
                logger.error(f"❌ Максимум попыток восстановления TP для {order.symbol} исчерпан")
                with self.lock:
                    order.status = OrderStatus.SL_TP_ERROR
                    self._save_persistent_state()
                self._send_tp_restore_failed_notification(order)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки отмененного TP: {e}")
    
    def _calculate_pnl(self, order: WatchedOrder, filled_order_info: Dict[str, Any], is_stop_loss: bool) -> float:
        """Рассчитывает прибыль/убыток в USDT с учетом плеча"""
        try:
            entry_price = order.price
            
            # Безопасное получение цены исполнения
            exit_price = None
            if 'avgFillPrice' in filled_order_info and filled_order_info['avgFillPrice']:
                exit_price = float(filled_order_info['avgFillPrice'])
            elif 'price' in filled_order_info and filled_order_info['price']:
                exit_price = float(filled_order_info['price'])
            elif 'stopPrice' in filled_order_info and filled_order_info['stopPrice']:
                exit_price = float(filled_order_info['stopPrice'])
            else:
                # Если цену получить не удалось, используем плановую цену
                exit_price = order.stop_loss if is_stop_loss else order.take_profit
                logger.warning(f"⚠️ Не удалось получить цену исполнения, использую плановую: {exit_price}")
            
            quantity = order.quantity
            
            # Для LONG позиций
            if order.signal_type == 'LONG':
                pnl = (exit_price - entry_price) * quantity
            else:  # SHORT позиций
                pnl = (entry_price - exit_price) * quantity
            
            # Делим на плечо для получения реальной прибыли
            pnl_adjusted = pnl / FUTURES_LEVERAGE
            
            logger.debug(f"📊 PnL расчет: {order.symbol} - сырой PnL: {pnl:.2f}, с плечом ({FUTURES_LEVERAGE}x): {pnl_adjusted:.2f}")
            
            return pnl_adjusted
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета P&L: {e}")
            return 0.0
    
    def _cancel_remaining_order(self, order: WatchedOrder, stop_loss_filled: bool) -> None:
        """Отменяет оставшийся SL или TP ордер"""
        if not self.client:
            return
            
        try:
            if stop_loss_filled and order.tp_order_id:
                # Stop Loss исполнен, отменяем Take Profit
                self.client.futures_cancel_order(
                    symbol=order.symbol,
                    orderId=order.tp_order_id
                )
                logger.info(f"🚫 Take Profit ордер {order.tp_order_id} отменен")
                
            elif not stop_loss_filled and order.sl_order_id:
                # Take Profit исполнен, отменяем Stop Loss
                self.client.futures_cancel_order(
                    symbol=order.symbol,
                    orderId=order.sl_order_id
                )
                logger.info(f"🚫 Stop Loss ордер {order.sl_order_id} отменен")
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка отмены оставшегося ордера: {e}")
    
    def _send_stop_loss_filled_notification(self, order: WatchedOrder, filled_info: Dict[str, Any], pnl: float) -> None:
        """Уведомление о срабатывании Stop Loss"""
        try:
            # Безопасное получение цены исполнения
            fill_price = order.stop_loss  # По умолчанию используем плановую цену
            if 'avgFillPrice' in filled_info and filled_info['avgFillPrice']:
                fill_price = float(filled_info['avgFillPrice'])
            elif 'price' in filled_info and filled_info['price']:
                fill_price = float(filled_info['price'])
            elif 'stopPrice' in filled_info and filled_info['stopPrice']:
                fill_price = float(filled_info['stopPrice'])
                
            pnl_symbol = "💔" if pnl < 0 else "💰"
            
            message = f"""
🛑 <b>СРАБОТАЛ СТОП ОРДЕР</b> 🛑

📊 <b>Символ:</b> {order.symbol}
📈 <b>Направление:</b> {order.signal_type}
💰 <b>Объем:</b> {order.quantity}

💵 <b>Цена входа:</b> {order.price:.6f}
🛑 <b>Цена выхода:</b> {fill_price:.6f}

{pnl_symbol} <b>ПРИБЫЛЬ:</b> {pnl:.2f} USDT

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление о Stop Loss для {order.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления о Stop Loss: {e}")
    
    def _send_take_profit_filled_notification(self, order: WatchedOrder, filled_info: Dict[str, Any], pnl: float) -> None:
        """Уведомление о срабатывании Take Profit"""
        try:
            # Безопасное получение цены исполнения
            fill_price = order.take_profit  # По умолчанию используем плановую цену
            if 'avgFillPrice' in filled_info and filled_info['avgFillPrice']:
                fill_price = float(filled_info['avgFillPrice'])
            elif 'price' in filled_info and filled_info['price']:
                fill_price = float(filled_info['price'])
                
            pnl_symbol = "💰" if pnl > 0 else "💔"
            
            message = f"""
🎯 <b>СРАБОТАЛ ТЕЙК ОРДЕР</b> 🎯

📊 <b>Символ:</b> {order.symbol}
📈 <b>Направление:</b> {order.signal_type}
💰 <b>Объем:</b> {order.quantity}

💵 <b>Цена входа:</b> {order.price:.6f}
🎯 <b>Цена выхода:</b> {fill_price:.6f}

{pnl_symbol} <b>ПРИБЫЛЬ:</b> {pnl:.2f} USDT

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление о Take Profit для {order.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления о Take Profit: {e}")
    
    def _place_stop_loss(self, order: WatchedOrder) -> Tuple[bool, Optional[str]]:
        """Размещает Stop Loss ордер"""
        if not self.client:
            return False, None
            
        try:
            sl_side = 'SELL' if order.signal_type == 'LONG' else 'BUY'
            sl_price = round_price_for_symbol(order.symbol, order.stop_loss)
            
            logger.info(f"🛡️ Размещаем STOP_MARKET {sl_side} для {order.symbol}: {order.quantity} at {sl_price}")
            
            stop_order = self.client.futures_create_order(
                symbol=order.symbol,
                side=sl_side,
                type='STOP_MARKET',
                quantity=order.quantity,
                stopPrice=str(sl_price),
                timeInForce='GTC',
                positionSide=order.position_side
            )
            
            logger.info(f"✅ Stop Loss размещен: {stop_order['orderId']}")
            return True, str(stop_order['orderId'])
            
        except Exception as e:
            logger.error(f"❌ Ошибка размещения Stop Loss: {e}")
            return False, None
    
    def _place_take_profit(self, order: WatchedOrder) -> Tuple[bool, Optional[str]]:
        """Размещает Take Profit ордер"""
        if not self.client:
            return False, None
            
        try:
            tp_side = 'SELL' if order.signal_type == 'LONG' else 'BUY'
            tp_price = round_price_for_symbol(order.symbol, order.take_profit)
            
            logger.info(f"🎯 Размещаем LIMIT {tp_side} для {order.symbol}: {order.quantity} at {tp_price}")
            
            tp_order = self.client.futures_create_order(
                symbol=order.symbol,
                side=tp_side,
                type='LIMIT',
                quantity=order.quantity,
                price=str(tp_price),
                timeInForce='GTC',
                positionSide=order.position_side
            )
            
            logger.info(f"✅ Take Profit размещен: {tp_order['orderId']}")
            return True, str(tp_order['orderId'])
            
        except Exception as e:
            logger.error(f"❌ Ошибка размещения Take Profit: {e}")
            return False, None
    
    def _send_watchdog_notification(self, message: str) -> None:
        """Отправляет уведомление от watchdog"""
        try:
            full_message = f"""
🐕 <b>ORDERS WATCHDOG</b> 🐕

{message}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_bot.send_message(full_message)
        except Exception as e:
            logger.error(f"❌ Ошибка отправки watchdog уведомления: {e}")
    
    def _send_order_filled_notification(self, order: WatchedOrder, order_info: Dict[str, Any]) -> None:
        """Уведомление об исполнении ордера"""
        try:
            filled_qty = float(order_info.get('executedQty', 0))
            avg_price = float(order_info.get('avgPrice', order.price))
            
            message = f"""
🎉 <b>ОРДЕР ИСПОЛНЕН!</b> 🎉

📊 <b>Символ:</b> {order.symbol}
📈 <b>Направление:</b> {order.signal_type}
💰 <b>Исполнено:</b> {filled_qty}
💵 <b>Средняя цена:</b> {avg_price:.6f}
⚡ <b>Плечо:</b> {FUTURES_LEVERAGE}x

🔄 <b>Размещаю SL/TP...</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_bot.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления об исполнении: {e}")
    
    def _send_order_cancelled_notification(self, order: WatchedOrder, status: str) -> None:
        """Уведомление об отмене ордера"""
        try:
            message = f"""
🚫 <b>ОРДЕР ОТМЕНЕН</b> 🚫

📊 <b>Символ:</b> {order.symbol}
🆔 <b>Ордер:</b> {order.order_id}
📝 <b>Статус:</b> {status}
⏳ <b>Время жизни:</b> {(datetime.now() - order.created_at).total_seconds():.0f}s

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_bot.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления об отмене: {e}")
    
    def _send_position_opened_notification(self, order: WatchedOrder, sl_order_id: str, tp_order_id: str) -> None:
        """Уведомление о полном открытии позиции"""
        try:
            # Корректный тип маржи для отображения
            display_margin_type = 'CROSSED' if FUTURES_MARGIN_TYPE == 'CROSS' else 'ISOLATED'
            
            message = f"""
🚀 <b>ПОЗИЦИЯ ОТКРЫТА!</b> 🚀

📊 <b>Символ:</b> {order.symbol}
📈 <b>Направление:</b> {order.signal_type}
💰 <b>Объем:</b> {order.quantity}
💵 <b>Цена входа:</b> {order.price:.6f}
⚡ <b>Плечо:</b> {FUTURES_LEVERAGE}x
🔧 <b>Режим маржи:</b> {display_margin_type}

🎯 <b>Защитные ордера:</b>
• 🛡️ Stop Loss: {order.stop_loss:.6f} (#{sl_order_id[-6:]})
• 🎯 Take Profit: {order.take_profit:.6f} (#{tp_order_id[-6:]})

✅ <b>Позиция полностью настроена!</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_bot.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о позиции: {e}")
    
    def _send_sl_tp_error_notification(self, order: WatchedOrder) -> None:
        """Уведомление об ошибке размещения SL/TP"""
        try:
            message = f"""
🚨 <b>ОШИБКА SL/TP!</b> 🚨

📊 <b>Символ:</b> {order.symbol}
🆔 <b>Ордер:</b> {order.order_id}

❌ <b>Не удалось разместить защитные ордера!</b>
⚠️ <b>Требуется ручное вмешательство</b>

📈 <b>Позиция открыта по:</b> {order.price:.6f}
🎯 <b>Планируемый SL:</b> {order.stop_loss:.6f}
🎯 <b>Планируемый TP:</b> {order.take_profit:.6f}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_bot.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления об ошибке SL/TP: {e}")
    
    def _send_sl_restored_notification(self, order: WatchedOrder, new_sl_order_id: str) -> None:
        """Уведомление о восстановлении SL ордера"""
        try:
            message = f"""
🔧 <b>SL ОРДЕР ВОССТАНОВЛЕН</b> 🔧

📊 <b>Символ:</b> {order.symbol}
📈 <b>Направление:</b> {order.signal_type}
💰 <b>Объем:</b> {order.quantity}

🛡️ <b>Новый SL:</b> {order.stop_loss:.6f} (#{new_sl_order_id[-6:]})
🎯 <b>TP активен:</b> {order.take_profit:.6f} (#{order.tp_order_id[-6:] if order.tp_order_id else 'N/A'})

✅ <b>Защита восстановлена!</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление о восстановлении SL для {order.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о восстановлении SL: {e}")
    
    def _send_sl_restore_failed_notification(self, order: WatchedOrder) -> None:
        """Уведомление о неудачном восстановлении SL"""
        try:
            message = f"""
🚨 <b>НЕ УДАЛОСЬ ВОССТАНОВИТЬ SL!</b> 🚨

📊 <b>Символ:</b> {order.symbol}
📈 <b>Направление:</b> {order.signal_type}
💰 <b>Объем:</b> {order.quantity}

❌ <b>SL ордер отменился и не восстанавливается</b>
🎯 <b>TP все еще активен:</b> {order.take_profit:.6f}

⚠️ <b>ПОЗИЦИЯ БЕЗ СТОП-ЛОССА!</b>
🛠️ <b>Требуется ручная установка SL</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_bot.send_message(message)
            logger.warning(f"📱 Уведомление о проблеме с SL для {order.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о проблеме SL: {e}")
    
    def _send_sl_tp_restored_notification(self, order: WatchedOrder, sl_order_id: str, tp_order_id: str) -> None:
        """Уведомление о восстановлении SL/TP ордеров"""
        try:
            message = f"""
🔧 <b>SL/TP ОРДЕРА ВОССТАНОВЛЕНЫ</b> 🔧

📊 <b>Символ:</b> {order.symbol}
📈 <b>Направление:</b> {order.signal_type}
💰 <b>Объем:</b> {order.quantity}

🛡️ <b>Новый SL:</b> {order.stop_loss:.6f} (#{sl_order_id[-6:]})
🎯 <b>Новый TP:</b> {order.take_profit:.6f} (#{tp_order_id[-6:]})

✅ <b>Защита полностью восстановлена!</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление о восстановлении SL/TP для {order.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о восстановлении SL/TP: {e}")
    
    def _send_tp_restored_notification(self, order: WatchedOrder, new_tp_order_id: str) -> None:
        """Уведомление о восстановлении TP ордера"""
        try:
            message = f"""
🔧 <b>TP ОРДЕР ВОССТАНОВЛЕН</b> 🔧

📊 <b>Символ:</b> {order.symbol}
📈 <b>Направление:</b> {order.signal_type}
💰 <b>Объем:</b> {order.quantity}

🎯 <b>Новый TP:</b> {order.take_profit:.6f} (#{new_tp_order_id[-6:]})
🛡️ <b>SL активен:</b> {order.stop_loss:.6f} (#{order.sl_order_id[-6:] if order.sl_order_id else 'N/A'})

✅ <b>TP восстановлен!</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление о восстановлении TP для {order.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о восстановлении TP: {e}")
    
    def _send_tp_restore_failed_notification(self, order: WatchedOrder) -> None:
        """Уведомление о неудачном восстановлении TP"""
        try:
            message = f"""
🚨 <b>НЕ УДАЛОСЬ ВОССТАНОВИТЬ TP!</b> 🚨

📊 <b>Символ:</b> {order.symbol}
📈 <b>Направление:</b> {order.signal_type}
💰 <b>Объем:</b> {order.quantity}

❌ <b>TP ордер отменился и не восстанавливается</b>
🛡️ <b>SL все еще активен:</b> {order.stop_loss:.6f}

⚠️ <b>ПОЗИЦИЯ БЕЗ ТЕЙК-ПРОФИТА!</b>
🛠️ <b>Требуется ручная установка TP</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_bot.send_message(message)
            logger.warning(f"📱 Уведомление о проблеме с TP для {order.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о проблеме TP: {e}")
    
    def check_positions_status(self) -> None:
        """Проверяет открытые позиции и удаляет связанные ордера если позиция закрыта"""
        if not self.client:
            return
            
        try:
            # Получаем все открытые позиции
            positions = self.client.futures_position_information()
            
            # Создаем множество символов с открытыми позициями
            open_positions = set()
            for pos in positions:
                position_amt = float(pos['positionAmt'])
                if position_amt != 0:  # Позиция открыта
                    open_positions.add(pos['symbol'])
            
            # Проверяем отслеживаемые ордера
            with self.lock:
                orders_to_remove = []
                for order_id, order in self.watched_orders.items():
                    # Если у ордера есть SL/TP, но позиции нет - позиция была закрыта извне
                    if (order.status == OrderStatus.SL_TP_PLACED and 
                        order.symbol not in open_positions):
                        
                        logger.info(f"🔍 Позиция {order.symbol} закрыта извне, удаляем связанные ордера")
                        
                        # Отменяем активные SL/TP ордера
                        self._cancel_external_sl_tp_orders(order)
                        
                        # Отправляем уведомление
                        self._send_position_closed_externally_notification(order)
                        
                        # Помечаем для удаления
                        orders_to_remove.append(order_id)
                
                # Удаляем обработанные ордера
                for order_id in orders_to_remove:
                    del self.watched_orders[order_id]
                
                if orders_to_remove:
                    self._save_persistent_state()
                    logger.info(f"🧹 Удалено {len(orders_to_remove)} ордеров с закрытыми позициями")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка проверки позиций: {e}")
    
    def _cancel_external_sl_tp_orders(self, order: WatchedOrder) -> None:
        """Отменяет SL/TP ордера для внешне закрытой позиции"""
        if not self.client:
            return
            
        try:
            # Отменяем Stop Loss
            if order.sl_order_id:
                try:
                    self.client.futures_cancel_order(
                        symbol=order.symbol,
                        orderId=order.sl_order_id
                    )
                    logger.info(f"🚫 Отменен SL ордер {order.sl_order_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось отменить SL {order.sl_order_id}: {e}")
            
            # Отменяем Take Profit
            if order.tp_order_id:
                try:
                    self.client.futures_cancel_order(
                        symbol=order.symbol,
                        orderId=order.tp_order_id
                    )
                    logger.info(f"🚫 Отменен TP ордер {order.tp_order_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось отменить TP {order.tp_order_id}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка отмены внешних SL/TP: {e}")
    
    def _send_position_closed_externally_notification(self, order: WatchedOrder) -> None:
        """Уведомление о внешнем закрытии позиции"""
        try:
            message = f"""
🔄 <b>ПОЗИЦИЯ ЗАКРЫТА ИЗВНЕ</b> 🔄

📊 <b>Символ:</b> {order.symbol}
📈 <b>Направление:</b> {order.signal_type}
💰 <b>Объем:</b> {order.quantity}

🚫 <b>Связанные ордера отменены:</b>
• SL: {order.sl_order_id or 'N/A'}
• TP: {order.tp_order_id or 'N/A'}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление о внешнем закрытии позиции {order.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о внешнем закрытии: {e}")
    
    def get_status(self) -> Dict[str, Union[int, List[Dict[str, Any]], bool]]:
        """Возвращает статус watchdog"""
        with self.lock:
            return {
                'watched_orders_count': len(self.watched_orders),
                'orders': [order.to_dict() for order in self.watched_orders.values()],
                'is_running': not self.stop_event.is_set(),
                'client_connected': self.client is not None
            }
    
    def check_exchange_sync(self) -> Dict[str, Any]:
        """
        Проверяет синхронизацию с биржей:
        1. Сверяет открытые ордера на бирже с локальным состоянием
        2. Проверяет открытые позиции
        3. Выявляет расхождения
        """
        if not self.client:
            return {"error": "Binance client not available"}
        
        sync_report = {
            "timestamp": datetime.now().isoformat(),
            "exchange_orders": {},
            "exchange_positions": {},
            "local_state": {},
            "discrepancies": [],
            "recommendations": []
        }
        
        try:
            logger.info("🔍 Начинаем проверку синхронизации с биржей...")
            
            # 1. Получаем все открытые ордера с биржи
            exchange_orders = self.client.futures_get_open_orders()
            sync_report["exchange_orders"] = {
                str(order['orderId']): {
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'type': order['type'],
                    'status': order['status'],
                    'quantity': float(order['origQty']),
                    'price': float(order['price']) if order['price'] else None,
                    'stopPrice': float(order['stopPrice']) if order['stopPrice'] else None
                }
                for order in exchange_orders
            }
            
            # 2. Получаем все открытые позиции с биржи
            exchange_positions = self.client.futures_position_information()
            sync_report["exchange_positions"] = {}
            for pos in exchange_positions:
                if float(pos['positionAmt']) != 0:  # Только открытые позиции
                    sync_report["exchange_positions"][pos['symbol']] = {
                        'positionAmt': float(pos['positionAmt']),
                        'entryPrice': float(pos['entryPrice']) if pos['entryPrice'] else 0.0,
                        'unrealizedPnl': float(pos.get('unrealizedPnl', 0) or 0),
                        'positionSide': pos['positionSide']
                    }
            
            # 3. Анализируем локальное состояние
            with self.lock:
                sync_report["local_state"] = {
                    "total_orders": len(self.watched_orders),
                    "by_status": {},
                    "orders_detail": {}
                }
                
                # Группируем по статусам
                status_count = {}
                for order in self.watched_orders.values():
                    status = order.status.value
                    status_count[status] = status_count.get(status, 0) + 1
                    
                    sync_report["local_state"]["orders_detail"][order.order_id] = {
                        'symbol': order.symbol,
                        'status': status,
                        'sl_order_id': order.sl_order_id,
                        'tp_order_id': order.tp_order_id,
                        'sl_tp_attempts': order.sl_tp_attempts
                    }
                
                sync_report["local_state"]["by_status"] = status_count
            
            # 4. Выявляем расхождения
            self._analyze_discrepancies(sync_report)
            
            logger.info(f"✅ Проверка синхронизации завершена. Найдено {len(sync_report['discrepancies'])} расхождений")
            return sync_report
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки синхронизации: {e}")
            sync_report["error"] = str(e)
            return sync_report
    
    def _analyze_discrepancies(self, sync_report: Dict[str, Any]) -> None:
        """Анализирует расхождения между локальным состоянием и биржей"""
        exchange_orders = sync_report["exchange_orders"]
        exchange_positions = sync_report["exchange_positions"]
        local_orders = sync_report["local_state"]["orders_detail"]
        
        # Проверяем SL/TP ордера которые должны быть на бирже
        for order_id, local_order in local_orders.items():
            if local_order['status'] == 'SL_TP_PLACED':
                symbol = local_order['symbol']
                sl_id = local_order['sl_order_id']
                tp_id = local_order['tp_order_id']
                
                # Проверяем наличие SL ордера
                if sl_id and sl_id not in exchange_orders:
                    sync_report["discrepancies"].append({
                        'type': 'MISSING_SL_ORDER',
                        'symbol': symbol,
                        'local_order_id': order_id,
                        'missing_sl_id': sl_id,
                        'message': f'SL ордер {sl_id} не найден на бирже для {symbol}'
                    })
                    sync_report["recommendations"].append(f'Проверить статус SL ордера {sl_id} для {symbol}')
                
                # Проверяем наличие TP ордера
                if tp_id and tp_id not in exchange_orders:
                    sync_report["discrepancies"].append({
                        'type': 'MISSING_TP_ORDER',
                        'symbol': symbol,
                        'local_order_id': order_id,
                        'missing_tp_id': tp_id,
                        'message': f'TP ордер {tp_id} не найден на бирже для {symbol}'
                    })
                    sync_report["recommendations"].append(f'Проверить статус TP ордера {tp_id} для {symbol}')
                
                # Проверяем наличие позиции
                if symbol not in exchange_positions:
                    sync_report["discrepancies"].append({
                        'type': 'MISSING_POSITION',
                        'symbol': symbol,
                        'local_order_id': order_id,
                        'message': f'Позиция {symbol} не найдена на бирже, но есть активные SL/TP'
                    })
                    sync_report["recommendations"].append(f'Удалить отслеживание {symbol} - позиция закрыта')
        
        # Проверяем PENDING ордера
        for order_id, local_order in local_orders.items():
            if local_order['status'] == 'PENDING':
                if order_id not in exchange_orders:
                    sync_report["discrepancies"].append({
                        'type': 'MISSING_PENDING_ORDER',
                        'symbol': local_order['symbol'],
                        'local_order_id': order_id,
                        'message': f'PENDING ордер {order_id} не найден на бирже'
                    })
                    sync_report["recommendations"].append(f'Проверить статус ордера {order_id} - возможно исполнен или отменен')
        
        # Проверяем "лишние" ордера на бирже
        all_local_order_ids = set(local_orders.keys())
        for sl_tp_order in local_orders.values():
            if sl_tp_order['sl_order_id']:
                all_local_order_ids.add(sl_tp_order['sl_order_id'])
            if sl_tp_order['tp_order_id']:
                all_local_order_ids.add(sl_tp_order['tp_order_id'])
        
        orphaned_orders = []
        for exchange_order_id in exchange_orders.keys():
            if exchange_order_id not in all_local_order_ids:
                order_info = exchange_orders[exchange_order_id]
                orphaned_orders.append({
                    'order_id': exchange_order_id,
                    'symbol': order_info['symbol'],
                    'type': order_info['type'],
                    'side': order_info['side']
                })
        
        if orphaned_orders:
            sync_report["discrepancies"].append({
                'type': 'ORPHANED_ORDERS',
                'count': len(orphaned_orders),
                'orders': orphaned_orders,
                'message': f'Найдено {len(orphaned_orders)} ордеров на бирже без отслеживания'
            })
            sync_report["recommendations"].append(f'Проанализировать {len(orphaned_orders)} "сиротских" ордеров на бирже')
    
    def _send_sync_alert(self, critical_issues: List[Dict[str, Any]]) -> None:
        """Отправляет критический алерт о проблемах синхронизации"""
        try:
            issues_text = "\n".join([f"• {issue['message']}" for issue in critical_issues])
            
            message = f"""
🚨 <b>КРИТИЧЕСКИЕ ПРОБЛЕМЫ СИНХРОНИЗАЦИИ</b> 🚨

Найдено {len(critical_issues)} серьезных расхождений:

{issues_text}

⚠️ <b>Требуется проверка состояния системы!</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_bot.send_message(message)
            logger.warning(f"📱 Отправлен алерт о критических проблемах синхронизации")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки алерта синхронизации: {e}")
    
    def print_sync_report(self, sync_report: Dict[str, Any]) -> None:
        """Выводит отчет о синхронизации в читаемом виде"""
        if "error" in sync_report:
            logger.error(f"❌ Ошибка генерации отчета: {sync_report['error']}")
            return
        
        logger.info("=" * 60)
        logger.info("📊 ОТЧЕТ О СИНХРОНИЗАЦИИ С БИРЖЕЙ")
        logger.info("=" * 60)
        
        # Общая статистика
        logger.info(f"🕐 Время проверки: {sync_report['timestamp']}")
        logger.info(f"📋 Ордеров на бирже: {len(sync_report['exchange_orders'])}")
        logger.info(f"📍 Открытых позиций: {len(sync_report['exchange_positions'])}")
        logger.info(f"👁️ Отслеживаемых ордеров: {sync_report['local_state']['total_orders']}")
        
        # Статистика по статусам
        logger.info("\n📊 Распределение по статусам:")
        for status, count in sync_report['local_state']['by_status'].items():
            logger.info(f"  • {status}: {count}")
        
        # Расхождения
        discrepancies = sync_report['discrepancies']
        if discrepancies:
            logger.warning(f"\n⚠️ НАЙДЕНО {len(discrepancies)} РАСХОЖДЕНИЙ:")
            for i, disc in enumerate(discrepancies, 1):
                logger.warning(f"  {i}. [{disc['type']}] {disc['message']}")
        else:
            logger.info("\n✅ Расхождений не найдено - все синхронизировано!")
        
        # Рекомендации
        recommendations = sync_report['recommendations']
        if recommendations:
            logger.info(f"\n🔧 РЕКОМЕНДАЦИИ ({len(recommendations)}):")
            for i, rec in enumerate(recommendations, 1):
                logger.info(f"  {i}. {rec}")
        
        logger.info("=" * 60)
    
    def cleanup_filled_orders(self) -> None:
        """
        Очищает ордера которые были исполнены, но остались в отслеживании
        Проверяет историю ордеров на бирже
        """
        if not self.client:
            logger.error("❌ Нет подключения к Binance")
            return
        
        with self.lock:
            orders_to_cleanup = list(self.watched_orders.values())
        
        if not orders_to_cleanup:
            logger.info("📋 Нет ордеров для очистки")
            return
        
        logger.info(f"🧹 Проверяем {len(orders_to_cleanup)} ордеров на необходимость очистки...")
        
        orders_to_remove = []
        
        for order in orders_to_cleanup:
            try:
                # Проверяем основной ордер в истории
                order_history = self.client.futures_get_order(
                    symbol=order.symbol,
                    orderId=order.order_id
                )
                
                order_status = order_history['status']
                logger.info(f"📋 {order.symbol} ордер {order.order_id}: {order_status}")
                
                # Если ордер был исполнен, но мы его не обработали
                if order_status == 'FILLED':
                    if order.status in [OrderStatus.PENDING, OrderStatus.FILLED, OrderStatus.SL_TP_PLACED, OrderStatus.SL_TP_ERROR]:
                        
                        # Проверяем есть ли еще позиция с этим точным количеством
                        positions = self.client.futures_position_information(symbol=order.symbol)
                        exact_position_exists = False
                        
                        for pos in positions:
                            if (pos['positionSide'] == order.position_side and 
                                abs(float(pos['positionAmt']) - order.quantity) < 0.001):  # Учитываем погрешность округления
                                exact_position_exists = True
                                break
                        
                        if not exact_position_exists:
                            logger.warning(f"🧹 Ордер {order.symbol} #{order.order_id} исполнен, но позиции с количеством {order.quantity} нет")
                            
                            # Если есть SL/TP ордера - проверяем их статус тоже
                            sl_tp_processed = False
                            if order.sl_order_id or order.tp_order_id:
                                logger.info(f"🔍 Проверяем SL/TP ордера для {order.symbol}...")
                                
                                # Проверяем SL
                                if order.sl_order_id:
                                    try:
                                        sl_history = self.client.futures_get_order(
                                            symbol=order.symbol,
                                            orderId=order.sl_order_id
                                        )
                                        sl_status = sl_history['status']
                                        logger.info(f"🛡️ SL статус: {sl_status}")
                                        
                                        if sl_status == 'FILLED':
                                            logger.info(f"✅ SL исполнен - позиция закрыта через SL")
                                            sl_tp_processed = True
                                            # Рассчитываем P&L и отправляем уведомление
                                            pnl = self._calculate_pnl(order, sl_history, is_stop_loss=True)
                                            self._send_stop_loss_filled_notification(order, sl_history, pnl)
                                            
                                    except Exception as e:
                                        logger.error(f"❌ Ошибка проверки SL: {e}")
                                
                                # Проверяем TP если SL не исполнен
                                if not sl_tp_processed and order.tp_order_id:
                                    try:
                                        tp_history = self.client.futures_get_order(
                                            symbol=order.symbol,
                                            orderId=order.tp_order_id
                                        )
                                        tp_status = tp_history['status']
                                        logger.info(f"🎯 TP статус: {tp_status}")
                                        
                                        if tp_status == 'FILLED':
                                            logger.info(f"✅ TP исполнен - позиция закрыта через TP")
                                            sl_tp_processed = True
                                            # Рассчитываем P&L и отправляем уведомление
                                            pnl = self._calculate_pnl(order, tp_history, is_stop_loss=False)
                                            self._send_take_profit_filled_notification(order, tp_history, pnl)
                                            
                                    except Exception as e:
                                        logger.error(f"❌ Ошибка проверки TP: {e}")
                            
                            # Если SL/TP не обработаны, отправляем уведомление о внешнем закрытии
                            if not sl_tp_processed:
                                logger.info(f"📤 Позиция {order.symbol} закрыта извне")
                                self._send_position_closed_externally_notification(order)
                            
                            orders_to_remove.append(order.order_id)
                            
                elif order_status in ['CANCELED', 'REJECTED', 'EXPIRED']:
                    logger.info(f"🚫 Ордер {order.symbol} #{order.order_id} отменен/отклонен: {order_status}")
                    orders_to_remove.append(order.order_id)
                    
            except Exception as e:
                logger.error(f"❌ Ошибка проверки ордера {order.order_id}: {e}")
        
        # Удаляем найденные ордера
        if orders_to_remove:
            with self.lock:
                for order_id in orders_to_remove:
                    if order_id in self.watched_orders:
                        removed_order = self.watched_orders.pop(order_id)
                        logger.info(f"🗑️ Удален из отслеживания: {removed_order.symbol} ордер {order_id}")
                
                self._save_persistent_state()
            
            logger.info(f"✅ Очищено {len(orders_to_remove)} завершенных ордеров")
            
            # Отправляем уведомление об очистке
            if len(orders_to_remove) > 0:
                self._send_cleanup_notification(len(orders_to_remove))
        else:
            logger.info("✅ Все ордера актуальны, очистка не требуется")
    
    def _send_cleanup_notification(self, count: int) -> None:
        """Уведомление об очистке завершенных ордеров"""
        try:
            message = f"""
🧹 <b>ОЧИСТКА ЗАВЕРШЕНА</b> 🧹

Удалено {count} завершенных ордеров из отслеживания

✅ Состояние синхронизировано с биржей

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление об очистке {count} ордеров")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления об очистке: {e}")
    
    def fix_desync_order(self, order_id: str) -> bool:
        """
        Исправляет конкретный десинхронизированный ордер
        
        Args:
            order_id: ID ордера для исправления
            
        Returns:
            bool: True если исправлено успешно
        """
        if not self.client:
            logger.error("❌ Нет подключения к Binance")
            return False
        
        with self.lock:
            order = self.watched_orders.get(order_id)
            if not order:
                logger.error(f"❌ Ордер {order_id} не найден в отслеживании")
                return False
        
        try:
            logger.info(f"🔧 Исправляем десинхронизацию для {order.symbol} ордер {order_id}")
            
            # Проверяем статус SL/TP ордеров
            if order.status == OrderStatus.SL_TP_PLACED:
                sl_cancelled = False
                tp_cancelled = False
                sl_filled = False
                tp_filled = False
                sl_info = None
                tp_info = None
                
                # Проверяем SL
                if order.sl_order_id:
                    try:
                        sl_info = self.client.futures_get_order(
                            symbol=order.symbol,
                            orderId=order.sl_order_id
                        )
                        sl_status = sl_info['status']
                        logger.info(f"🛡️ SL статус: {sl_status}")
                        
                        if sl_status == 'CANCELED':
                            sl_cancelled = True
                        elif sl_status == 'FILLED':
                            sl_filled = True
                            
                    except Exception as e:
                        logger.error(f"❌ Ошибка проверки SL: {e}")
                
                # Проверяем TP
                if order.tp_order_id:
                    try:
                        tp_info = self.client.futures_get_order(
                            symbol=order.symbol,
                            orderId=order.tp_order_id
                        )
                        tp_status = tp_info['status']
                        logger.info(f"🎯 TP статус: {tp_status}")
                        
                        if tp_status == 'CANCELED':
                            tp_cancelled = True
                        elif tp_status == 'FILLED':
                            tp_filled = True
                            
                    except Exception as e:
                        logger.error(f"❌ Ошибка проверки TP: {e}")
                
                # Проверяем позицию
                positions = self.client.futures_position_information(symbol=order.symbol)
                position_open = False
                for pos in positions:
                    if pos['positionSide'] == order.position_side and float(pos['positionAmt']) != 0:
                        position_open = True
                        break
                
                logger.info(f"📍 Позиция {order.symbol} {'открыта' if position_open else 'закрыта'}")
                
                # Принимаем решение об исправлении
                if not position_open:
                    # Позиция закрыта - удаляем из отслеживания
                    logger.info(f"✅ Позиция закрыта, удаляем ордер {order_id} из отслеживания")
                    self.remove_order_from_watch(order_id)
                    self._send_position_closed_externally_notification(order)
                    return True
                    
                elif sl_filled or tp_filled:
                    # Один из ордеров исполнен - обрабатываем
                    if sl_filled and sl_info:
                        logger.info(f"✅ SL исполнен, обрабатываем закрытие позиции")
                        self._handle_sl_tp_filled(order, sl_info, is_stop_loss=True)
                    elif tp_filled and tp_info:
                        logger.info(f"✅ TP исполнен, обрабатываем закрытие позиции")
                        self._handle_sl_tp_filled(order, tp_info, is_stop_loss=False)
                    return True
                    
                elif sl_cancelled and not tp_cancelled:
                    # SL отменен, но TP активен - восстанавливаем SL
                    logger.info(f"🔧 SL отменен, восстанавливаем защиту")
                    self._handle_cancelled_sl_order(order)
                    return True
                    
                elif tp_cancelled and not sl_cancelled:
                    # TP отменен, но SL активен - восстанавливаем TP
                    logger.info(f"🔧 TP отменен, восстанавливаем цель прибыли")
                    tp_success, new_tp_id = self._place_take_profit(order)
                    if tp_success and new_tp_id:
                        with self.lock:
                            order.tp_order_id = new_tp_id
                            self._save_persistent_state()
                        logger.info(f"✅ TP восстановлен: {new_tp_id}")
                        return True
                    else:
                        logger.error(f"❌ Не удалось восстановить TP")
                        return False
                        
                elif sl_cancelled and tp_cancelled:
                    # Оба ордера отменены - позиция без защиты
                    logger.warning(f"⚠️ Оба ордера отменены, позиция без защиты!")
                    with self.lock:
                        order.status = OrderStatus.SL_TP_ERROR
                        self._save_persistent_state()
                    
                    # Пытаемся восстановить защиту
                    sl_success, new_sl_id = self._place_stop_loss(order)
                    tp_success, new_tp_id = self._place_take_profit(order)
                    
                    if sl_success and tp_success and new_sl_id and new_tp_id:
                        with self.lock:
                            order.sl_order_id = new_sl_id
                            order.tp_order_id = new_tp_id
                            order.status = OrderStatus.SL_TP_PLACED
                            self._save_persistent_state()
                        logger.info(f"✅ Защита полностью восстановлена: SL={new_sl_id}, TP={new_tp_id}")
                        return True
                    else:
                        logger.error(f"❌ Не удалось восстановить полную защиту")
                        return False
                else:
                    logger.info(f"✅ Ордер синхронизирован, никаких действий не требуется")
                    return True
                    
            else:
                logger.info(f"📋 Ордер в статусе {order.status.value}, проверяем обычным способом")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка исправления десинхронизации: {e}")
            return False
    
    def run(self) -> None:
        """Главный цикл мониторинга"""
        logger.info("🐕 Orders Watchdog запущен!")
        
        # Отправляем уведомление о запуске
        self._send_watchdog_notification("🚀 Orders Watchdog запущен и готов к мониторингу")
        
        try:
            cycle_counter = 0  # Счетчик циклов для периодической проверки позиций
            sync_counter = 0   # Счетчик для проверки синхронизации (каждые 10 минут)
            while not self.stop_event.is_set():
                try:
                    # Проверяем входящие запросы
                    self._process_incoming_requests()
                    
                    # Проверяем статус ордеров
                    self.check_orders_status()
                    
                    # Проверяем позиции каждые 6 циклов (30 секунд)
                    cycle_counter += 1
                    if cycle_counter >= 6:
                        self.check_positions_status()
                        cycle_counter = 0
                    
                    # Проверяем синхронизацию каждые 120 циклов (10 минут)
                    sync_counter += 1
                    if sync_counter >= 120:
                        logger.info("🔍 Запускаем периодическую проверку синхронизации...")
                        sync_report = self.check_exchange_sync()
                        if sync_report.get('discrepancies'):
                            logger.warning(f"⚠️ Найдено {len(sync_report['discrepancies'])} расхождений с биржей")
                            # Отправляем уведомление только если есть серьезные проблемы
                            critical_issues = [d for d in sync_report['discrepancies'] 
                                             if d['type'] in ['MISSING_POSITION', 'MISSING_PENDING_ORDER']]
                            if critical_issues:
                                self._send_sync_alert(critical_issues)
                        sync_counter = 0
                    
                    time.sleep(self.check_interval)
                    
                except KeyboardInterrupt:
                    logger.info("⌨️ Получен сигнал остановки")
                    break
                except Exception as e:
                    logger.error(f"❌ Ошибка в главном цикле: {e}")
                    time.sleep(self.check_interval)
        
        except Exception as e:
            logger.error(f"💥 Критическая ошибка в Orders Watchdog: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self) -> None:
        """Корректное завершение работы"""
        logger.info("🛑 Завершение работы Orders Watchdog...")
        self.stop_event.set()
        
        # Сохраняем состояние
        self._save_persistent_state()
        
        # Отправляем уведомление о завершении
        try:
            self._send_watchdog_notification("🛑 Orders Watchdog остановлен")
        except:
            pass
        
        logger.info("✅ Orders Watchdog завершен")
        sys.exit(0)


# API для интеграции с order_executor
class WatchdogAPI:
    """API для взаимодействия с Orders Watchdog"""
    
    def __init__(self):
        self.watchdog_file = Path('orders_watchdog_requests.json')
    
    def add_order_for_monitoring(self, order_data: Dict[str, Any]) -> bool:
        """
        Добавляет ордер в очередь для мониторинга
        Используется order_executor для передачи ордеров в watchdog
        """
        try:
            # Читаем существующие запросы
            requests_data = []
            if self.watchdog_file.exists():
                with open(self.watchdog_file, 'r', encoding='utf-8') as f:
                    requests_data = json.load(f)
            
            # Добавляем новый запрос
            request = {
                'action': 'add_order',
                'data': order_data,
                'timestamp': datetime.now().isoformat()
            }
            requests_data.append(request)
            
            # Сохраняем
            with open(self.watchdog_file, 'w', encoding='utf-8') as f:
                json.dump(requests_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📝 Добавлен запрос на мониторинг ордера {order_data.get('symbol', 'UNKNOWN')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления запроса на мониторинг: {e}")
            return False


# Глобальный экземпляр API для использования в order_executor
watchdog_api = WatchdogAPI()


def main():
    """Точка входа в приложение"""
    try:
        watchdog = OrdersWatchdog()
        
        if not watchdog.client:
            logger.error("❌ Не удалось инициализировать Binance клиент")
            sys.exit(1)
        
        watchdog.run()
        
    except KeyboardInterrupt:
        logger.info("👋 Получен сигнал завершения от пользователя")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
