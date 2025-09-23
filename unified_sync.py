#!/usr/bin/env python3
"""
Unified Synchronization System - Объединенная система синхронизации
================================================================

Заменяет дублирующие компоненты и объединяет всю логику синхронизации:
- state_recovery.py
- orders_synchronizer.py  
- sync_check.py
- sync_monitor.py

Основные функции:
1. Синхронизация состояния перед запуском компонентов
2. Автоматическое исправление расхождений с биржей
3. Удаление отмененных/исполненных ордеров
4. Анализ истории сделок для пропущенных закрытий
5. Telegram уведомления о всех изменениях

Author: HEDGER
Version: 2.0 - Unified State Management
"""

import json
import time
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from utils import logger
from config import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET

# Binance imports
try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    BINANCE_AVAILABLE = True
except ImportError:
    logger.error("❌ python-binance not installed")
    BINANCE_AVAILABLE = False
    Client = None
    BinanceAPIException = Exception

# Telegram notifications
try:
    from telegram_bot import telegram_bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Telegram bot not available")
    TELEGRAM_AVAILABLE = False
    telegram_bot = None


@dataclass
class SyncAction:
    """Действие синхронизации"""
    action_type: str  # 'remove_order', 'close_position', 'cancel_order', 'update_state'
    symbol: str
    order_id: Optional[str]
    description: str
    details: Optional[Dict] = None
    timestamp: Optional[datetime] = None


@dataclass
class SyncResult:
    """Результат синхронизации"""
    timestamp: datetime
    total_checked: int
    actions_taken: int
    successful_actions: int
    failed_actions: int
    actions: List[SyncAction]
    warnings: List[str]
    errors: List[str]
    is_synchronized: bool = True


