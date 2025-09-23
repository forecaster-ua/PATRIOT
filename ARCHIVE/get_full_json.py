import json
from api_client import api_client

def main():
    pair = "ETHUSDT"  # Можно заменить на нужный тикер
    timeframe = "4h"   # Можно заменить на нужный таймфрейм
    data = api_client.get_signal(pair, timeframe)
    if data:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        # Печатаем полный адрес запроса
        print(f"Ответ получен от: {api_client.base_url}/signal?pair={pair}&timeframe={timeframe}")
    else:
        print("Не удалось получить данные от API")

if __name__ == "__main__":
    main()
