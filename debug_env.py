#!/usr/bin/env python3
"""
Тестовая проверка переменных окружения
"""

import os
print("=== DIRECT OS.GETENV ===")
print(f"BINANCE_TESTNET (raw): '{os.getenv('BINANCE_TESTNET')}'")
print(f"BINANCE_TESTNET == 'true': {os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'}")
print(f"BINANCE_TESTNET == 'false': {os.getenv('BINANCE_TESTNET', 'true').lower() == 'false'}")

try:
    print("\n=== CONFIG.PY ===")
    from config import BINANCE_TESTNET, NETWORK_MODE, BINANCE_API_KEY
    print(f"BINANCE_TESTNET: {BINANCE_TESTNET}")
    print(f"NETWORK_MODE: {NETWORK_MODE}")
    print(f"BINANCE_API_KEY: {BINANCE_API_KEY[:20]}..." if BINANCE_API_KEY else f"BINANCE_API_KEY: {BINANCE_API_KEY}")
except Exception as e:
    print(f"Error importing config: {e}")

print("\n=== ALL BINANCE ENV VARS ===")
for key, value in os.environ.items():
    if 'BINANCE' in key:
        if 'KEY' in key or 'SECRET' in key:
            print(f"{key}: {value[:20]}..." if value else f"{key}: {value}")
        else:
            print(f"{key}: {value}")
