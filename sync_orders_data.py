#!/usr/bin/env python3
"""
Скрипт для синхронизации данных между orders_watchdog_state.json и БД
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Set
from pathlib import Path

def get_db_connection():
    """Создает соединение с БД"""
    return sqlite3.connect('signals.db', timeout=10)

def load_json_orders() -> List[Dict]:
    """Загружает ордера из JSON файла"""
    try:
        with open('orders_watchdog_state.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('watched_orders', [])
    except Exception as e:
        print(f"❌ Ошибка загрузки JSON: {e}")
        return []

def load_db_orders() -> List[Dict]:
    """Загружает ордера из БД"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT symbol, order_id, side, position_side, quantity, price, 
                   signal_type, stop_loss, take_profit, status, created_at, 
                   filled_at, sl_order_id, tp_order_id, timestamp
            FROM watchdog_orders
        """)
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"❌ Ошибка загрузки из БД: {e}")
        return []

def compare_orders(json_orders: List[Dict], db_orders: List[Dict]) -> Dict:
    """Сравнивает ордера между JSON и БД"""
    
    # Создаем множества order_id для быстрого поиска
    json_ids = {order.get('order_id') for order in json_orders if order.get('order_id')}
    db_ids = {order.get('order_id') for order in db_orders if order.get('order_id')}
    
    # Находим различия
    only_in_json = json_ids - db_ids  # Есть в JSON, нет в БД
    only_in_db = db_ids - json_ids    # Есть в БД, нет в JSON
    in_both = json_ids & db_ids       # Есть в обоих
    
    return {
        'only_in_json': only_in_json,
        'only_in_db': only_in_db,
        'in_both': in_both,
        'total_json': len(json_ids),
        'total_db': len(db_ids)
    }

def sync_missing_to_db(json_orders: List[Dict], missing_ids: Set[str]):
    """Добавляет недостающие ордера в БД"""
    if not missing_ids:
        return 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    added_count = 0
    
    for order in json_orders:
        order_id = order.get('order_id')
        if order_id in missing_ids:
            try:
                cursor.execute("""
                    INSERT INTO watchdog_orders 
                    (symbol, order_id, side, position_side, quantity, price, 
                     signal_type, stop_loss, take_profit, status, created_at, 
                     filled_at, sl_order_id, tp_order_id, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order.get('symbol'),
                    order.get('order_id'),
                    order.get('side'),
                    order.get('position_side'),
                    order.get('quantity'),
                    order.get('price'),
                    order.get('signal_type'),
                    order.get('stop_loss'),
                    order.get('take_profit'),
                    order.get('status'),
                    order.get('created_at'),
                    order.get('filled_at'),
                    order.get('sl_order_id'),
                    order.get('tp_order_id'),
                    order.get('timestamp', datetime.now().isoformat())
                ))
                added_count += 1
                print(f"➕ Добавлен в БД: {order.get('symbol')} | {order_id}")
            except Exception as e:
                print(f"❌ Ошибка добавления {order_id}: {e}")
    
    conn.commit()
    conn.close()
    return added_count

def update_json_from_db(json_orders: List[Dict], db_orders: List[Dict], missing_ids: Set[str]) -> List[Dict]:
    """Обновляет JSON данные из БД для недостающих ордеров"""
    if not missing_ids:
        return json_orders
    
    # Создаем словарь БД ордеров для быстрого поиска
    db_orders_dict = {order.get('order_id'): order for order in db_orders}
    
    # Добавляем недостающие ордера в JSON
    updated_orders = json_orders.copy()
    added_count = 0
    
    for order_id in missing_ids:
        if order_id in db_orders_dict:
            db_order = db_orders_dict[order_id]
            
            # Преобразуем формат БД в формат JSON
            json_order = {
                'symbol': db_order.get('symbol'),
                'order_id': db_order.get('order_id'),
                'side': db_order.get('side'),
                'position_side': db_order.get('position_side'),
                'quantity': db_order.get('quantity'),
                'price': db_order.get('price'),
                'signal_type': db_order.get('signal_type'),
                'stop_loss': db_order.get('stop_loss'),
                'take_profit': db_order.get('take_profit'),
                'status': db_order.get('status'),
                'created_at': db_order.get('created_at'),
                'filled_at': db_order.get('filled_at'),
                'sl_order_id': db_order.get('sl_order_id'),
                'tp_order_id': db_order.get('tp_order_id'),
                'sl_tp_attempts': 0,  # Значения по умолчанию для полей, которых нет в БД
                'expires_at': None,
                'source_timeframe': None,
                'trailing_triggered': False
            }
            
            updated_orders.append(json_order)
            added_count += 1
            print(f"➕ Добавлен в JSON: {db_order.get('symbol')} | {order_id}")
    
    return updated_orders

