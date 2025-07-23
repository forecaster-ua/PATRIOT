#!/usr/bin/env python3
"""
Полный торговый тест и управление ордерами Binance
Версия: 4.0 - с торговыми функциями
"""
import os
import sys
from binance.exceptions import BinanceAPIException
from binance.client import Client

def show_account_details(client, mode_name, testnet_mode=True):
    """Показывает детальную информацию об аккаунте"""
    print(f"\n💰 ДЕТАЛИ АККАУНТА ({mode_name})")
    print("="*60)
    
    try:
        # Получаем информацию о фьючерсном аккаунте
        futures_account = client.futures_account()
        
        # Баланс
        total_balance = float(futures_account['totalWalletBalance'])
        available_balance = float(futures_account['availableBalance'])
        print(f"📊 Общий баланс: {total_balance:.2f} USDT")
        print(f"💵 Доступный капитал: {available_balance:.2f} USDT")
        
        # Позиции
        positions = client.futures_position_information()
        active_positions = [pos for pos in positions if float(pos['positionAmt']) != 0]
        
        print(f"\n📈 ОТКРЫТЫЕ ПОЗИЦИИ ({len(active_positions)} из {len(positions)}):")
        if active_positions:
            print("-" * 80)
            print(f"{'Тикер':<12} {'Размер':<15} {'Плечо':<8} {'Маржа':<12} {'PnL':<12} {'ROE%':<8}")
            print("-" * 80)
            
            for pos in active_positions:
                symbol = pos['symbol']
                size = float(pos['positionAmt'])
                leverage = get_symbol_leverage(client, symbol)  # Используем новую функцию
                margin = float(pos.get('initialMargin', pos.get('isolatedMargin', 0)))
                pnl = float(pos.get('unrealizedProfit', pos.get('unRealizedProfit', 0)))
                
                # ROE рассчитываем сами
                entry_price = float(pos.get('entryPrice', 0))
                mark_price = float(pos.get('markPrice', 0))
                roe = 0
                if entry_price > 0 and mark_price > 0:
                    if size > 0:  # LONG
                        roe = ((mark_price - entry_price) / entry_price) * 100
                    else:  # SHORT
                        roe = ((entry_price - mark_price) / entry_price) * 100
                
                # Форматируем направление
                direction = "🟢 LONG" if size > 0 else "🔴 SHORT"
                size_str = f"{abs(size):.4f} ({direction})"
                
                # Цветное форматирование PnL
                pnl_str = f"{'🟢' if pnl >= 0 else '🔴'}{pnl:+.2f}"
                roe_str = f"{'🟢' if roe >= 0 else '🔴'}{roe:+.2f}%"
                
                print(f"{symbol:<12} {size_str:<15} {leverage}x{'':<4} {margin:.2f}{'':<7} {pnl_str:<12} {roe_str:<8}")
        else:
            print("   ✅ Нет открытых позиций")
        
        return total_balance, available_balance, active_positions
        
    except Exception as e:
        print(f"❌ Ошибка получения данных аккаунта: {e}")
        return 0, 0, []

def get_current_price(client, symbol):
    """Получает текущую цену символа"""
    try:
        ticker = client.futures_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
    except Exception as e:
        print(f"❌ Ошибка получения цены {symbol}: {e}")
        return None

def calculate_position_size(capital, leverage, price):
    """Рассчитывает размер позиции"""
    return (capital * leverage) / price

