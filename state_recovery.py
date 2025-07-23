#!/usr/bin/env python3
"""
State Recovery Manager - Система восстановления состояния
========================================================

Модуль для восстановления полного состояния торговой системы при перезапуске:
- Синхронизация с Orders Watchdog
- Восстановление открытых позиций с биржи
- Проверка соответствия локального и биржевого состояния
- Автоматическое исправление рассинхронизации
- Блокировка дублирующих ордеров

Author: HEDGER
Version: 1.0 - State Recovery System
"""

import json
import time
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


@dataclass
class ActivePosition:
    """Активная позиция в системе"""
    symbol: str
    side: str  # LONG/SHORT
    size: float
    entry_price: float
    unrealized_pnl: float
    margin_type: str
    isolated_wallet: float
    has_sl: bool = False
    has_tp: bool = False
    sl_order_id: Optional[str] = None
    tp_order_id: Optional[str] = None
    main_order_id: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None


@dataclass
class SystemState:
    """Состояние торговой системы"""
    timestamp: datetime
    active_positions: Dict[str, ActivePosition]
    watchdog_orders: Dict[str, Dict[str, Any]]
    exchange_positions: Dict[str, Dict[str, Any]]
    exchange_orders: Dict[str, List[Dict[str, Any]]]
    synchronization_issues: List[str]
    recovery_actions: List[str]
    is_synchronized: bool = True


