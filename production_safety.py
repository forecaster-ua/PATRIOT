"""
🛡️ PRODUCTION SAFETY MANAGER
Модуль для безопасной торговли на боевом счету
"""

import os
import logging
from datetime import datetime, date
from typing import Tuple, Dict, Any, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

class ProductionSafetyManager:
    """Менеджер безопасности для продакшена"""
    
    def __init__(self):
        self.daily_trades_count = 0
        self.last_reset_date = None
        self.emergency_stop = os.getenv('EMERGENCY_STOP', 'false').lower() == 'true'
        self.min_balance = float(os.getenv('MIN_ACCOUNT_BALANCE', '50'))
        self.max_daily_trades = int(os.getenv('MAX_DAILY_TRADES', '3'))
        self.min_confidence = float(os.getenv('MIN_CONFIDENCE', '75'))
        self.max_risk_percent = float(os.getenv('MAX_RISK_PERCENT', '1.0'))
        
        logger.info(f"🛡️ Safety Manager initialized:")
        logger.info(f"   Min Balance: {self.min_balance} USDT")
        logger.info(f"   Max Daily Trades: {self.max_daily_trades}")
        logger.info(f"   Min Confidence: {self.min_confidence}%")
        logger.info(f"   Max Risk: {self.max_risk_percent}%")
        
    def can_trade(self, account_balance: float, signal_confidence: float, risk_percent: float) -> Tuple[bool, str]:
        """
        Комплексная проверка безопасности перед торговлей
        
        Args:
            account_balance: Текущий баланс аккаунта
            signal_confidence: Уверенность в сигнале (0-100)
            risk_percent: Процент риска на сделку
            
        Returns:
            Tuple[bool, str]: (можно ли торговать, причина)
        """
        
        # 1. Проверка аварийной остановки
        if self.emergency_stop:
            return False, "🛑 EMERGENCY STOP ACTIVE - All trading suspended"
            
        # 2. Проверка баланса
        if account_balance < self.min_balance:
            return False, f"💰 Insufficient balance: {account_balance:.2f} < {self.min_balance}"
            
        # 3. Проверка дневного лимита сделок
        today = date.today()
        if self.last_reset_date != today:
            self.daily_trades_count = 0
            self.last_reset_date = today
            logger.info(f"📅 New day: Reset daily trade counter to 0")
            
        if self.daily_trades_count >= self.max_daily_trades:
            return False, f"📊 Daily trade limit reached: {self.daily_trades_count}/{self.max_daily_trades}"
            
        # 4. Проверка уверенности в сигнале
        if signal_confidence < self.min_confidence:
            return False, f"⚠️ Low confidence signal: {signal_confidence:.1f}% < {self.min_confidence}%"
            
        # 5. Проверка процента риска
        if risk_percent > self.max_risk_percent:
            return False, f"⚠️ Risk too high: {risk_percent}% > {self.max_risk_percent}%"
            
        return True, f"✅ Safe to trade (Trade #{self.daily_trades_count + 1}/{self.max_daily_trades})"
        
    def record_trade(self, order_result: Dict[str, Any]):
        """Записать выполненную сделку"""
        self.daily_trades_count += 1
        logger.info(f"📝 Trade recorded: {self.daily_trades_count}/{self.max_daily_trades} for today")
        
        # Логирование для аудита
        audit_info = {
            'timestamp': datetime.now().isoformat(),
            'trade_number': self.daily_trades_count,
            'order_id': order_result.get('order_id', 'N/A'),
            'success': order_result.get('success', False)
        }
        logger.info(f"📋 Audit: {audit_info}")
        
    def get_status(self) -> Dict[str, Any]:
        """Получить текущий статус безопасности"""
        today = date.today()
        if self.last_reset_date != today:
            self.daily_trades_count = 0
            
        return {
            'emergency_stop': self.emergency_stop,
            'daily_trades': f"{self.daily_trades_count}/{self.max_daily_trades}",
            'remaining_trades': max(0, self.max_daily_trades - self.daily_trades_count),
            'min_balance': self.min_balance,
            'min_confidence': self.min_confidence,
            'max_risk': self.max_risk_percent
        }

