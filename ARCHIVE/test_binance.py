#!/usr/bin/env python3
"""
Простой тест Binance подключения
"""
import config
from binance.client import Client

print(f"🔧 Режим: {config.NETWORK_MODE}")
print(f"🧪 Testnet: {config.BINANCE_TESTNET}")
print(f"🔑 API Key: {config.BINANCE_API_KEY[:20]}...")
print(f"🔐 Secret: {config.BINANCE_API_SECRET[:20]}...")

try:
    client = Client(
        api_key=config.BINANCE_API_KEY,
        api_secret=config.BINANCE_API_SECRET,
        testnet=config.BINANCE_TESTNET
    )
    
    # Для testnet фьючерсов используем futures_account()
    if config.BINANCE_TESTNET:
        print("🧪 Тестируем фьючерсный аккаунт (TESTNET)...")
        account = client.futures_account()
        print(f"✅ Подключение успешно!")
        print(f"💰 Баланс: {account['totalWalletBalance']} USDT")
        print(f"💵 Доступно: {account['availableBalance']} USDT")
    else:
        print("⚡ Тестируем спот аккаунт (MAINNET)...")
        account = client.get_account()
        print(f"✅ Подключение успешно!")
        print(f"📊 Тип аккаунта: {account['accountType']}")
        
        # Получаем баланс USDT
        balances = [b for b in account['balances'] if float(b['free']) > 0]
        print(f"💰 Активные балансы: {len(balances)}")
        
        for balance in balances:
            if balance['asset'] == 'USDT':
                print(f"  💵 USDT: {balance['free']}")
            
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")