class StateRecoveryManager:
    """Менеджер восстановления состояния системы"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.state_file = Path('system_state.json')
        self.watchdog_state_file = Path('orders_watchdog_state.json')
        self.blocked_symbols: Set[str] = set()
        
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
    
    def recover_system_state(self) -> SystemState:
        """
        Восстанавливает полное состояние системы
        
        Returns:
            SystemState с полной информацией о состоянии
        """
        logger.info("🔄 Начинаем восстановление состояния системы...")
        
        # Инициализируем состояние
        system_state = SystemState(
            timestamp=datetime.now(),
            active_positions={},
            watchdog_orders={},
            exchange_positions={},
            exchange_orders={},
            synchronization_issues=[],
            recovery_actions=[]
        )
        
        try:
            # 1. Загружаем состояние Orders Watchdog
            logger.info("📂 Загружаем состояние Orders Watchdog...")
            system_state.watchdog_orders = self._load_watchdog_state()
            logger.info(f"✅ Загружено {len(system_state.watchdog_orders)} отслеживаемых ордеров")
            
            # 2. Получаем данные с биржи
            if self.client:
                logger.info("🌐 Получаем данные с биржи...")
                system_state.exchange_positions = self._get_exchange_positions()
                system_state.exchange_orders = self._get_exchange_orders()
                logger.info(f"✅ С биржи: {len(system_state.exchange_positions)} позиций, {len(system_state.exchange_orders)} символов с ордерами")
            else:
                system_state.synchronization_issues.append("❌ Binance API недоступен")
            
            # 3. Анализируем и сопоставляем данные
            logger.info("🔍 Анализ состояния и поиск расхождений...")
            system_state.active_positions = self._analyze_and_merge_positions(system_state)
            
            # 4. Проводим проверки целостности
            self._validate_state_integrity(system_state)
            
            # 5. Применяем автоматические исправления
            self._apply_auto_corrections(system_state)
            
            # 6. Сохраняем восстановленное состояние
            self._save_system_state(system_state)
            
            logger.info("✅ Восстановление состояния завершено")
            return system_state
            
        except Exception as e:
            logger.error(f"❌ Ошибка восстановления состояния: {e}")
            system_state.synchronization_issues.append(f"Критическая ошибка: {e}")
            system_state.is_synchronized = False
            return system_state
    
    def _load_watchdog_state(self) -> Dict[str, Dict[str, Any]]:
        """Загружает состояние Orders Watchdog"""
        watchdog_orders = {}
        
        try:
            if self.watchdog_state_file.exists():
                with open(self.watchdog_state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for order_data in data.get('watched_orders', []):
                    order_id = order_data.get('order_id')
                    if order_id:
                        watchdog_orders[order_id] = order_data
                        
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки состояния watchdog: {e}")
        
        return watchdog_orders
    
    def _get_exchange_positions(self) -> Dict[str, Dict[str, Any]]:
        """Получает открытые позиции с биржи"""
        positions = {}
        
        if not self.client:
            return positions
        
        try:
            positions_data = self.client.futures_position_information()
            
            for pos in positions_data:
                position_amt = float(pos.get('positionAmt', 0))
                if position_amt != 0:  # Только открытые позиции
                    symbol = pos['symbol']
                    positions[symbol] = {
                        'symbol': symbol,
                        'side': 'LONG' if position_amt > 0 else 'SHORT',
                        'size': abs(position_amt),
                        'entry_price': float(pos.get('entryPrice', 0)),
                        'unrealized_pnl': float(pos.get('unrealizedPnl', 0)),
                        'margin_type': pos.get('marginType', 'crossed').upper(),
                        'isolated_wallet': float(pos.get('isolatedWallet', 0)),
                        'percentage': float(pos.get('percentage', 0))
                    }
                    
        except Exception as e:
            logger.error(f"❌ Ошибка получения позиций с биржи: {e}")
        
        return positions
    
    def _get_exchange_orders(self) -> Dict[str, List[Dict[str, Any]]]:
        """Получает открытые ордера с биржи"""
        orders_by_symbol = {}
        
        if not self.client:
            return orders_by_symbol
        
        try:
            orders_data = self.client.futures_get_open_orders()
            
            for order in orders_data:
                symbol = order['symbol']
                if symbol not in orders_by_symbol:
                    orders_by_symbol[symbol] = []
                
                orders_by_symbol[symbol].append({
                    'order_id': str(order['orderId']),
                    'symbol': symbol,
                    'type': order['type'],
                    'side': order['side'],
                    'amount': float(order['origQty']),
                    'price': float(order['price']) if order.get('price') else None,
                    'stop_price': float(order['stopPrice']) if order.get('stopPrice') else None,
                    'status': order['status'],
                    'time': order['time'],
                    'update_time': order['updateTime']
                })
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения ордеров с биржи: {e}")
        
        return orders_by_symbol
    
    def _analyze_and_merge_positions(self, system_state: SystemState) -> Dict[str, ActivePosition]:
        """Анализирует и объединяет данные в единое состояние"""
        active_positions = {}
        
        # Сначала обрабатываем позиции с биржи (они самые точные)
        for symbol, exchange_pos in system_state.exchange_positions.items():
            position = ActivePosition(
                symbol=symbol,
                side=exchange_pos['side'],
                size=exchange_pos['size'],
                entry_price=exchange_pos['entry_price'],
                unrealized_pnl=exchange_pos['unrealized_pnl'],
                margin_type=exchange_pos['margin_type'],
                isolated_wallet=exchange_pos['isolated_wallet'],
                last_updated=datetime.now()
            )
            
            # Ищем связанные ордера в watchdog
            symbol_orders = [order for order in system_state.watchdog_orders.values() 
                           if order.get('symbol') == symbol]
            
            for order in symbol_orders:
                if order.get('sl_order_id'):
                    position.has_sl = True
                    position.sl_order_id = order.get('sl_order_id')
                if order.get('tp_order_id'):
                    position.has_tp = True
                    position.tp_order_id = order.get('tp_order_id')
                if not position.main_order_id:
                    position.main_order_id = order.get('order_id')
                    if order.get('created_at'):
                        try:
                            position.created_at = datetime.fromisoformat(order['created_at'])
                        except:
                            pass
            
            active_positions[symbol] = position
        
        # Проверяем orphaned ордера в watchdog (есть в watchdog, но нет позиции)
        watchdog_symbols = set(order.get('symbol') for order in system_state.watchdog_orders.values())
        exchange_symbols = set(system_state.exchange_positions.keys())
        orphaned_symbols = watchdog_symbols - exchange_symbols
        
        if orphaned_symbols:
            system_state.synchronization_issues.append(
                f"⚠️ Найдены ордера без позиций: {', '.join(orphaned_symbols)}"
            )
        
        # Проверяем untracked позиции (есть позиция, но нет в watchdog)
        untracked_symbols = exchange_symbols - watchdog_symbols
        if untracked_symbols:
            system_state.synchronization_issues.append(
                f"⚠️ Найдены позиции без отслеживания: {', '.join(untracked_symbols)}"
            )
            
            # Добавляем их как активные позиции без SL/TP
            for symbol in untracked_symbols:
                if symbol in system_state.exchange_positions:
                    pos_data = system_state.exchange_positions[symbol]
                    if symbol not in active_positions:  # На всякий случай
                        active_positions[symbol] = ActivePosition(
                            symbol=symbol,
                            side=pos_data['side'],
                            size=pos_data['size'],
                            entry_price=pos_data['entry_price'],
                            unrealized_pnl=pos_data['unrealized_pnl'],
                            margin_type=pos_data['margin_type'],
                            isolated_wallet=pos_data['isolated_wallet'],
                            has_sl=False,
                            has_tp=False,
                            last_updated=datetime.now()
                        )
        
        logger.info(f"🔍 Найдено {len(active_positions)} активных позиций")
        if system_state.synchronization_issues:
            logger.warning(f"⚠️ Обнаружено {len(system_state.synchronization_issues)} проблем синхронизации")
        
        return active_positions
    
    def _validate_state_integrity(self, system_state: SystemState) -> None:
        """Проверяет целостность состояния"""
        for symbol, position in system_state.active_positions.items():
            # Проверяем наличие SL/TP ордеров на бирже
            if position.has_sl and position.sl_order_id:
                if not self._order_exists_on_exchange(symbol, position.sl_order_id, system_state.exchange_orders):
                    system_state.synchronization_issues.append(
                        f"⚠️ {symbol}: SL ордер {position.sl_order_id} не найден на бирже"
                    )
                    position.has_sl = False
                    position.sl_order_id = None
            
            if position.has_tp and position.tp_order_id:
                if not self._order_exists_on_exchange(symbol, position.tp_order_id, system_state.exchange_orders):
                    system_state.synchronization_issues.append(
                        f"⚠️ {symbol}: TP ордер {position.tp_order_id} не найден на бирже"
                    )
                    position.has_tp = False
                    position.tp_order_id = None
            
            # Проверяем, что позиция без SL/TP защищена
            if not position.has_sl and not position.has_tp:
                system_state.synchronization_issues.append(
                    f"⚠️ {symbol}: Позиция не защищена SL/TP ордерами"
                )
    
    def _order_exists_on_exchange(self, symbol: str, order_id: str, exchange_orders: Dict[str, List[Dict]]) -> bool:
        """Проверяет существование ордера на бирже"""
        symbol_orders = exchange_orders.get(symbol, [])
        return any(order['order_id'] == order_id for order in symbol_orders)
    
    def _apply_auto_corrections(self, system_state: SystemState) -> None:
        """Применяет автоматические исправления"""
        # Здесь можно добавить логику автоисправления
        # Например, создание отсутствующих SL/TP ордеров
        pass
    
    def _save_system_state(self, system_state: SystemState) -> None:
        """Сохраняет состояние системы в файл"""
        try:
            # Преобразуем в сериализуемый формат
            state_dict = {
                'timestamp': system_state.timestamp.isoformat(),
                'active_positions': {
                    symbol: asdict(position) for symbol, position in system_state.active_positions.items()
                },
                'synchronization_issues': system_state.synchronization_issues,
                'recovery_actions': system_state.recovery_actions,
                'is_synchronized': system_state.is_synchronized,
                'total_positions': len(system_state.active_positions),
                'watchdog_orders_count': len(system_state.watchdog_orders),
                'exchange_positions_count': len(system_state.exchange_positions)
            }
            
            # Конвертируем datetime объекты
            for symbol, pos_data in state_dict['active_positions'].items():
                if pos_data.get('created_at'):
                    pos_data['created_at'] = pos_data['created_at'].isoformat() if isinstance(pos_data['created_at'], datetime) else pos_data['created_at']
                if pos_data.get('last_updated'):
                    pos_data['last_updated'] = pos_data['last_updated'].isoformat() if isinstance(pos_data['last_updated'], datetime) else pos_data['last_updated']
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Состояние системы сохранено в {self.state_file}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения состояния: {e}")
    
    def load_system_state(self) -> Optional[SystemState]:
        """Загружает сохраненное состояние системы"""
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Восстанавливаем позиции
            active_positions = {}
            for symbol, pos_data in data.get('active_positions', {}).items():
                # Восстанавливаем datetime объекты
                if pos_data.get('created_at'):
                    try:
                        pos_data['created_at'] = datetime.fromisoformat(pos_data['created_at'])
                    except:
                        pos_data['created_at'] = None
                
                if pos_data.get('last_updated'):
                    try:
                        pos_data['last_updated'] = datetime.fromisoformat(pos_data['last_updated'])
                    except:
                        pos_data['last_updated'] = None
                
                active_positions[symbol] = ActivePosition(**pos_data)
            
            system_state = SystemState(
                timestamp=datetime.fromisoformat(data['timestamp']),
                active_positions=active_positions,
                watchdog_orders={},
                exchange_positions={},
                exchange_orders={},
                synchronization_issues=data.get('synchronization_issues', []),
                recovery_actions=data.get('recovery_actions', []),
                is_synchronized=data.get('is_synchronized', True)
            )
            
            logger.info(f"📂 Загружено состояние системы: {len(active_positions)} позиций")
            return system_state
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки состояния: {e}")
            return None
    
    def _get_watchdog_symbols(self) -> Set[str]:
        """Получает список символов под наблюдением Orders Watchdog"""
        try:
            if not self.watchdog_state_file.exists():
                return set()
            
            with open(self.watchdog_state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                watched_orders = data.get('watched_orders', [])
                
                # Извлекаем символы из списка наблюдаемых ордеров
                symbols = set()
                for order in watched_orders:
                    if isinstance(order, dict) and 'symbol' in order:
                        symbols.add(order['symbol'])
                
                return symbols
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки состояния Watchdog: {e}")
            return set()
    
    def is_symbol_blocked_for_new_orders(self, symbol: str) -> Tuple[bool, str]:
        """
        Проверяет, заблокирован ли символ для новых ордеров
        
        Returns:
            Tuple[is_blocked: bool, reason: str]
        """
        # 1. ПРОСТАЯ ПРОВЕРКА: Orders Watchdog
        watchdog_symbols = self._get_watchdog_symbols()
        if symbol in watchdog_symbols:
            return True, f"Символ под наблюдением Orders Watchdog (ожидает исполнения)"
        
        # 2. ПРОВЕРКА: Открытые ордера на бирже
        if self.client:
            try:
                open_orders = self.client.futures_get_open_orders(symbol=symbol)
                if open_orders:
                    order_types = [order['type'] for order in open_orders]
                    return True, f"Есть открытые ордера на бирже: {', '.join(set(order_types))}"
            except Exception as e:
                logger.warning(f"⚠️ Ошибка проверки открытых ордеров для {symbol}: {e}")
        
        # 3. Загружаем текущее состояние
        current_state = self.load_system_state()
        if not current_state:
            # Если нет сохраненного состояния, делаем быстрое восстановление
            current_state = self.recover_system_state()
        
        # 4. Проверяем наличие активной позиции
        if symbol in current_state.active_positions:
            position = current_state.active_positions[symbol]
            return True, f"Активная позиция {position.side} {position.size} (PnL: {position.unrealized_pnl:+.2f})"
        
        # 5. Проверяем кэш заблокированных символов
        if symbol in self.blocked_symbols:
            return True, "Символ временно заблокирован"
        
        return False, "Символ доступен для торговли"
    
    def print_recovery_report(self, system_state: SystemState) -> None:
        """Выводит отчет о восстановлении состояния"""
        print("=" * 80)
        print("🔄 ОТЧЕТ ВОССТАНОВЛЕНИЯ СОСТОЯНИЯ СИСТЕМЫ")
        print("=" * 80)
        
        print(f"🕐 Время восстановления: {system_state.timestamp.strftime('%H:%M:%S')}")
        print(f"📊 Статус синхронизации: {'✅ СИНХРОНИЗИРОВАНА' if system_state.is_synchronized else '❌ РАССИНХРОНИЗИРОВАНА'}")
        print(f"📍 Активных позиций: {len(system_state.active_positions)}")
        print(f"🔍 Проблем обнаружено: {len(system_state.synchronization_issues)}")
        
        # Показываем активные позиции
        if system_state.active_positions:
            print(f"\n📊 АКТИВНЫЕ ПОЗИЦИИ ({len(system_state.active_positions)}):")
            print("-" * 60)
            
            for symbol, position in system_state.active_positions.items():
                sl_status = "✅ SL" if position.has_sl else "❌ NO SL"
                tp_status = "✅ TP" if position.has_tp else "❌ NO TP"
                pnl_str = f"{position.unrealized_pnl:+.2f}" if position.unrealized_pnl != 0 else "0.00"
                
                print(f"• {symbol}: {position.side} {position.size} @ {position.entry_price} "
                      f"(PnL: {pnl_str}) | {sl_status} | {tp_status}")
        
        # Показываем проблемы
        if system_state.synchronization_issues:
            print(f"\n⚠️ ПРОБЛЕМЫ СИНХРОНИЗАЦИИ ({len(system_state.synchronization_issues)}):")
            print("-" * 60)
            for issue in system_state.synchronization_issues:
                print(f"  {issue}")
        
        # Показываем действия восстановления
        if system_state.recovery_actions:
            print(f"\n🔧 ВЫПОЛНЕННЫЕ ДЕЙСТВИЯ ({len(system_state.recovery_actions)}):")
            print("-" * 60)
            for action in system_state.recovery_actions:
                print(f"  {action}")
        
        print("=" * 80)


# Глобальный экземпляр менеджера восстановления
state_recovery = StateRecoveryManager()


def recover_system_state() -> SystemState:
    """Удобная функция для восстановления состояния"""
    return state_recovery.recover_system_state()


def is_symbol_available_for_trading(symbol: str) -> Tuple[bool, str]:
    """Проверяет доступность символа для торговли"""
    is_blocked, reason = state_recovery.is_symbol_blocked_for_new_orders(symbol)
    return not is_blocked, reason


if __name__ == "__main__":
    """Тестирование системы восстановления"""
    print("🔄 Тестирование State Recovery Manager...")
    
    manager = StateRecoveryManager()
    system_state = manager.recover_system_state()
    manager.print_recovery_report(system_state)
    
    # Тестируем проверку символов
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    print(f"\n🧪 ТЕСТ ДОСТУПНОСТИ СИМВОЛОВ:")
    print("-" * 40)
    for symbol in test_symbols:
        is_available, reason = is_symbol_available_for_trading(symbol)
        status = "✅ ДОСТУПЕН" if is_available else "❌ ЗАБЛОКИРОВАН"
        print(f"• {symbol}: {status} - {reason}")