class UnifiedSynchronizer:
    """Объединенная система синхронизации"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.watchdog_state_file = Path('orders_watchdog_state.json')
        self.backup_state_file = Path('orders_watchdog_state_backup.json')
        self.sync_log_file = Path('sync_log.json')
        
        self._init_binance_client()
    
    def _init_binance_client(self) -> None:
        """Инициализация Binance клиента"""
        if not BINANCE_AVAILABLE or Client is None:
            logger.error("❌ Binance library not available")
            return
            
        if not BINANCE_API_KEY or not BINANCE_API_SECRET:
            logger.error("❌ Binance API ключи не настроены")
            return
        
        try:
            logger.info(f"🔧 Подключение к Binance ({'TESTNET' if BINANCE_TESTNET else 'MAINNET'})...")
            self.client = Client(
                api_key=BINANCE_API_KEY,
                api_secret=BINANCE_API_SECRET,
                testnet=BINANCE_TESTNET
            )
            
            # Тест подключения
            self.client.futures_account()
            logger.info("✅ Подключение к Binance успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Binance: {e}")
            self.client = None
    
    def _load_watchdog_state(self) -> Dict[str, Any]:
        """Загрузка состояния Orders Watchdog"""
        try:
            if not self.watchdog_state_file.exists():
                logger.warning("⚠️ Файл состояния Orders Watchdog не найден")
                return {'watched_orders': [], 'symbols': {}, 'last_update': None}
            
            with open(self.watchdog_state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            orders_count = len(data.get('watched_orders', []))
            symbols_count = len(data.get('symbols', {}))
            
            logger.info(f"📂 Загружено состояние: {orders_count} ордеров, {symbols_count} символов")
            return data
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки состояния: {e}")
            return {'watched_orders': [], 'symbols': {}, 'last_update': None}
    
    def _save_watchdog_state(self, state_data: Dict[str, Any]) -> bool:
        """Сохранение обновленного состояния"""
        try:
            # Создаем резервную копию
            if self.watchdog_state_file.exists():
                with open(self.watchdog_state_file, 'r', encoding='utf-8') as src:
                    with open(self.backup_state_file, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
            
            # Обновляем timestamp
            state_data['last_update'] = datetime.now().isoformat()
            
            # Сохраняем новое состояние
            with open(self.watchdog_state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info("💾 Состояние Orders Watchdog обновлено")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения состояния: {e}")
            return False
    
    def _get_exchange_orders(self) -> Dict[str, List[Dict]]:
        """Получение открытых ордеров с биржи"""
        if not self.client:
            return {}
        
        try:
            open_orders = self.client.futures_get_open_orders()
            
            # Группируем по символам
            orders_by_symbol = {}
            for order in open_orders:
                symbol = order['symbol']
                if symbol not in orders_by_symbol:
                    orders_by_symbol[symbol] = []
                orders_by_symbol[symbol].append(order)
            
            logger.info(f"📊 Получено {len(open_orders)} открытых ордеров с биржи ({len(orders_by_symbol)} символов)")
            return orders_by_symbol
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения ордеров с биржи: {e}")
            return {}
    
    def _get_exchange_positions(self) -> Dict[str, Dict]:
        """Получение активных позиций с биржи"""
        if not self.client:
            return {}
        
        try:
            positions = self.client.futures_position_information()
            
            # Фильтруем только активные позиции
            active_positions = {}
            for pos in positions:
                position_amt = float(pos.get('positionAmt', 0))
                if position_amt != 0:
                    active_positions[pos['symbol']] = pos
            
            logger.info(f"📊 Получено {len(active_positions)} активных позиций с биржи")
            return active_positions
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения позиций с биржи: {e}")
            return {}
    
    def _check_order_history(self, symbol: str, order_id: str, hours_back: int = 24) -> Optional[Dict]:
        """Проверка истории конкретного ордера"""
        if not self.client:
            return None
        
        try:
            # Получаем историю ордеров
            end_time = int(time.time() * 1000)
            start_time = end_time - (hours_back * 60 * 60 * 1000)
            
            order_history = self.client.futures_get_all_orders(
                symbol=symbol,
                orderId=int(order_id),
                startTime=start_time,
                endTime=end_time,
                limit=1
            )
            
            if order_history:
                return order_history[0]
            
        except Exception as e:
            logger.debug(f"⚠️ Не удалось получить историю ордера {order_id}: {e}")
        
        return None
    
    def _analyze_order_fate(self, local_order: Dict, exchange_orders: Dict[str, List], exchange_positions: Dict[str, Dict]) -> Optional[SyncAction]:
        """Анализирует судьбу пропавшего ордера"""
        symbol = local_order.get('symbol')
        order_id = local_order.get('order_id')
        order_type = local_order.get('order_type', 'UNKNOWN')
        
        if not symbol or not order_id:
            return None
        
        # Проверяем историю ордера
        order_history = self._check_order_history(symbol, order_id)
        
        if order_history:
            status = order_history.get('status', 'UNKNOWN')
            
            if status == 'FILLED':
                # Ордер исполнен
                if symbol in exchange_positions:
                    return SyncAction(
                        action_type='remove_order',
                        symbol=symbol,
                        order_id=order_id,
                        description=f"{order_type} ордер исполнен - позиция активна",
                        details={'status': 'FILLED', 'position_exists': True},
                        timestamp=datetime.now()
                    )
                else:
                    return SyncAction(
                        action_type='close_position',
                        symbol=symbol,
                        order_id=order_id,
                        description=f"{order_type} ордер исполнен и позиция закрыта",
                        details={'status': 'FILLED', 'position_closed': True},
                        timestamp=datetime.now()
                    )
            
            elif status in ['CANCELED', 'REJECTED', 'EXPIRED']:
                return SyncAction(
                    action_type='remove_order',
                    symbol=symbol,
                    order_id=order_id,
                    description=f"{order_type} ордер отменен ({status})",
                    details={'status': status},
                    timestamp=datetime.now()
                )
        
        # Если истории нет, но ордера нет на бирже
        return SyncAction(
            action_type='remove_order',
            symbol=symbol,
            order_id=order_id,
            description=f"{order_type} ордер исчез с биржи (причина неизвестна)",
            details={'status': 'MISSING'},
            timestamp=datetime.now()
        )
    
    def synchronize_state(self, send_telegram: bool = True) -> SyncResult:
        """
        Выполняет полную синхронизацию состояния системы
        
        Args:
            send_telegram: Отправлять уведомления в Telegram
            
        Returns:
            Результат синхронизации
        """
        logger.info("🔄 Начинаем синхронизацию состояния системы...")
        
        result = SyncResult(
            timestamp=datetime.now(),
            total_checked=0,
            actions_taken=0,
            successful_actions=0,
            failed_actions=0,
            actions=[],
            warnings=[],
            errors=[]
        )
        
        if not self.client:
            result.errors.append("Binance клиент недоступен")
            result.is_synchronized = False
            return result
        
        try:
            # 1. Загружаем локальное состояние
            watchdog_state = self._load_watchdog_state()
            local_orders = watchdog_state.get('watched_orders', [])
            result.total_checked = len(local_orders)
            
            if not local_orders:
                logger.info("✅ Нет ордеров для синхронизации")
                return result
            
            # 2. Получаем данные с биржи
            exchange_orders = self._get_exchange_orders()
            exchange_positions = self._get_exchange_positions()
            
            # 3. Анализируем каждый ордер
            orders_to_remove = []
            
            for local_order in local_orders:
                symbol = local_order.get('symbol')
                order_id = local_order.get('order_id')
                
                if not symbol or not order_id:
                    result.warnings.append(f"Некорректный ордер в состоянии: {local_order}")
                    continue
                
                # Проверяем, существует ли ордер на бирже
                exchange_symbol_orders = exchange_orders.get(symbol, [])
                order_exists = any(str(order['orderId']) == str(order_id) for order in exchange_symbol_orders)
                
                if not order_exists:
                    # Ордер отсутствует на бирже - анализируем причину
                    action = self._analyze_order_fate(local_order, exchange_orders, exchange_positions)
                    if action:
                        result.actions.append(action)
                        orders_to_remove.append(local_order)
                        result.actions_taken += 1
            
            # 4. Применяем изменения
            if orders_to_remove:
                # Обновляем список ордеров
                updated_orders = [order for order in local_orders if order not in orders_to_remove]
                watchdog_state['watched_orders'] = updated_orders
                
                # Пересчитываем символы
                symbols_data = {}
                for order in updated_orders:
                    symbol = order.get('symbol')
                    if symbol:
                        if symbol not in symbols_data:
                            symbols_data[symbol] = {
                                'orders': [], 
                                'has_main': False, 
                                'has_sl': False, 
                                'has_tp': False,
                                'main_order_filled': False
                            }
                        
                        symbols_data[symbol]['orders'].append(order)
                        
                        order_type = order.get('order_type', '')
                        if order_type == 'MAIN':
                            symbols_data[symbol]['has_main'] = True
                            symbols_data[symbol]['main_order_filled'] = order.get('filled', False)
                        elif order_type == 'SL':
                            symbols_data[symbol]['has_sl'] = True
                        elif order_type == 'TP':
                            symbols_data[symbol]['has_tp'] = True
                
                watchdog_state['symbols'] = symbols_data
                
                # Сохраняем обновленное состояние
                if self._save_watchdog_state(watchdog_state):
                    result.successful_actions = len(orders_to_remove)
                    logger.info(f"✅ Обновлено состояние: удалено {len(orders_to_remove)} ордеров")
                else:
                    result.failed_actions = len(orders_to_remove)
                    result.errors.append("Не удалось сохранить обновленное состояние")
            
            # 5. Отправляем уведомления
            if send_telegram and TELEGRAM_AVAILABLE and telegram_bot and result.actions_taken > 0:
                self._send_sync_notification(result)
            
            # 6. Логируем результат
            self._log_sync_result(result)
            
            result.is_synchronized = result.failed_actions == 0
            
            if result.actions_taken > 0:
                logger.info(f"✅ Синхронизация завершена: {result.successful_actions}/{result.actions_taken} изменений применено")
            else:
                logger.info("✅ Синхронизация завершена: изменений не требуется")
            
        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации: {e}")
            result.errors.append(str(e))
            result.is_synchronized = False
        
        return result
    
    def _send_sync_notification(self, result: SyncResult) -> None:
        """Отправка уведомления о синхронизации в Telegram"""
        try:
            if not telegram_bot:
                return
            
            status_emoji = "✅" if result.is_synchronized else "⚠️"
            
            message = f"""
{status_emoji} <b>СИНХРОНИЗАЦИЯ СОСТОЯНИЯ</b> {status_emoji}

