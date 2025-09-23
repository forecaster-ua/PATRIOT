#!/usr/bin/env python3
"""
Простейший скрипт для запроса сигнала по BTCUSDT 15M
без зависимостей от других модулей проекта
"""

import json
import requests
from datetime import datetime
from pathlib import Path

def fetch_btc_signal():
    """
    Запрашивает сигнал по BTCUSDT 15M напрямую через API
    и сохраняет в current_data_examp.json
    """
    # Настройки API
    base_url = "http://194.135.94.212:8001/confirm-trade"
    headers = {
        "Authorization": "Bearer maxa-secret-123",
        "Content-Type": "application/json"
    }
    
    # Параметры запроса
    params = {
        "pair": "BTCUSDT",
        "timeframe": "15m"
    }
    
    try:
        print(f"🔄 Запрос сигнала для {params['pair']} {params['timeframe']}...")
        
        # Выполняем запрос
        url = f"{base_url}/signal"
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Добавляем метку времени запроса
            data['fetch_timestamp'] = datetime.now().isoformat()
            
            # Сохраняем в JSON файл
            output_file = Path(__file__).parent / "current_data_examp.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Данные сохранены в {output_file.name}")
            print(f"📊 Сигнал: {data.get('signal', 'N/A')}")
            print(f"💰 Текущая цена: {data.get('current_price', 'N/A')}")
            print(f"🎯 Цена входа: {data.get('entry_price', 'N/A')}")
            print(f"🎲 Уверенность: {data.get('confidence', 0) * 100:.1f}%")
            
            return True
            
        else:
            print(f"❌ Ошибка API: {response.status_code}")
            print(f"📝 Ответ: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def main():
    """Основная функция"""
    print("=" * 50)
    print("🚀 PATRIOT Signal Fetcher")
    print("=" * 50)
    
    success = fetch_btc_signal()
    
    if success:
        print("\n🎉 Успешно выполнено!")
    else:
        print("\n💥 Выполнение завершилось с ошибкой!")
        exit(1)

if __name__ == "__main__":
    main()
