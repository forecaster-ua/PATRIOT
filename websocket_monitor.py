"""
Order Monitor - Мониторинг ордеров через REST API
================================================

УПРОЩЕННАЯ ВЕРСИЯ ДЛЯ MVP:
- Периодический опрос ордеров через REST API (каждые 30 сек)
- OCO логика (One-Cancels-Other)  
- Уведомления о статусах ордеров
- Обнаружение внешних изменений

Author: HEDGER
Version: 1.0 - MVP Simplified
"""

import threading
import time
from typing import Dict, List, Optional, Set
from datetime import datetime

# Локальные импорты
from utils import logger
from telegram_bot import telegram_bot
from config import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET

# Binance REST API
from binance.client import Client
from binance.exceptions import BinanceAPIException

class OrderMonitor:
    """Мониторинг ордеров через REST API"""
    
    def __init__(self):
        """Инициализация мониторинга"""
        self.binance_client = None
        self.active_order_groups = {}  # order_id -> order_group_info
        self.monitoring_active = False
        self.monitoring_thread = None
        self.check_interval = 30  # Проверяем каждые 30 секунд
        
        self._init_binance_client()
        
        logger.info("👁️ OrderMonitor initialized (REST API polling)")
    
    def _init_binance_client(self) -> None:
        """Инициализация Binance клиента"""
        try:
            if not BINANCE_API_KEY or not BINANCE_API_SECRET:
                logger.error("❌ Binance API ключи не настроены")
                return
            
            self.binance_client = Client(
                api_key=BINANCE_API_KEY,
                api_secret=BINANCE_API_SECRET,
                testnet=BINANCE_TESTNET
            )
            
            logger.info("✅ REST API client initialized")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации REST API: {e}")
    
    def add_order_group(self, order_result: Dict) -> None:
        """
        Добавляет группу ордеров для мониторинга
        
        Args:
            order_result: Результат от order_executor.place_market_order()
        """
        try:
            if not order_result.get('success', False):
                return
            
            main_order = order_result['main_order']
            stop_order = order_result['stop_order']
            tp_order = order_result['tp_order']
            signal_data = order_result['signal_data']
            
            # Создаем группу ордеров
            group_id = f"group_{int(time.time())}"
            order_group = {
                'group_id': group_id,
                'ticker': signal_data['ticker'],
                'signal_type': signal_data['signal'],
                'quantity': order_result['quantity'],
                'main_order_id': main_order['orderId'],
                'stop_order_id': stop_order['orderId'],
                'tp_order_id': tp_order['orderId'],
                'main_status': 'FILLED',  # Market ордер исполняется сразу
                'stop_status': 'NEW',
                'tp_status': 'NEW',
                'created_at': datetime.now(),
                'signal_data': signal_data
            }
            
            # Добавляем все ордера в отслеживание
            self.active_order_groups[main_order['orderId']] = order_group
            self.active_order_groups[stop_order['orderId']] = order_group
            self.active_order_groups[tp_order['orderId']] = order_group
            
            logger.info(f"👁️ Группа ордеров {group_id} добавлена в мониторинг ({signal_data['ticker']})")
            
            # Запускаем мониторинг если не запущен
            if not self.monitoring_active:
                self.start_monitoring()
                
        except Exception as e:
            logger.error(f"❌ Ошибка добавления группы ордеров в мониторинг: {e}")
    
    def start_monitoring(self) -> None:
        """Запускает мониторинг через REST API"""
        if self.monitoring_active or not self.binance_client:
            return
        
        try:
            logger.info("🚀 Запуск REST API мониторинга ордеров...")
            
            self.monitoring_active = True
            
            # Запускаем мониторинг в отдельном потоке
            self.monitoring_thread = threading.Thread(
                target=self._run_monitoring_loop,
                daemon=True,
                name="OrderMonitor"
            )
            self.monitoring_thread.start()
            
            logger.info("✅ REST API мониторинг запущен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска мониторинга: {e}")
            self.monitoring_active = False
    
    def _run_monitoring_loop(self) -> None:
        """Основной цикл мониторинга"""
        try:
            while self.monitoring_active:
                if self.active_order_groups:
                    self._check_all_orders()
                
                # Ждем до следующей проверки
                time.sleep(self.check_interval)
                
        except Exception as e:
            logger.error(f"❌ Ошибка цикла мониторинга: {e}")
            self.monitoring_active = False
    
    def _check_all_orders(self) -> None:
        """Проверяет статусы всех отслеживаемых ордеров"""
        try:
            # Группируем ордера по символам для оптимизации API запросов
            symbols_to_check = set()
            for group in self.active_order_groups.values():
                symbols_to_check.add(group['ticker'])
            
            # Проверяем каждый символ
            for symbol in symbols_to_check:
                try:
                    # Получаем все открытые ордера по символу
                    open_orders = self.binance_client.futures_get_open_orders(symbol=symbol)
                    
                    # Проверяем наши отслеживаемые ордера
                    self._process_symbol_orders(symbol, open_orders)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка проверки ордеров {symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка проверки всех ордеров: {e}")
    
    def _process_symbol_orders(self, symbol: str, open_orders: List[Dict]) -> None:
        """Обрабатывает ордера для конкретного символа"""
        try:
            # Создаем множество ID открытых ордеров
            open_order_ids = {str(order['orderId']) for order in open_orders}
            
            # Проверяем наши отслеживаемые ордера этого символа
            groups_to_check = []
            for order_id, group in self.active_order_groups.items():
                if group['ticker'] == symbol:
                    groups_to_check.append((order_id, group))
            
            # Проверяем каждую группу
            for order_id, group in groups_to_check:
                self._check_order_status(order_id, group, open_order_ids)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки ордеров символа {symbol}: {e}")
    
    def _check_order_status(self, order_id: str, group: Dict, open_order_ids: Set[str]) -> None:
        """Проверяет статус конкретного ордера"""
        try:
            # Если ордер не в списке открытых - значит исполнен или отменен
            if order_id not in open_order_ids:
                # Получаем историю ордера для определения статуса
                try:
                    order_info = self.binance_client.futures_get_order(
                        symbol=group['ticker'],
                        orderId=order_id
                    )
                    
                    status = order_info['status']
                    
                    if status == 'FILLED':
                        self._handle_filled_order(group, order_id, order_info)
                    elif status == 'CANCELED':
                        self._handle_canceled_order(group, order_id, order_info)
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка получения информации об ордере {order_id}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка проверки статуса ордера {order_id}: {e}")
    
    def _handle_filled_order(self, order_group: Dict, order_id: str, order_data: Dict) -> None:
        """Обрабатывает исполненный ордер"""
        try:
            ticker = order_group['ticker']
            
            # Определяем тип ордера
            if order_id == order_group['stop_order_id']:
                order_type = "STOP"
            elif order_id == order_group['tp_order_id']:
                order_type = "TAKE_PROFIT"
            else:
                return  # Основной ордер мы не отслеживаем
            
            if order_type == "STOP":
                # Исполнился Stop Loss - отменяем Take Profit
                logger.warning(f"🛡️ STOP LOSS исполнен для {ticker}")
                
                tp_order_id = order_group['tp_order_id']
                self._cancel_order(ticker, tp_order_id, "Stop Loss исполнен")
                
                # Отправляем уведомление
                self._send_stop_loss_notification(order_group, order_data)
                
                # Удаляем группу из мониторинга
                self._remove_order_group(order_group)
                
            elif order_type == "TAKE_PROFIT":
                # Исполнился Take Profit - отменяем Stop Loss
                logger.info(f"🎯 TAKE PROFIT исполнен для {ticker}")
                
                stop_order_id = order_group['stop_order_id']
                self._cancel_order(ticker, stop_order_id, "Take Profit исполнен")
                
                # Отправляем уведомление
                self._send_take_profit_notification(order_group, order_data)
                
                # Удаляем группу из мониторинга
                self._remove_order_group(order_group)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки исполненного ордера: {e}")
    
    def _handle_canceled_order(self, order_group: Dict, order_id: str, order_data: Dict) -> None:
        """Обрабатывает отмененный ордер"""
        try:
            ticker = order_group['ticker']
            
            # Определяем тип ордера
            if order_id == order_group['stop_order_id']:
                order_type = "STOP"
            elif order_id == order_group['tp_order_id']:
                order_type = "TAKE_PROFIT"
            else:
                return
                
            logger.warning(f"⚠️ Ордер {order_type} отменен внешне для {ticker}")
            
            # Отправляем уведомление о внешней отмене
            self._send_external_cancel_notification(order_group, order_type, order_data)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки отмененного ордера: {e}")
    
    def _cancel_order(self, symbol: str, order_id: str, reason: str) -> bool:
        """Отменяет ордер"""
        try:
            if not self.binance_client:
                return False
            
            result = self.binance_client.futures_cancel_order(
                symbol=symbol,
                orderId=order_id
            )
            
            logger.info(f"❌ Ордер {order_id} отменен ({reason})")
            return True
            
        except BinanceAPIException as e:
            if e.code == -2011:  # Order does not exist
                logger.info(f"ℹ️ Ордер {order_id} уже не существует")
                return True
            else:
                logger.error(f"❌ Ошибка отмены ордера {order_id}: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка отмены ордера {order_id}: {e}")
            return False
    
    def _remove_order_group(self, order_group: Dict) -> None:
        """Удаляет группу ордеров из мониторинга"""
        try:
            main_order_id = order_group['main_order_id']
            stop_order_id = order_group['stop_order_id']
            tp_order_id = order_group['tp_order_id']
            group_id = order_group['group_id']
            
            # Удаляем все ордера группы
            self.active_order_groups.pop(main_order_id, None)
            self.active_order_groups.pop(stop_order_id, None)
            self.active_order_groups.pop(tp_order_id, None)
            
            logger.info(f"🗑️ Группа ордеров {group_id} удалена из мониторинга")
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления группы ордеров: {e}")
    
    def _send_stop_loss_notification(self, order_group: Dict, order_data: Dict) -> None:
        """Отправляет уведомление о срабатывании Stop Loss"""
        try:
            ticker = order_group['ticker']
            signal_type = order_group['signal_type']
            quantity = order_group['quantity']
            fill_price = float(order_data.get('ap', 0))  # Average price
            
            message = f"""
🛡️ <b>STOP LOSS ИСПОЛНЕН</b> 🛡️

📊 <b>Символ:</b> {ticker}
📈 <b>Позиция:</b> {signal_type}
💰 <b>Количество:</b> {quantity}
💵 <b>Цена исполнения:</b> {fill_price:.6f}

❌ Take Profit автоматически отменен

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление о Stop Loss {ticker} отправлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления Stop Loss: {e}")
    
    def _send_take_profit_notification(self, order_group: Dict, order_data: Dict) -> None:
        """Отправляет уведомление о срабатывании Take Profit"""
        try:
            ticker = order_group['ticker']
            signal_type = order_group['signal_type']
            quantity = order_group['quantity']
            fill_price = float(order_data.get('ap', 0))  # Average price
            
            message = f"""
🎯 <b>TAKE PROFIT ИСПОЛНЕН!</b> 🎯

📊 <b>Символ:</b> {ticker}
📈 <b>Позиция:</b> {signal_type}
💰 <b>Количество:</b> {quantity}
💵 <b>Цена исполнения:</b> {fill_price:.6f}

✅ Stop Loss автоматически отменен

🎉 <b>ПРИБЫЛЬ ЗАФИКСИРОВАНА!</b>

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление о Take Profit {ticker} отправлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления Take Profit: {e}")
    
    def _send_external_cancel_notification(self, order_group: Dict, order_type: str, order_data: Dict) -> None:
        """Отправляет уведомление о внешней отмене ордера"""
        try:
            ticker = order_group['ticker']
            
            message = f"""
⚠️ <b>ВНЕШНЯЯ ОТМЕНА ОРДЕРА</b> ⚠️

📊 <b>Символ:</b> {ticker}
🎯 <b>Тип ордера:</b> {order_type}

❗ Ордер был отменен не системой!
🔍 Проверьте позицию вручную

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
            
            telegram_bot.send_message(message)
            logger.info(f"📱 Уведомление о внешней отмене {ticker} отправлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о внешней отмене: {e}")
    
    def get_monitoring_status(self) -> Dict:
        """Возвращает статус мониторинга"""
        return {
            'monitoring_active': self.monitoring_active,
            'active_groups': len(set(group['group_id'] for group in self.active_order_groups.values())),
            'total_orders': len(self.active_order_groups)
        }
    
    def stop_monitoring(self) -> None:
        """Останавливает мониторинг"""
        try:
            if self.monitoring_active:
                self.monitoring_active = False
                if self.monitoring_thread and self.monitoring_thread.is_alive():
                    self.monitoring_thread.join(timeout=5)
                logger.info("🛑 REST API мониторинг остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка остановки мониторинга: {e}")


# Глобальный экземпляр для использования в order_executor
order_monitor = OrderMonitor()


if __name__ == "__main__":
    """Тест мониторинга ордеров"""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    monitor = OrderMonitor()
    
    if monitor.binance_client:
        logger.info("✅ Order monitor готов к работе")
        
        # Запускаем мониторинг для теста
        monitor.start_monitoring()
        
        # Ждем немного для тестирования
        import time
        time.sleep(10)
        
        status = monitor.get_monitoring_status()
        logger.info(f"📊 Статус мониторинга: {status}")
        
        monitor.stop_monitoring()
    else:
        logger.error("❌ Order monitor не может быть запущен")
