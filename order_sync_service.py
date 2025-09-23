#!/usr/bin/env python3
"""
Order Synchronization Service - Сервис синхронизации ордеров
===========================================================

Реализует техническое задание по синхронизации ордеров:
- F0: Сверка и восстановление SL/TP ордеров для открытых позиций
- F1: Метод syncOrders() для вызова перед watchdog и ticker_monitor
- F2: Полная логика синхронизации с биржей
- F3: Формирование SyncReport
- F4: Отправка отчетов в Telegram
- F5: Fail-safe обработка исключений
- F6: Опциональный фоновый режим

Архитектура:
- OrderSyncService: основной сервис
- ExchangeClient: единый API клиент
- OrderRepository: DAO для работы с данными
- TelegramNotifier: уведомления
- SyncReport: отчеты о синхронизации

Author: HEDGER
Version: 1.0.1 - Order Synchronization Service (Рефакторенная версия)
"""

import json
import os
import time
import threading
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum


# Load environment variables early
try:
    from env_loader import load_env_file
    load_env_file()
except ImportError:
    pass

# Local imports
from config import BINANCE_API_KEY, BINANCE_API_SECRET
from utils import logger
from symbol_cache import round_price_for_symbol, round_quantity_for_symbol


# Binance imports
try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    BINANCE_AVAILABLE = True
except ImportError:
    Client = None
    BinanceAPIException = Exception
    BINANCE_AVAILABLE = False
    logger.warning("⚠️ python-binance не установлен")

def is_binance_client_available():
    return BINANCE_AVAILABLE and Client is not None and callable(Client)

# Telegram imports
try:
    from telegram_bot import telegram_bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    telegram_bot = None
    TELEGRAM_AVAILABLE = False
    logger.warning("⚠️ telegram_bot недоступен")

# Database imports
try:
    import sqlite3
    from database import SignalDatabase
    DB_AVAILABLE = True
    
    def get_watchdog_db_connection():
        """Создает соединение с БД для watchdog orders"""
        return sqlite3.connect('signals.db', timeout=10)
    
    def init_watchdog_table():
        """Инициализирует таблицу watchdog_orders если не существует"""
        conn = get_watchdog_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watchdog_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                order_id TEXT NOT NULL UNIQUE,
                side TEXT NOT NULL,
                position_side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                signal_type TEXT NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                status TEXT DEFAULT 'PENDING',
                created_at TEXT,
                filled_at TEXT,
                sl_order_id TEXT,
                tp_order_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    # Инициализируем таблицу при импорте
    init_watchdog_table()
    
except ImportError:
    def get_watchdog_db_connection_stub():
        """Заглушка для БД"""
        raise ImportError("БД недоступна")
    get_watchdog_db_connection = get_watchdog_db_connection_stub
    DB_AVAILABLE = False
    logger.warning("⚠️ database модуль недоступен")


# ========================================
# Data Classes & Models
# ========================================

@dataclass
class WatchdogOrder:
    """Модель ордера из БД watchdog"""
    symbol: str
    order_id: str
    side: str  # BUY/SELL
    position_side: str  # LONG/SHORT
    quantity: float
    price: float
    signal_type: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: str = 'PENDING'
    created_at: str = ''
    filled_at: Optional[str] = None
    sl_order_id: Optional[str] = None
    tp_order_id: Optional[str] = None


@dataclass
class ExchangeOrder:
    """Модель ордера с биржи"""
    order_id: str
    symbol: str
    side: str
    type: str
    status: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None


@dataclass
class ExchangePosition:
    """Модель позиции с биржи"""
    symbol: str
    side: str  # LONG/SHORT
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float


class OrderAction(Enum):
    """Типы действий с ордерами"""
    ADDED = "ADDED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"
    SL_RESTORED = "SL_RESTORED"
    TP_RESTORED = "TP_RESTORED"