def save_updated_json(orders: List[Dict]):
    """Сохраняет обновленный JSON файл"""
    try:
        data = {
            'timestamp': datetime.now().isoformat(),
            'watched_orders': orders
        }
        
        with open('orders_watchdog_state.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print("✅ Обновленный JSON сохранен")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения JSON: {e}")
        return False

def show_sync_report(comparison: Dict, added_to_db: int, added_to_json: int):
    """Показывает отчет о синхронизации"""
    print(f"\n📊 ОТЧЕТ О СИНХРОНИЗАЦИИ:")
    print("=" * 40)
    print(f"📁 JSON ордеров: {comparison['total_json']}")
    print(f"🗄️  БД ордеров: {comparison['total_db']}")
    print(f"🔗 Синхронизированных: {len(comparison['in_both'])}")
    print(f"📁➡️🗄️  Добавлено в БД: {added_to_db}")
    print(f"🗄️➡️📁 Добавлено в JSON: {added_to_json}")
    
    if comparison['only_in_json']:
        print(f"\n📁 Только в JSON ({len(comparison['only_in_json'])}):")
        for order_id in list(comparison['only_in_json'])[:5]:  # Показываем первые 5
            print(f"   - {order_id}")
        if len(comparison['only_in_json']) > 5:
            print(f"   ... и еще {len(comparison['only_in_json']) - 5}")
    
    if comparison['only_in_db']:
        print(f"\n🗄️  Только в БД ({len(comparison['only_in_db'])}):")
        for order_id in list(comparison['only_in_db'])[:5]:  # Показываем первые 5
            print(f"   - {order_id}")
        if len(comparison['only_in_db']) > 5:
            print(f"   ... и еще {len(comparison['only_in_db']) - 5}")

def main():
    """Главная функция синхронизации"""
    print("🔄 НАЧИНАЕМ СИНХРОНИЗАЦИЮ JSON ↔ БД")
    print("=" * 50)
    
    # 1. Загружаем данные из обоих источников
    print("📂 Загружаем данные...")
    json_orders = load_json_orders()
    db_orders = load_db_orders()
    
    if not json_orders and not db_orders:
        print("❌ Нет данных для синхронизации")
        return
    
    # 2. Сравниваем данные
    print("🔍 Анализируем различия...")
    comparison = compare_orders(json_orders, db_orders)
    
    # 3. Синхронизируем недостающие данные
    print("🔄 Синхронизируем данные...")
    
    # Добавляем недостающие ордера в БД
    added_to_db = sync_missing_to_db(json_orders, comparison['only_in_json'])
    
    # Добавляем недостающие ордера в JSON
    updated_json_orders = update_json_from_db(json_orders, db_orders, comparison['only_in_db'])
    added_to_json = len(comparison['only_in_db'])
    
    # 4. Сохраняем обновленный JSON если были изменения
    if added_to_json > 0:
        save_updated_json(updated_json_orders)
    
    # 5. Показываем отчет
    show_sync_report(comparison, added_to_db, added_to_json)
    
    print(f"\n✅ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА!")

if __name__ == "__main__":
    main()
