#!/usr/bin/env python3
"""
Orders Synchronizer - Синхронизация между компонентами системы
==============================================================

Модуль для синхронизации состояния между ticker_monitor и orders_watchdog:
- Проверка конфликтов перед размещением ордеров
- Получение информации о наблюдаемых символах
- Автоматическое разрешение конфликтов
- Уведомления о проблемах синхронизации

Author: HEDGER
Version: 1.0 - Orders Synchronization System
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from utils import logger


class OrdersSynchronizer:
    """Синхронизатор состояния между компонентами системы"""
    
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self.requests_file = Path('orders_watchdog_requests.json')
        self.response_file = Path('orders_watchdog_response.json')
        
    def _send_request_to_watchdog(self, action: str, data: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """
        Отправляет запрос к Orders Watchdog и ждет ответа
        
        Args:
            action: Действие для выполнения
            data: Данные запроса
            
        Returns:
            Ответ от watchdog или None при ошибке/таймауте
        """
        try:
            # Удаляем старый файл ответа если существует
            if self.response_file.exists():
                self.response_file.unlink()
            
            # Формируем запрос
            request = {
                'action': action,
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            # Читаем существующие запросы или создаем новый список
            existing_requests = []
            if self.requests_file.exists():
                try:
                    with open(self.requests_file, 'r', encoding='utf-8') as f:
                        existing_requests = json.load(f)
                except:
                    existing_requests = []
            
            # Добавляем новый запрос
            existing_requests.append(request)
            
            # Записываем запросы
            with open(self.requests_file, 'w', encoding='utf-8') as f:
                json.dump(existing_requests, f, indent=2, ensure_ascii=False)
            
            # Ждем ответа с таймаутом
            start_time = time.time()
            expected_response = f"{action}_response"
            
            while time.time() - start_time < self.timeout:
                if self.response_file.exists():
                    try:
                        with open(self.response_file, 'r', encoding='utf-8') as f:
                            response = json.load(f)
                        
                        if response.get('action') == expected_response:
                            # Удаляем файл ответа после чтения
                            self.response_file.unlink()
                            return response.get('data')
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка чтения ответа: {e}")
                
                time.sleep(0.1)  # Проверяем каждые 100ms
            
            logger.warning(f"⏰ Таймаут ожидания ответа от Orders Watchdog ({self.timeout}s)")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки запроса к Orders Watchdog: {e}")
            return None
    
    def is_watchdog_running(self) -> bool:
        """Проверяет, запущен ли Orders Watchdog"""
        try:
            status = self._send_request_to_watchdog('get_status')
            return status is not None and status.get('is_running', False)
        except:
            return False
    
    def get_watched_symbols(self) -> Dict[str, Dict[str, Any]]:
        """
        Получает список символов под наблюдением Orders Watchdog
        
        Returns:
            Словарь с информацией о наблюдаемых символах
        """
        try:
            symbols_data = self._send_request_to_watchdog('get_watched_symbols')
            if symbols_data is not None:
                logger.info(f"📊 Получена информация о {len(symbols_data)} наблюдаемых символах")
                return symbols_data
            else:
                logger.warning("⚠️ Не удалось получить информацию о наблюдаемых символах")
                return {}
        except Exception as e:
            logger.error(f"❌ Ошибка получения наблюдаемых символов: {e}")
            return {}
    
    def check_order_conflicts(self, proposed_orders: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
        """
        Проверяет конфликты с предлагаемыми ордерами
        
        Args:
            proposed_orders: Список ордеров для проверки с ключами:
                           - symbol: str
                           - side: str (BUY/SELL)
                           - quantity: float
                           - order_type: str (опционально)
        
        Returns:
            Tuple[safe_to_proceed: bool, conflict_info: dict]
        """
        try:
            if not proposed_orders:
                return True, {'conflicts': [], 'recommendations': []}
            
            conflict_result = self._send_request_to_watchdog('check_conflicts', proposed_orders)
            
            if conflict_result is not None:
                safe_to_proceed = conflict_result.get('safe_to_proceed', True)
                conflicts_count = conflict_result.get('total_conflicts', 0)
                
                if conflicts_count > 0:
                    logger.warning(f"⚠️ Обнаружено {conflicts_count} потенциальных конфликтов")
                    
                    # Выводим рекомендации
                    for recommendation in conflict_result.get('recommendations', []):
                        logger.warning(f"  {recommendation}")
                
                return safe_to_proceed, conflict_result
            else:
                logger.error("❌ Не удалось проверить конфликты с Orders Watchdog")
                # В случае недоступности watchdog - разрешаем операцию
                return True, {'error': 'Watchdog недоступен', 'conflicts': [], 'recommendations': []}
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки конфликтов: {e}")
            return True, {'error': str(e), 'conflicts': [], 'recommendations': []}
    
    def validate_new_signal(self, symbol: str, side: str, quantity: float) -> Tuple[bool, str]:
        """
        Валидирует новый торговый сигнал перед исполнением
        
        Args:
            symbol: Торговая пара
            side: Направление (BUY/SELL)
            quantity: Количество
            
        Returns:
            Tuple[is_valid: bool, reason: str]
        """
        try:
            # Проверяем доступность watchdog
            if not self.is_watchdog_running():
                logger.warning("⚠️ Orders Watchdog недоступен - валидация пропущена")
                return True, "Watchdog недоступен"
            
            # Формируем проверочный ордер
            proposed_order = {
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'order_type': 'MAIN'
            }
            
            # Проверяем конфликты
            safe_to_proceed, conflict_info = self.check_order_conflicts([proposed_order])
            
            if not safe_to_proceed:
                # Есть серьезные конфликты
                error_conflicts = [c for c in conflict_info.get('conflicts', []) if c.get('severity') == 'ERROR']
                if error_conflicts:
                    conflict = error_conflicts[0]
                    reason = f"Конфликт {conflict['conflict_type']}: {conflict.get('existing_position_side', 'неизвестно')}"
                    return False, reason
            
            # Проверяем предупреждения
            warning_conflicts = [c for c in conflict_info.get('conflicts', []) if c.get('severity') == 'WARNING']
            if warning_conflicts:
                # Есть предупреждения, но можно продолжать
                return True, f"Предупреждение: найдено {len(warning_conflicts)} потенциальных конфликтов"
            
            return True, "Конфликтов не обнаружено"
            
        except Exception as e:
            logger.error(f"❌ Ошибка валидации сигнала: {e}")
            return True, f"Ошибка валидации: {e}"
    
    def get_synchronization_report(self) -> Dict[str, Any]:
        """
        Получает полный отчет о синхронизации системы
        
        Returns:
            Отчет с информацией о состоянии синхронизации
        """
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'watchdog_running': False,
                'watched_symbols': {},
                'total_watched_orders': 0,
                'synchronization_issues': [],
                'recommendations': []
            }
            
            # Проверяем статус watchdog
            watchdog_status = self._send_request_to_watchdog('get_status')
            if watchdog_status:
                report['watchdog_running'] = watchdog_status.get('is_running', False)
                report['total_watched_orders'] = watchdog_status.get('watched_orders_count', 0)
                
                # Получаем детальную информацию о символах
                watched_symbols = self.get_watched_symbols()
                report['watched_symbols'] = watched_symbols
                
                # Анализируем возможные проблемы
                for symbol, info in watched_symbols.items():
                    if info.get('main_order_filled', False):
                        if not info.get('has_sl', False) and not info.get('has_tp', False):
                            report['synchronization_issues'].append(f"⚠️ {symbol}: Открытая позиция без SL/TP")
                    
                    if len(info.get('orders', [])) > 3:
                        report['synchronization_issues'].append(f"⚠️ {symbol}: Слишком много ордеров ({len(info['orders'])})")
            else:
                report['synchronization_issues'].append("❌ Orders Watchdog недоступен")
                report['recommendations'].append("Запустите Orders Watchdog для полной синхронизации")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации отчета синхронизации: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'watchdog_running': False,
                'synchronization_issues': [f"Ошибка получения отчета: {e}"]
            }
    
    def print_sync_report(self, report: Optional[Dict[str, Any]] = None) -> None:
        """Выводит отчет о синхронизации в удобном формате"""
        if report is None:
            report = self.get_synchronization_report()
        
        print("=" * 70)
        print("🔄 ОТЧЕТ СИНХРОНИЗАЦИИ СИСТЕМЫ")
        print("=" * 70)
        
        print(f"🕐 Время: {report['timestamp']}")
        print(f"🐕 Orders Watchdog: {'✅ РАБОТАЕТ' if report['watchdog_running'] else '❌ НЕ РАБОТАЕТ'}")
        print(f"📊 Наблюдаемых ордеров: {report['total_watched_orders']}")
        print(f"📈 Символов под наблюдением: {len(report.get('watched_symbols', {}))}")
        
        # Детали по символам
        watched_symbols = report.get('watched_symbols', {})
        if watched_symbols:
            print(f"\n📋 ДЕТАЛИ ПО СИМВОЛАМ:")
            print("-" * 50)
            
            for symbol, info in watched_symbols.items():
                status = "📍 ПОЗИЦИЯ" if info.get('main_order_filled') else "⏳ ОРДЕРА"
                orders_count = len(info.get('orders', []))
                position_side = info.get('position_side', 'UNKNOWN')
                
                sl_status = "✅ SL" if info.get('has_sl') else "❌ NO SL"
                tp_status = "✅ TP" if info.get('has_tp') else "❌ NO TP"
                
                print(f"• {symbol}: {status} {position_side} | {orders_count} ордеров | {sl_status} | {tp_status}")
        
        # Проблемы синхронизации
        issues = report.get('synchronization_issues', [])
        if issues:
            print(f"\n⚠️ ПРОБЛЕМЫ СИНХРОНИЗАЦИИ ({len(issues)}):")
            print("-" * 50)
            for issue in issues:
                print(f"  {issue}")
        
        # Рекомендации
        recommendations = report.get('recommendations', [])
        if recommendations:
            print(f"\n💡 РЕКОМЕНДАЦИИ:")
            print("-" * 50)
            for rec in recommendations:
                print(f"  {rec}")
        
        if not issues and not recommendations and report['watchdog_running']:
            print(f"\n✅ Система синхронизирована, проблем не обнаружено")
        
        print("=" * 70)


# Глобальный экземпляр синхронизатора
orders_sync = OrdersSynchronizer()


def validate_signal_before_execution(symbol: str, side: str, quantity: float) -> Tuple[bool, str]:
    """
    Удобная функция для валидации сигнала перед исполнением
    
    Args:
        symbol: Торговая пара
        side: Направление (BUY/SELL) 
        quantity: Количество
        
    Returns:
        Tuple[is_valid: bool, reason: str]
    """
    return orders_sync.validate_new_signal(symbol, side, quantity)


def get_watched_symbols_info() -> Dict[str, Dict[str, Any]]:
    """Получает информацию о наблюдаемых символах"""
    return orders_sync.get_watched_symbols()


def check_synchronization() -> Dict[str, Any]:
    """Проверяет синхронизацию системы"""
    return orders_sync.get_synchronization_report()


if __name__ == "__main__":
    """Тестирование синхронизатора"""
    print("🔄 Тестирование Orders Synchronizer...")
    
    sync = OrdersSynchronizer()
    
    # Проверяем статус watchdog
    print(f"🐕 Watchdog running: {sync.is_watchdog_running()}")
    
    # Получаем отчет синхронизации
    sync.print_sync_report()
    
    # Тестируем валидацию сигнала
    is_valid, reason = sync.validate_new_signal("BTCUSDT", "BUY", 0.001)
    print(f"🧪 Тест валидации: {'✅' if is_valid else '❌'} {reason}")
