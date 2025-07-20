#!/usr/bin/env python3
from enhanced_signal_processor import AdvancedSignalProcessor

processor = AdvancedSignalProcessor('BTCUSDT')
prices = [118000.480000, 118698.51400000001, 115012.9363]

print('🔢 === ТЕСТ ИСПРАВЛЕННОГО ОКРУГЛЕНИЯ ===')
for price in prices:
    rounded = processor._round_price_for_symbol(price)
    remainder = rounded % 0.01
    print(f'   {price} → {rounded} (остаток: {remainder:.15f})')
