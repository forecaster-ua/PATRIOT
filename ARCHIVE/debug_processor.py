#!/usr/bin/env python3
"""
Отладка enhanced_signal_processor
"""
import config
print(f"🔧 Config loaded. TESTNET: {config.BINANCE_TESTNET}")
print(f"🔑 API Key: {config.BINANCE_API_KEY[:20]}...")

from binance.client import Client

try:
    print("📱 Создаем Binance клиента...")
    client = Client(
        api_key=config.BINANCE_API_KEY,
        api_secret=config.BINANCE_API_SECRET,
        testnet=config.BINANCE_TESTNET
    )
    
    print("🧪 Тестируем фьючерсы...")
    account = client.futures_account()
    print(f"✅ Фьючерсы работают! Баланс: {account['totalWalletBalance']}")
    
    print("📊 Импортируем EnhancedSignalProcessor...")
    from enhanced_signal_processor import EnhancedSignalProcessor
    
    print("🚀 Создаем процессор...")
    processor = EnhancedSignalProcessor("BTCUSDT", risk_percent=5.0)
    
    print("✅ Все успешно!")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    print(traceback.format_exc())
