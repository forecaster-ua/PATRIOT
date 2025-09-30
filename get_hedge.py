#!/usr/bin/env python3
"""
Scheduled Hedge Entry Generator
Автоматически запускает анализ хедж-сигналов с заданными интервалами
и автоматически отправляет результаты в Telegram.

Алгоритм таймера (кратность от 00:00 локального дня):
- TZ: Europe/Kyiv
- Выполняется каждые 15 минут (900 секунд)
- Автоматически выбирает опцию 2 (анализ всех тестовых тикеров)
- Автоматически подтверждает отправку в Telegram
"""

import time
import datetime
import math
import sys
import os
import subprocess
from pathlib import Path
import signal
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hedge_scheduler.log'),
        logging.StreamHandler()
    ]
)

class HedgeScheduler:
    def __init__(self, interval_minutes=15, timezone='Europe/Kyiv'):
        """
        Инициализация планировщика
        
        Args:
            interval_minutes (int): Интервал выполнения в минутах
            timezone (str): Временная зона
        """
        self.interval_seconds = interval_minutes * 60
        self.timezone = timezone
        self.script_path = Path(__file__).parent / "get_hedge_entry_generator.py"
        self.running = True
        
        # Настройка обработчиков сигналов для graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logging.info(f"🚀 Hedge Scheduler инициализирован")
        logging.info(f"   📍 Интервал: {interval_minutes} минут ({self.interval_seconds} секунд)")
        logging.info(f"   🌍 Временная зона: {timezone}")
        logging.info(f"   📂 Скрипт: {self.script_path}")
        
    def signal_handler(self, signum, frame):
        """Обработчик сигналов для корректного завершения"""
        logging.info(f"📡 Получен сигнал {signum}, завершаю работу...")
        self.running = False
        
    def get_local_midnight_timestamp(self) -> float:
        """Получает timestamp локальной полуночи сегодня"""
        try:
            # Устанавливаем временную зону для расчетов
            os.environ['TZ'] = self.timezone
            time.tzset()
            
            # Получаем текущее локальное время
            now = datetime.datetime.now()
            
            # Находим полуночь сегодня (00:00:00)
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Возвращаем timestamp
            return midnight.timestamp()
            
        except Exception as e:
            logging.error(f"❌ Ошибка при получении полуночи: {e}")
            # Fallback: используем системное время
            now = time.time()
            midnight = now - (now % 86400)  # 86400 секунд в дне
            return midnight
            
    def calculate_next_tick(self) -> float:
        """
        Рассчитывает следующий момент выполнения по алгоритму
        
        Returns:
            float: Timestamp следующего выполнения
        """
        now = time.time()
        midnight = self.get_local_midnight_timestamp()
        elapsed = now - midnight
        step = self.interval_seconds
        
        # Проверяем, попали ли мы ровно в кратную точку
        if elapsed % step == 0:
            next_tick = now
            logging.info("🎯 Попали ровно в кратную точку - выполняем немедленно")
        else:
            # Рассчитываем следующую кратную точку
            next_tick = midnight + math.ceil(elapsed / step) * step
            
        return next_tick
        
    def format_time(self, timestamp: float) -> str:
        """Форматирует timestamp в читаемое время"""
        # Устанавливаем временную зону
        os.environ['TZ'] = self.timezone
        time.tzset()
        
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
        
    def run_hedge_analyzer(self) -> bool:
        """
        Запускает анализатор хедж-сигналов с автоматическими ответами
        
        Returns:
            bool: True если успешно, False если ошибка
        """
        if not self.script_path.exists():
            logging.error(f"❌ Скрипт не найден: {self.script_path}")
            return False
            
        try:
            logging.info("🔍 Запуск hedge analyzer...")
            
            # Подготавливаем команду
            cmd = [sys.executable, str(self.script_path)]
            
            # Запускаем процесс с автоматическими ответами
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.script_path.parent
            )
            
            try:
                # Отправляем автоматические ответы:
                # "2" - выбираем опцию 2 (анализ всех тестовых тикеров)  
                # "y" - подтверждаем отправку в Telegram
                input_sequence = "2\ny\n"
                
                stdout, stderr = process.communicate(input=input_sequence, timeout=300)  # 5 минут timeout
                
                if process.returncode == 0:
                    logging.info("✅ Hedge analyzer завершился успешно")
                    
                    # Логируем важные части вывода
                    if "✅ Анализ завершен" in stdout:
                        logging.info("📊 Анализ тикеров завершен")
                        
                    if "отправлено в Telegram" in stdout or "сообщений успешно отправлено" in stdout:
                        logging.info("📱 Сообщения отправлены в Telegram")
                        
                    return True
                else:
                    logging.error(f"❌ Hedge analyzer завершился с ошибкой (код: {process.returncode})")
                    if stderr:
                        logging.error(f"STDERR: {stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                logging.error("⏱️ Timeout: hedge analyzer выполнялся слишком долго")
                process.kill()
                return False
                
        except Exception as e:
            logging.error(f"❌ Ошибка при запуске hedge analyzer: {e}")
            return False
            
    def run_scheduler(self):
        """Основной цикл планировщика"""
        logging.info("🎯 Запуск планировщика hedge signals...")
        
        # Рассчитываем первое выполнение
        next_tick = self.calculate_next_tick()
        
        while self.running:
            try:
                current_time = time.time()
                
                # Проверяем, не пора ли выполняться
                if current_time >= next_tick:
                    execution_time = self.format_time(next_tick)
                    logging.info(f"⏰ Время выполнения: {execution_time}")
                    
                    # Запускаем анализ
                    success = self.run_hedge_analyzer()
                    
                    if success:
                        logging.info("✅ Цикл анализа завершен успешно")
                    else:
                        logging.warning("⚠️ Цикл анализа завершился с ошибками")
                    
                    # Рассчитываем следующее выполнение
                    next_tick += self.interval_seconds
                    
                    # Проверяем на перерасход времени
                    current_after_execution = time.time()
                    if current_after_execution > next_tick:
                        # Перерасход времени - прыгаем на следующий слот
                        midnight = self.get_local_midnight_timestamp()
                        elapsed = current_after_execution - midnight
                        next_tick = midnight + math.ceil(elapsed / self.interval_seconds) * self.interval_seconds
                        logging.warning(f"⚠️ Перерасход времени, прыгаем на {self.format_time(next_tick)}")
                    
                    next_execution = self.format_time(next_tick)
                    logging.info(f"⏭️ Следующее выполнение: {next_execution}")
                
                # Спим до следующей проверки (каждые 10 секунд)
                time.sleep(10)
                
            except KeyboardInterrupt:
                logging.info("🛑 Получен сигнал прерывания")
                break
            except Exception as e:
                logging.error(f"❌ Ошибка в основном цикле: {e}")
                time.sleep(30)  # Ждем перед повтором при ошибке
                
        logging.info("🏁 Планировщик hedge signals остановлен")

def main():
    """Главная функция"""
    # Проверяем аргументы командной строки
    interval_minutes = 15  # По умолчанию 15 минут
    
    if len(sys.argv) > 1:
        try:
            interval_minutes = int(sys.argv[1])
            if interval_minutes <= 0:
                raise ValueError("Интервал должен быть положительным")
        except ValueError as e:
            print(f"❌ Ошибка в аргументе интервала: {e}")
            print("Использование: python3 get_hedge.py [интервал_в_минутах]")
            print("Пример: python3 get_hedge.py 15")
            sys.exit(1)
    
    print(f"""
🔄 Hedge Signals Scheduler
=========================
📍 Интервал: {interval_minutes} минут
🌍 Временная зона: Europe/Kyiv
📂 Рабочая директория: {Path.cwd()}

Для остановки нажмите Ctrl+C
    """)
    
    # Создаем и запускаем планировщик
    scheduler = HedgeScheduler(interval_minutes=interval_minutes)
    
    try:
        scheduler.run_scheduler()
    except KeyboardInterrupt:
        print("\n🛑 Остановка планировщика...")
    except Exception as e:
        logging.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