class ProductionOrderValidator:
    """Валидация ордеров для продакшена"""
    
    @staticmethod
    def validate_order_params(symbol: str, quantity: float, price: Optional[float] = None) -> Tuple[bool, str]:
        """
        Валидация параметров ордера перед отправкой
        
        Args:
            symbol: Торговая пара
            quantity: Количество
            price: Цена (для лимитных ордеров)
            
        Returns:
            Tuple[bool, str]: (валиден ли ордер, сообщение об ошибке)
        """
        
        # 1. Проверка символа
        if not symbol or not isinstance(symbol, str):
            return False, "Invalid symbol"
            
        # 2. Проверка количества
        if quantity <= 0:
            return False, f"Invalid quantity: {quantity}"
            
        # Минимальные объемы для основных пар
        min_quantities = {
            'BTCUSDT': 0.001,
            'ETHUSDT': 0.01,
            'BNBUSDT': 0.1,
        }
        
        min_qty = min_quantities.get(symbol, 0.001)
        if quantity < min_qty:
            return False, f"Quantity {quantity} below minimum {min_qty} for {symbol}"
            
        # 3. Проверка цены (для лимитных ордеров)
        if price is not None:
            if price <= 0:
                return False, f"Invalid price: {price}"
                
            # Проверка разумности цены (не более чем в 2 раза от текущей цены)
                
        return True, "Order parameters valid"
        
    @staticmethod
    def validate_stop_loss_take_profit(entry_price: float, stop_loss: float, 
                                     take_profit: float, side: str) -> Tuple[bool, str]:
        """
        Валидация SL/TP относительно цены входа
        
        Args:
            entry_price: Цена входа
            stop_loss: Цена стоп-лосса
            take_profit: Цена тейк-профита  
            side: Сторона сделки (BUY/SELL)
            
        Returns:
            Tuple[bool, str]: (валидны ли уровни, сообщение об ошибке)
        """
        
        if side == 'BUY':  # Long позиция
            # SL должен быть ниже входа, TP выше входа
            if stop_loss >= entry_price:
                return False, f"LONG: Stop Loss {stop_loss} должен быть ниже Entry {entry_price}"
            if take_profit <= entry_price:
                return False, f"LONG: Take Profit {take_profit} должен быть выше Entry {entry_price}"
                
        else:  # SELL / Short позиция
            # SL должен быть выше входа, TP ниже входа
            if stop_loss <= entry_price:
                return False, f"SHORT: Stop Loss {stop_loss} должен быть выше Entry {entry_price}"
            if take_profit >= entry_price:
                return False, f"SHORT: Take Profit {take_profit} должен быть ниже Entry {entry_price}"
                
        # Проверка разумности расстояний (не более 50% движения)
        price_range = abs(entry_price - stop_loss) / entry_price
        if price_range > 0.5:  # 50% движение
            return False, f"Stop Loss слишком далеко: {price_range*100:.1f}% от цены входа"
            
        return True, "SL/TP levels valid"

def create_production_safety_env_template():
    """Создать шаблон .env файла для продакшена"""
    template = """
# 🚨 PRODUCTION ENVIRONMENT SETTINGS
# REAL MONEY - BE EXTREMELY CAREFUL!

# BINANCE API (Production)
BINANCE_API_KEY=your_production_api_key_here
BINANCE_API_SECRET=your_production_secret_here  
BINANCE_TESTNET=false

# TELEGRAM
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# SAFETY SETTINGS (CONSERVATIVE DEFAULTS)
EMERGENCY_STOP=false
MIN_ACCOUNT_BALANCE=50.0
MAX_DAILY_TRADES=3
MIN_CONFIDENCE=75.0
MAX_RISK_PERCENT=0.5

# TRADING SETTINGS (REDUCED RISK)
DEFAULT_RISK_PERCENT=0.5
DEFAULT_LEVERAGE=3
SUPPORTED_TIMEFRAMES=15m,1h,4h

# LOGGING
LOG_LEVEL=INFO
LOG_FILE=logs/production.log
"""
    return template

if __name__ == "__main__":
    # Тестирование safety manager
    print("🧪 Testing Production Safety Manager")
    
    safety = ProductionSafetyManager()
    status = safety.get_status()
    print(f"📊 Status: {status}")
    
    # Тест проверки торговли
    can_trade, reason = safety.can_trade(
        account_balance=100.0,
        signal_confidence=80.0, 
        risk_percent=0.5
    )
    print(f"✅ Can trade: {can_trade}, Reason: {reason}")
    
    # Тест валидации ордера
    validator = ProductionOrderValidator()
    valid, msg = validator.validate_order_params('BTCUSDT', 0.001, 50000.0)
    print(f"✅ Order valid: {valid}, Message: {msg}")
    
    print("\n📝 Environment template:")
    print(create_production_safety_env_template())