⏰ <b>Время:</b> {result.timestamp.strftime('%H:%M:%S')}
📊 <b>Проверено ордеров:</b> {result.total_checked}
🔄 <b>Изменений:</b> {result.actions_taken}
✅ <b>Успешно:</b> {result.successful_actions}
❌ <b>Ошибок:</b> {result.failed_actions}
"""
            
            if result.actions:
                message += f"\n\n<b>🔄 Выполненные действия:</b>"
                for action in result.actions[:10]:  # Показываем не более 10 действий
                    action_emoji = {
                        'remove_order': '🗑️',
                        'close_position': '🔒',
                        'cancel_order': '❌',
                        'update_state': '📝'
                    }.get(action.action_type, '🔧')
                    
                    order_display = f"#{action.order_id}" if action.order_id else ""
                    message += f"\n{action_emoji} {action.symbol} {order_display}: {action.description}"
                
                if len(result.actions) > 10:
                    message += f"\n... и еще {len(result.actions) - 10} действий"
            
            if result.warnings:
                message += f"\n\n⚠️ <b>Предупреждения:</b>"
                for warning in result.warnings[:5]:
                    message += f"\n• {warning}"
            
            if result.errors:
                message += f"\n\n❌ <b>Ошибки:</b>"
                for error in result.errors[:3]:
                    message += f"\n• {error}"
            
            telegram_bot.send_message(message)
            logger.info("📱 Уведомление о синхронизации отправлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления: {e}")
    
    def _log_sync_result(self, result: SyncResult) -> None:
        """Логирование результата синхронизации"""
        try:
            log_entry = {
                'timestamp': result.timestamp.isoformat(),
                'total_checked': result.total_checked,
                'actions_taken': result.actions_taken,
                'successful_actions': result.successful_actions,
                'failed_actions': result.failed_actions,
                'is_synchronized': result.is_synchronized,
                'actions': [asdict(action) for action in result.actions],
                'warnings': result.warnings,
                'errors': result.errors
            }
            
            # Читаем существующий лог
            sync_log = []
            if self.sync_log_file.exists():
                try:
                    with open(self.sync_log_file, 'r', encoding='utf-8') as f:
                        sync_log = json.load(f)
                except:
                    sync_log = []
            
            # Добавляем новую запись
            sync_log.append(log_entry)
            
            # Оставляем только последние 100 записей
            sync_log = sync_log[-100:]
            
            # Сохраняем лог
            with open(self.sync_log_file, 'w', encoding='utf-8') as f:
                json.dump(sync_log, f, indent=2, ensure_ascii=False, default=str)
            
        except Exception as e:
            logger.error(f"❌ Ошибка логирования результата: {e}")
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Получение статуса синхронизации"""
        try:
            if not self.sync_log_file.exists():
                return {
                    'last_sync': None,
                    'is_synchronized': False,
                    'needs_sync': True,
                    'total_checked': 0,
                    'actions_taken': 0
                }
            
            with open(self.sync_log_file, 'r', encoding='utf-8') as f:
                sync_log = json.load(f)
            
            if not sync_log:
                return {
                    'last_sync': None,
                    'is_synchronized': False,
                    'needs_sync': True,
                    'total_checked': 0,
                    'actions_taken': 0
                }
            
            last_entry = sync_log[-1]
            last_sync_time = datetime.fromisoformat(last_entry['timestamp'])
            age_minutes = (datetime.now() - last_sync_time).total_seconds() / 60
            
            return {
                'last_sync': last_sync_time.strftime('%Y-%m-%d %H:%M:%S'),
                'age_minutes': int(age_minutes),
                'is_synchronized': last_entry.get('is_synchronized', False),
                'needs_sync': age_minutes > 30 or not last_entry.get('is_synchronized', False),
                'total_checked': last_entry.get('total_checked', 0),
                'actions_taken': last_entry.get('actions_taken', 0),
                'errors': len(last_entry.get('errors', []))
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса синхронизации: {e}")
            return {
                'last_sync': None,
                'is_synchronized': False,
                'needs_sync': True,
                'total_checked': 0,
                'actions_taken': 0,
                'error': str(e)
            }
    
    def print_status(self) -> None:
        """Вывод статуса синхронизации"""
        print("=" * 80)
        print("🔄 СТАТУС СИНХРОНИЗАЦИИ СИСТЕМЫ")
        print("=" * 80)
        
        status = self.get_sync_status()
        
        if status.get('last_sync'):
            sync_status = "✅ Синхронизировано" if status.get('is_synchronized', False) else "⚠️ Требует синхронизации"
            
            print(f"📅 Последняя синхронизация: {status['last_sync']}")
            print(f"⏱️ Возраст: {status.get('age_minutes', 0)} минут назад")
            print(f"📊 Статус: {sync_status}")
            print(f"🔍 Проверено ордеров: {status.get('total_checked', 0)}")
            print(f"🔄 Действий выполнено: {status.get('actions_taken', 0)}")
            
            if status.get('errors', 0) > 0:
                print(f"❌ Ошибок: {status['errors']}")
        else:
            print("❌ Синхронизация еще не выполнялась")
        
        print(f"🔗 Binance подключение: {'✅ Активно' if self.client else '❌ Отсутствует'}")
        print(f"📱 Telegram уведомления: {'✅ Доступны' if TELEGRAM_AVAILABLE else '❌ Недоступны'}")
        
        if status.get('needs_sync', True):
            print("\n⚠️ Рекомендуется выполнить синхронизацию")

    def recover_system_state(self) -> 'SystemState':
        """Восстановление состояния системы (метод для совместимости с orders_watchdog)"""
        return recover_system_state()


# Глобальный экземпляр синхронизатора
unified_sync = UnifiedSynchronizer()


# ================================
# ИНТЕРФЕЙСЫ ОБРАТНОЙ СОВМЕСТИМОСТИ
# ================================

@dataclass
class SystemState:
    """Класс для представления состояния системы - совместимость с orders_watchdog"""
    timestamp: datetime
    active_positions: Dict[str, Dict]
    watchdog_orders: Dict[str, Dict] 
    exchange_positions: Dict[str, Dict]
    exchange_orders: Dict[str, List]
    synchronization_issues: List[str]
    recovery_actions: List[str]
    is_synchronized: bool


class OrdersSyncInterface:
    """Интерфейс синхронизации ордеров для обратной совместимости"""
    
    def __init__(self, sync_instance=None):
        self._sync_instance = sync_instance
    
    @property
    def unified_sync(self):
        """Получение экземпляра синхронизатора"""
        if self._sync_instance is None:
            # Используем глобальный экземпляр
            return globals().get('unified_sync')
        return self._sync_instance
    
    def validate_new_signal(self, symbol: str, side: str, quantity: float) -> Tuple[bool, str]:
        """Валидация нового сигнала перед исполнением"""
        return validate_signal_before_execution(symbol, side, quantity)
    
    def get_synchronization_report(self) -> Dict[str, Any]:
        """Получение отчета о синхронизации для совместимости"""
        sync_instance = self.unified_sync
        if sync_instance is None:
            return {
                'watchdog_running': False,
                'last_sync': None,
                'is_synchronized': False,
                'total_checked': 0,
                'actions_taken': 0,
                'unified_sync': True,
                'error': 'Sync instance not available'
            }
        
        status = sync_instance.get_sync_status()
        return {
            'watchdog_running': True,
            'last_sync': status.get('last_sync'),
            'is_synchronized': status.get('is_synchronized', False),
            'total_checked': status.get('total_checked', 0),
            'actions_taken': status.get('actions_taken', 0),
            'unified_sync': True
        }
    
    def print_sync_report(self, report: Optional[Dict] = None) -> None:
        """Вывод отчета о синхронизации"""
        if report is None:
            report = self.get_synchronization_report()
        
        print("🔄 Sync Report (Unified System):")
        print(f"   📊 Synchronized: {report.get('is_synchronized', False)}")
        print(f"   📅 Last sync: {report.get('last_sync', 'Never')}")
        print(f"   🔍 Checked: {report.get('total_checked', 0)} orders")
        print(f"   🔄 Actions: {report.get('actions_taken', 0)}")


class StateRecoveryInterface:
    """Интерфейс восстановления состояния для обратной совместимости"""
    
    def __init__(self, sync_instance=None):
        self._sync_instance = sync_instance
    
    @property
    def unified_sync(self):
        """Получение экземпляра синхронизатора"""
        if self._sync_instance is None:
            # Используем глобальный экземпляр
            return globals().get('unified_sync')
        return self._sync_instance


# Создаем интерфейсы для обратной совместимости
# (Перенесено в конец файла после определения классов)


def validate_signal_before_execution(symbol: str, side: str, quantity: float) -> Tuple[bool, str]:
    """
    Валидация сигнала перед исполнением
    
    Args:
        symbol: Торговая пара
        side: Направление (BUY/SELL)
        quantity: Количество
        
    Returns:
        (is_valid, message)
    """
    try:
        if not unified_sync.client:
            return True, "Binance недоступен - валидация пропущена"
        
        # Проверяем доступность символа для торговли
        is_available, availability_msg = is_symbol_available_for_trading(symbol)
        if not is_available:
            return False, f"Символ недоступен: {availability_msg}"
        
        # Проверяем состояние синхронизации
        status = unified_sync.get_sync_status()
        if status.get('needs_sync', True):
            logger.warning(f"⚠️ Система требует синхронизации перед торговлей {symbol}")
            return False, "Требуется синхронизация состояния"
        
        # Дополнительные проверки можно добавить здесь
        
        return True, "Валидация пройдена успешно"
        
    except Exception as e:
        logger.error(f"❌ Ошибка валидации сигнала {symbol}: {e}")
        return False, f"Ошибка валидации: {e}"


def recover_system_state() -> SystemState:
    """
    Восстановление состояния системы
    
    Returns:
        Объект состояния системы
    """
    try:
        logger.info("🔄 Starting system state recovery...")
        
        # Выполняем синхронизацию
        sync_result = unified_sync.synchronize_state(send_telegram=False)
        
        # Загружаем текущее состояние
        watchdog_state = unified_sync._load_watchdog_state()
        exchange_positions = unified_sync._get_exchange_positions()
        exchange_orders = unified_sync._get_exchange_orders()
        
        # Создаем объект состояния
        system_state = SystemState(
            timestamp=datetime.now(),
            active_positions=watchdog_state.get('active_positions', {}),
            watchdog_orders=watchdog_state.get('orders', {}),
            exchange_positions=exchange_positions,
            exchange_orders=exchange_orders,
            synchronization_issues=sync_result.errors if sync_result.errors else [],
            recovery_actions=[f"Unified sync executed: {sync_result.actions_taken} actions"],
            is_synchronized=sync_result.is_synchronized
        )
        
        logger.info(f"✅ System state recovered: {len(system_state.active_positions)} positions")
        
        return system_state
        
    except Exception as e:
        logger.error(f"❌ Ошибка восстановления состояния: {e}")
        
        # Возвращаем пустое состояние в случае ошибки
        return SystemState(
            timestamp=datetime.now(),
            active_positions={},
            watchdog_orders={},
            exchange_positions={},
            exchange_orders={},
            synchronization_issues=[f"Recovery error: {e}"],
            recovery_actions=["Emergency state recovery"],
            is_synchronized=False
        )


def is_symbol_available_for_trading(symbol: str) -> Tuple[bool, str]:
    """
    Проверка доступности символа для торговли
    
    Args:
        symbol: Торговая пара
        
    Returns:
        (is_available, message)
    """
    try:
        if not unified_sync.client:
            return True, "Binance недоступен - считаем доступным"
        
        # Получаем информацию о символе
        exchange_info = unified_sync.client.futures_exchange_info()
        
        for symbol_info in exchange_info['symbols']:
            if symbol_info['symbol'] == symbol:
                status = symbol_info.get('status', 'UNKNOWN')
                
                if status == 'TRADING':
                    return True, "Символ доступен для торговли"
                else:
                    return False, f"Символ недоступен: статус {status}"
        
        return False, "Символ не найден на бирже"
        
    except Exception as e:
        logger.warning(f"⚠️ Ошибка проверки доступности {symbol}: {e}")
        return True, f"Ошибка проверки - считаем доступным: {e}"


def sync_before_startup(component_name: str = "system") -> bool:
    """
    Синхронизация состояния перед запуском компонента
    
    Args:
        component_name: Имя запускаемого компонента
        
    Returns:
        True если синхронизация прошла успешно
    """
    logger.info(f"🔄 Синхронизация состояния перед запуском {component_name}...")
    
    if not unified_sync.client:
        logger.warning("⚠️ Binance клиент недоступен - пропускаем синхронизацию")
        return True
    
    # Проверяем, нужна ли синхронизация
    status = unified_sync.get_sync_status()
    if not status.get('needs_sync', True):
        logger.info("✅ Состояние уже синхронизировано")
        return True
    
    # Выполняем синхронизацию
    result = unified_sync.synchronize_state()
    
    if result.is_synchronized:
        logger.info(f"✅ Синхронизация перед запуском {component_name} завершена успешно")
        return True
    else:
        logger.error(f"❌ Синхронизация перед запуском {component_name} завершена с ошибками")
        return False


def force_sync() -> SyncResult:
    """Принудительная синхронизация состояния"""
    logger.info("🔄 Принудительная синхронизация состояния...")
    return unified_sync.synchronize_state()


if __name__ == "__main__":
    """Утилита синхронизации состояния"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        unified_sync.print_status()
    elif len(sys.argv) > 1 and sys.argv[1] == "--force":
        print("🔄 Запуск принудительной синхронизации...")
        result = force_sync()
        print(f"\n✅ Синхронизация завершена:")
        print(f"   📊 Проверено: {result.total_checked} ордеров")
        print(f"   🔄 Изменений: {result.actions_taken}")
        print(f"   ✅ Успешно: {result.successful_actions}")
        print(f"   ❌ Ошибок: {result.failed_actions}")
        
        if result.errors:
            print(f"\n❌ Ошибки:")
            for error in result.errors:
                print(f"   • {error}")
        
        if result.warnings:
            print(f"\n⚠️ Предупреждения:")
            for warning in result.warnings:
                print(f"   • {warning}")
    else:
        print("🔄 Unified Synchronization System")
        print("=================================")
        print("Использование:")
        print("  python unified_sync.py --status   # показать статус")
        print("  python unified_sync.py --force    # принудительная синхронизация")
        print("")
        
        # Показываем статус по умолчанию
        unified_sync.print_status()
        
        # Предлагаем синхронизацию если нужно
        status = unified_sync.get_sync_status()
        if status.get('needs_sync', True):
            print("\n⚠️ Требуется синхронизация состояния")
            user_input = input("🔄 Выполнить синхронизацию сейчас? (y/N): ")
            if user_input.lower() in ['y', 'yes', 'да', 'д']:
                result = force_sync()
                print(f"\n✅ Синхронизация завершена: {result.successful_actions}/{result.actions_taken} успешно")


# Финальная инициализация интерфейсов совместимости
# (После определения всех классов)
if 'orders_sync' not in globals():
    orders_sync = OrdersSyncInterface(unified_sync)
if 'state_recovery' not in globals():  
    state_recovery = StateRecoveryInterface(unified_sync)
