#!/usr/bin/env python3
"""
Ручной синхронизатор - очистка ордеров из БД, которых нет на бирже
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Set
import sys
import os

# Добавляем текущую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from api_client import BinanceClient
    from config import BINANCE_API_KEY, BINANCE_SECRET_KEY, BINANCE_TESTNET
    API_AVAILABLE = True
    print("✅ API модули загружены")
except ImportError as e:
    print(f"⚠️ API недоступен: {e}")
    API_AVAILABLE = False

def get_db_connection():
    """Создает соединение с БД"""
    return sqlite3.connect('signals.db', timeout=10)

def load_db_orders() -> List[Dict]:
    """Загружает все ордера из БД"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, symbol, order_id, side, position_side, quantity, price, 
                   signal_type, stop_loss, take_profit, status, created_at, 
                   filled_at, sl_order_id, tp_order_id, timestamp
            FROM watchdog_orders
            ORDER BY timestamp DESC
        """)
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        db_orders = [dict(zip(columns, row)) for row in rows]
        print(f"📊 Загружено из БД: {len(db_orders)} ордеров")
        return db_orders
    except Exception as e:
        print(f"❌ Ошибка загрузки из БД: {e}")
        return []

def get_exchange_orders() -> Dict[str, Dict]:
    """Получает все открытые ордера с биржи"""
    if not API_AVAILABLE:
        print("❌ API недоступен - используем симуляцию")
        return simulate_exchange_orders()
    
    try:
        client = BinanceClient()
        
        # Получаем все открытые ордера
        if BINANCE_TESTNET:
            open_orders = client.client.futures_get_open_orders()
        else:
            open_orders = client.client.futures_get_open_orders()
        
        # Преобразуем в словарь для быстрого поиска
        exchange_orders = {}
        for order in open_orders:
            order_id = str(order['orderId'])
            exchange_orders[order_id] = {
                'symbol': order['symbol'],
                'order_id': order_id,
                'status': order['status'],
                'side': order['side'],
                'position_side': order.get('positionSide', 'BOTH'),
                'quantity': float(order['origQty']),
                'price': float(order['price']) if order['price'] != '0' else 0,
                'type': order['type']
            }
        
        print(f"📊 Загружено с биржи: {len(exchange_orders)} открытых ордеров")
        return exchange_orders
        
    except Exception as e:
        print(f"❌ Ошибка получения ордеров с биржи: {e}")
        print("🔄 Используем симуляцию...")
        return simulate_exchange_orders()

def simulate_exchange_orders() -> Dict[str, Dict]:
    """Симуляция ордеров с биржи (для тестирования без API)"""
    # Берем несколько случайных ордеров из БД как "существующие на бирже"
    db_orders = load_db_orders()
    
    # Симулируем что на бирже есть только последние 10 ордеров
    simulated_orders = {}
    for order in db_orders[:10]:  # Первые 10 как "существующие"
        order_id = str(order['order_id'])
        simulated_orders[order_id] = {
            'symbol': order['symbol'],
            'order_id': order_id,
            'status': 'NEW',  # Симулируем как активные
            'side': order['side'],
            'position_side': order['position_side'],
            'quantity': order['quantity'],
            'price': order['price'],
            'type': 'LIMIT'
        }
    
    print(f"🎭 СИМУЛЯЦИЯ: На бирже {len(simulated_orders)} ордеров из {len(db_orders)} в БД")
    return simulated_orders

def find_orphaned_orders(db_orders: List[Dict], exchange_orders: Dict[str, Dict]) -> List[Dict]:
    """Находит ордера, которые есть в БД, но нет на бирже"""
    orphaned = []
    
    for db_order in db_orders:
        order_id = str(db_order['order_id'])
        
        # Пропускаем ордера, которые уже помечены как завершенные
        if db_order['status'] in ['FILLED', 'CANCELED', 'CANCELLED', 'REJECTED', 'EXPIRED']:
            continue
        
        # Если ордера нет на бирже - это сирота
        if order_id not in exchange_orders:
            orphaned.append(db_order)
    
    return orphaned

def show_orphaned_report(orphaned_orders: List[Dict]):
    """Показывает отчет о сиротских ордерах"""
    if not orphaned_orders:
        print("✅ Сиротских ордеров не найдено!")
        return
    
    print(f"\n🔍 НАЙДЕНО СИРОТСКИХ ОРДЕРОВ: {len(orphaned_orders)}")
    print("=" * 80)
    print(f"{'№':<3} {'Symbol':<12} {'Order ID':<15} {'Status':<12} {'Created':<20}")
    print("-" * 80)
    
    for i, order in enumerate(orphaned_orders[:20], 1):  # Показываем первые 20
        created = order.get('created_at', 'N/A')[:19] if order.get('created_at') else 'N/A'
        print(f"{i:<3} {order['symbol']:<12} {order['order_id']:<15} {order['status']:<12} {created}")
    
    if len(orphaned_orders) > 20:
        print(f"... и еще {len(orphaned_orders) - 20} ордеров")

def cleanup_orphaned_orders(orphaned_orders: List[Dict], simulate_only: bool = True) -> int:
    """Очищает сиротские ордера из БД"""
    if not orphaned_orders:
        return 0
    
    if simulate_only:
        print(f"\n🎭 СИМУЛЯЦИЯ: Будет удалено {len(orphaned_orders)} ордеров")
        return len(orphaned_orders)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        removed_count = 0
        
        for order in orphaned_orders:
            cursor.execute("DELETE FROM watchdog_orders WHERE order_id = ?", (order['order_id'],))
            removed_count += 1
            print(f"🗑️  Удален: {order['symbol']} | {order['order_id']} | {order['status']}")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Удалено из БД: {removed_count} сиротских ордеров")
        return removed_count
        
    except Exception as e:
        print(f"❌ Ошибка удаления: {e}")
        return 0

def update_orders_status(exchange_orders: Dict[str, Dict]) -> int:
    """Обновляет статусы ордеров в БД на основе данных с биржи"""
    if not exchange_orders:
        return 0
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        updated_count = 0
        
        for order_id, exchange_order in exchange_orders.items():
            # Обновляем статус ордера в БД
            cursor.execute("""
                UPDATE watchdog_orders 
                SET status = ? 
                WHERE order_id = ? AND status != ?
            """, (exchange_order['status'], order_id, exchange_order['status']))
            
            if cursor.rowcount > 0:
                updated_count += 1
                print(f"🔄 Обновлен статус: {exchange_order['symbol']} | {order_id} → {exchange_order['status']}")
        
        conn.commit()
        conn.close()
        
        if updated_count > 0:
            print(f"\n✅ Обновлено статусов: {updated_count}")
        
        return updated_count
        
    except Exception as e:
        print(f"❌ Ошибка обновления статусов: {e}")
        return 0

def show_db_stats():
    """Показывает статистику по БД"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute("SELECT COUNT(*) FROM watchdog_orders")
        total_orders = cursor.fetchone()[0]
        
        # По статусам
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM watchdog_orders 
            GROUP BY status 
            ORDER BY COUNT(*) DESC
        """)
        status_stats = cursor.fetchall()
        
        conn.close()
        
        print(f"\n📊 СТАТИСТИКА БД:")
        print(f"   Всего ордеров: {total_orders}")
        print(f"   По статусам:")
        for status, count in status_stats:
            print(f"     {status}: {count}")
            
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")

def main():
    """Главная функция синхронизации"""
    print("🔄 РУЧНОЙ СИНХРОНИЗАТОР ОРДЕРОВ")
    print("=" * 50)
    print("Очищает ордера из БД, которых нет на бирже")
    
    # 1. Показываем текущую статистику БД
    show_db_stats()
    
    # 2. Загружаем данные
    print(f"\n📂 Загружаем данные...")
    db_orders = load_db_orders()
    exchange_orders = get_exchange_orders()
    
    if not db_orders:
        print("❌ Нет ордеров в БД")
        return
    
    # 3. Обновляем статусы ордеров из биржи
    print(f"\n🔄 Обновляем статусы...")
    updated_count = update_orders_status(exchange_orders)
    
    # 4. Находим сиротские ордера
    print(f"\n🔍 Ищем сиротские ордера...")
    orphaned_orders = find_orphaned_orders(db_orders, exchange_orders)
    
    # 5. Показываем отчет
    show_orphaned_report(orphaned_orders)
    
    # 6. Запрашиваем подтверждение на удаление
    if orphaned_orders:
        print(f"\n❓ Удалить {len(orphaned_orders)} сиротских ордеров из БД?")
        print("   [y] - Да, удалить")
        print("   [s] - Симуляция (показать что будет удалено)")
        print("   [n] - Нет, пропустить")
        
        choice = input("Ваш выбор: ").lower().strip()
        
        if choice == 'y':
            removed = cleanup_orphaned_orders(orphaned_orders, simulate_only=False)
            print(f"\n✅ РЕАЛЬНОЕ УДАЛЕНИЕ: {removed} ордеров удалено")
        elif choice == 's':
            removed = cleanup_orphaned_orders(orphaned_orders, simulate_only=True)
            print(f"\n🎭 СИМУЛЯЦИЯ ЗАВЕРШЕНА: {removed} ордеров было бы удалено")
        else:
            print("\n⏭️  Удаление пропущено")
    
    # 7. Показываем финальную статистику
    print(f"\n📊 ФИНАЛЬНАЯ СТАТИСТИКА:")
    show_db_stats()
    
    print(f"\n✅ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА!")

if __name__ == "__main__":
    main()
