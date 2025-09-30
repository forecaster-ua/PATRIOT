#!/usr/bin/env python3
"""
Тест алгоритма расчета времени для hedge scheduler
"""

import time
import datetime
import math
import os

def test_timing_algorithm():
    """Тестирует алгоритм расчета времени"""
    
    # Устанавливаем временную зону
    timezone = 'Europe/Kyiv'
    os.environ['TZ'] = timezone
    time.tzset()
    
    # Получаем текущее время
    now = time.time()
    current_dt = datetime.datetime.fromtimestamp(now)
    
    # Получаем полуночь сегодня
    midnight_dt = current_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    midnight = midnight_dt.timestamp()
    
    print(f"🕐 Текущее время: {current_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"🌙 Полночь сегодня: {midnight_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Тестируем разные интервалы
    intervals = [15, 30, 60]  # минуты
    
    for interval_min in intervals:
        step = interval_min * 60  # секунды
        elapsed = now - midnight
        
        print(f"\n📊 Тест для интервала {interval_min} минут:")
        print(f"   Прошло с полуночи: {elapsed/3600:.2f} часов ({int(elapsed)} секунд)")
        
        if elapsed % step == 0:
            next_tick = now
            print(f"   🎯 Попадание в кратную точку - выполняем немедленно!")
        else:
            next_tick = midnight + math.ceil(elapsed / step) * step
        
        next_dt = datetime.datetime.fromtimestamp(next_tick)
        wait_seconds = next_tick - now
        
        print(f"   ⏰ Следующее выполнение: {next_dt.strftime('%H:%M:%S')}")
        print(f"   ⏱️ Ожидание: {wait_seconds:.0f} секунд ({wait_seconds/60:.1f} минут)")
        
        # Показываем следующие несколько выполнений
        print(f"   📅 Следующие выполнения:")
        for i in range(1, 4):
            future_tick = next_tick + (i * step)
            future_dt = datetime.datetime.fromtimestamp(future_tick)
            print(f"      {i+1}. {future_dt.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    test_timing_algorithm()