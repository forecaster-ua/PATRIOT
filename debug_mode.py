#!/usr/bin/env python3
"""
Отладка режима testnet/mainnet
"""

import os

print("🔍 Debug режима testnet/mainnet")
print("=" * 50)

# 1. Сырое значение из .env
raw_value = os.getenv('BINANCE_TESTNET')
print(f"1. Raw BINANCE_TESTNET: '{raw_value}' (type: {type(raw_value)})")

# 2. После обработки по логике config.py
config_logic = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
print(f"2. Config.py логика: {config_logic}")
print(f"   ('{os.getenv('BINANCE_TESTNET', 'true')}' -> '{os.getenv('BINANCE_TESTNET', 'true').lower()}' -> == 'true' -> {config_logic})")

# 3. Импортируем config
print("\n📦 Импорт config.py...")
try:
    from config import BINANCE_TESTNET, NETWORK_MODE, BINANCE_API_KEY
    print(f"3. Config BINANCE_TESTNET: {BINANCE_TESTNET}")
    print(f"4. Config NETWORK_MODE: {NETWORK_MODE}")
    print(f"5. API Key starts with: {BINANCE_API_KEY[:10]}...")
    
    # Правильное определение режима
    if BINANCE_TESTNET:
        print("✅ Система определила: TESTNET режим")
    else:
        print("✅ Система определила: MAINNET режим")
        
except Exception as e:
    print(f"❌ Ошибка импорта config: {e}")

print("\n🧮 Логическая проверка:")
print(f"   'false' == 'true': {'false' == 'true'}")
print(f"   'true' == 'true': {'true' == 'true'}")

print("\n💡 Должно быть:")
print("   BINANCE_TESTNET=false -> MAINNET режим")
print("   BINANCE_TESTNET=true -> TESTNET режим")
