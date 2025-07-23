"""
Futures Monitor - Мониторинг баланса и позиций
==============================================

Скрипт для проверки:
1. Доступной маржи на фьючерсах
2. Открытых позиций
3. Общей статистики аккаунта

Интегрируется с существующей архитектурой PATRIOT:
- Использует config.py для настроек API
- Логирует через utils.logger
- Совместим с testnet/mainnet режимами

Author: HEDGER  
Version: 1.0 - Production Ready
"""

import sys
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
import json
from tabulate import tabulate

# Локальные импорты
from config import (
    BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET, 
    NETWORK_MODE, FUTURES_LEVERAGE, RISK_PERCENT
)
from utils import logger

# Binance
try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    BINANCE_AVAILABLE = True
except ImportError:
    logger.error("❌ python-binance not installed. Install with: pip install python-binance")
    BINANCE_AVAILABLE = False
    # Define dummy Client for type hints when import fails
    Client = None


class FuturesMonitor:
    """Монитор состояния фьючерсного аккаунта"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.account_info: Optional[Dict] = None
        self._init_client()
    
    def _init_client(self) -> None:
        """Инициализация Binance клиента"""
        if not BINANCE_AVAILABLE:
            logger.error("❌ Binance library not available")
            return
            
        if not BINANCE_API_KEY or not BINANCE_API_SECRET:
            logger.error("❌ Binance API ключи не настроены")
            logger.error("Проверьте переменные окружения:")
            if BINANCE_TESTNET:
                logger.error("- BINANCE_TESTNET_API_KEY")
                logger.error("- BINANCE_TESTNET_API_SECRET") 
            else:
                logger.error("- BINANCE_MAINNET_API_KEY")
                logger.error("- BINANCE_MAINNET_API_SECRET")
            return
        
        try:
            if Client is None:
                logger.error("❌ Binance Client недоступен")
                return
                
            logger.info(f"🔧 Подключение к Binance {NETWORK_MODE}...")
            
            self.client = Client(
                api_key=BINANCE_API_KEY,
                api_secret=BINANCE_API_SECRET,
                testnet=BINANCE_TESTNET
            )
            
            # Тест подключения
            self.client.futures_account()
            logger.info(f"✅ Подключение к Binance {NETWORK_MODE} установлено")
            
        except BinanceAPIException as e:
            logger.error(f"❌ Ошибка Binance API: {e}")
            self.client = None
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка подключения: {e}")
            self.client = None
    
    def get_account_info(self) -> Optional[Dict]:
        """Получает информацию об аккаунте"""
        if not self.client:
            logger.error("❌ Клиент не инициализирован")
            return None
        
        try:
            self.account_info = self.client.futures_account()
            return self.account_info
        except BinanceAPIException as e:
            logger.error(f"❌ Ошибка получения данных аккаунта: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}")
            return None
    
    def get_balance_info(self) -> Optional[Dict]:
        """Получает информацию о балансе"""
        if not self.account_info:
            self.get_account_info()
        
        if not self.account_info:
            return None
        
        try:
            # Основные балансы
            total_wallet_balance = float(self.account_info.get('totalWalletBalance', 0))
            total_unrealized_pnl = float(self.account_info.get('totalUnrealizedProfit', 0))
            total_margin_balance = float(self.account_info.get('totalMarginBalance', 0))
            available_balance = float(self.account_info.get('availableBalance', 0))
            total_position_initial_margin = float(self.account_info.get('totalPositionInitialMargin', 0))
            total_open_order_initial_margin = float(self.account_info.get('totalOpenOrderInitialMargin', 0))
            max_withdraw_amount = float(self.account_info.get('maxWithdrawAmount', 0))
            
            return {
                'total_wallet_balance': total_wallet_balance,
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_margin_balance': total_margin_balance,
                'available_balance': available_balance,
                'total_position_initial_margin': total_position_initial_margin,
                'total_open_order_initial_margin': total_open_order_initial_margin,
                'max_withdraw_amount': max_withdraw_amount,
                'margin_ratio': float(self.account_info.get('totalMaintenanceMargin', 0)) / total_margin_balance * 100 if total_margin_balance > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки баланса: {e}")
            return None
    
    def get_open_positions(self) -> List[Dict]:
        """Получает открытые позиции"""
        if not self.client:
            logger.error("❌ Клиент не инициализирован")
            return []
        
        try:
            positions = self.client.futures_position_information()
            
            # Фильтруем только открытые позиции
            open_positions = []
            for position in positions:
                position_amt = float(position.get('positionAmt', 0))
                if position_amt != 0:
                    unrealized_pnl = float(position.get('unRealizedProfit', 0))
                    entry_price = float(position.get('entryPrice', 0))
                    mark_price = float(position.get('markPrice', 0))
                    
                    # Рассчитываем ROE (Return on Equity)
                    roe_percent = 0
                    if entry_price > 0:
                        if position_amt > 0:  # Long position
                            roe_percent = (mark_price - entry_price) / entry_price * 100
                        else:  # Short position
                            roe_percent = (entry_price - mark_price) / entry_price * 100
                    
                    open_positions.append({
                        'symbol': position.get('symbol'),
                        'side': 'LONG' if position_amt > 0 else 'SHORT',
                        'size': abs(position_amt),
                        'entry_price': entry_price,
                        'mark_price': mark_price,
                        'unrealized_pnl': unrealized_pnl,
                        'roe_percent': roe_percent,
                        'leverage': int(float(position.get('leverage', 1))),
                        'margin_type': position.get('marginType', 'UNKNOWN')
                    })
            
            return sorted(open_positions, key=lambda x: abs(x['unrealized_pnl']), reverse=True)
            
        except BinanceAPIException as e:
            logger.error(f"❌ Ошибка получения позиций: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}")
            return []
    
    def get_open_orders(self) -> List[Dict]:
        """Получает открытые ордера"""
        if not self.client:
            logger.error("❌ Клиент не инициализирован")
            return []
        
        try:
            orders = self.client.futures_get_open_orders()
            
            processed_orders = []
            for order in orders:
                processed_orders.append({
                    'symbol': order.get('symbol'),
                    'side': order.get('side'),
                    'type': order.get('type'),
                    'quantity': float(order.get('origQty', 0)),
                    'price': float(order.get('price', 0)),
                    'stop_price': float(order.get('stopPrice', 0)),
                    'time_in_force': order.get('timeInForce'),
                    'order_id': order.get('orderId'),
                    'client_order_id': order.get('clientOrderId'),
                    'time': datetime.fromtimestamp(int(order.get('time', 0)) / 1000).strftime('%H:%M:%S')
                })
            
            return processed_orders
            
        except BinanceAPIException as e:
            logger.error(f"❌ Ошибка получения ордеров: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}")
            return []
    
    def print_balance_summary(self) -> None:
        """Выводит сводку по балансу"""
        balance = self.get_balance_info()
        if not balance:
            print("❌ Не удалось получить информацию о балансе")
            return
        
        print("=" * 60)
        print(f"💰 БАЛАНС ФЬЮЧЕРСОВ ({NETWORK_MODE})")
        print("=" * 60)
        
        # Основные показатели
        print(f"💼 Общий баланс кошелька:     {balance['total_wallet_balance']:.4f} USDT")
        print(f"📊 Баланс с учетом позиций:   {balance['total_margin_balance']:.4f} USDT")
        print(f"💚 Доступный баланс:          {balance['available_balance']:.4f} USDT")
        print(f"📈 Нереализованная P&L:       {balance['total_unrealized_pnl']:.4f} USDT")
        
        # Маржинальные показатели
        print(f"🔒 Маржа в позициях:          {balance['total_position_initial_margin']:.4f} USDT")
        print(f"📋 Маржа в ордерах:           {balance['total_open_order_initial_margin']:.4f} USDT")
        print(f"💸 Максимальный вывод:        {balance['max_withdraw_amount']:.4f} USDT")
        print(f"⚡ Коэффициент маржи:         {balance['margin_ratio']:.2f}%")
        
        # Расчеты для торговли
        risk_amount = balance['available_balance'] * (RISK_PERCENT / 100)
        print(f"\n🎯 ТОРГОВЫЕ РАСЧЕТЫ (Risk: {RISK_PERCENT}%)")
        print(f"💰 Сумма на сделку:           {risk_amount:.4f} USDT")
        print(f"⚡ Плечо по умолчанию:        {FUTURES_LEVERAGE}x")
        
        print("=" * 60)
    
    def print_positions_summary(self) -> None:
        """Выводит сводку по позициям"""
        positions = self.get_open_positions()
        
        print(f"\n📊 ОТКРЫТЫЕ ПОЗИЦИИ ({len(positions)})")
        print("=" * 80)
        
        if not positions:
            print("✅ Открытых позиций нет")
            return
        
        # Подготавливаем данные для таблицы
        table_data = []
        total_pnl = 0
        
        for pos in positions:
            total_pnl += pos['unrealized_pnl']
            
            # Цветовые индикаторы для PnL
            pnl_indicator = "📈" if pos['unrealized_pnl'] > 0 else "📉" if pos['unrealized_pnl'] < 0 else "➖"
            side_indicator = "🟢" if pos['side'] == 'LONG' else "🔴"
            
            table_data.append([
                f"{side_indicator} {pos['symbol']}",
                pos['side'],
                f"{pos['size']:.4f}",
                f"{pos['entry_price']:.4f}",
                f"{pos['mark_price']:.4f}",
                f"{pnl_indicator} {pos['unrealized_pnl']:.4f}",
                f"{pos['roe_percent']:.2f}%",
                f"{pos['leverage']}x",
                pos['margin_type']
            ])
        
        headers = ['Символ', 'Сторона', 'Размер', 'Вход', 'Текущая', 'PnL', 'ROE%', 'Плечо', 'Тип']
        print(tabulate(table_data, headers=headers, tablefmt='grid', floatfmt='.4f'))
        
        # Итоговая PnL
        pnl_color = "📈 Прибыль" if total_pnl > 0 else "📉 Убыток" if total_pnl < 0 else "➖ Ноль"
        print(f"\n💰 Общая нереализованная PnL: {pnl_color}: {total_pnl:.4f} USDT")
    
    def print_orders_summary(self) -> None:
        """Выводит сводку по открытым ордерам"""
        orders = self.get_open_orders()
        
        print(f"\n📋 ОТКРЫТЫЕ ОРДЕРА ({len(orders)})")
        print("=" * 80)
        
        if not orders:
            print("✅ Открытых ордеров нет")
            return
        
        # Подготавливаем данные для таблицы
        table_data = []
        
        for order in orders:
            side_indicator = "🟢" if order['side'] == 'BUY' else "🔴"
            type_indicator = "💰" if order['type'] == 'LIMIT' else "⚡" if order['type'] == 'MARKET' else "🛑"
            
            price_display = f"{order['price']:.4f}" if order['price'] > 0 else "MARKET"
            stop_display = f"{order['stop_price']:.4f}" if order['stop_price'] > 0 else "-"
            
            table_data.append([
                f"{side_indicator} {order['symbol']}",
                f"{type_indicator} {order['type']}",
                order['side'],
                f"{order['quantity']:.4f}",
                price_display,
                stop_display,
                order['time_in_force'],
                order['time'],
                str(order['order_id'])[-6:]  # Последние 6 цифр ID
            ])
        
        headers = ['Символ', 'Тип', 'Сторона', 'Количество', 'Цена', 'Стоп', 'TIF', 'Время', 'ID']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
    
    def export_to_json(self, filename: str = None) -> str:
        """Экспортирует данные в JSON файл"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"futures_report_{timestamp}.json"
        
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'network': NETWORK_MODE,
                'balance': self.get_balance_info(),
                'positions': self.get_open_positions(),
                'orders': self.get_open_orders()
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📄 Отчет сохранен в {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения отчета: {e}")
            return ""
    
    def run_full_report(self, save_json: bool = False) -> None:
        """Запускает полный отчет"""
        logger.info("🚀 Запуск мониторинга фьючерсов...")
        
        if not self.client:
            print("❌ Не удалось подключиться к Binance API")
            return
        
        try:
            # Получаем все данные
            self.get_account_info()
            
            # Выводим отчеты
            self.print_balance_summary()
            self.print_positions_summary()
            self.print_orders_summary()
            
            # Сохраняем в JSON если нужно
            if save_json:
                filename = self.export_to_json()
                if filename:
                    print(f"\n💾 Отчет сохранен: {filename}")
            
            print(f"\n⏰ Последнее обновление: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации отчета: {e}")


def main():
    """Основная функция запуска"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Мониторинг фьючерсного аккаунта Binance')
    parser.add_argument('--json', action='store_true', help='Сохранить отчет в JSON файл')
    parser.add_argument('--balance-only', action='store_true', help='Показать только баланс')
    parser.add_argument('--positions-only', action='store_true', help='Показать только позиции')
    parser.add_argument('--orders-only', action='store_true', help='Показать только ордера')
    
    args = parser.parse_args()
    
    monitor = FuturesMonitor()
    
    if not monitor.client:
        print("❌ Не удалось инициализировать монитор")
        sys.exit(1)
    
    try:
        # Получаем данные аккаунта
        monitor.get_account_info()
        
        # Выводим запрошенные секции
        if args.balance_only:
            monitor.print_balance_summary()
        elif args.positions_only:
            monitor.print_positions_summary()
        elif args.orders_only:
            monitor.print_orders_summary()
        else:
            # Полный отчет
            monitor.run_full_report(save_json=args.json)
    
    except KeyboardInterrupt:
        print("\n👋 Работа прервана пользователем")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
