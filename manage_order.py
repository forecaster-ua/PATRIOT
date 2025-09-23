import sys
import time
import os
from binance.client import Client
from binance.exceptions import BinanceAPIException
from config import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from orders_watchdog import OrdersWatchdog

# --- Инициализация Binance клиента ---
client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=BINANCE_TESTNET)
orders_watchdog = OrdersWatchdog()

# --- Получение позиций и ордеров из Watchdog ---
def get_position(ticker):
    watched = orders_watchdog.get_watched_symbols()
    pos = watched.get(ticker)
    if pos:
        return [pos]
    # Если не найдено в Watchdog — ищем на Binance Futures среди всех позиций
    positions = client.futures_position_information()
    found = []
    for p in positions:
        symbol = p.get('symbol', '').upper()
        amt = float(p.get('positionAmt', 0))
        side = p.get('positionSide', '-')
        price = p.get('markPrice', '-')
        if symbol == ticker and amt != 0:
            found.append({
                'positionAmt': amt,
                'side': side,
                'stop_order': {},
                'take_order': {},
                'current_price': float(price)
            })
    return found

def print_orders(ticker):
    pos_list = get_position(ticker)
    if not pos_list:
        print("ТИКЕР без позиции.")
        return
    for pos in pos_list:
        position_amt = getattr(pos, 'positionAmt', None) or pos.get('positionAmt', None)
        if not position_amt or position_amt == 0:
            continue
        stop_order = getattr(pos, 'stop_order', None) or pos.get('stop_order', {})
        take_order = getattr(pos, 'take_order', None) or pos.get('take_order', {})
        current_price = getattr(pos, 'current_price', None) or pos.get('current_price', None)
        side = getattr(pos, 'side', None) or pos.get('side', '-')
        print(f"\nПозиция {ticker} [{side}]:")
        print(f"STOP:  Order ID {stop_order.get('orderId', '-')}, Цена {stop_order.get('price', '-')}")
        print(f"TAKE:  Order ID {take_order.get('orderId', '-')}, Цена {take_order.get('price', '-')}")
        print(f"Текущая рыночная цена: {current_price}")

ORDER_TYPE_MAP = {
    'STOP': 'stop_order',
    'TAKE': 'take_order'
}

def send_telegram_notification(message):
    pass  # Отключено по запросу пользователя

def main():
    if len(sys.argv) < 3:
        print("Использование: python manage_order.py {ticker} {order_type|get-orders} [new_order_type_price]")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    command = sys.argv[2].upper()

    if command == 'GET-ORDERS':
        print_orders(ticker)
        sys.exit(0)

    if len(sys.argv) != 4:
        print("Использование: python manage_order.py {ticker} {order_type} {new_order_type_price}")
        sys.exit(1)

    order_type = command
    new_price = float(sys.argv[3])

    pos_list = get_position(ticker)
    if not pos_list:
        print("ТИКЕР без позиции.")
        sys.exit(1)

    # Если несколько позиций по тикеру — спрашиваем side
    if len(pos_list) > 1:
        print(f"\nПо тикеру {ticker} открыто несколько позиций:")
        for idx, pos in enumerate(pos_list):
            side = pos.get('side', '-')
            amt = pos.get('positionAmt', '-')
            print(f"[{idx}] {side}: {amt}")
        choice = input("Выберите сторону позиции (номер): ").strip()
        try:
            pos = pos_list[int(choice)]
        except Exception:
            print("Некорректный выбор.")
            sys.exit(1)
    else:
        pos = pos_list[0]

    position_amt = pos.get('positionAmt', None)
    if not position_amt or position_amt == 0:
        print("ТИКЕР без позиции.")
        sys.exit(1)

    current_price = pos.get('current_price', None)
    order_key = ORDER_TYPE_MAP.get(order_type)
    if not order_key:
        print("Неверный тип ордера. Используйте STOP или TAKE.")
        sys.exit(1)

    old_order = pos.get(order_key, {})
    print(f"Текущая цена: {current_price}")
    print(f"Текущая цена ордера {order_type}: {old_order.get('price', '-')}")
    print(f"Новая цена: {new_price}")

    # Проверка на "хуже" рыночной цены
    warn = False
    if order_type == 'STOP' and new_price >= current_price:
        warn = True
    if order_type == 'TAKE' and new_price <= current_price:
        warn = True
    if warn:
        print("\nПРОВЕРЬ ЦЕНУ - ОРДЕР ИСПОЛНИТСЯ МОМЕНТАЛЬНО! ТЕКУЩАЯ ЦЕНА:", current_price)
        confirm = input("Продолжить? (Y/N): ").strip().upper()
        if confirm != 'Y':
            print("Ордер отклонен.")
            sys.exit(0)

    # --- Отмена старого ордера ---
    try:
        client.futures_cancel_order(symbol=ticker, orderId=old_order.get('orderId', None))
        print(f"Старый ордер {order_type} #{old_order.get('orderId', '-')} отменен.")
    except BinanceAPIException as e:
        print(f"Ошибка отмены ордера: {e}")
        send_telegram_notification(f"Ошибка отмены ордера {order_type} #{old_order.get('orderId', '-')} по {ticker}: {e}")
        sys.exit(1)

    # --- Размещение нового ордера ---
    try:
        if order_type == 'STOP':
            new_order = client.futures_create_order(
                symbol=ticker,
                side='SELL' if pos.get('side', '-') == 'LONG' else 'BUY',
                type='STOP_MARKET',
                stopPrice=new_price,
                quantity=pos.get('positionAmt', 0),
                positionSide=pos.get('side', '-')
            )
        else:
            new_order = client.futures_create_order(
                symbol=ticker,
                side='SELL' if pos.get('side', '-') == 'LONG' else 'BUY',
                type='TAKE_PROFIT_MARKET',
                stopPrice=new_price,
                quantity=pos.get('positionAmt', 0),
                positionSide=pos.get('side', '-')
            )
        print(f"Новый ордер {order_type} размещен: Order ID {new_order['orderId']}")
        send_telegram_notification(f"Новый ордер {order_type} по {ticker} размещен: Order ID {new_order['orderId']}, Цена {new_price}")
    except BinanceAPIException as e:
        print(f"Ошибка размещения ордера: {e}")
        send_telegram_notification(f"Ошибка размещения ордера {order_type} по {ticker}: {e}")
        sys.exit(1)

    # --- Обновить реестр ---
    pos[order_key] = {'orderId': new_order['orderId'], 'price': new_price}
    from orders_watchdog import WatchedOrder
    orders_watchdog.watched_orders[new_order['orderId']] = WatchedOrder(**pos)  # обновить связь
    print("Связь с позицией обновлена.")

if __name__ == "__main__":
    main()
