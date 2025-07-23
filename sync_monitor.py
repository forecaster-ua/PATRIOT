#!/usr/bin/env python3
"""
Sync Monitor - Утилита мониторинга синхронизации
===============================================

Утилита для мониторинга и управления синхронизацией между компонентами:
- Отображение текущего состояния синхронизации
- Проверка конфликтов между ticker_monitor и orders_watchdog
- Принудительная синхронизация состояния
- Диагностика проблем синхронизации

Использование:
python sync_monitor.py [--continuous] [--interval SECONDS] [--fix-conflicts]

--continuous    : непрерывный мониторинг
--interval N    : интервал проверки в секундах (по умолчанию 30)
--fix-conflicts : попытка автоматически исправить конфликты

Author: HEDGER  
Version: 1.0 - Synchronization Monitor
"""

import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

try:
    from orders_synchronizer import OrdersSynchronizer
    from utils import logger
    SYNC_AVAILABLE = True
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("❌ Убедитесь, что orders_synchronizer.py и utils.py доступны")
    sys.exit(1)


class SyncMonitor:
    """Монитор синхронизации системы"""
    
    def __init__(self):
        self.sync = OrdersSynchronizer()
        
    def display_current_status(self) -> Dict[str, Any]:
        """Отображает текущий статус синхронизации"""
        print("=" * 80)
        print("🔄 МОНИТОР СИНХРОНИЗАЦИИ PATRIOT TRADING SYSTEM")
        print("=" * 80)
        
        # Получаем отчет синхронизации
        report = self.sync.get_synchronization_report()
        
        # Выводим отчет
        self.sync.print_sync_report(report)
        
        return report
    
    def check_files_status(self) -> Dict[str, Any]:
        """Проверяет состояние файлов системы"""
        files_status = {
            'orders_watchdog_state.json': {'exists': False, 'size': 0, 'modified': None},
            'orders_watchdog_requests.json': {'exists': False, 'size': 0, 'modified': None},
            'orders_watchdog_response.json': {'exists': False, 'size': 0, 'modified': None},
            'tickers.txt': {'exists': False, 'size': 0, 'modified': None},
            'signals.db': {'exists': False, 'size': 0, 'modified': None}
        }
        
        for filename, info in files_status.items():
            filepath = Path(filename)
            if filepath.exists():
                info['exists'] = True
                info['size'] = filepath.stat().st_size
                info['modified'] = datetime.fromtimestamp(filepath.stat().st_mtime).strftime('%H:%M:%S')
        
        print("\n📁 СОСТОЯНИЕ ФАЙЛОВ СИСТЕМЫ:")
        print("-" * 50)
        for filename, info in files_status.items():
            status = "✅" if info['exists'] else "❌"
            size_str = f"{info['size']} bytes" if info['exists'] else "N/A"
            modified_str = info['modified'] if info['exists'] else "N/A"
            print(f"{status} {filename}: {size_str} (изменен: {modified_str})")
        
        return files_status
    
    def test_communication(self) -> Dict[str, Any]:
        """Тестирует коммуникацию с Orders Watchdog"""
        print(f"\n🔧 ТЕСТ КОММУНИКАЦИИ С ORDERS WATCHDOG:")
        print("-" * 50)
        
        test_results = {
            'watchdog_running': False,
            'response_time': None,
            'watched_symbols_count': 0,
            'communication_ok': False
        }
        
        try:
            start_time = time.time()
            
            # Проверяем, работает ли watchdog
            watchdog_running = self.sync.is_watchdog_running()
            response_time = time.time() - start_time
            
            test_results['watchdog_running'] = watchdog_running
            test_results['response_time'] = response_time
            
            if watchdog_running:
                print(f"✅ Orders Watchdog отвечает ({response_time:.2f}s)")
                
                # Получаем информацию о символах
                watched_symbols = self.sync.get_watched_symbols()
                test_results['watched_symbols_count'] = len(watched_symbols)
                test_results['communication_ok'] = True
                
                print(f"✅ Получена информация о {len(watched_symbols)} символах")
                
            else:
                print(f"❌ Orders Watchdog не отвечает (таймаут: {response_time:.2f}s)")
                print("❌ Проверьте, запущен ли orders_watchdog.py")
                
        except Exception as e:
            print(f"❌ Ошибка коммуникации: {e}")
            test_results['error'] = str(e)
        
        return test_results
    
    def run_conflict_test(self) -> Dict[str, Any]:
        """Запускает тест проверки конфликтов"""
        print(f"\n🧪 ТЕСТ ПРОВЕРКИ КОНФЛИКТОВ:")
        print("-" * 50)
        
        # Тестовые ордера для проверки
        test_orders = [
            {'symbol': 'BTCUSDT', 'side': 'BUY', 'quantity': 0.001, 'order_type': 'MAIN'},
            {'symbol': 'ETHUSDT', 'side': 'SELL', 'quantity': 0.01, 'order_type': 'MAIN'},
            {'symbol': 'ADAUSDT', 'side': 'BUY', 'quantity': 100.0, 'order_type': 'MAIN'}
        ]
        
        conflict_results = {}
        
        for test_order in test_orders:
            symbol = test_order['symbol']
            try:
                safe_to_proceed, conflict_info = self.sync.check_order_conflicts([test_order])
                
                conflict_results[symbol] = {
                    'safe_to_proceed': safe_to_proceed,
                    'conflicts_count': len(conflict_info.get('conflicts', [])),
                    'has_warnings': len([c for c in conflict_info.get('conflicts', []) if c.get('severity') == 'WARNING']) > 0,
                    'has_errors': len([c for c in conflict_info.get('conflicts', []) if c.get('severity') == 'ERROR']) > 0
                }
                
                status = "✅ OK" if safe_to_proceed else "❌ КОНФЛИКТ"
                conflicts_count = conflict_results[symbol]['conflicts_count']
                print(f"{status} {symbol}: {conflicts_count} потенциальных конфликтов")
                
            except Exception as e:
                print(f"❌ {symbol}: Ошибка проверки - {e}")
                conflict_results[symbol] = {'error': str(e)}
        
        return conflict_results
    
    def continuous_monitoring(self, interval: int = 30) -> None:
        """Запускает непрерывный мониторинг"""
        print(f"🔄 Запуск непрерывного мониторинга (интервал: {interval}s)")
        print("Нажмите Ctrl+C для остановки...\n")
        
        try:
            cycle = 0
            while True:
                cycle += 1
                print(f"\n{'='*20} ЦИКЛ #{cycle} - {datetime.now().strftime('%H:%M:%S')} {'='*20}")
                
                # Основной статус
                report = self.display_current_status()
                
                # Каждые 5 циклов - расширенная проверка
                if cycle % 5 == 0:
                    self.test_communication()
                    self.check_files_status()
                
                # Проверяем критические проблемы
                issues = report.get('synchronization_issues', [])
                if issues:
                    print(f"\n⚠️ ОБНАРУЖЕНО {len(issues)} ПРОБЛЕМ:")
                    for issue in issues:
                        print(f"  {issue}")
                
                # Ждем следующего цикла
                print(f"\n💤 Ожидание {interval} секунд до следующей проверки...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"\n👋 Мониторинг остановлен пользователем")
    
    def attempt_fix_conflicts(self) -> bool:
        """Попытка автоматического исправления конфликтов"""
        print(f"\n🔧 ПОПЫТКА ИСПРАВЛЕНИЯ КОНФЛИКТОВ:")
        print("-" * 50)
        
        try:
            # Получаем текущий отчет
            report = self.sync.get_synchronization_report()
            
            if not report.get('watchdog_running', False):
                print("❌ Orders Watchdog не работает - исправление невозможно")
                return False
            
            issues = report.get('synchronization_issues', [])
            if not issues:
                print("✅ Конфликтов для исправления не найдено")
                return True
            
            print(f"🔍 Найдено {len(issues)} проблем для исправления:")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
            
            # В будущих версиях здесь можно добавить автоматическое исправление
            print("\n⚠️ Автоматическое исправление пока не реализовано")
            print("💡 Рекомендации:")
            print("  1. Перезапустите ticker_monitor.py для синхронизации")
            print("  2. Используйте orders_cleaner.py для очистки сиротских ордеров")
            print("  3. Проверьте logs/ для диагностики проблем")
            
            return False
            
        except Exception as e:
            print(f"❌ Ошибка исправления конфликтов: {e}")
            return False


def main():
    """Точка входа в приложение"""
    parser = argparse.ArgumentParser(description='Монитор синхронизации PATRIOT Trading System')
    parser.add_argument('--continuous', '-c', action='store_true',
                       help='Непрерывный мониторинг')
    parser.add_argument('--interval', '-i', type=int, default=30,
                       help='Интервал проверки в секундах (по умолчанию: 30)')
    parser.add_argument('--fix-conflicts', '-f', action='store_true',
                       help='Попытка автоматически исправить конфликты')
    parser.add_argument('--test-communication', '-t', action='store_true',
                       help='Только тест коммуникации с Orders Watchdog')
    
    args = parser.parse_args()
    
    try:
        monitor = SyncMonitor()
        
        if args.test_communication:
            # Только тест коммуникации
            monitor.test_communication()
            monitor.run_conflict_test()
        elif args.continuous:
            # Непрерывный мониторинг
            monitor.continuous_monitoring(args.interval)
        else:
            # Разовая проверка
            report = monitor.display_current_status()
            monitor.check_files_status()
            comm_test = monitor.test_communication()
            conflict_test = monitor.run_conflict_test()
            
            if args.fix_conflicts:
                monitor.attempt_fix_conflicts()
            
            # Итоговый статус
            print(f"\n{'='*80}")
            print("📊 ИТОГОВЫЙ СТАТУС:")
            print("=" * 80)
            
            watchdog_status = "✅ РАБОТАЕТ" if comm_test.get('communication_ok') else "❌ НЕ РАБОТАЕТ"
            issues_count = len(report.get('synchronization_issues', []))
            symbols_count = len(report.get('watched_symbols', {}))
            
            print(f"🐕 Orders Watchdog: {watchdog_status}")
            print(f"📊 Символов под наблюдением: {symbols_count}")
            print(f"⚠️ Проблем синхронизации: {issues_count}")
            
            if issues_count == 0 and comm_test.get('communication_ok'):
                print("✅ Система синхронизирована и работает корректно")
            else:
                print("⚠️ Обнаружены проблемы - рекомендуется диагностика")
            
            print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n👋 Операция прервана пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