def get_symbol_info(client, symbol):
    """Получает информацию о символе для правильного форматирования ордеров"""
    try:
        exchange_info = client.futures_exchange_info()
        symbol_info = None
        
        for s in exchange_info['symbols']:
            if s['symbol'] == symbol:
                symbol_info = s
                break
        
        if not symbol_info:
            return None
        
        # Извлекаем точность для цены и количества
        price_precision = 0
        quantity_precision = 0
        min_qty = 0
        tick_size = 0
        
        for filter_item in symbol_info['filters']:
            if filter_item['filterType'] == 'PRICE_FILTER':
                tick_size = float(filter_item['tickSize'])
                # Вычисляем точность цены
                price_precision = len(str(tick_size).rstrip('0').split('.')[-1]) if '.' in str(tick_size) else 0
            elif filter_item['filterType'] == 'LOT_SIZE':
                step_size = float(filter_item['stepSize'])
                min_qty = float(filter_item['minQty'])
                # Вычисляем точность количества
                quantity_precision = len(str(step_size).rstrip('0').split('.')[-1]) if '.' in str(step_size) else 0
        
        return {
            'symbol': symbol,
            'price_precision': price_precision,
            'quantity_precision': quantity_precision,
            'min_qty': min_qty,
            'tick_size': tick_size,
            'status': symbol_info['status']
        }
    except Exception as e:
        print(f"❌ Ошибка получения информации о символе: {e}")
        return None

def round_to_precision(value, precision):
    """Округляет значение до указанной точности"""
    return round(value, precision)

def get_symbol_leverage(client, symbol):
    """
    Получает текущее плечо для символа из информации аккаунта
    """
    try:
        account = client.futures_account()
        
        if 'positions' in account:
            positions = account['positions']
            
            # Ищем позицию с нужным символом
            for pos in positions:
                if pos.get('symbol') == symbol:
                    leverage = pos.get('leverage')
                    if leverage:
                        return leverage
        
        return 'N/A'
        
    except Exception as e:
        return 'N/A'