@dataclass
class SyncRecord:
    """Запись об изменении при синхронизации"""
    action: OrderAction
    symbol: str
    order_id: str
    order_type: str
    side: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SyncReport:
    """F3: Отчет о синхронизации ордеров"""
    timestamp: datetime
    duration_ms: int = 0
    total_processed: int = 0
    added_count: int = 0
    updated_count: int = 0
    deleted_count: int = 0
    sl_restored_count: int = 0
    tp_restored_count: int = 0
    error_count: int = 0
    records: List[SyncRecord] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def add_record(self, record: SyncRecord) -> None:
        """Добавляет запись в отчет"""
        self.records.append(record)
        self.total_processed += 1
        
        if record.action == OrderAction.ADDED:
            self.added_count += 1
        elif record.action == OrderAction.UPDATED:
            self.updated_count += 1
        elif record.action == OrderAction.DELETED:
            self.deleted_count += 1
        elif record.action == OrderAction.SL_RESTORED:
            self.sl_restored_count += 1
        elif record.action == OrderAction.TP_RESTORED:
            self.tp_restored_count += 1
    
    def add_error(self, error: str) -> None:
        """Добавляет ошибку в отчет"""
        self.errors.append(error)
        self.error_count += 1
    
    def has_changes(self) -> bool:
        """Проверяет, есть ли изменения в отчете"""
        return self.added_count > 0 or self.updated_count > 0 or self.deleted_count > 0 or \
               self.sl_restored_count > 0 or self.tp_restored_count > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует отчет в словарь"""
        return asdict(self)


# ========================================
# Exchange Client - API для биржи
# ========================================

class ExchangeClient:
    """Единый клиент для работы с биржей (MAINNET ONLY)"""
    def __init__(self):
        self.client: Optional[Any] = None
        self._init_client()

    def _init_client(self) -> None:
        """Инициализация клиента биржи (MAINNET ONLY)"""
        if not is_binance_client_available():
            logger.error("❌ Binance client недоступен: python-binance не установлен или импорт не удался")
            self.client = None
            return
        # Check MAINNET keys
        if not BINANCE_API_KEY or not BINANCE_API_SECRET:
            logger.error("❌ MAINNET Binance API keys not configured! Required: BINANCE_API_KEY, BINANCE_API_SECRET")
            self.client = None
            return
        try:
            if Client is None:
                logger.error("❌ Binance Client is None (python-binance не установлен)")
                self.client = None
                return
            self.client = Client(
                api_key=BINANCE_API_KEY,
                api_secret=BINANCE_API_SECRET
            )
            self.client.futures_account()
            logger.info("✅ Binance futures client инициализирован (MAINNET)")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Binance client: {e}")
            self.client = None
    
    def fetch_open_orders(self, symbol: Optional[str] = None) -> List[ExchangeOrder]:
        """Получает открытые ордера с биржи"""
        if not self.client:
            return []
        
        try:
            if symbol:
                orders = self.client.futures_get_open_orders(symbol=symbol)
            else:
                orders = self.client.futures_get_open_orders()
            
            exchange_orders = []
            for order in orders:
                exchange_order = ExchangeOrder(
                    order_id=str(order['orderId']),
                    symbol=order['symbol'],
                    side=order['side'],
                    type=order['type'],
                    status=order['status'],
                    quantity=float(order['origQty']),
                    price=float(order['price']) if order['price'] and order['price'] != '0' else None,
                    stop_price=float(order['stopPrice']) if order['stopPrice'] and order['stopPrice'] != '0' else None
                )
                exchange_orders.append(exchange_order)
            
            return exchange_orders
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения ордеров: {e}")
            return []

    def fetch_positions(self) -> List[ExchangePosition]:
        """Получает открытые позиции с биржи"""
        if not self.client:
            return []

        try:
            account = self.client.futures_account()
            positions = []
            for pos in account.get('positions', []):
                size = float(pos.get('positionAmt', 0))
                if size == 0:
                    continue
                position = ExchangePosition(
                    symbol=pos['symbol'],
                    side='LONG' if size > 0 else 'SHORT',
                    size=abs(size),
                    entry_price=float(pos.get('entryPrice', 0)),
                    mark_price=float(pos.get('markPrice', 0)),
                    unrealized_pnl=float(pos.get('unrealizedProfit', 0))
                )
                positions.append(position)
            return positions
        except Exception as e:
            logger.error(f"❌ Ошибка получения позиций: {e}")
            return []
    
    def place_take_order(self, symbol: str, side: str, quantity: float, take_price: float) -> Optional[str]:
        """Размещает тейк-профит ордер"""
        if not self.client:
            return None
        
        try:
            # Округляем значения
            quantity = round_quantity_for_symbol(symbol, quantity)
            take_price = round_price_for_symbol(symbol, take_price)
            
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='TAKE_PROFIT_MARKET',
                quantity=quantity,
                stopPrice=take_price,
                timeInForce='GTC'
            )
            
            order_id = str(order['orderId'])
            logger.info(f"✅ Размещен TP ордер {order_id}: {side} {quantity} {symbol} @ {take_price}")
            return order_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка размещения TP ордера: {e}")
            return None

    def place_stop_order(self, symbol: str, side: str, quantity: float, stop_price: float) -> Optional[str]:
        """Размещает стоп-лосс ордер"""
        if not self.client:
            return None

        try:
            # Округляем значения
            quantity = round_quantity_for_symbol(symbol, quantity)
            stop_price = round_price_for_symbol(symbol, stop_price)

            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='STOP_MARKET',
                quantity=quantity,
                stopPrice=stop_price,
                timeInForce='GTC'
            )

            order_id = str(order['orderId'])
            logger.info(f"✅ Размещен SL ордер {order_id}: {side} {quantity} {symbol} @ {stop_price}")
            return order_id

        except Exception as e:
            logger.error(f"❌ Ошибка размещения SL ордера: {e}")
            return None


# ========================================
# Order Repository - DAO для данных
# ========================================

class OrderRepository:
    """DAO для работы с ордерами в БД"""
    
    def __init__(self):
        self.db_available = DB_AVAILABLE
    
    def get_all_orders(self) -> List[WatchdogOrder]:
        """Получает все ордера из БД"""
        if not self.db_available:
            logger.warning("⚠️ БД недоступна, возвращаем пустой список")
            return []
        
        try:
            conn = get_watchdog_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT symbol, order_id, side, position_side, quantity, price, 
                       signal_type, stop_loss, take_profit, status, created_at, 
                       filled_at, sl_order_id, tp_order_id
                FROM watchdog_orders
                WHERE status IN ('PENDING', 'FILLED')
            """)
            rows = cursor.fetchall() if cursor else []
            orders = []
            for row in rows:
                order = WatchdogOrder(
                    symbol=row[0],
                    order_id=row[1],
                    side=row[2],
                    position_side=row[3],
                    quantity=float(row[4]),
                    price=float(row[5]),
                    signal_type=row[6],
                    stop_loss=float(row[7]) if row[7] else None,
                    take_profit=float(row[8]) if row[8] else None,
                    status=row[9] or 'PENDING',
                    created_at=row[10] or '',
                    filled_at=row[11],
                    sl_order_id=row[12],
                    tp_order_id=row[13]
                )
                orders.append(order)
            conn.close()
            return orders
        except Exception as e:
            logger.error(f"❌ Ошибка получения ордеров из БД: {e}")
            return []

    def save_all_orders(self, orders: List[WatchdogOrder]) -> bool:
        """Сохраняет все ордера в БД (обновляет или вставляет)"""
        if not self.db_available:
            logger.warning("⚠️ БД недоступна, не сохраняем ордера")
            return False
        try:
            conn = get_watchdog_db_connection()
            cursor = conn.cursor()
            for order in orders:
                cursor.execute("""
                    INSERT INTO watchdog_orders 
                    (symbol, order_id, side, position_side, quantity, price, 
                     signal_type, stop_loss, take_profit, status, created_at, 
                     filled_at, sl_order_id, tp_order_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(order_id) DO UPDATE SET
                        symbol=excluded.symbol,
                        side=excluded.side,
                        position_side=excluded.position_side,
                        quantity=excluded.quantity,
                        price=excluded.price,
                        signal_type=excluded.signal_type,
                        stop_loss=excluded.stop_loss,
                        take_profit=excluded.take_profit,
                        status=excluded.status,
                        created_at=excluded.created_at,
                        filled_at=excluded.filled_at,
                        sl_order_id=excluded.sl_order_id,
                        tp_order_id=excluded.tp_order_id
                """, (
                    order.symbol, order.order_id, order.side, order.position_side,
                    order.quantity, order.price, order.signal_type,
                    order.stop_loss, order.take_profit, order.status,
                    order.created_at, order.filled_at, order.sl_order_id, order.tp_order_id
                ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения ордеров в БД: {e}")
            return False


# ========================================
# Telegram Notifier - уведомления
# ========================================

class TelegramNotifier:
    """Класс для отправки уведомлений в Telegram"""
    
    @staticmethod
    def send_sync_report(report: SyncReport) -> bool:
        """F4: Отправляет отчет о синхронизации в Telegram"""
        if not TELEGRAM_AVAILABLE or not telegram_bot:
            return False
        
        try:
            # Формируем сообщение
            message = f"📊 ОТЧЕТ СИНХРОНИЗАЦИИ\n"
            message += f"⏰ {report.timestamp.strftime('%H:%M:%S')}\n"
            message += f"⚡ Время: {report.duration_ms}ms\n\n"
            
            if report.has_changes():
                message += f"📈 ИЗМЕНЕНИЯ:\n"
                if report.added_count > 0:
                    message += f"➕ Добавлено: {report.added_count}\n"
                if report.updated_count > 0:
                    message += f"🔄 Обновлено: {report.updated_count}\n"
                if report.deleted_count > 0:
                    message += f"🗑️ Удалено: {report.deleted_count}\n"
                if report.sl_restored_count > 0:
                    message += f"🛡️ SL восстановлено: {report.sl_restored_count}\n"
                if report.tp_restored_count > 0:
                    message += f"🎯 TP восстановлено: {report.tp_restored_count}\n"
                
                # Добавляем детали важных изменений
                important_records = [r for r in report.records 
                                   if r.action in [OrderAction.SL_RESTORED, OrderAction.TP_RESTORED,
                                                 OrderAction.ADDED, OrderAction.DELETED]]
                
                if important_records:
                    message += f"\n📋 ДЕТАЛИ:\n"
                    for record in important_records[:5]:  # Первые 5
                        if record.action == OrderAction.SL_RESTORED:
                            message += f"🛡️ {record.symbol}: SL @ {record.price}\n"
                        elif record.action == OrderAction.TP_RESTORED:
                            message += f"🎯 {record.symbol}: TP @ {record.price}\n"
                        elif record.action == OrderAction.ADDED:
                            message += f"➕ {record.symbol}: {record.side} @ {record.price}\n"
                        elif record.action == OrderAction.DELETED:
                            message += f"🗑️ {record.symbol}: {record.reason}\n"
                    
                    if len(important_records) > 5:
                        message += f"... и еще {len(important_records) - 5} изменений\n"
            else:
                message += f"✅ Изменений нет, все синхронизировано\n"
            
            if report.error_count > 0:
                message += f"\n❌ Ошибок: {report.error_count}\n"
                for error in report.errors[:3]:  # Первые 3 ошибки
                    message += f"• {error}\n"
            
            # Отправляем сообщение
            telegram_bot.send_message(message)
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки отчета в Telegram: {e}")
            return False
    
    @staticmethod
    def send_sl_tp_restoration(symbol: str, order_type: str, price: float) -> bool:
        """F0: Отправляет уведомление о восстановлении SL/TP"""
        if not TELEGRAM_AVAILABLE or not telegram_bot:
            return False
        
        try:
            emoji = "🛡️" if order_type == "SL" else "🎯"
            message = f"{emoji} ВОССТАНОВЛЕН {order_type}\n"
            message += f"📍 Символ: {symbol}\n"
            message += f"💰 Цена: {price}\n"
            message += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            
            telegram_bot.send_message(message)
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о восстановлении: {e}")
            return False


# ========================================
# Order Sync Service - Main Service
# ========================================

class OrderSyncService:
    """
    Основной сервис синхронизации ордеров
    Реализует требования F0-F6 из технического задания
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.exchange_client = ExchangeClient()
        self.order_repository = OrderRepository()
        self.sync_logger = self._setup_sync_logger()
        
        # Настройки из конфига
        self.sync_interval = self.config.get('sync_interval', 30)  # секунды
        self.max_sync_duration = self.config.get('max_sync_duration', 120)  # секунды
        self.enable_sl_tp_restoration = self.config.get('enable_sl_tp_restoration', True)
        
        # Для фонового режима
        self._background_thread: Optional[threading.Thread] = None
        self._stop_background = threading.Event()
        
        logger.info("🔄 OrderSyncService инициализирован")
    
    def _setup_sync_logger(self) -> logging.Logger:
        """Настраивает отдельный логгер для синхронизации"""
        sync_logger = logging.getLogger('order_sync')
        sync_logger.setLevel(logging.INFO)
        
        # Проверяем, есть ли уже обработчики
        if not sync_logger.handlers:
            # Создаем директорию logs если не существует
            Path('logs').mkdir(exist_ok=True)
            
            # Создаем обработчик для файла
            file_handler = logging.FileHandler('logs/order_sync.log', encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # Создаем форматтер
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            sync_logger.addHandler(file_handler)
        
        return sync_logger
    
    def sync_orders(self) -> SyncReport:
        """
        F1: Основной метод синхронизации ордеров
        Вызывается перед запуском watchdog и ticker_monitor
        """
        start_time = datetime.now()
        report = SyncReport(timestamp=start_time)
        
        try:
            self.sync_logger.info("🔄 Начинаем синхронизацию ордеров...")
            
            # F2.1: Получаем данные из БД
            db_orders = self.order_repository.get_all_orders()
            self.sync_logger.info(f"📂 Загружено {len(db_orders)} ордеров из БД")
            
            # F2.2: Получаем данные с биржи
            exchange_orders = self.exchange_client.fetch_open_orders()
            exchange_positions = self.exchange_client.fetch_positions()
            self.sync_logger.info(f"🌐 Получено с биржи: {len(exchange_orders)} ордеров, {len(exchange_positions)} позиций")
            
            # F2.3-6: Сравниваем и применяем изменения
            updated_orders = self._compare_and_patch(db_orders, exchange_orders, report, exchange_positions)
            
            # F0: Проверяем и восстанавливаем SL/TP ордера
            if self.enable_sl_tp_restoration:
                self._reconcile_stops_and_takes(exchange_positions, updated_orders, report)
            
            # Сохраняем изменения
            if report.has_changes():
                self.order_repository.save_all_orders(updated_orders)
                self.sync_logger.info(f"💾 Сохранены изменения в БД")
            
            # F3: Формируем итоговый отчет
            duration = (datetime.now() - start_time).total_seconds() * 1000
            report.duration_ms = int(duration)
            
            # F4: Отправляем отчет в Telegram
            TelegramNotifier.send_sync_report(report)
            
            self.sync_logger.info(f"✅ Синхронизация завершена за {duration:.0f}ms")
            
        except Exception as e:
            # F5: Fail-safe обработка исключений
            error_msg = f"Критическая ошибка синхронизации: {e}"
            report.add_error(error_msg)
            self.sync_logger.error(f"❌ {error_msg}")
            logger.error(f"❌ {error_msg}")
        
        return report
    
    def _compare_and_patch(self, db_orders: List[WatchdogOrder], 
                          exchange_orders: List[ExchangeOrder],
                          report: SyncReport,
                          exchange_positions: Optional[List[ExchangePosition]] = None) -> List[WatchdogOrder]:
        """F2: Логика сравнения и обновления ордеров"""
        if exchange_positions is None:
            exchange_positions = self.exchange_client.fetch_positions()
        open_position_symbols = set(pos.symbol for pos in exchange_positions)

        # Создаем словари для быстрого поиска
        db_orders_dict = {order.order_id: order for order in db_orders}
        exchange_orders_dict = {order.order_id: order for order in exchange_orders}
        
        updated_orders = []
        
        # F2.4: Ордера только в БД → удалить, если нет позиции и нет на бирже
        for order_id, db_order in db_orders_dict.items():
            if order_id not in exchange_orders_dict:
                # Проверяем историю ордера перед удалением
                # Проверяем историю ордера через Binance API
                history = None
                if self.exchange_client.client:
                    try:
                        history = self.exchange_client.client.futures_get_order(
                            symbol=db_order.symbol,
                            orderId=order_id
                        )
                    except Exception as e:
                        self.sync_logger.warning(f"⚠️ Не удалось получить историю ордера {order_id}: {e}")
                has_position = db_order.symbol in open_position_symbols

                if history and history.get('status') in ['FILLED', 'CANCELED']:
                    # Обновляем статус вместо удаления
                    db_order.status = history['status']
                    if history['status'] == 'FILLED':
                        db_order.filled_at = datetime.now().isoformat()
                    updated_orders.append(db_order)
                    record = SyncRecord(
                        action=OrderAction.UPDATED,
                        symbol=db_order.symbol,
                        order_id=order_id,
                        order_type=db_order.side,
                        old_status='PENDING',
                        new_status=history['status'],
                        reason=f"Обновлен статус из истории"
                    )
                    report.add_record(record)
                elif not has_position:
                    # Удаляем сиротский ордер (нет на бирже, нет позиции)
                    record = SyncRecord(
                        action=OrderAction.DELETED,
                        symbol=db_order.symbol,
                        order_id=order_id,
                        order_type=db_order.side,
                        reason="Сиротский ордер: отсутствует на бирже и нет позиции"
                    )
                    report.add_record(record)
                    self.sync_logger.info(f"🗑️ Сиротский ордер {order_id} ({db_order.symbol}) удалён: нет на бирже и нет позиции")
                    # Не добавляем сиротский ордер в updated_orders (он будет удалён из БД)
                else:
                    # Если есть позиция, не удаляем
                    updated_orders.append(db_order)
            else:
                # Ордер есть в обоих списках
                updated_orders.append(db_order)
        
        # F2.5: Ордера только на бирже → создать запись если необходимо
        for order_id, exchange_order in exchange_orders_dict.items():
            if order_id not in db_orders_dict:
                # Проверяем, нужно ли добавлять этот ордер
                if exchange_order.status in ['NEW', 'PARTIALLY_FILLED'] and exchange_order.type == 'LIMIT':
                    # Создаем новую запись
                    new_order = WatchdogOrder(
                        symbol=exchange_order.symbol,
                        order_id=order_id,
                        side=exchange_order.side,
                        position_side='LONG' if exchange_order.side == 'BUY' else 'SHORT',
                        quantity=exchange_order.quantity,
                        price=exchange_order.price or 0,
                        signal_type='LONG' if exchange_order.side == 'BUY' else 'SHORT',
                        stop_loss=None,
                        take_profit=None,
                        status='PENDING',
                        created_at=datetime.now().isoformat(),
                        filled_at=None,
                        sl_order_id=None,
                        tp_order_id=None
                    )
                    
                    updated_orders.append(new_order)
                    
                    record = SyncRecord(
                        action=OrderAction.ADDED,
                        symbol=exchange_order.symbol,
                        order_id=order_id,
                        order_type=exchange_order.type,
                        side=exchange_order.side,
                        quantity=exchange_order.quantity,
                        price=exchange_order.price,
                        reason="Новый ордер с биржи"
                    )
                    report.add_record(record)
                    
                    self.sync_logger.info(f"➕ Добавлен новый ордер {order_id} ({exchange_order.symbol})")
        
        # F2.6: Ордера в обоих списках с разными статусами → обновить
        for order_id in set(db_orders_dict.keys()) & set(exchange_orders_dict.keys()):
            db_order = db_orders_dict[order_id]
            exchange_order = exchange_orders_dict[order_id]
            
            # Проверяем статус
            if exchange_order.status != 'NEW' and db_order.status == 'PENDING':
                old_status = db_order.status
                db_order.status = exchange_order.status
                
                if exchange_order.status == 'FILLED':
                    db_order.filled_at = datetime.now().isoformat()
                
                record = SyncRecord(
                    action=OrderAction.UPDATED,
                    symbol=db_order.symbol,
                    order_id=order_id,
                    order_type=db_order.side,
                    old_status=old_status,
                    new_status=exchange_order.status,
                    reason="Обновлен статус с биржи"
                )
                report.add_record(record)
                
                self.sync_logger.info(f"🔄 Обновлен статус ордера {order_id} ({db_order.symbol}): {old_status} → {exchange_order.status}")
        
        return updated_orders
    
    def _reconcile_stops_and_takes(self, exchange_positions: List[ExchangePosition],
                                 updated_orders: List[WatchdogOrder],
                                 report: SyncReport) -> None:
        """F0: Сверка и восстановление SL/TP ордеров для открытых позиций"""
        
        if not exchange_positions:
            return
        
        self.sync_logger.info(f"🔍 Проверяем SL/TP ордера для {len(exchange_positions)} позиций...")
        
        # Получаем актуальные ордера с биржи для проверки SL/TP
        all_exchange_orders = self.exchange_client.fetch_open_orders()
        exchange_orders_by_symbol = {}
        for order in all_exchange_orders:
            if order.symbol not in exchange_orders_by_symbol:
                exchange_orders_by_symbol[order.symbol] = []
            exchange_orders_by_symbol[order.symbol].append(order)
        
        for position in exchange_positions:
            symbol = position.symbol
            
            # Ищем соответствующий ордер в БД для получения SL/TP значений
            db_order = None
            for order in updated_orders:
                if order.symbol == symbol and order.status in ['FILLED', 'PENDING']:
                    db_order = order
                    break
            
            if not db_order or not (db_order.stop_loss or db_order.take_profit):
                continue  # Нет сохраненных SL/TP значений
            
            # Проверяем наличие SL/TP ордеров на бирже
            symbol_orders = exchange_orders_by_symbol.get(symbol, [])
            
            has_sl = any(order.type in ['STOP_MARKET', 'STOP'] for order in symbol_orders)
            has_tp = any(order.type in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT'] for order in symbol_orders)
            
            # Определяем направление закрытия
            close_side = 'SELL' if position.side == 'LONG' else 'BUY'
            
            # Восстанавливаем отсутствующие SL ордера
            if not has_sl and db_order.stop_loss:
                sl_order_id = self.exchange_client.place_stop_order(
                    symbol=symbol,
                    side=close_side,
                    quantity=position.size,
                    stop_price=db_order.stop_loss
                )
                
                if sl_order_id:
                    db_order.sl_order_id = sl_order_id
                    
                    record = SyncRecord(
                        action=OrderAction.SL_RESTORED,
                        symbol=symbol,
                        order_id=sl_order_id,
                        order_type='STOP_MARKET',
                        side=close_side,
                        quantity=position.size,
                        price=db_order.stop_loss,
                        reason=f"Восстановлен SL для позиции {position.side}"
                    )
                    report.add_record(record)
                    
                    # F0: Отправляем уведомление
                    TelegramNotifier.send_sl_tp_restoration(symbol, 'SL', db_order.stop_loss)
                    
                    self.sync_logger.info(f"🛡️ Восстановлен SL для {symbol}: {close_side} {position.size} @ {db_order.stop_loss}")
            
            # Восстанавливаем отсутствующие TP ордера
            if not has_tp and db_order.take_profit:
                tp_order_id = self.exchange_client.place_take_order(
                    symbol=symbol,
                    side=close_side,
                    quantity=position.size,
                    take_price=db_order.take_profit
                )
                
                if tp_order_id:
                    db_order.tp_order_id = tp_order_id
                    
                    record = SyncRecord(
                        action=OrderAction.TP_RESTORED,
                        symbol=symbol,
                        order_id=tp_order_id,
                        order_type='TAKE_PROFIT_MARKET',
                        side=close_side,
                        quantity=position.size,
                        price=db_order.take_profit,
                        reason=f"Восстановлен TP для позиции {position.side}"
                    )
                    report.add_record(record)
                    
                    # F0: Отправляем уведомление
                    TelegramNotifier.send_sl_tp_restoration(symbol, 'TP', db_order.take_profit)
                    
                    self.sync_logger.info(f"🎯 Восстановлен TP для {symbol}: {close_side} {position.size} @ {db_order.take_profit}")
    
    def start_background_sync(self) -> None:
        """F6: Запуск синхронизации в фоновом режиме"""
        if self._background_thread and self._background_thread.is_alive():
            logger.warning("⚠️ Фоновая синхронизация уже запущена")
            return
        
        self._stop_background.clear()
        self._background_thread = threading.Thread(target=self._background_sync_loop, daemon=True)
        self._background_thread.start()
        
        logger.info(f"🔄 Запущена фоновая синхронизация с интервалом {self.sync_interval}s")
    
    def stop_background_sync(self) -> None:
        """Остановка фоновой синхронизации"""
        if self._background_thread and self._background_thread.is_alive():
            self._stop_background.set()
            self._background_thread.join(timeout=5)
            logger.info("⏹️ Фоновая синхронизация остановлена")
    
    def _background_sync_loop(self) -> None:
        """Цикл фоновой синхронизации"""
        while not self._stop_background.is_set():
            try:
                report = self.sync_orders()
                
                # Логируем результат
                if report.has_changes():
                    self.sync_logger.info(f"🔄 Фоновая синхронизация: {report.total_processed} обработано, {report.added_count + report.updated_count + report.deleted_count + report.sl_restored_count + report.tp_restored_count} изменений")
                
            except Exception as e:
                self.sync_logger.error(f"❌ Ошибка фоновой синхронизации: {e}")
            
            # Ждем следующего цикла
            self._stop_background.wait(self.sync_interval)
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Получает статус сервиса синхронизации"""
        return {
            'exchange_connected': self.exchange_client.client is not None,
            'background_running': self._background_thread and self._background_thread.is_alive(),
            'sync_interval': self.sync_interval,
            'sl_tp_restoration_enabled': self.enable_sl_tp_restoration,
            'last_sync': 'N/A'  # TODO: добавить отслеживание последней синхронизации
        }


# ========================================
# Factory & Configuration
# ========================================

def create_order_sync_service(config_file: Optional[str] = None) -> OrderSyncService:
    """Фабрика для создания OrderSyncService с конфигурацией"""
    config = {}

    if config_file:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.endswith('.json'):
                    config = json.load(f)
                # TODO: добавить поддержку YAML
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить конфиг {config_file}: {e}")

    # Загружаем параметры из переменных окружения
    config.update({
        'sync_interval': int(os.getenv('SYNC_INTERVAL', '30')),
        'max_sync_duration': int(os.getenv('MAX_SYNC_DURATION', '120')),
        'enable_sl_tp_restoration': os.getenv('ENABLE_SL_TP_RESTORATION', 'true').lower() == 'true'
    })

    # MAINNET ONLY: No TESTNET keys or logic
    return OrderSyncService(config)


# ========================================
# CLI Interface & Testing
# ========================================


def main():
    """CLI интерфейс для тестирования"""
    parser = argparse.ArgumentParser(description='Order Synchronization Service')
    parser.add_argument('--sync', action='store_true', help='Выполнить разовую синхронизацию')
    parser.add_argument('--background', action='store_true', help='Запустить фоновую синхронизацию')
    parser.add_argument('--status', action='store_true', help='Показать статус сервиса')
    parser.add_argument('--config', type=str, help='Путь к файлу конфигурации')

    args = parser.parse_args()

    try:
        # MAINNET ONLY: .env should exist, no TESTNET logic
        # Создаем сервис
        service = create_order_sync_service(args.config)

        if args.status:
            status = service.get_sync_status()
            print("📊 СТАТУС ORDER SYNC SERVICE")
            print("=" * 40)
            for key, value in status.items():
                print(f"{key}: {value}")

        elif args.sync:
            print("🔄 Запуск разовой синхронизации...")
            report = service.sync_orders()

            print(f"✅ Синхронизация завершена за {report.duration_ms}ms")
            print(f"📊 Обработано: {report.total_processed}")
            print(f"➕ Добавлено: {report.added_count}")
            print(f"🔄 Обновлено: {report.updated_count}")
            print(f"🗑️ Удалено: {report.deleted_count}")
            print(f"🛡️ SL восстановлено: {report.sl_restored_count}")
            print(f"🎯 TP восстановлено: {report.tp_restored_count}")
            print(f"❌ Ошибок: {report.error_count}")

        elif args.background:
            print("🔄 Запуск фоновой синхронизации...")
            service.start_background_sync()

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n⏹️ Остановка фоновой синхронизации...")
                service.stop_background_sync()

        else:
            parser.print_help()

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
