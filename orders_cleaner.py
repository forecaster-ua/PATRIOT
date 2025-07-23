#!/usr/bin/env python3
"""
Orders Cleaner - Мусорщик сиротских ордеров
==========================================

Утилита для очистки "сиротских" ордеров на бирже Binance:
- Находит ордера без связанных позиций
- Анализирует типы ордеров (только SL/TP без лимиток на открытие)
- Предоставляет детальный отчет по символам
- Позволяет интерактивно очищать мусорные ордера

Использование:
python orders_cleaner.py [--auto-confirm] [--dry-run] [--report-only]

--auto-confirm : автоматически подтверждать все удаления (осторожно!)
--dry-run      : показать что будет удалено, но не удалять
--report-only  : только показать отчет без возможности удаления

Author: HEDGER
Version: 1.0 - Orders Cleanup Utility
"""

import sys
import argparse
import json
from datetime import datetime
from typing import Dict, List, Set, Tuple
from pathlib import Path
from collections import defaultdict

# Локальные импорты
from config import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET
from utils import logger

# Binance
try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    BINANCE_AVAILABLE = True
except ImportError:
    logger.error("❌ python-binance not installed")
    BINANCE_AVAILABLE = False


class OrdersCleaner:
    """Мусорщик сиротских ордеров"""
    
    def __init__(self):
        self.client = None
        self.positions = {}
        self.orders = {}
        self.orphaned_analysis = {}
        
        self._init_client()
    
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
    
    def analyze_orphaned_orders(self) -> Dict:
        """Анализирует сиротские ордера на бирже"""
        if not self.client:
            return {"error": "Binance client not available"}
        
        try:
            logger.info("🔍 Получаем данные с биржи...")
            
            # Получаем все открытые позиции
            positions_data = self.client.futures_position_information()
            self.positions = {}
            for pos in positions_data:
                if float(pos['positionAmt']) != 0:
                    self.positions[pos['symbol']] = {
                        'amount': float(pos['positionAmt']),
                        'side': 'LONG' if float(pos['positionAmt']) > 0 else 'SHORT',
                        'entry_price': float(pos['entryPrice']) if pos['entryPrice'] else 0.0,
                        'unrealized_pnl': float(pos.get('unrealizedPnl', 0) or 0)
                    }
            
            # Получаем все открытые ордера
            orders_data = self.client.futures_get_open_orders()
            self.orders = {}
            for order in orders_data:
                symbol = order['symbol']
                if symbol not in self.orders:
                    self.orders[symbol] = []
                
                self.orders[symbol].append({
                    'order_id': order['orderId'],
                    'type': order['type'],
                    'side': order['side'],
                    'quantity': float(order['origQty']),
                    'price': float(order['price']) if order['price'] else None,
                    'stop_price': float(order['stopPrice']) if order['stopPrice'] else None,
                    'status': order['status']
                })
            
            logger.info(f"📊 Найдено {len(self.positions)} открытых позиций")
            logger.info(f"📋 Найдено ордеров по {len(self.orders)} символам")
            
            # Анализируем каждый символ
            self.orphaned_analysis = self._analyze_symbols()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "total_positions": len(self.positions),
                "total_symbols_with_orders": len(self.orders),
                "orphaned_symbols": len([s for s in self.orphaned_analysis.values() if s['is_orphaned']]),
                "analysis": self.orphaned_analysis
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа ордеров: {e}")
            return {"error": str(e)}
    
    def _analyze_symbols(self) -> Dict:
        """Анализирует символы на предмет сиротских ордеров"""
        analysis = {}
        
        # Проверяем все символы с ордерами
        for symbol, orders in self.orders.items():
            has_position = symbol in self.positions
            position_info = self.positions.get(symbol, {})
            
            # Классифицируем ордера
            entry_orders = []  # Ордера на открытие позиции
            exit_orders = []   # Ордера на закрытие (SL/TP)
            
            for order in orders:
                order_type = order['type']
                if order_type in ['LIMIT', 'MARKET']:
                    entry_orders.append(order)
                elif order_type in ['STOP_MARKET', 'TAKE_PROFIT_MARKET', 'STOP', 'TAKE_PROFIT']:
                    exit_orders.append(order)
                else:
                    # Неизвестный тип - считаем как entry для безопасности
                    entry_orders.append(order)
            
            # Определяем статус символа
            is_orphaned = (
                not has_position and           # Нет открытой позиции
                len(entry_orders) == 0 and    # Нет ордеров на открытие
                len(exit_orders) > 0           # Есть только SL/TP ордера
            )
            
            analysis[symbol] = {
                'has_position': has_position,
                'position_info': position_info,
                'total_orders': len(orders),
                'entry_orders': len(entry_orders),
                'exit_orders': len(exit_orders),
                'is_orphaned': is_orphaned,
                'orders_detail': {
                    'entry': entry_orders,
                    'exit': exit_orders
                }
            }
        
        return analysis
    
    def print_analysis_report(self, analysis_data: Dict) -> None:
        """Выводит детальный отчет анализа"""
        if "error" in analysis_data:
            logger.error(f"❌ Ошибка анализа: {analysis_data['error']}")
            return
        
        print("=" * 80)
        print("🧹 ОТЧЕТ АНАЛИЗА СИРОТСКИХ ОРДЕРОВ")
        print("=" * 80)
        
        # Общая статистика
        print(f"🕐 Время анализа: {analysis_data['timestamp']}")
        print(f"📍 Открытых позиций: {analysis_data['total_positions']}")
        print(f"📋 Символов с ордерами: {analysis_data['total_symbols_with_orders']}")
        print(f"🧹 Сайротских символов: {analysis_data['orphaned_symbols']}")
        
        analysis = analysis_data['analysis']
        
        # Группируем символы
        orphaned_symbols = []
        clean_symbols = []
        
        for symbol, data in analysis.items():
            if data['is_orphaned']:
                orphaned_symbols.append(symbol)
            else:
                clean_symbols.append(symbol)
        
        # Показываем сиротские символы
        if orphaned_symbols:
            print(f"\n🧹 СИРОТСКИЕ СИМВОЛЫ ({len(orphaned_symbols)}):")
            print("-" * 60)
            
            for symbol in sorted(orphaned_symbols):
                data = analysis[symbol]
                print(f"\n📊 {symbol}:")
                print(f"  • Позиция: ❌ НЕТ")
                print(f"  • Всего ордеров: {data['total_orders']}")
                print(f"  • Ордера на открытие: {data['entry_orders']}")
                print(f"  • Ордера на закрытие: {data['exit_orders']}")
                
                # Детали ордеров на закрытие
                exit_orders = data['orders_detail']['exit']
                for order in exit_orders:
                    order_type = order['type']
                    side = order['side']
                    price_info = ""
                    if order['price']:
                        price_info = f" @ {order['price']:.6f}"
                    elif order['stop_price']:
                        price_info = f" @ {order['stop_price']:.6f}"
                    
                    print(f"    - {order_type} {side} {order['quantity']}{price_info} (#{order['order_id']})")
        
        # Показываем чистые символы (кратко)
        if clean_symbols:
            print(f"\n✅ ЧИСТЫЕ СИМВОЛЫ ({len(clean_symbols)}):")
            print("-" * 60)
            
            for symbol in sorted(clean_symbols):
                data = analysis[symbol]
                pos_status = "✅ ЕСТЬ" if data['has_position'] else "❌ НЕТ"
                entry_count = data['entry_orders']
                exit_count = data['exit_orders']
                
                if data['has_position']:
                    pos_info = data['position_info']
                    side = pos_info['side']
                    amount = abs(pos_info['amount'])
                    pnl = pos_info['unrealized_pnl']
                    pnl_str = f"(PnL: {pnl:+.2f})" if pnl != 0 else ""
                    print(f"• {symbol}: {pos_status} {side} {amount} {pnl_str}, Ордеров: {entry_count + exit_count}")
                else:
                    print(f"• {symbol}: {pos_status}, Ордеров открытия: {entry_count}, Закрытия: {exit_count}")
        
        print("=" * 80)
    
    def cleanup_orphaned_orders(self, analysis_data: Dict, auto_confirm: bool = False, dry_run: bool = False) -> Dict:
        """Очищает сиротские ордера с подтверждением"""
        if "error" in analysis_data:
            return analysis_data
        
        analysis = analysis_data['analysis']
        orphaned_symbols = [s for s, data in analysis.items() if data['is_orphaned']]
        
        if not orphaned_symbols:
            print("\n✅ Сиротских ордеров не найдено!")
            return {"cleaned": 0, "skipped": 0, "errors": []}
        
        print(f"\n🧹 Найдено {len(orphaned_symbols)} символов с сиротскими ордерами")
        
        cleaned_count = 0
        skipped_count = 0
        errors = []
        
        for symbol in orphaned_symbols:
            data = analysis[symbol]
            exit_orders = data['orders_detail']['exit']
            
            print(f"\n📊 {symbol} - {len(exit_orders)} сиротских ордеров:")
            for order in exit_orders:
                order_type = order['type']
                side = order['side']
                price_info = ""
                if order['price']:
                    price_info = f" @ {order['price']:.6f}"
                elif order['stop_price']:
                    price_info = f" @ {order['stop_price']:.6f}"
                
                print(f"  • {order_type} {side} {order['quantity']}{price_info} (#{order['order_id']})")
            
            # Запрос подтверждения
            if not auto_confirm:
                response = input(f"\n🗑️ Удалить {len(exit_orders)} ордеров для {symbol}? (y/n/q): ").lower().strip()
                
                if response == 'q':
                    print("❌ Операция прервана пользователем")
                    break
                elif response != 'y':
                    print(f"⏭️ Пропускаем {symbol}")
                    skipped_count += 1
                    continue
            
            # Удаляем ордера
            if dry_run:
                print(f"🔍 [DRY RUN] Будет удалено {len(exit_orders)} ордеров для {symbol}")
                cleaned_count += len(exit_orders)
            else:
                symbol_errors = self._cancel_orders(symbol, exit_orders)
                if symbol_errors:
                    errors.extend(symbol_errors)
                else:
                    cleaned_count += len(exit_orders)
                    print(f"✅ Удалено {len(exit_orders)} ордеров для {symbol}")
        
        return {
            "cleaned": cleaned_count,
            "skipped": skipped_count,
            "errors": errors
        }
    
    def _cancel_orders(self, symbol: str, orders: List[Dict]) -> List[str]:
        """Отменяет список ордеров для символа"""
        errors = []
        
        for order in orders:
            try:
                self.client.futures_cancel_order(
                    symbol=symbol,
                    orderId=order['order_id']
                )
                logger.info(f"✅ Отменен ордер {order['order_id']} для {symbol}")
                
            except BinanceAPIException as e:
                error_msg = f"❌ Ошибка отмены ордера {order['order_id']} для {symbol}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
            except Exception as e:
                error_msg = f"❌ Неожиданная ошибка отмены ордера {order['order_id']} для {symbol}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        return errors
    
    def save_analysis_report(self, analysis_data: Dict, filename: str) -> None:
        """Сохраняет отчет анализа в файл"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Отчет сохранен в {filename}")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения отчета: {e}")


def main():
    """Точка входа в приложение"""
    parser = argparse.ArgumentParser(description='Очистка сиротских ордеров на Binance')
    parser.add_argument('--auto-confirm', '-y', action='store_true',
                       help='Автоматически подтверждать все удаления (ОСТОРОЖНО!)')
    parser.add_argument('--dry-run', '-d', action='store_true',
                       help='Показать что будет удалено, но не удалять')
    parser.add_argument('--report-only', '-r', action='store_true',
                       help='Только показать отчет без возможности удаления')
    parser.add_argument('--save', '-s', type=str,
                       help='Сохранить отчет в JSON файл')
    
    args = parser.parse_args()
    
    try:
        logger.info("🧹 Запуск Orders Cleaner...")
        
        # Создаем экземпляр cleaner
        cleaner = OrdersCleaner()
        
        if not cleaner.client:
            logger.error("❌ Не удалось подключиться к Binance API")
            sys.exit(1)
        
        # Анализируем ордера
        analysis_data = cleaner.analyze_orphaned_orders()
        
        if "error" in analysis_data:
            logger.error(f"❌ Ошибка анализа: {analysis_data['error']}")
            sys.exit(1)
        
        # Показываем отчет
        cleaner.print_analysis_report(analysis_data)
        
        # Сохраняем отчет если нужно
        if args.save:
            cleaner.save_analysis_report(analysis_data, args.save)
        
        # Только отчет - выходим
        if args.report_only:
            logger.info("📋 Режим только отчета - завершение")
            sys.exit(0)
        
        # Проверяем есть ли что чистить
        orphaned_count = analysis_data['orphaned_symbols']
        if orphaned_count == 0:
            logger.info("✅ Сиротских ордеров не найдено")
            sys.exit(0)
        
        # Предупреждение для автоподтверждения
        if args.auto_confirm and not args.dry_run:
            print("\n⚠️ ВНИМАНИЕ: Включен режим автоподтверждения!")
            print("⚠️ Все сиротские ордера будут удалены БЕЗ дополнительных вопросов!")
            response = input("⚠️ Продолжить? (yes/no): ").lower().strip()
            if response != 'yes':
                print("❌ Операция отменена")
                sys.exit(0)
        
        # Выполняем очистку
        cleanup_result = cleaner.cleanup_orphaned_orders(
            analysis_data, 
            auto_confirm=args.auto_confirm,
            dry_run=args.dry_run
        )
        
        # Результаты очистки
        print("\n" + "=" * 60)
        print("📊 РЕЗУЛЬТАТЫ ОЧИСТКИ")
        print("=" * 60)
        print(f"✅ Удалено ордеров: {cleanup_result['cleaned']}")
        print(f"⏭️ Пропущено символов: {cleanup_result['skipped']}")
        print(f"❌ Ошибок: {len(cleanup_result['errors'])}")
        
        if cleanup_result['errors']:
            print("\n❌ ОШИБКИ:")
            for error in cleanup_result['errors']:
                print(f"  • {error}")
        
        if args.dry_run:
            print("\n🔍 Это был пробный запуск - ничего не было удалено")
        
        print("=" * 60)
        
        # Код выхода
        if cleanup_result['errors']:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("👋 Операция прервана пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