def create_order_menu(client, mode_name, testnet_mode=True):
    """Меню создания ордера"""
    print(f"\n🎯 СОЗДАНИЕ ОРДЕРА ({mode_name})")
    print("="*50)
    
    try:
        # Запрашиваем параметры ордера
        symbol = input("📝 Введите тикер (например, BTCUSDT): ").strip().upper()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        # Получаем информацию о символе
        print(f"🔍 Получаем информацию о символе {symbol}...")
        symbol_info = get_symbol_info(client, symbol)
        if not symbol_info:
            print(f"❌ Не удалось получить информацию о символе {symbol}")
            return False
        
        if symbol_info['status'] != 'TRADING':
            print(f"❌ Символ {symbol} недоступен для торговли (статус: {symbol_info['status']})")
            return False
        
        print(f"✅ Символ найден:")
        print(f"   - Точность цены: {symbol_info['price_precision']} знаков")
        print(f"   - Точность количества: {symbol_info['quantity_precision']} знаков")
        print(f"   - Минимальное количество: {symbol_info['min_qty']}")
        print(f"   - Шаг цены: {symbol_info['tick_size']}")
        
        # Получаем текущую цену
        current_price = get_current_price(client, symbol)
        if not current_price:
            return False
        
        print(f"💲 Текущая цена {symbol}: {current_price:.{symbol_info['price_precision']}f} USDT")
        
        leverage = int(input("⚡ Введите плечо (например, 10): "))
        capital = float(input("💰 Фактический размер капитала (USDT): "))
        stop_percent = float(input("🛑 Стоп-лосс в % от капитала (например, 2): "))
        take_percent = float(input("🎯 Тейк-профит в % от капитала (например, 4): "))
        
        direction = input("📊 Направление (L - Long, S - Short): ").strip().upper()
        if direction not in ['L', 'S']:
            print("❌ Неверное направление! Используйте L или S")
            return False
        
        print(f"\n🧮 РАСЧЕТЫ ОРДЕРА:")
        print("="*50)
        
        # Рассчитываем размер позиции
        print(f"1️⃣ Расчет размера позиции:")
        print(f"   Формула: (Капитал × Плечо) ÷ Цена")
        print(f"   ({capital} × {leverage}) ÷ {current_price} = {capital * leverage / current_price:.8f}")
        
        position_size_raw = calculate_position_size(capital, leverage, current_price)
        position_size = round_to_precision(position_size_raw, symbol_info['quantity_precision'])
        
        print(f"   Размер позиции (сырой): {position_size_raw:.8f}")
        print(f"   Размер позиции (округленный): {position_size:.{symbol_info['quantity_precision']}f}")
        
        # Проверяем минимальное количество
        if position_size < symbol_info['min_qty']:
            print(f"❌ Размер позиции {position_size} меньше минимального {symbol_info['min_qty']}")
            return False
        
        # Рассчитываем цены для стоп-лосса и тейк-профита
        print(f"\n2️⃣ Расчет сумм прибыли/убытка:")
        stop_loss_amount = capital * (stop_percent / 100)
        take_profit_amount = capital * (take_percent / 100)
        print(f"   Стоп-лосс: {capital} × {stop_percent}% = {stop_loss_amount:.2f} USDT")
        print(f"   Тейк-профит: {capital} × {take_percent}% = {take_profit_amount:.2f} USDT")
        
        print(f"\n3️⃣ Расчет уровней цен:")
        if direction == 'L':
            # Long позиция
            entry_price_raw = current_price * 1.001  # +0.1% от текущей цены
            stop_price_raw = current_price - (stop_loss_amount / position_size)
            take_price_raw = current_price + (take_profit_amount / position_size)
            side = 'BUY'
            
            print(f"   LONG позиция:")
            print(f"   Цена входа: {current_price} × 1.001 = {entry_price_raw:.8f}")
            print(f"   Стоп-лосс: {current_price} - ({stop_loss_amount} ÷ {position_size}) = {stop_price_raw:.8f}")
            print(f"   Тейк-профит: {current_price} + ({take_profit_amount} ÷ {position_size}) = {take_price_raw:.8f}")
        else:
            # Short позиция
            entry_price_raw = current_price * 0.999  # -0.1% от текущей цены
            stop_price_raw = current_price + (stop_loss_amount / position_size)
            take_price_raw = current_price - (take_profit_amount / position_size)
            side = 'SELL'
            
            print(f"   SHORT позиция:")
            print(f"   Цена входа: {current_price} × 0.999 = {entry_price_raw:.8f}")
            print(f"   Стоп-лосс: {current_price} + ({stop_loss_amount} ÷ {position_size}) = {stop_price_raw:.8f}")
            print(f"   Тейк-профит: {current_price} - ({take_profit_amount} ÷ {position_size}) = {take_price_raw:.8f}")
        
        # Округляем цены согласно требованиям биржи
        entry_price = round_to_precision(entry_price_raw, symbol_info['price_precision'])
        stop_price = round_to_precision(stop_price_raw, symbol_info['price_precision'])
        take_price = round_to_precision(take_price_raw, symbol_info['price_precision'])
        
        print(f"\n4️⃣ Округление до точности биржи:")
        print(f"   Цена входа: {entry_price_raw:.8f} → {entry_price:.{symbol_info['price_precision']}f}")
        print(f"   Стоп-лосс: {stop_price_raw:.8f} → {stop_price:.{symbol_info['price_precision']}f}")
        print(f"   Тейк-профит: {take_price_raw:.8f} → {take_price:.{symbol_info['price_precision']}f}")
        
        # Выводим финальные детали ордера
        print(f"\n📋 ФИНАЛЬНЫЕ ДЕТАЛИ ОРДЕРА:")
        print("="*60)
        print(f"🎯 Тикер: {symbol}")
        print(f"📊 Направление: {'🟢 LONG' if direction == 'L' else '🔴 SHORT'}")
        print(f"📏 Размер позиции: {position_size:.{symbol_info['quantity_precision']}f}")
        print(f"💰 Цена входа: {entry_price:.{symbol_info['price_precision']}f} USDT (текущая ±0.1%)")
        print(f"🛑 Стоп-лосс: {stop_price:.{symbol_info['price_precision']}f} USDT (-{stop_percent}% = -{stop_loss_amount:.2f} USDT)")
        print(f"🎯 Тейк-профит: {take_price:.{symbol_info['price_precision']}f} USDT (+{take_percent}% = +{take_profit_amount:.2f} USDT)")
        print(f"⚡ Плечо: {leverage}x")
        print(f"💵 Задействованный капитал: {capital:.2f} USDT")
        print(f"💎 Маржа: {(position_size * entry_price) / leverage:.2f} USDT")
        
        # Подтверждение
        confirm = input(f"\n✅ Выставить ордер в {mode_name}? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Ордер отменен")
            return False
        
        # Устанавливаем плечо
        print(f"⚡ Устанавливаем плечо {leverage}x для {symbol}...")
        client.futures_change_leverage(symbol=symbol, leverage=leverage)
        
        # Проверяем и устанавливаем режим позиций
        print(f"🔧 Проверяем режим позиций...")
        try:
            position_mode = client.futures_get_position_mode()
            if not position_mode['dualSidePosition']:
                print("   Переключаем в режим Hedge (двусторонние позиции)...")
                client.futures_change_position_mode(dualSidePosition=True)
                print("   ✅ Режим Hedge активирован")
            else:
                print("   ✅ Режим Hedge уже активен")
        except Exception as e:
            print(f"   ⚠️ Не удалось изменить режим позиций: {e}")
            print("   💡 Попробуем создать ордер в текущем режиме...")
        
        # Выставляем основной ордер
        print(f"📊 Выставляем {side} ордер...")
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='LIMIT',
            timeInForce='GTC',
            quantity=position_size,
            price=entry_price,
            positionSide='LONG' if direction == 'L' else 'SHORT'  # Указываем сторону позиции
        )
        
        print(f"✅ Ордер выставлен! ID: {order['orderId']}")
        print(f"📊 Статус: {order['status']}")
        print(f"💰 Цена: {order.get('price', 'N/A')}")
        print(f"📏 Количество: {order.get('origQty', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА ПРИ СОЗДАНИИ ОРДЕРА: {e}")
        import traceback
        print(f"📋 Полная ошибка:\n{traceback.format_exc()}")
        return False

