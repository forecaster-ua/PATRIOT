import asyncio
import logging
import logging.config
from binance.client import Client
from binance.exceptions import BinanceAPIException
from datetime import datetime
import config

# Используем общую конфигурацию логирования с UTF-8
logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)

class BinanceFactory:
    def __init__(self):
        """Инициализация Binance Factory с API ключами из config для фьючерсов"""
        try:
            self.api_key = config.BINANCE_API_KEY
            self.api_secret = config.BINANCE_API_SECRET
            self.testnet = config.BINANCE_TESTNET
            self.network_mode = config.NETWORK_MODE
            
            # Проверяем наличие API ключей для выбранного режима
            if not self.api_key or not self.api_secret:
                error_msg = f"❌ ОШИБКА: API ключи Binance {self.network_mode} не настроены!"
                print(error_msg)
                print(f"Требуемые переменные окружения:")
                if self.testnet:
                    print("- BINANCE_TESTNET_API_KEY")
                    print("- BINANCE_TESTNET_API_SECRET")
                else:
                    print("- BINANCE_MAINNET_API_KEY")
                    print("- BINANCE_MAINNET_API_SECRET")
                logger.error(error_msg)
                raise ValueError(f"Binance {self.network_mode} API keys are not configured")
            
            # Показываем какой режим используется
            print(f"🔧 [INIT] Инициализация Binance Factory в режиме: {self.network_mode}")
            logger.info(f"Initializing Binance Factory in {self.network_mode} mode")
            
            # Инициализируем клиент с учетом testnet
            try:
                if self.testnet:
                    self.client = Client(self.api_key, self.api_secret, testnet=True)
                    print(f"🧪 [INIT] Using TESTNET mode")
                else:
                    self.client = Client(self.api_key, self.api_secret)
                    print(f"⚡ [INIT] Using MAINNET mode (PRODUCTION)")
            except Exception as e:
                error_msg = f"❌ ОШИБКА ПОДКЛЮЧЕНИЯ К BINANCE API ({self.network_mode}): {e}"
                print(error_msg)
                logger.error(error_msg)
                raise ConnectionError(f"Failed to connect to Binance API: {e}")
            
            # ОБЯЗАТЕЛЬНАЯ проверка доступности фьючерсов
            try:
                print(f"[INIT] Проверка подключения к Binance Futures API ({self.network_mode})...")
                account_info = self.client.futures_account()
                print(f"✅ [INIT] Futures account accessible on {self.network_mode}")
                logger.info(f"Futures account verified on {self.network_mode}")
            except BinanceAPIException as e:
                error_msg = f"❌ ОШИБКА BINANCE API ({self.network_mode}): {e.message} (код: {e.code})"
                print(error_msg)
                logger.error(error_msg)
                raise ConnectionError(f"Binance API error: {e.message} (code: {e.code})")
            except Exception as e:
                error_msg = f"❌ КРИТИЧЕСКАЯ ОШИБКА ПОДКЛЮЧЕНИЯ К BINANCE ({self.network_mode}): {e}"
                print(error_msg)
                logger.error(error_msg)
                raise ConnectionError(f"Critical Binance connection error: {e}")
            
            # Настройки из config
            self.capital_percentage = getattr(config, 'CAPITAL_PERCENTAGE', 0.1)  # 10% по умолчанию
            self.order_queue = []  # Очередь ордеров от ticker_monitor
            self.stop_event = asyncio.Event()  # Событие для остановки
            
            print(f"✅ [INIT] Binance Factory (FUTURES) инициализирован на {self.network_mode}")
            print(f"💰 [INIT] Процент капитала для ордеров: {self.capital_percentage * 100}%")
            logger.info(f"Binance Factory (FUTURES) успешно инициализирован на {self.network_mode}")
            
        except Exception as e:
            error_msg = f"❌ КРИТИЧЕСКАЯ ОШИБКА ИНИЦИАЛИЗАЦИИ BINANCE FACTORY: {e}"
            print(error_msg)
            logger.error(error_msg)
            raise

    async def check_account_status(self):
        """Проверка состояния фьючерсного счета"""
        try:
            print("\n[FUTURES ACCOUNT] Проверка состояния фьючерсного счета...")
            
            # Получение информации о фьючерсном аккаунте
            account_info = self.client.futures_account()
            
            # Баланс фьючерсного счета
            assets = [a for a in account_info['assets'] if float(a['walletBalance']) > 0]
            positions = [p for p in account_info['positions'] if float(p['positionAmt']) != 0]
            
            print(f"[FUTURES ACCOUNT] Можно торговать: {account_info['canTrade']}")
            print(f"[FUTURES ACCOUNT] Можно депозитировать: {account_info['canDeposit']}")
            print(f"[FUTURES ACCOUNT] Можно выводить: {account_info['canWithdraw']}")
            print(f"[FUTURES ACCOUNT] Общий баланс: {account_info['totalWalletBalance']} USDT")
            print(f"[FUTURES ACCOUNT] Доступный баланс: {account_info['availableBalance']} USDT")
            
            print(f"\n[FUTURES BALANCE] Активные активы:")
            for asset in assets:
                wallet_balance = float(asset['walletBalance'])
                available_balance = float(asset['availableBalance'])
                print(f"  {asset['asset']}: {wallet_balance:.8f} (доступно: {available_balance:.8f})")
            
            print(f"\n[FUTURES POSITIONS] Открытые позиции:")
            if positions:
                for pos in positions:
                    side = "LONG" if float(pos['positionAmt']) > 0 else "SHORT"
                    print(f"  {pos['symbol']}: {side} {abs(float(pos['positionAmt']))} @ {pos['entryPrice']}")
                    print(f"    PnL: {pos['unrealizedProfit']} USDT, Маржа: {pos['initialMargin']} USDT")
            else:
                print("  Открытых позиций нет")
            
            logger.info(f"Проверка фьючерсного счета завершена. Активных активов: {len(assets)}, позиций: {len(positions)}")
            return account_info
            
        except BinanceAPIException as e:
            print(f"[ERROR] API ошибка при проверке фьючерсного счета: {e}")
            logger.error(f"API ошибка при проверке фьючерсного счета: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Общая ошибка при проверке фьючерсного счета: {e}")
            logger.error(f"Общая ошибка при проверке фьючерсного счета: {e}")
            return None

    async def check_open_positions(self):
        """Проверка открытых позиций на фьючерсном счете"""
        try:
            print("\n[FUTURES POSITIONS] Проверка открытых позиций...")
            
            # Получаем открытые позиции
            positions = self.client.futures_position_information()
            open_positions = [p for p in positions if float(p['positionAmt']) != 0]
            
            # Получаем открытые ордера
            open_orders = self.client.futures_get_open_orders()
            
            print(f"[FUTURES POSITIONS] Открытых позиций: {len(open_positions)}")
            print(f"[FUTURES POSITIONS] Открытых ордеров: {len(open_orders)}")
            
            # Выводим информацию о позициях
            if open_positions:
                print("\n[OPEN POSITIONS]:")
                for pos in open_positions:
                    side = "LONG" if float(pos['positionAmt']) > 0 else "SHORT"
                    pnl = float(pos['unrealizedProfit'])
                    pnl_pct = float(pos['percentage'])
                    print(f"  {pos['symbol']}: {side} {abs(float(pos['positionAmt']))}")
                    print(f"    Цена входа: {pos['entryPrice']}")
                    print(f"    Текущая цена: {pos['markPrice']}")
                    print(f"    PnL: {pnl:.4f} USDT ({pnl_pct:.2f}%)")
                    print(f"    Маржа: {pos['initialMargin']} USDT")
            
            # Выводим информацию о ордерах
            if open_orders:
                print("\n[OPEN ORDERS]:")
                for order in open_orders:
                    print(f"  Ордер {order['orderId']}: {order['symbol']} {order['side']} {order['type']}")
                    print(f"    Количество: {order['origQty']}, Цена: {order['price']}")
                    print(f"    Статус: {order['status']}, Время: {order['time']}")
            
            logger.info(f"Проверка фьючерсных позиций завершена. Открытых позиций: {len(open_positions)}, ордеров: {len(open_orders)}")
            return {'positions': open_positions, 'orders': open_orders}
            
        except BinanceAPIException as e:
            print(f"[ERROR] API ошибка при проверке позиций: {e}")
            logger.error(f"API ошибка при проверке позиций: {e}")
            return {'positions': [], 'orders': []}
        except Exception as e:
            print(f"[ERROR] Общая ошибка при проверке позиций: {e}")
            logger.error(f"Общая ошибка при проверке позиций: {e}")
            return {'positions': [], 'orders': []}

    async def generate_report(self):
        """Генерация отчета о состоянии фьючерсного счета"""
        print("\n" + "="*50)
        print("ОТЧЕТ О СОСТОЯНИИ ФЬЮЧЕРСНОГО СЧЕТА")
        print("="*50)
        
        # Проверка аккаунта
        account_info = await self.check_account_status()
        
        # Проверка позиций
        positions_info = await self.check_open_positions()
        
        # Время отчета
        print(f"\n[REPORT] Время генерации отчета: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Итоговая информация
        if account_info:
            try:
                # Получаем цену BTC для расчета стоимости портфеля
                btc_price = float(self.client.futures_symbol_ticker(symbol="BTCUSDT")['price'])
                total_balance = float(account_info['totalWalletBalance'])
                available_balance = float(account_info['availableBalance'])
                
                total_btc_value = total_balance / btc_price
                print(f"[REPORT] Общий баланс: {total_balance:.2f} USDT (~{total_btc_value:.6f} BTC)")
                print(f"[REPORT] Доступный баланс: {available_balance:.2f} USDT")
                
                # Информация о позициях
                open_positions = positions_info.get('positions', [])
                open_orders = positions_info.get('orders', [])
                
                if open_positions:
                    total_pnl = sum(float(pos['unrealizedProfit']) for pos in open_positions)
                    print(f"[REPORT] Общий PnL: {total_pnl:.2f} USDT")
                
                print(f"[REPORT] Открытых позиций: {len(open_positions)}")
                print(f"[REPORT] Открытых ордеров: {len(open_orders)}")
                
            except Exception as e:
                print(f"[REPORT] Не удалось рассчитать детальную информацию: {e}")
        
        print("="*50)
        logger.info("Отчет о состоянии фьючерсного счета сгенерирован")

    async def place_order(self, symbol, side, quantity, order_type='MARKET', price=None, stop_loss=None, take_profit=None):
        """Размещение фьючерсного ордера"""
        try:
            print(f"\n[FUTURES ORDER] Размещение ордера: {symbol} {side} {quantity}")
            
            # Основные параметры ордера
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity,
            }
            
            if order_type == 'LIMIT' and price:
                order_params['price'] = price
                order_params['timeInForce'] = 'GTC'
            
            # Размещение основного ордера
            result = self.client.futures_create_order(**order_params)
            
            print(f"[FUTURES ORDER] Ордер успешно размещен!")
            print(f"  ID: {result['orderId']}")
            print(f"  Символ: {result['symbol']}")
            print(f"  Сторона: {result['side']}")
            print(f"  Количество: {result['origQty']}")
            print(f"  Статус: {result['status']}")
            
            # Размещение Stop Loss ордера (если указан)
            if stop_loss and result['status'] == 'FILLED':
                try:
                    stop_side = 'SELL' if side == 'BUY' else 'BUY'
                    stop_params = {
                        'symbol': symbol,
                        'side': stop_side,
                        'type': 'STOP_MARKET',
                        'quantity': quantity,
                        'stopPrice': stop_loss,
                    }
                    
                    stop_result = self.client.futures_create_order(**stop_params)
                    print(f"[STOP LOSS] Stop Loss ордер размещен: {stop_result['orderId']} @ {stop_loss}")
                    
                except Exception as e:
                    print(f"[WARNING] Не удалось разместить Stop Loss: {e}")
            
            # Размещение Take Profit ордера (если указан)
            if take_profit and result['status'] == 'FILLED':
                try:
                    tp_side = 'SELL' if side == 'BUY' else 'BUY'
                    tp_params = {
                        'symbol': symbol,
                        'side': tp_side,
                        'type': 'TAKE_PROFIT_MARKET',
                        'quantity': quantity,
                        'stopPrice': take_profit,
                    }
                    
                    tp_result = self.client.futures_create_order(**tp_params)
                    print(f"[TAKE PROFIT] Take Profit ордер размещен: {tp_result['orderId']} @ {take_profit}")
                    
                except Exception as e:
                    print(f"[WARNING] Не удалось разместить Take Profit: {e}")
            
            logger.info(f"Фьючерсный ордер размещен: {result['orderId']} {symbol} {side} {quantity}")
            return result
            
        except BinanceAPIException as e:
            print(f"[ERROR] API ошибка при размещении ордера: {e}")
            logger.error(f"API ошибка при размещении ордера: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Общая ошибка при размещении ордера: {e}")
            logger.error(f"Общая ошибка при размещении ордера: {e}")
            return None

    def get_current_price(self, symbol):
        """Получение текущей цены символа на фьючерсном рынке"""
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price'])
            print(f"[FUTURES PRICE] Текущая цена {symbol}: {current_price:.8f}")
            return current_price
        except BinanceAPIException as e:
            print(f"[ERROR] API ошибка при получении цены {symbol}: {e}")
            logger.error(f"API ошибка при получении цены {symbol}: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Общая ошибка при получении цены {symbol}: {e}")
            logger.error(f"Общая ошибка при получении цены {symbol}: {e}")
            return None

    def validate_price(self, symbol, entry_price, tolerance_percent=1.0):
        """Проверка валидности цены (current_price vs entry_price)"""
        try:
            current_price = self.get_current_price(symbol)
            
            if current_price is None:
                print(f"[VALIDATION] Не удалось получить текущую цену для {symbol}")
                return False
            
            # Расчет отклонения в процентах
            price_diff_percent = abs((current_price - entry_price) / entry_price * 100)
            
            is_valid = price_diff_percent <= tolerance_percent
            
            print(f"[VALIDATION] Проверка цены для {symbol}:")
            print(f"  Цена входа: {entry_price:.8f}")
            print(f"  Текущая цена: {current_price:.8f}")
            print(f"  Отклонение: {price_diff_percent:.2f}%")
            print(f"  Допустимое отклонение: {tolerance_percent}%")
            print(f"  Результат: {'ВАЛИДНА' if is_valid else 'НЕ ВАЛИДНА'}")
            
            logger.info(f"Проверка цены {symbol}: entry={entry_price:.8f}, current={current_price:.8f}, diff={price_diff_percent:.2f}%, valid={is_valid}")
            
            return is_valid
            
        except Exception as e:
            print(f"[ERROR] Ошибка валидации цены: {e}")
            logger.error(f"Ошибка валидации цены: {e}")
            return False

    def calculate_order_quantity(self, symbol, side, current_price):
        """Расчет количества для фьючерсного ордера на основе процента от капитала"""
        try:
            # Получение баланса фьючерсного счета
            account_info = self.client.futures_account()
            available_balance = float(account_info['availableBalance'])
            
            # Расчет суммы для ордера
            order_amount = available_balance * self.capital_percentage
            
            # Расчет количества для фьючерсов
            quantity = order_amount / current_price
            
            # Получение информации о символе для корректировки точности
            exchange_info = self.client.futures_exchange_info()
            step_size = None
            
            for symbol_info in exchange_info['symbols']:
                if symbol_info['symbol'] == symbol:
                    for filter in symbol_info['filters']:
                        if filter['filterType'] == 'LOT_SIZE':
                            step_size = float(filter['stepSize'])
                            break
                    break
            
            if step_size:
                # Округление до допустимого шага
                quantity = round(quantity / step_size) * step_size
            
            print(f"[FUTURES CALC] Расчет количества для {symbol}:")
            print(f"  Доступный баланс: {available_balance:.2f} USDT")
            print(f"  Процент капитала: {self.capital_percentage * 100}%")
            print(f"  Сумма ордера: {order_amount:.2f} USDT")
            print(f"  Текущая цена: {current_price:.8f}")
            print(f"  Количество: {quantity:.8f}")
            
            return quantity
            
        except Exception as e:
            print(f"[ERROR] Ошибка расчета количества: {e}")
            logger.error(f"Ошибка расчета количества: {e}")
            return 0

    async def process_order_from_monitor(self, order_data):
        """Обработка ордера от ticker_monitor"""
        try:
            print(f"\n[MONITOR] Получен ордер от ticker_monitor: {order_data}")
            
            symbol = order_data.get('symbol')
            side = order_data.get('side')
            entry_price = float(order_data.get('price', 0))
            tolerance_percent = float(order_data.get('tolerance_percent', 1.0))
            
            if not symbol or not side or entry_price <= 0:
                print(f"[ERROR] Некорректные данные ордера: {order_data}")
                return None
            
            # Проверка валидности цены
            if not self.validate_price(symbol, entry_price, tolerance_percent):
                print(f"[ERROR] Цена не прошла валидацию для {symbol}")
                return None
            
            # Получение текущей цены для расчета количества
            current_price = self.get_current_price(symbol)
            if current_price is None:
                print(f"[ERROR] Не удалось получить текущую цену для {symbol}")
                return None
            
            # Расчет количества
            quantity = self.calculate_order_quantity(symbol, side, current_price)
            
            if quantity <= 0:
                print(f"[ERROR] Некорректное количество для ордера: {quantity}")
                return None
            
            # Размещение ордера
            result = await self.place_order(
                symbol=symbol, 
                side=side, 
                quantity=quantity,
                stop_loss=order_data.get('stop_loss'),
                take_profit=order_data.get('take_profit')
            )
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Ошибка обработки ордера от монитора: {e}")
            logger.error(f"Ошибка обработки ордера от монитора: {e}")
            return None

    async def run(self):
        """Основной цикл работы"""
        print(f"\n[START] Запуск Binance Factory...")
        logger.info("Запуск Binance Factory")
        
        try:
            # Генерация начального отчета
            await self.generate_report()
            
            # Основной цикл
            while not self.stop_event.is_set():
                print(f"\n[MAIN] Проверка очереди ордеров...")
                
                # Обработка ордеров из очереди
                while self.order_queue:
                    order_data = self.order_queue.pop(0)
                    await self.process_order_from_monitor(order_data)
                
                # Периодическое обновление отчета (каждые 60 секунд)
                try:
                    await asyncio.wait_for(self.stop_event.wait(), timeout=60.0)
                    break  # Если stop_event установлен, выходим
                except asyncio.TimeoutError:
                    # Таймаут - продолжаем работу
                    await self.generate_report()
                
        except KeyboardInterrupt:
            print(f"\n[STOP] Остановка Binance Factory...")
            logger.info("Binance Factory остановлен пользователем")
        except Exception as e:
            print(f"[ERROR] Критическая ошибка: {e}")
            logger.error(f"Критическая ошибка: {e}")
        finally:
            print(f"[SHUTDOWN] Binance Factory завершен")
            logger.info("Binance Factory shutdown complete")

    def add_order_to_queue(self, order_data):
        """Добавление ордера в очередь (вызывается из ticker_monitor)"""
        self.order_queue.append(order_data)
        print(f"[QUEUE] Ордер добавлен в очередь: {order_data}")
        logger.info(f"Ордер добавлен в очередь: {order_data}")

    def stop(self):
        """Остановка Binance Factory"""
        self.stop_event.set()
        print(f"[STOP] Получен сигнал остановки")
        logger.info("Binance Factory stop signal received")

# Пример использования
if __name__ == "__main__":
    factory = BinanceFactory()
    
    # Пример добавления ордера в очередь с валидацией цены
    # factory.add_order_to_queue({
    #     'symbol': 'BTCUSDT',
    #     'side': 'BUY',
    #     'price': 50000,  # entry_price для валидации
    #     'tolerance_percent': 1.0  # допустимое отклонение цены в %
    # })
    
    asyncio.run(factory.run())