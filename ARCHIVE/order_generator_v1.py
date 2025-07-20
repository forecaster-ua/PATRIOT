"""
Order Generator - Генерация ордеров и уведомлений
===============================================

Модуль для создания торговых ордеров и отправки уведомлений на основе
проанализированных торговых сигналов.

Основные функции:
1. Создание уведомлений в Telegram
2. Генерация шаблонов ордеров для Binance  
3. Сохранение данных ордеров (опционально)
4. Валидация параметров ордеров

Author: HEDGER
Version: 1.0
"""

import uuid
from typing import Dict, List, Set, Optional
from datetime import datetime, timezone

# Local imports
from telegram_bot import telegram_bot
from config import TIMEFRAMES
from utils import logger

try:
    from database import db
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logger.warning("Database module not available - order saving disabled")

# Глобальная переменная для binance_factory
binance_factory_instance = None

def set_binance_factory(factory_instance):
    """Устанавливает экземпляр binance_factory для создания ордеров"""
    global binance_factory_instance
    binance_factory_instance = factory_instance
    logger.info("Binance Factory instance set for order processing")


class OrderGenerator:
    """
    Генератор торговых ордеров и уведомлений
    
    Основные функции:
    1. Создание уведомлений для Telegram
    2. Генерация шаблонов ордеров для бирж
    3. Расчет оптимальных параметров ордера
    4. Сохранение истории ордеров
    """
    
    def __init__(self):
        """Инициализация генератора ордеров"""
        # Порядок таймфреймов от меньшего к большему для выбора стоп-лосса
        self.timeframe_hierarchy = {
            '1m': 1, '5m': 2, '15m': 3, '30m': 4,
            '1h': 5, '2h': 6, '4h': 7, '6h': 8, '12h': 9,
            '1d': 10, '3d': 11, '1w': 12
        }
        logger.info("OrderGenerator initialized")

    def create_telegram_alert(self, signal_data: Dict) -> bool:
        """
        Создает и отправляет уведомление в Telegram
        
        Args:
            signal_data: Консолидированные данные сигнала
            
        Returns:
            bool: True если уведомление отправлено успешно
        """
        try:
            logger.info(f"📱 Creating Telegram alert for {signal_data['ticker']}")
            
            # Логируем детальную информацию о сигнале
            self._log_signal_details(signal_data)
            
            # Формируем сообщение для Telegram
            message = self._format_telegram_message(signal_data)
            
            # Отправляем через telegram_bot
            telegram_data = {
                'pair': signal_data['ticker'],
                'timeframe': signal_data['timeframes_str'],
                'signal': signal_data['signal'],
                'current_price': signal_data['current_price'],
                'entry_price': signal_data['entry_price'],
                'stop_loss': signal_data['stop_loss'],
                'take_profit': signal_data['take_profit'],
                'confidence': signal_data['confidence'],
                'dominance_change_percent': signal_data.get('dominance_change_percent', 0),
                'timestamp': signal_data['timestamp']
            }
            
            telegram_bot.send_signal(telegram_data)
            logger.info(f"✅ Telegram alert sent successfully for {signal_data['ticker']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram alert for {signal_data['ticker']}: {str(e)}", exc_info=True)
            return False

    def create_binance_template(self, signal_data: Dict) -> Optional[Dict]:
        """
        Создает шаблон ордера для Binance
        
        Args:
            signal_data: Консолидированные данные сигнала
            
        Returns:
            Optional[Dict]: Шаблон ордера или None при ошибке
        """
        try:
            logger.info(f"📋 Creating Binance order template for {signal_data['ticker']}")
            
            # Выбираем стоп-лосс с большего таймфрейма
            optimal_stop_loss = self._select_stop_loss_from_larger_timeframe(signal_data)
            
            # Генерируем уникальный ID для ордера
            order_id = str(uuid.uuid4())
            
            # Рассчитываем размер позиции (пока фиксированный)
            position_size = self._calculate_position_size(signal_data)
            
            # Создаем шаблон ордера
            order_template = {
                'order_id': order_id,
                'exchange': 'binance_futures',  # Указываем фьючерсы
                'symbol': signal_data['ticker'],
                'side': 'BUY' if signal_data['signal'] == 'LONG' else 'SELL',
                'type': 'MARKET',  # Для фьючерсов используем MARKET ордера
                'quantity': position_size,
                'price': signal_data['entry_price'],
                'stop_loss': optimal_stop_loss,
                'take_profit': signal_data['take_profit'],
                'time_in_force': 'GTC',  # Good Till Cancelled
                'status': 'PENDING',
                'signal_data': {
                    'matched_timeframes': signal_data['matched_timeframes'],
                    'confidence': signal_data['confidence'],
                    'timestamp': signal_data['timestamp']
                },
                'created_at': datetime.now(timezone.utc).isoformat(),
                'risk_reward_ratio': self._calculate_risk_reward_ratio(
                    signal_data['entry_price'], 
                    optimal_stop_loss, 
                    signal_data['take_profit'],
                    signal_data['signal']
                ),
                'leverage': 1  # Можно добавить настройку плеча
            }
            
            # Валидируем параметры ордера
            if self._validate_order_params(order_template):
                logger.info(f"✅ Binance order template created: {order_id}")
                self._log_order_details(order_template)
                
                # Сохраняем в базу данных (если доступна)
                if DATABASE_AVAILABLE:
                    self._save_order_to_database(order_template)
                    
                return order_template
            else:
                logger.error(f"❌ Order validation failed for {signal_data['ticker']}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to create Binance template for {signal_data['ticker']}: {str(e)}", exc_info=True)
            return None

    def _select_stop_loss_from_larger_timeframe(self, signal_data: Dict) -> float:
        """
        Выбирает стоп-лосс с большего таймфрейма из совпадающих
        
        Args:
            signal_data: Данные сигнала с информацией о таймфреймах
            
        Returns:
            float: Оптимальный стоп-лосс
        """
        matched_timeframes = signal_data['matched_timeframes']
        raw_signals = signal_data['raw_signals']
        
        # Находим самый большой таймфрейм из совпадающих
        largest_tf = None
        largest_tf_rank = 0
        
        for tf in matched_timeframes:
            tf_rank = self.timeframe_hierarchy.get(tf, 0)
            if tf_rank > largest_tf_rank:
                largest_tf_rank = tf_rank
                largest_tf = tf
        
        if largest_tf and largest_tf in raw_signals:
            selected_stop = raw_signals[largest_tf]['stop_loss']
            logger.info(
                f"🎯 Stop-loss selected from larger timeframe {largest_tf}: {selected_stop:.6f}"
            )
            
            # Логируем все доступные стоп-лоссы для сравнения
            logger.info("📊 Stop-loss comparison across timeframes:")
            for tf in sorted(matched_timeframes):
                if tf in raw_signals:
                    stop_value = raw_signals[tf]['stop_loss']
                    is_selected = tf == largest_tf
                    status = "🎯 SELECTED" if is_selected else "  "
                    logger.info(f"  {status} {tf}: {stop_value:.6f}")
            
            return selected_stop
        else:
            # Fallback к усредненному значению
            logger.warning(f"⚠️ Could not determine larger timeframe, using averaged stop-loss")
            return signal_data['stop_loss']

    def _calculate_position_size(self, signal_data: Dict) -> float:
        """
        Рассчитывает размер позиции (базовая логика)
        
        Args:
            signal_data: Данные сигнала
            
        Returns:
            float: Размер позиции
        """
        # Пока используем фиксированный размер
        # В будущем можно добавить расчет на основе риска
        base_position_size = 0.01
        
        # Можно учитывать confidence для корректировки размера
        confidence_multiplier = min(signal_data['confidence'] * 1.5, 2.0)
        
        position_size = base_position_size * confidence_multiplier
        
        logger.debug(
            f"Position size calculation: base={base_position_size}, "
            f"confidence={signal_data['confidence']:.3f}, "
            f"multiplier={confidence_multiplier:.3f}, "
            f"final={position_size:.6f}"
        )
        
        return round(position_size, 6)

    def _calculate_risk_reward_ratio(self, entry_price: float, stop_loss: float, 
                                   take_profit: float, signal_direction: str) -> float:
        """
        Рассчитывает соотношение риск/прибыль
        
        Args:
            entry_price: Цена входа
            stop_loss: Стоп-лосс
            take_profit: Тейк-профит
            signal_direction: Направление сигнала (LONG/SHORT)
            
        Returns:
            float: Соотношение риск/прибыль
        """
        try:
            if signal_direction == 'LONG':
                risk = abs(entry_price - stop_loss)
                reward = abs(take_profit - entry_price)
            else:  # SHORT
                risk = abs(stop_loss - entry_price)
                reward = abs(entry_price - take_profit)
            
            if risk > 0:
                ratio = reward / risk
                logger.debug(f"Risk/Reward calculation: Risk={risk:.6f}, Reward={reward:.6f}, Ratio={ratio:.2f}")
                return round(ratio, 2)
            else:
                logger.warning("Risk is zero - invalid stop loss configuration")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculating risk/reward ratio: {str(e)}")
            return 0.0

    def _validate_order_params(self, order_template: Dict) -> bool:
        """
        Валидирует параметры ордера
        
        Args:
            order_template: Шаблон ордера для проверки
            
        Returns:
            bool: True если параметры корректны
        """
        required_fields = ['symbol', 'side', 'quantity', 'price', 'stop_loss', 'take_profit']
        
        # Проверяем наличие обязательных полей
        for field in required_fields:
            if field not in order_template or order_template[field] is None:
                logger.error(f"Missing required field in order: {field}")
                return False
        
        # Проверяем положительные значения
        numeric_fields = ['quantity', 'price', 'stop_loss', 'take_profit']
        for field in numeric_fields:
            if order_template[field] <= 0:
                logger.error(f"Invalid value for {field}: {order_template[field]}")
                return False
        
        # Проверяем корректность направления
        if order_template['side'] not in ['BUY', 'SELL']:
            logger.error(f"Invalid side: {order_template['side']}")
            return False
        
        # Проверяем логику стоп-лосса и тейк-профита
        entry = order_template['price']
        stop = order_template['stop_loss']
        target = order_template['take_profit']
        
        if order_template['side'] == 'BUY':  # LONG
            if stop >= entry:
                logger.error(f"Invalid LONG stop-loss: {stop} >= {entry}")
                return False
            if target <= entry:
                logger.error(f"Invalid LONG take-profit: {target} <= {entry}")
                return False
        else:  # SELL (SHORT)
            if stop <= entry:
                logger.error(f"Invalid SHORT stop-loss: {stop} <= {entry}")
                return False
            if target >= entry:
                logger.error(f"Invalid SHORT take-profit: {target} >= {entry}")
                return False
        
        # Проверяем риск/прибыль
        rr_ratio = order_template.get('risk_reward_ratio', 0)
        if rr_ratio < 1.0:
            logger.warning(f"Poor risk/reward ratio: {rr_ratio:.2f} (should be >= 1.0)")
        
        logger.debug(f"✅ Order validation passed for {order_template['symbol']}")
        return True

    def _log_signal_details(self, signal_data: Dict) -> None:
        """Детальное логирование информации о сигнале"""
        logger.info(f"📊 Signal Details for {signal_data['ticker']}:")
        logger.info(f"  Direction: {signal_data['signal']}")
        logger.info(f"  Matched Timeframes: {signal_data['timeframes_str']}")
        logger.info(f"  Current Price: {signal_data['current_price']:.6f}")
        logger.info(f"  Entry Price: {signal_data['entry_price']:.6f}")
        logger.info(f"  Stop Loss: {signal_data['stop_loss']:.6f}")
        logger.info(f"  Take Profit: {signal_data['take_profit']:.6f}")
        logger.info(f"  Confidence: {signal_data['confidence']:.3f}")
        logger.info(f"  Dominance Change: {signal_data.get('dominance_change_percent', 0):.2f}%")
        
        # Детальная информация по каждому таймфрейму
        if 'raw_signals' in signal_data:
            logger.info("📋 Individual Timeframe Data:")
            for tf in sorted(signal_data['matched_timeframes']):
                if tf in signal_data['raw_signals']:
                    tf_data = signal_data['raw_signals'][tf]
                    logger.info(
                        f"  {tf}: {tf_data['signal']} | "
                        f"Entry: {tf_data['entry_price']:.6f} | "
                        f"Stop: {tf_data['stop_loss']:.6f} | "
                        f"Target: {tf_data['take_profit']:.6f} | "
                        f"Confidence: {tf_data['confidence']:.3f}"
                    )

    def _log_order_details(self, order_template: Dict) -> None:
        """Детальное логирование информации об ордере"""
        logger.info(f"📋 Order Template Details:")
        logger.info(f"  Order ID: {order_template['order_id']}")
        logger.info(f"  Symbol: {order_template['symbol']}")
        logger.info(f"  Side: {order_template['side']}")
        logger.info(f"  Quantity: {order_template['quantity']}")
        logger.info(f"  Entry Price: {order_template['price']:.6f}")
        logger.info(f"  Stop Loss: {order_template['stop_loss']:.6f}")
        logger.info(f"  Take Profit: {order_template['take_profit']:.6f}")
        logger.info(f"  Risk/Reward Ratio: {order_template['risk_reward_ratio']:.2f}")
        logger.info(f"  Timeframes: {', '.join(order_template['signal_data']['matched_timeframes'])}")

    def _format_telegram_message(self, signal_data: Dict) -> str:
        """
        Форматирует сообщение для Telegram
        
        Args:
            signal_data: Данные сигнала
            
        Returns:
            str: Отформатированное сообщение
        """
        # Рассчитываем риск/прибыль для отображения
        rr_ratio = self._calculate_risk_reward_ratio(
            signal_data['entry_price'],
            signal_data['stop_loss'], 
            signal_data['take_profit'],
            signal_data['signal']
        )
        
        message = (
            f"🚀 *{signal_data['ticker']}* ({signal_data['timeframes_str']})\n"
            f"📍 Direction: *{signal_data['signal']}*\n"
            f"💰 Current: `{signal_data['current_price']:.6f}`\n"
            f"🔢 Entry: `{signal_data['entry_price']:.6f}`\n"
            f"🛑 Stop: `{signal_data['stop_loss']:.6f}`\n"
            f"🎯 Target: `{signal_data['take_profit']:.6f}`\n"
            f"📊 Confidence: {signal_data['confidence']*100:.1f}%\n"
            f"⚖️ R/R Ratio: {rr_ratio:.2f}\n"
            f"🔍 Dominance: {signal_data.get('dominance_change_percent', 0):.2f}%\n"
            f"⏱️ {signal_data['timestamp']}"
        )
        
        return message

    def _save_order_to_database(self, order_template: Dict) -> bool:
        """
        Сохраняет ордер в базу данных (если доступна)
        
        Args:
            order_template: Шаблон ордера
            
        Returns:
            bool: True если сохранено успешно
        """
        try:
            # Здесь можно добавить логику сохранения в БД
            # Пока просто логируем
            logger.info(f"💾 Order template saved to database: {order_template['order_id']}")
            return True
        except Exception as e:
            logger.error(f"Failed to save order to database: {str(e)}")
            return False

    def process_signal(self, signal_data: Dict) -> bool:
        """
        Полная обработка сигнала: создание уведомления и ордера
        
        Args:
            signal_data: Консолидированные данные сигнала
            
        Returns:
            bool: True если обработка прошла успешно
        """
        logger.info(f"🔄 Processing signal for {signal_data['ticker']}")
        
        success = True
        
        # 1. Отправляем уведомление в Telegram
        if not self.create_telegram_alert(signal_data):
            logger.error(f"Failed to send Telegram alert for {signal_data['ticker']}")
            success = False
        
        # 2. Создаем шаблон ордера для Binance
        order_template = self.create_binance_template(signal_data)
        if not order_template:
            logger.error(f"Failed to create Binance template for {signal_data['ticker']}")
            success = False
        
        # 3. Отправляем ордер в binance_factory (если подключен)
        if binance_factory_instance and order_template:
            try:
                # Преобразуем данные в формат binance_factory
                factory_order_data = {
                    'symbol': signal_data['ticker'],
                    'side': 'BUY' if signal_data['signal'] == 'LONG' else 'SELL',
                    'price': signal_data['entry_price'],  # entry_price для валидации
                    'tolerance_percent': 1.0,  # допустимое отклонение цены в %
                    'stop_loss': signal_data['stop_loss'],
                    'take_profit': signal_data['take_profit'],
                    'confidence': signal_data['confidence'],
                    'timeframes': signal_data['timeframes_str'],
                    'order_id': order_template['order_id']
                }
                
                binance_factory_instance.add_order_to_queue(factory_order_data)
                logger.info(f"📦 Order sent to Binance Factory: {signal_data['ticker']}")
                
            except Exception as e:
                logger.error(f"Failed to send order to Binance Factory: {str(e)}")
                success = False
        
        if success:
            logger.info(f"✅ Signal processing completed successfully for {signal_data['ticker']}")
        else:
            logger.error(f"❌ Signal processing failed for {signal_data['ticker']}")
            
        return success


# Singleton instance for application-wide use
order_generator = OrderGenerator()


# Utility function for external use
def process_trading_signal(signal_data: Dict) -> bool:
    """
    Convenience function для обработки торгового сигнала
    
    Args:
        signal_data: Данные сигнала для обработки
        
    Returns:
        bool: True если обработка успешна
    """
    return order_generator.process_signal(signal_data)