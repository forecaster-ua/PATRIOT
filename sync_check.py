#!/usr/bin/env python3
"""
Orders Watchdog Sync Check
==========================

Утилита для проверки синхронизации состояния Orders Watchdog с биржей Binance.
Выполняет детальную сверку открытых ордеров и позиций.

Использование:
python sync_check.py [--report] [--fix]

--report  : детальный отчет в консоль
--fix     : автоматическое исправление найденных проблем (НЕ РЕАЛИЗОВАНО)

Author: HEDGER
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Dict

# Локальные импорты
from orders_watchdog import OrdersWatchdog
from utils import logger


def main():
    parser = argparse.ArgumentParser(description='Проверка синхронизации Orders Watchdog с биржей')
    parser.add_argument('--report', '-r', action='store_true', 
                       help='Показать детальный отчет')
    parser.add_argument('--json', '-j', action='store_true',
                       help='Вывести отчет в JSON формате')
    parser.add_argument('--save', '-s', type=str,
                       help='Сохранить отчет в файл')
    
    args = parser.parse_args()
    
    try:
        logger.info("🔍 Запуск проверки синхронизации...")
        
        # Создаем экземпляр watchdog (только для проверки)
        watchdog = OrdersWatchdog()
        
        if not watchdog.client:
            logger.error("❌ Не удалось подключиться к Binance API")
            sys.exit(1)
        
        # Выполняем проверку синхронизации  
        sync_report = watchdog.check_exchange_sync()
        
        if args.json:
            # Вывод в JSON формате
            print(json.dumps(sync_report, indent=2, ensure_ascii=False))
        elif args.report:
            # Детальный отчет
            watchdog.print_sync_report(sync_report)
        else:
            # Краткий отчет
            print_brief_report(sync_report)
        
        # Сохранение в файл
        if args.save:
            with open(args.save, 'w', encoding='utf-8') as f:
                json.dump(sync_report, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Отчет сохранен в {args.save}")
        
        # Завершаем с кодом ошибки если есть расхождения
        if sync_report.get('discrepancies'):
            sys.exit(1)
        else:
            logger.info("✅ Все синхронизировано!")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"💥 Ошибка проверки синхронизации: {e}")
        sys.exit(1)


def print_brief_report(sync_report: Dict) -> None:
    """Выводит краткий отчет о синхронизации"""
    if "error" in sync_report:
        print(f"❌ Ошибка: {sync_report['error']}")
        return
    
    print("=" * 50)
    print("📊 КРАТКИЙ ОТЧЕТ О СИНХРОНИЗАЦИИ")
    print("=" * 50)
    
    # Основные метрики
    print(f"📋 Ордеров на бирже: {len(sync_report['exchange_orders'])}")
    print(f"📍 Открытых позиций: {len(sync_report['exchange_positions'])}")
    print(f"👁️ Отслеживаемых ордеров: {sync_report['local_state']['total_orders']}")
    
    # Расхождения
    discrepancies = sync_report.get('discrepancies', [])
    if discrepancies:
        print(f"⚠️ Найдено расхождений: {len(discrepancies)}")
        
        # Группируем по типам
        by_type = {}
        for disc in discrepancies:
            disc_type = disc['type']
            by_type[disc_type] = by_type.get(disc_type, 0) + 1
        
        for disc_type, count in by_type.items():
            print(f"  • {disc_type}: {count}")
    else:
        print("✅ Расхождений не найдено")
    
    print("=" * 50)


if __name__ == "__main__":
    main()
