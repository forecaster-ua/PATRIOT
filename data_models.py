"""
Data Classes - Структуры данных для рефакторинга PATRIOT
========================================================

Определяет классы данных для передачи информации между модулями
в новой архитектуре без binance_factory.

Author: HEDGER
Version: 1.0 - Рефакторинг
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class SignalDirection(Enum):
    """Направление торгового сигнала"""
    LONG = "LONG"
    SHORT = "SHORT"


class OrderStatus(Enum):
    """Статус ордера"""
    PENDING = "PENDING"          # Ожидает отправки
    SENT = "SENT"               # Отправлен на биржу
    FILLED = "FILLED"           # Исполнен
    CANCELLED = "CANCELLED"     # Отменен
    FAILED = "FAILED"           # Ошибка исполнения


class PositionStatus(Enum):
    """Статус позиции"""
    ACTIVE = "ACTIVE"           # Активная позиция
    CLOSED_PROFIT = "CLOSED_PROFIT"    # Закрыта по Take Profit
    CLOSED_LOSS = "CLOSED_LOSS"        # Закрыта по Stop Loss
    CLOSED_MANUAL = "CLOSED_MANUAL"    # Закрыта вручную


@dataclass
class OrderData:
    """
    Структура данных для передачи ордера между модулями
    
    Используется для передачи данных от order_generator к trading_engine
    """
    # Основная информация
    symbol: str                          # "BTCUSDT"
    signal_direction: SignalDirection    # LONG | SHORT
    
    # Цены
    entry_price: float                   # Цена входа
    current_price: float                 # Текущая цена
    stop_loss: float                     # Стоп-лосс
    take_profit: float                   # Тейк-профит
    
    # Метаданные сигнала
    confidence: float                    # 0.0 - 1.0
    timeframes: List[str]                # ["1H", "4H"]
    timestamp: datetime
    
    # Идентификация
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = "ticker_monitor"       # "ticker_monitor" | "enhanced_processor"
    
    # Торговые параметры
    risk_percent: float = 5.0            # % от капитала
    position_size: Optional[float] = None # Размер позиции (рассчитывается в trading_engine)
    
    # Дополнительная информация
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь для передачи"""
        return {
            'symbol': self.symbol,
            'signal_direction': self.signal_direction.value,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'confidence': self.confidence,
            'timeframes': self.timeframes,
            'timestamp': self.timestamp.isoformat(),
            'signal_id': self.signal_id,
            'source': self.source,
            'risk_percent': self.risk_percent,
            'position_size': self.position_size,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_signal_data(cls, signal_data: Dict[str, Any]) -> "OrderData":
        """
        Создает OrderData из существующего формата signal_data
        
        Для совместимости с существующим кодом
        """
        return cls(
            symbol=signal_data['ticker'],
            signal_direction=SignalDirection(signal_data['signal']),
            entry_price=signal_data['entry_price'],
            current_price=signal_data.get('current_price', signal_data['entry_price']),
            stop_loss=signal_data['stop_loss'],
            take_profit=signal_data['take_profit'],
            confidence=signal_data.get('confidence', 0.0),
            timeframes=signal_data.get('timeframes', []),
            timestamp=datetime.fromisoformat(signal_data['timestamp']) if isinstance(signal_data['timestamp'], str) else signal_data['timestamp'],
            source=signal_data.get('source', 'ticker_monitor'),
            risk_percent=signal_data.get('risk_percent', 5.0),
            metadata=signal_data.get('metadata', {})
        )


@dataclass
class OrderResult:
    """
    Результат выставления ордера от trading_engine
    """
    success: bool
    order_id: Optional[str] = None
    error_message: Optional[str] = None
    binance_order_data: Optional[Dict[str, Any]] = None
    position_data: Optional["PositionData"] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь"""
        return {
            'success': self.success,
            'order_id': self.order_id,
            'error_message': self.error_message,
            'binance_order_data': self.binance_order_data,
            'position_data': self.position_data.to_dict() if self.position_data else None
        }


@dataclass
class PositionData:
    """
    Данные о торговой позиции для мониторинга
    """
    # Основная информация
    position_id: str                     # Уникальный ID позиции
    symbol: str                          # "BTCUSDT"
    direction: SignalDirection           # LONG | SHORT
    
    # Ордера
    entry_order_id: str                  # ID входного ордера
    
    # Цены и размеры
    entry_price: float                   # Цена входа
    position_size: float                 # Размер позиции
    stop_price: float                    # Цена стоп-лосса
    take_price: float                    # Цена тейк-профита
    
    # Исходный сигнал
    original_signal_id: str              # ID исходного сигнала
    original_order_data: OrderData       # Исходные данные ордера
    
    # Поля с default values
    stop_order_id: Optional[str] = None  # ID стоп-лосс ордера
    take_order_id: Optional[str] = None  # ID тейк-профит ордера
    
    # Статус и время
    status: PositionStatus = PositionStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None
    
    # P&L
    realized_pnl: Optional[float] = None # Реализованная прибыль/убыток
    close_price: Optional[float] = None  # Цена закрытия
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь"""
        return {
            'position_id': self.position_id,
            'symbol': self.symbol,
            'direction': self.direction.value,
            'entry_order_id': self.entry_order_id,
            'stop_order_id': self.stop_order_id,
            'take_order_id': self.take_order_id,
            'entry_price': self.entry_price,
            'position_size': self.position_size,
            'stop_price': self.stop_price,
            'take_price': self.take_price,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'original_signal_id': self.original_signal_id,
            'realized_pnl': self.realized_pnl,
            'close_price': self.close_price
        }


@dataclass
class TradingEngineConfig:
    """
    Конфигурация для торгового движка
    """
    testnet: bool = True                 # Использовать testnet
    risk_percent: float = 5.0            # % от капитала на сделку
    max_positions: int = 5               # Максимальное количество позиций
    enable_stop_loss: bool = True        # Включить стоп-лосс
    enable_take_profit: bool = True      # Включить тейк-профит
    position_monitoring: bool = True     # Включить мониторинг позиций
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь"""
        return {
            'testnet': self.testnet,
            'risk_percent': self.risk_percent,
            'max_positions': self.max_positions,
            'enable_stop_loss': self.enable_stop_loss,
            'enable_take_profit': self.enable_take_profit,
            'position_monitoring': self.position_monitoring
        }


# Utility functions для конвертации данных

def convert_legacy_signal_to_order_data(signal_data: Dict[str, Any]) -> OrderData:
    """
    Конвертирует старый формат signal_data в новый OrderData
    
    Для обеспечения совместимости с существующим кодом
    """
    return OrderData.from_signal_data(signal_data)


def validate_order_data(order_data: OrderData) -> List[str]:
    """
    Валидирует данные ордера и возвращает список ошибок
    
    Returns:
        List[str]: Список ошибок валидации (пустой если всё ОК)
    """
    errors = []
    
    # Проверка обязательных полей
    if not order_data.symbol:
        errors.append("Symbol is required")
    
    if order_data.entry_price <= 0:
        errors.append("Entry price must be positive")
    
    if order_data.stop_loss <= 0:
        errors.append("Stop loss must be positive")
    
    if order_data.take_profit <= 0:
        errors.append("Take profit must be positive")
    
    # Логическая проверка цен
    if order_data.signal_direction == SignalDirection.LONG:
        if order_data.stop_loss >= order_data.entry_price:
            errors.append("For LONG: stop loss must be below entry price")
        if order_data.take_profit <= order_data.entry_price:
            errors.append("For LONG: take profit must be above entry price")
    
    elif order_data.signal_direction == SignalDirection.SHORT:
        if order_data.stop_loss <= order_data.entry_price:
            errors.append("For SHORT: stop loss must be above entry price")
        if order_data.take_profit >= order_data.entry_price:
            errors.append("For SHORT: take profit must be below entry price")
    
    # Проверка confidence
    if not (0.0 <= order_data.confidence <= 1.0):
        errors.append("Confidence must be between 0.0 and 1.0")
    
    # Проверка risk_percent
    if not (0.1 <= order_data.risk_percent <= 50.0):
        errors.append("Risk percent must be between 0.1 and 50.0")
    
    return errors


# Примеры использования
if __name__ == "__main__":
    # Пример создания OrderData
    order = OrderData(
        symbol="BTCUSDT",
        signal_direction=SignalDirection.LONG,
        entry_price=50000.0,
        current_price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
        confidence=0.85,
        timeframes=["1H", "4H"],
        timestamp=datetime.now(),
        risk_percent=5.0
    )
    
    print("📊 OrderData example:")
    print(f"Symbol: {order.symbol}")
    print(f"Direction: {order.signal_direction.value}")
    print(f"Entry: {order.entry_price}")
    print(f"Stop: {order.stop_loss}")
    print(f"Take: {order.take_profit}")
    print(f"Signal ID: {order.signal_id}")
    
    # Валидация
    errors = validate_order_data(order)
    if errors:
        print(f"❌ Validation errors: {errors}")
    else:
        print("✅ Order data is valid")
    
    # Конвертация в словарь
    order_dict = order.to_dict()
    print(f"📦 As dict: {order_dict}")
