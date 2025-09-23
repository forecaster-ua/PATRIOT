#!/usr/bin/env python3
"""
Скрипт для очистки устаревших ордеров из orders_watchdog_state.json
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import shutil

def backup_state_file():
    """Создает резервную копию файла состояния"""
    state_file = Path('orders_watchdog_state.json')
    if state_file.exists():
        backup_name = f"orders_watchdog_state_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        shutil.copy2(state_file, backup_name)
        print(f"✅ Создан бэкап: {backup_name}")
        return True
    else:
        print("❌ Файл состояния не найден")
        return False

def load_watchdog_state():
    """Загружает текущее состояние watchdog"""
    try:
        with open('orders_watchdog_state.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Ошибка загрузки состояния: {e}")
        return None

def get_exchange_active_orders():
    """Получает список активных ордеров с биржи (заглушка - нужна реальная реализация)"""
    # TODO: Здесь должна быть реальная проверка через Binance API
    # Пока возвращаем пустой список для демонстрации
    return []

def clean_old_orders(data, cutoff_days=7):
    """Очищает старые ордера с проблемным статусом"""
    if not data or 'watched_orders' not in data:
        return data
    
    cutoff_date = datetime.now() - timedelta(days=cutoff_days)
    original_count = len(data['watched_orders'])
    
    cleaned_orders = []
    removed_count = 0
    
    for order in data['watched_orders']:
        # Парсим дату создания
        try:
            created_at = datetime.fromisoformat(order.get('created_at', ''))
        except:
            created_at = datetime.now()  # Если дата невалидна, считаем новым
        
        # Условия для удаления:
        should_remove = (
            # Ордера с ошибками SL/TP старше 7 дней
            (order.get('status') == 'SL_TP_ERROR' and created_at < cutoff_date) or
            # Ордера без связанных позиций на бирже
            (order.get('status') in ['CANCELLED', 'REJECTED', 'EXPIRED']) or
            # Очень старые ордера (более 30 дней) независимо от статуса
            (created_at < datetime.now() - timedelta(days=30)) or
            # Ордера с нулевыми ID (явно проблемные)
            (not order.get('order_id') or order.get('order_id') == 'None')
        )
        
        if should_remove:
            removed_count += 1
            print(f"🗑️  Удаляем: {order.get('symbol')} | {order.get('order_id')} | {order.get('status')} | {created_at.strftime('%Y-%m-%d')}")
        else:
            cleaned_orders.append(order)
    
    data['watched_orders'] = cleaned_orders
    
    print(f"\n📊 РЕЗУЛЬТАТ ОЧИСТКИ:")
    print(f"   Было ордеров: {original_count}")
    print(f"   Удалено: {removed_count}")  
    print(f"   Осталось: {len(cleaned_orders)}")
    
    return data

def save_cleaned_state(data):
    """Сохраняет очищенное состояние"""
    try:
        with open('orders_watchdog_state.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("✅ Очищенное состояние сохранено")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False

def show_statistics(data):
    """Показывает статистику по статусам ордеров"""
    if not data or 'watched_orders' not in data:
        return
    
    status_counts = {}
    for order in data['watched_orders']:
        status = order.get('status', 'UNKNOWN')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"\n📈 СТАТИСТИКА ПО СТАТУСАМ:")
    for status, count in sorted(status_counts.items()):
        print(f"   {status}: {count}")

def main():
    """Главная функция очистки"""
    print("🧹 НАЧИНАЕМ ОЧИСТКУ УСТАРЕВШИХ ОРДЕРОВ")
    print("=" * 50)
    
    # 1. Создаем бэкап
    if not backup_state_file():
        return
    
    # 2. Загружаем текущее состояние
    data = load_watchdog_state()
    if not data:
        return
    
    # 3. Показываем статистику ДО очистки
    print(f"\n📊 СТАТИСТИКА ДО ОЧИСТКИ:")
    show_statistics(data)
    
    # 4. Очищаем старые ордера
    cleaned_data = clean_old_orders(data)
    
    # 5. Показываем статистику ПОСЛЕ очистки
    print(f"\n📊 СТАТИСТИКА ПОСЛЕ ОЧИСТКИ:")
    show_statistics(cleaned_data)
    
    # 6. Сохраняем результат
    if save_cleaned_state(cleaned_data):
        print(f"\n✅ ОЧИСТКА ЗАВЕРШЕНА УСПЕШНО!")
    else:
        print(f"\n❌ ОШИБКА ПРИ СОХРАНЕНИИ!")

if __name__ == "__main__":
    main()
