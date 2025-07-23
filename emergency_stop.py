"""
🛑 EMERGENCY STOP SCRIPT
Аварийная остановка всех торговых операций
"""

import os
import sys
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def activate_emergency_stop():
    """Активировать аварийную остановку в .env файле"""
    try:
        env_file = '.env'
        if not os.path.exists(env_file):
            logger.error("❌ .env file not found!")
            return False
            
        # Читаем файл
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Заменяем EMERGENCY_STOP на true
        if 'EMERGENCY_STOP=false' in content:
            content = content.replace('EMERGENCY_STOP=false', 'EMERGENCY_STOP=true')
        elif 'EMERGENCY_STOP=' not in content:
            content += '\nEMERGENCY_STOP=true\n'
        else:
            content = content.replace('EMERGENCY_STOP=true', 'EMERGENCY_STOP=true')  # Уже активен
            
        # Записываем обратно
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.info("🛑 EMERGENCY STOP ACTIVATED in .env file")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to activate emergency stop: {e}")
        return False

def close_all_positions():
    """Закрыть все открытые позиции"""
    try:
        # Получаем API ключи
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        
        if not api_key or not api_secret:
            logger.error("❌ Binance API keys not found in environment!")
            return False
            
        # Создаем клиент
        testnet = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
        client = Client(api_key, api_secret, testnet=testnet)
        
        # Получаем все открытые позиции
        account = client.futures_account()
        positions = [p for p in account['positions'] if float(p['positionAmt']) != 0]
        
        if not positions:
            logger.info("✅ No open positions to close")
            return True
            
        logger.info(f"🔍 Found {len(positions)} open positions")
        
        # Закрываем каждую позицию
        closed_count = 0
        for position in positions:
            symbol = position['symbol'] 
            size = abs(float(position['positionAmt']))
            side = 'SELL' if float(position['positionAmt']) > 0 else 'BUY'
            
            try:
                logger.info(f"🔄 Closing {symbol}: {side} {size}")
                
                # Размещаем рыночный ордер для закрытия
                order = client.futures_create_order(
                    symbol=symbol,
                    side=side,
                    type=Client.ORDER_TYPE_MARKET,
                    quantity=size,
                    positionSide='BOTH'  # Пытаемся оба режима
                )
                
                logger.info(f"✅ Closed {symbol}: Order ID {order['orderId']}")
                closed_count += 1
                
            except BinanceAPIException as e:
                if e.code == -4046:  # Position side doesn't match
                    try:
                        # Пробуем с правильным positionSide
                        pos_side = 'LONG' if float(position['positionAmt']) > 0 else 'SHORT'
                        order = client.futures_create_order(
                            symbol=symbol,
                            side=side,
                            type=Client.ORDER_TYPE_MARKET,
                            quantity=size,
                            positionSide=pos_side
                        )
                        logger.info(f"✅ Closed {symbol}: Order ID {order['orderId']}")
                        closed_count += 1
                    except Exception as e2:
                        logger.error(f"❌ Failed to close {symbol}: {e2}")
                else:
                    logger.error(f"❌ Failed to close {symbol}: {e}")
            except Exception as e:
                logger.error(f"❌ Unexpected error closing {symbol}: {e}")
                
        logger.info(f"✅ Closed {closed_count}/{len(positions)} positions")
        return closed_count == len(positions)
        
    except Exception as e:
        logger.error(f"❌ Failed to close positions: {e}")
        return False

def cancel_all_orders():
    """Отменить все открытые ордера"""
    try:
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        testnet = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
        
        client = Client(api_key, api_secret, testnet=testnet)
        
        # Получаем все открытые ордера
        open_orders = client.futures_get_open_orders()
        
        if not open_orders:
            logger.info("✅ No open orders to cancel")
            return True
            
        logger.info(f"🔍 Found {len(open_orders)} open orders")
        
        # Отменяем все ордера
        cancelled_count = 0
        for order in open_orders:
            symbol = order['symbol']
            order_id = order['orderId']
            
            try:
                client.futures_cancel_order(symbol=symbol, orderId=order_id)
                logger.info(f"✅ Cancelled order {order_id} for {symbol}")
                cancelled_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to cancel order {order_id}: {e}")
                
        logger.info(f"✅ Cancelled {cancelled_count}/{len(open_orders)} orders")
        return cancelled_count == len(open_orders)
        
    except Exception as e:
        logger.error(f"❌ Failed to cancel orders: {e}")
        return False

