#!/usr/bin/env python3
"""
Простой скрипт для запроса сигнала по BTCUSDT 15M
и сохранения полученных данных в current_data_examp.json
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Добавляем текущую директорию в путь для импорта модулей
sys.path.append(str(Path(__file__).parent))

from api_client import api_client
from utils import logger

def fetch_and_save_signal():
    """
    Запрашивает сигнал по BTCUSDT 15M и сохраняет в JSON файл
    """
    try:
        logger.info("Запрос сигнала для BTCUSDT 15M...")
        
        # Запрашиваем сигнал
        signal_data = api_client.get_signal("BTCUSDT", "4h")
        
        if signal_data is None:
            logger.error("Не удалось получить данные сигнала")
            return False
        
        # Добавляем метку времени запроса
        signal_data['fetch_timestamp'] = datetime.now().isoformat()
        
        # Путь к файлу для сохранения
        output_file = Path(__file__).parent / "current_data_examp.json"
        
        # Сохраняем данные в JSON файл
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(signal_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Данные сигнала сохранены в {output_file}")
        logger.info(f"Получен сигнал: {signal_data.get('signal')} для {signal_data.get('pair')} {signal_data.get('timeframe')}")
        logger.info(f"Текущая цена: {signal_data.get('current_price')}")
        logger.info(f"Цена входа: {signal_data.get('entry_price')}")
        logger.info(f"Уверенность: {signal_data.get('confidence', 0) * 100:.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при запросе сигнала: {e}")
        return False

def main():
    """Основная функция"""
    print("Запуск скрипта для получения сигнала BTCUSDT 15M...")
    
    success = fetch_and_save_signal()
    
    if success:
        print("✅ Сигнал успешно получен и сохранен в current_data_examp.json")
    else:
        print("❌ Не удалось получить сигнал")
        sys.exit(1)

if __name__ == "__main__":
    main()
