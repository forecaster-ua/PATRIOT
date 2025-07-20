import time
import subprocess
from datetime import datetime, timedelta
import pytz
import sys
import os
import ctypes

def is_admin():
    """Проверяет права администратора"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_in_new_window(script_path):
    """Запускает скрипт в новом окне терминала"""
    try:
        if os.name == 'nt':
            if not os.path.exists(script_path):
                print(f"ОШИБКА: Файл {script_path} не найден!")
                return False
            
            subprocess.Popen(
                ['start', 'cmd', '/k', 'python', os.path.abspath(script_path)], 
                shell=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE
            )
            time.sleep(2)  # Даем время для запуска
            return True
    except Exception as e:
        print(f"ОШИБКА: {str(e)}")
        return False

def get_next_15min_interval():
    """Вычисляет следующий интервал, кратный 15 минутам"""
    now = datetime.now(pytz.utc)
    next_run = now.replace(second=0, microsecond=0) + timedelta(minutes=15)
    return next_run.replace(minute=(next_run.minute // 15) * 15)

def wait_until(target_time):
    """Ожидает наступления указанного времени"""
    while datetime.now(pytz.utc) < target_time:
        time_left = (target_time - datetime.now(pytz.utc)).total_seconds()
        sleep_time = min(time_left, 1)  # Проверяем каждую секунду
        if sleep_time > 0:
            time.sleep(sleep_time)

def main():
    print("15-минутный планировщик запущен (UTC)")
    print(f"Текущее время: {datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    if os.name == 'nt' and not is_admin():
        print("Предупреждение: Для лучшей работы запустите от имени администратора")

    # Первый запуск только если текущее время кратно 15 минутам
    now = datetime.now(pytz.utc)
    if now.minute % 15 == 0 and now.second < 10:  # Только в первые 10 секунд интервала
        print(f"\n=== Первый запуск в {now.strftime('%H:%M:%S UTC')} ===")
        run_in_new_window("ticker_monitor.py")
        time.sleep(1)

    while True:
        try:
            next_run = get_next_15min_interval()
            print(f"\nСледующий запуск в {next_run.strftime('%H:%M:%S UTC')}")
            
            wait_until(next_run)
            
            print(f"\n=== Запуск в {datetime.now(pytz.utc).strftime('%H:%M:%S UTC')} ===")
            run_in_new_window("ticker_monitor.py")
            
            # Защита от повторного запуска в том же интервале
            time.sleep(10)
            
        except KeyboardInterrupt:
            print("\nРабота планировщика остановлена")
            sys.exit(0)
        except Exception as e:
            print(f"\nОШИБКА: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    main()