def test_mode(testnet_mode=True):
    """Тестирует указанный режим"""
    mode_name = "TESTNET" if testnet_mode else "MAINNET"
    print(f"\n{'='*50}")
    print(f"🔄 ТЕСТИРОВАНИЕ {mode_name} РЕЖИМА")
    print(f"{'='*50}")
    
    # Устанавливаем режим
    os.environ['BINANCE_TESTNET'] = 'true' if testnet_mode else 'false'
    
    # Очищаем кеш модулей
    if 'config' in sys.modules:
        del sys.modules['config']
    
    try:
        import config
        print(f"🔧 Режим: {config.NETWORK_MODE}")
        print(f"🧪 Testnet: {config.BINANCE_TESTNET}")
        print(f"🔑 API Key: {config.BINANCE_API_KEY[:20]}..." if config.BINANCE_API_KEY else "❌ НЕ НАСТРОЕН")
        print(f"🔐 Secret: {config.BINANCE_API_SECRET[:20]}..." if config.BINANCE_API_SECRET else "❌ НЕ НАСТРОЕН")
        
        if not config.BINANCE_API_KEY or not config.BINANCE_API_SECRET:
            print(f"❌ {mode_name} ключи не настроены!")
            if testnet_mode:
                print("💡 Для TESTNET создайте ключи на: https://testnet.binancefuture.com/")
                print("   и установите BINANCE_TESTNET_API_KEY и BINANCE_TESTNET_API_SECRET")
            else:
                print("💡 Для MAINNET создайте ключи на: https://binance.com/")
                print("   и установите BINANCE_MAINNET_API_KEY и BINANCE_MAINNET_API_SECRET")
            return False, None
        print(f"\n🔄 Тестируем подключение к {mode_name}...")
        print(f"\n🔄 Тестируем подключение к {mode_name}...")
        client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, testnet=testnet_mode)
        
        if testnet_mode:
            # Для TESTNET проверяем только фьючерсы (спот может быть недоступен)
            print("   - Проверяем статус фьючерсного сервера...")
            status = client.futures_ping()
            print(f"   ✅ Фьючерсный сервер доступен")
            
            print("   - Проверяем доступ к фьючерсному аккаунту...")
            futures_account = client.futures_account()
            balance = float(futures_account['totalWalletBalance'])
            print(f"   ✅ Фьючерсный аккаунт доступен, баланс: {balance} USDT")
            
            # Проверяем информацию о позициях
            positions = client.futures_position_information()
            print(f"   📊 Доступно позиций: {len(positions)}")
            
        else:
            # Для MAINNET проверяем и спот, и фьючерсы
            print("   - Проверяем статус сервера...")
            status = client.get_system_status()
            print(f"   ✅ Статус сервера: OK (status={status['status']})")
            
            print("   - Проверяем доступ к спот аккаунту...")
            account = client.get_account()
            print("   ✅ Подключение к спот аккаунту успешно")
            
            print("   - Проверяем доступ к фьючерсам...")
            futures_account = client.futures_account()
            balance = float(futures_account['totalWalletBalance'])
            print(f"   ✅ Фьючерсный аккаунт доступен, баланс: {balance} USDT")
            
            # Проверяем разрешения для MAINNET
            permissions = account.get('permissions', [])
            print(f"   📋 Разрешения: {', '.join(permissions)}")
            
            # Современные разрешения Binance могут быть LEVERAGED вместо FUTURES
            futures_enabled = any(perm in permissions for perm in ['FUTURES', 'LEVERAGED'])
            if not futures_enabled:
                print("   ⚠️  ВНИМАНИЕ: Нет разрешения на торговлю фьючерсами!")
                print("   💡 Ожидаемые разрешения: FUTURES или LEVERAGED")
                return False, None
            else:
                print("   ✅ Разрешения на фьючерсную торговлю обнаружены!")
        
        print(f"\n🎉 {mode_name} ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        
        # Показываем детали аккаунта
        show_account_details(client, mode_name, testnet_mode)
        
        return True, client
        
    except BinanceAPIException as e:
        print(f"❌ ОШИБКА BINANCE API: {e.message} (код: {e.code})")
        if e.code == -2015:
            print("💡 Это означает:")
            if testnet_mode:
                print("   - Ключи созданы для MAINNET, а не для TESTNET")
                print("   - Создайте отдельные ключи на https://testnet.binancefuture.com/")
            else:
                print("   - Неверные API ключи или недостаточно разрешений")
                print("   - Проверьте ключи на https://binance.com/")
        return False, None
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        print(f"   Тип: {type(e).__name__}")
        return False, None

def show_open_orders(client, mode_name):
    """Показывает открытые ордера"""
    print(f"\n📋 ОТКРЫТЫЕ ОРДЕРА ({mode_name})")
    print("="*60)
    
    try:
        orders = client.futures_get_open_orders()
        
        if not orders:
            print("✅ Нет открытых ордеров")
            return
        
        print(f"Найдено ордеров: {len(orders)}")
        print("-" * 80)
        print(f"{'ID':<12} {'Тикер':<12} {'Тип':<8} {'Сторона':<6} {'Количество':<15} {'Цена':<12}")
        print("-" * 80)
        
        for order in orders:
            order_id = order['orderId']
            symbol = order['symbol']
            order_type = order['type']
            side = order['side']
            quantity = float(order['origQty'])
            price = float(order['price']) if order['price'] != '0' else 'MARKET'
            
            side_symbol = "🟢 BUY" if side == 'BUY' else "🔴 SELL"
            
            print(f"{order_id:<12} {symbol:<12} {order_type:<8} {side_symbol:<6} {quantity:<15.4f} {price if isinstance(price, str) else f'{price:.4f}':<12}")
        
    except Exception as e:
        print(f"❌ Ошибка получения ордеров: {e}")

def show_open_positions(client, mode_name):
    """Показывает детальную информацию об открытых позициях"""
    print(f"\n📊 ОТКРЫТЫЕ ПОЗИЦИИ ({mode_name})")
    print("="*80)
    
    try:
        positions = client.futures_position_information()
        active_positions = [pos for pos in positions if float(pos['positionAmt']) != 0]
        
        if not active_positions:
            print("✅ Нет открытых позиций")
            return
        
        print(f"Найдено позиций: {len(active_positions)}")
        print("-" * 100)
        print(f"{'Тикер':<12} {'Сторона':<8} {'Размер':<15} {'Цена входа':<12} {'Текущая цена':<12} {'PnL':<12} {'ROE%':<8} {'Плечо':<6}")
        print("-" * 100)
        
        total_pnl = 0
        
        for pos in active_positions:
            symbol = pos['symbol']
            size = float(pos['positionAmt'])
            entry_price = float(pos.get('entryPrice', 0))
            mark_price = float(pos.get('markPrice', 0))
            pnl = float(pos.get('unrealizedProfit', pos.get('unRealizedProfit', 0)))
            
            # ROE рассчитываем сами, если нет в API
            roe = 0
            if entry_price > 0 and mark_price > 0:
                if size > 0:  # LONG
                    roe = ((mark_price - entry_price) / entry_price) * 100
                else:  # SHORT
                    roe = ((entry_price - mark_price) / entry_price) * 100
            
            leverage = get_symbol_leverage(client, symbol)  # Используем новую функцию
            
            # Определяем направление
            if size > 0:
                side = "🟢 LONG"
                size_display = f"{size:.4f}"
            else:
                side = "🔴 SHORT"
                size_display = f"{abs(size):.4f}"
            
            # Цветное форматирование PnL и ROE
            if pnl >= 0:
                pnl_str = f"🟢 +{pnl:.2f}"
                roe_str = f"🟢 +{roe:.2f}%"
            else:
                pnl_str = f"🔴 {pnl:.2f}"
                roe_str = f"🔴 {roe:.2f}%"
            
            total_pnl += pnl
            
            print(f"{symbol:<12} {side:<8} {size_display:<15} {entry_price:.4f}{'':<7} {mark_price:.4f}{'':<7} {pnl_str:<12} {roe_str:<8} {leverage}x{'':<3}")
        
        # Итоговая сводка
        print("-" * 100)
        total_pnl_str = f"🟢 +{total_pnl:.2f}" if total_pnl >= 0 else f"🔴 {total_pnl:.2f}"
        print(f"{'ИТОГО:':<12} {'':<8} {'':<15} {'':<12} {'':<12} {total_pnl_str} USDT{'':<8} {'':<6}")
        
        # Дополнительная информация
        print(f"\n📊 ДЕТАЛИЗАЦИЯ ПОЗИЦИЙ:")
        print("-" * 100)
        print(f"{'Тикер':<12} {'Маржа':<12} {'Ликвидация':<12} {'Обновлено':<20}")
        print("-" * 100)
        
        for pos in active_positions:
            symbol = pos['symbol']
            margin = float(pos.get('initialMargin', pos.get('isolatedMargin', 0)))
            liquidation_price = float(pos.get('liquidationPrice', 0)) if pos.get('liquidationPrice') and pos.get('liquidationPrice') != '0' else 0
            update_time = pos.get('updateTime', 0)
            
            # Конвертируем время
            from datetime import datetime
            try:
                if update_time and update_time != 0:
                    update_dt = datetime.fromtimestamp(int(update_time) / 1000)
                    update_str = update_dt.strftime("%d.%m.%Y %H:%M:%S")
                else:
                    update_str = "N/A"
            except:
                update_str = "N/A"
            
            liquidation_str = f"{liquidation_price:.4f}" if liquidation_price > 0 else "N/A"
            
            print(f"{symbol:<12} {margin:.2f}{'':<7} {liquidation_str:<12} {update_str:<20}")
        
    except Exception as e:
        print(f"❌ Ошибка получения позиций: {e}")
        import traceback
        print(f"📋 Детали ошибки:\n{traceback.format_exc()}")

def main():
    """Главная функция - тестирует режимы и предлагает торговлю"""
    print("🚀 ТОРГОВЫЙ ТЕСТ И УПРАВЛЕНИЕ ОРДЕРАМИ BINANCE")
    print("Версия: 4.0 - с полными торговыми функциями")
    
    # Определяем режим работы
    mode_choice = input("\n🔧 Выберите режим:\n1. TESTNET (безопасное тестирование)\n2. MAINNET (реальная торговля)\n3. Оба режима (проверка)\nВыбор (1/2/3): ").strip()
    
    working_client = None
    working_mode = None
    working_testnet = None
    
    if mode_choice == "1":
        # Только TESTNET
        print("\n🧪 Работаем в TESTNET режиме")
        testnet_ok, client = test_mode(testnet_mode=True)
        if testnet_ok:
            working_client = client
            working_mode = "TESTNET"
            working_testnet = True
    elif mode_choice == "2":
        # Только MAINNET
        print("\n⚡ Работаем в MAINNET режиме")
        mainnet_ok, client = test_mode(testnet_mode=False)
        if mainnet_ok:
            working_client = client
            working_mode = "MAINNET"
            working_testnet = False
    else:
        # Оба режима для проверки
        print("\n🔍 Проверяем оба режима")
        testnet_ok, testnet_client = test_mode(testnet_mode=True)
        mainnet_ok, mainnet_client = test_mode(testnet_mode=False)
        
        # Итоговый отчет
        print(f"\n{'='*50}")
        print("📊 ИТОГОВЫЙ ОТЧЕТ")
        print(f"{'='*50}")
        print(f"🧪 TESTNET:  {'✅ РАБОТАЕТ' if testnet_ok else '❌ НЕ РАБОТАЕТ'}")
        print(f"⚡ MAINNET:  {'✅ РАБОТАЕТ' if mainnet_ok else '❌ НЕ РАБОТАЕТ'}")
        print(f"{'='*50}")
        
        if testnet_ok and mainnet_ok:
            print("🎉 Все ключи настроены корректно!")
            
            # Предлагаем выбрать режим для торговли
            trade_choice = input("\n💼 С каким режимом продолжить работу?\n1. TESTNET\n2. MAINNET\n3. Завершить\nВыбор (1/2/3): ").strip()
            if trade_choice == "1" and testnet_ok:
                working_client = testnet_client
                working_mode = "TESTNET"
                working_testnet = True
            elif trade_choice == "2" and mainnet_ok:
                working_client = mainnet_client
                working_mode = "MAINNET"
                working_testnet = False
        elif testnet_ok:
            print("⚠️  Работает только TESTNET")
            working_client = testnet_client
            working_mode = "TESTNET"
            working_testnet = True
        elif mainnet_ok:
            print("⚠️  Работает только MAINNET")
            working_client = mainnet_client
            working_mode = "MAINNET"
            working_testnet = False
        else:
            print("🚨 Требуется настройка API ключей!")
    
    # Если есть рабочий клиент, продолжаем
    if working_client and working_mode:
        print(f"\n{'='*50}")
        print(f"💼 РАБОТАЕМ В РЕЖИМЕ: {working_mode}")
        print(f"{'='*50}")
        
        # Основное меню
        while True:
            print(f"\n🔄 ГЛАВНОЕ МЕНЮ ({working_mode})")
            print("-" * 30)
            print("1. 📊 Обновить информацию об аккаунте")
            print("2. 🎯 Создать новый ордер")
            print("3. 📋 Показать открытые ордера")
            print("4. 📊 Показать открытые позиции")
            print("5. ❌ Завершить работу")
            
            choice = input("\nВыбор (1-5): ").strip()
            
            if choice == "1":
                if working_testnet is not None:
                    show_account_details(working_client, working_mode, working_testnet)
            elif choice == "2":
                if working_testnet is not None:
                    if create_order_menu(working_client, working_mode, working_testnet):
                        print("✅ Ордер успешно создан!")
                    else:
                        print("❌ Не удалось создать ордер")
            elif choice == "3":
                show_open_orders(working_client, working_mode)
            elif choice == "4":
                show_open_positions(working_client, working_mode)
            elif choice == "5":
                print(f"\n👋 Завершаем работу с {working_mode}")
                break
            else:
                print("❌ Неверный выбор, попробуйте снова")
    else:
        print("\n❌ Нет доступных подключений для работы")
    
    print("\n👋 Работа завершена")

if __name__ == "__main__":
    main()