def emergency_shutdown():
    """Полная аварийная остановка"""
    logger.info("🚨 EMERGENCY SHUTDOWN INITIATED")
    logger.info("=" * 50)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"🕐 Timestamp: {timestamp}")
    
    results = {
        'emergency_stop_activated': False,
        'orders_cancelled': False,
        'positions_closed': False
    }
    
    # 1. Активировать emergency stop в конфиге
    logger.info("\n🔥 Step 1: Activating emergency stop...")
    results['emergency_stop_activated'] = activate_emergency_stop()
    
    # 2. Отменить все открытые ордера
    logger.info("\n🔥 Step 2: Cancelling all orders...")
    results['orders_cancelled'] = cancel_all_orders()
    
    # 3. Закрыть все позиции
    logger.info("\n🔥 Step 3: Closing all positions...")
    results['positions_closed'] = close_all_positions()
    
    # Итоговый отчет
    logger.info("\n" + "=" * 50)
    logger.info("🏁 EMERGENCY SHUTDOWN RESULTS:")
    
    for action, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"   {action}: {status}")
        
    all_success = all(results.values())
    
    if all_success:
        logger.info("\n🎯 ALL EMERGENCY ACTIONS COMPLETED SUCCESSFULLY")
        logger.info("💡 Trading is now stopped. Check your Binance account.")
        logger.info("🔄 To resume: Set EMERGENCY_STOP=false in .env")
    else:
        logger.info("\n⚠️  SOME EMERGENCY ACTIONS FAILED")
        logger.info("🔧 Check errors above and manually verify your Binance account")
        
    return all_success

def show_status():
    """Показать текущий статус аварийной остановки"""
    emergency_active = os.getenv('EMERGENCY_STOP', 'false').lower() == 'true'
    
    print(f"🛑 Emergency Stop Status: {'ACTIVE' if emergency_active else 'INACTIVE'}")
    
    if emergency_active:
        print("🚨 Trading is currently STOPPED")
        print("💡 To resume: Change EMERGENCY_STOP=false in .env")
    else:
        print("✅ Trading is currently ENABLED")
        print("🛑 To stop: Run this script or change EMERGENCY_STOP=true")

if __name__ == "__main__":
    print("🛑 PATRIOT Emergency Stop System")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--status':
            show_status()
            sys.exit(0)
        elif sys.argv[1] == '--activate-only':
            activate_emergency_stop()
            sys.exit(0)
        elif sys.argv[1] == '--close-positions':
            close_all_positions()
            sys.exit(0)
        elif sys.argv[1] == '--cancel-orders':
            cancel_all_orders()
            sys.exit(0)
        elif sys.argv[1] == '--help':
            print("Usage:")
            print("  python emergency_stop.py              - Full emergency shutdown")
            print("  python emergency_stop.py --status     - Show current status")  
            print("  python emergency_stop.py --activate-only - Only set emergency stop")
            print("  python emergency_stop.py --close-positions - Close all positions")
            print("  python emergency_stop.py --cancel-orders - Cancel all orders")
            sys.exit(0)
    
    # Подтверждение пользователя
    print("⚠️  This will:")
    print("   1. Stop all future trading")
    print("   2. Cancel all open orders") 
    print("   3. Close all open positions")
    print()
    
    confirm = input("🤔 Are you sure? Type 'YES' to proceed: ")
    
    if confirm != 'YES':
        print("❌ Emergency shutdown cancelled")
        sys.exit(0)
        
    # Запуск аварийной остановки
    success = emergency_shutdown()
    
    if success:
        print("\n🎉 Emergency shutdown completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Emergency shutdown completed with errors!")
        sys.exit(1)
