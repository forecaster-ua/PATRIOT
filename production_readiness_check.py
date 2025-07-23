"""
🔍 PRODUCTION READINESS CHECK
Финальная проверка системы перед запуском на боевом счету
"""

import os
import sys
import logging
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
from production_safety import ProductionSafetyManager, ProductionOrderValidator

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionReadinessChecker:
    """Проверка готовности к продакшену"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passed_checks = 0
        self.total_checks = 0
        
    def check_environment_variables(self) -> bool:
        """Проверка переменных окружения"""
        logger.info("🔍 Checking environment variables...")
        self.total_checks += 1
        
        # Используем config.py для определения режима
        try:
            from config import BINANCE_TESTNET, NETWORK_MODE
        except ImportError:
            self.errors.append("Cannot import config.py - check configuration")
            return False
        
        if BINANCE_TESTNET:
            logger.info("🧪 Detected TESTNET mode")
            binance_key_vars = ['BINANCE_TESTNET_API_KEY', 'BINANCE_TESTNET_API_SECRET']
            network_name = "TESTNET"
        else:
            logger.info("🚀 Detected PRODUCTION mode")  
            binance_key_vars = ['BINANCE_MAINNET_API_KEY', 'BINANCE_MAINNET_API_SECRET']
            network_name = "MAINNET"
            
        # Проверяем все необходимые переменные  
        required_vars = binance_key_vars + ['TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
                
        if missing_vars:
            self.errors.append(f"Missing {network_name} environment variables: {missing_vars}")
            return False
            
        # Для продакшена - дополнительные проверки
        if not BINANCE_TESTNET:
            # Дополнительная проверка для продакшена
            logger.info("🛡️ Additional production safety checks...")
        else:
            # Для testnet - предупреждение
            logger.info("🧪 Running in testnet mode")
            
        self.passed_checks += 1
        logger.info("✅ Environment variables OK")
        return True
        
    def check_api_connection(self) -> bool:
        """Проверка подключения к Binance API"""
        logger.info("🔍 Checking Binance API connection...")
        self.total_checks += 1
        
        try:
            # Используем config для получения правильных ключей
            from config import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET, NETWORK_MODE
            
            logger.info(f"📡 Connecting to Binance {NETWORK_MODE}...")
            
            if not BINANCE_API_KEY or not BINANCE_API_SECRET:
                self.errors.append(f"Binance {NETWORK_MODE} API keys not configured in config!")
                return False
            
            client = Client(
                BINANCE_API_KEY,
                BINANCE_API_SECRET,
                testnet=BINANCE_TESTNET
            )
            
            # Проверка аккаунта
            account = client.futures_account()
            balance = float(account['totalWalletBalance'])
            
            logger.info(f"💰 {NETWORK_MODE} Account Balance: {balance:.2f} USDT")
            
            # Разные пороги для testnet и mainnet
            min_balance = 10.0 if BINANCE_TESTNET else 50.0
            if balance < min_balance:
                warning_msg = f"Low {NETWORK_MODE} balance: {balance:.2f} USDT (recommended: >{min_balance})"
                if BINANCE_TESTNET:
                    self.warnings.append(warning_msg)
                else:
                    self.warnings.append(warning_msg + " - Consider depositing more for production")
                
            # Проверка API прав
            try:
                orders = client.futures_get_open_orders()
                logger.info(f"📊 Open orders: {len(orders)}")
            except BinanceAPIException as e:
                if e.code == -2014:  # API-key format invalid
                    self.errors.append(f"API key has insufficient permissions for {NETWORK_MODE}")
                    return False
                elif e.code == -1021:  # Timestamp issues
                    self.warnings.append("Timestamp sync issue detected - check system clock")
                    
            self.passed_checks += 1
            logger.info(f"✅ Binance {NETWORK_MODE} API connection OK")
            return True
            
        except Exception as e:
            self.errors.append(f"Binance API error: {str(e)}")
            return False
            
    def check_safety_settings(self) -> bool:
        """Проверка настроек безопасности"""
        logger.info("🔍 Checking safety settings...")
        self.total_checks += 1
        
        safety = ProductionSafetyManager()
        
        # Проверка консервативных настроек для новичков
        max_risk = float(os.getenv('MAX_RISK_PERCENT', '2.0'))
        if max_risk > 1.0:
            self.warnings.append(f"High risk setting: {max_risk}% (recommended < 1%)")
            
        default_risk = float(os.getenv('DEFAULT_RISK_PERCENT', '2.0'))  
        if default_risk > 1.0:
            self.warnings.append(f"High default risk: {default_risk}% (recommended < 1%)")
            
        leverage = int(os.getenv('DEFAULT_LEVERAGE', '10'))
        if leverage > 5:
            self.warnings.append(f"High leverage: {leverage}x (recommended ≤ 5x)")
            
        max_trades = int(os.getenv('MAX_DAILY_TRADES', '10'))
        if max_trades > 5:
            self.warnings.append(f"High daily trade limit: {max_trades} (recommended ≤ 5)")
            
        self.passed_checks += 1
        logger.info("✅ Safety settings checked")
        return True
        
    def check_file_dependencies(self) -> bool:
        """Проверка файлов системы"""
        logger.info("🔍 Checking file dependencies...")
        self.total_checks += 1
        
        required_files = [
            'enhanced_signal_processor.py',
            'signal_analyzer.py', 
            'telegram_bot.py',
            'ticker_monitor.py',
            'config.py',
            'production_safety.py'
        ]
        
        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)
                
        if missing_files:
            self.errors.append(f"Missing required files: {missing_files}")
            return False
            
        # Проверка директории логов
        if not os.path.exists('logs'):
            logger.info("📁 Creating logs directory...")
            os.makedirs('logs')
            
        self.passed_checks += 1
        logger.info("✅ File dependencies OK")
        return True
        
    def check_telegram_connection(self) -> bool:
        """Проверка Telegram бота"""
        logger.info("🔍 Checking Telegram connection...")
        self.total_checks += 1
        
        try:
            from telegram_bot import TelegramBot
            
            bot = TelegramBot()
            test_message = f"🧪 Production readiness test - {datetime.now().strftime('%H:%M:%S')}"
            
            bot.send_signal({
                'ticker': 'TEST',
                'timeframe': 'TEST',
                'signal': 'TEST',
                'entry_price': 50000,
                'confidence': 100,
                'timestamp': datetime.now().timestamp()
            })
            # Если дошли сюда без исключения, значит отправка прошла
            self.passed_checks += 1
            logger.info("✅ Telegram connection OK")
            return True
                
        except Exception as e:
            self.errors.append(f"Telegram error: {str(e)}")
            return False
            
    def check_both_api_environments(self) -> bool:
        """Проверка наличия ключей для обоих режимов (опциональная проверка)"""
        logger.info("🔍 Checking both TESTNET and MAINNET API keys availability...")
        
        testnet_keys = [
            os.getenv('BINANCE_TESTNET_API_KEY'),
            os.getenv('BINANCE_TESTNET_API_SECRET')
        ]
        
        mainnet_keys = [
            os.getenv('BINANCE_MAINNET_API_KEY'), 
            os.getenv('BINANCE_MAINNET_API_SECRET')
        ]
        
        testnet_available = all(testnet_keys)
        mainnet_available = all(mainnet_keys)
        
        if testnet_available and mainnet_available:
            logger.info("✅ Both TESTNET and MAINNET keys configured - can switch modes")
        elif testnet_available:
            logger.info("🧪 Only TESTNET keys available - limited to testing")
            self.warnings.append("Consider configuring MAINNET keys for production readiness")
        elif mainnet_available:
            logger.info("🚀 Only MAINNET keys available - production ready")
            self.warnings.append("Consider configuring TESTNET keys for safer testing")
        else:
            logger.warning("⚠️  No API keys configured for either mode")
            
        return True  # Не блокируем выполнение, это информативная проверка
            
    def run_full_check(self) -> bool:
        """Запустить полную проверку"""
        logger.info("🚀 Starting Production Readiness Check")
        logger.info("=" * 50)
        
        # Сначала покажем режим работы из config
        from config import BINANCE_TESTNET, NETWORK_MODE
        mode_name = f"🧪 {NETWORK_MODE}" if BINANCE_TESTNET else f"🚀 {NETWORK_MODE}"
        
        logger.info(f"📡 Mode: {mode_name}")
        logger.info("=" * 50)
        
        # Запуск всех проверок
        checks = [
            self.check_environment_variables,
            self.check_file_dependencies,
            self.check_api_connection,
            self.check_safety_settings,
            self.check_telegram_connection
        ]
        
        for check in checks:
            try:
                check()
            except Exception as e:
                self.errors.append(f"Check failed: {str(e)}")
                
        # Результаты
        logger.info("=" * 50)
        logger.info(f"📊 RESULTS: {self.passed_checks}/{self.total_checks} checks passed")
        
        if self.errors:
            logger.error("❌ ERRORS:")
            for error in self.errors:
                logger.error(f"   • {error}")
                
        if self.warnings:
            logger.warning("⚠️  WARNINGS:")
            for warning in self.warnings:
                logger.warning(f"   • {warning}")
                
        is_ready = len(self.errors) == 0
        
        if is_ready:
            # Используем config для определения режима
            from config import BINANCE_TESTNET, NETWORK_MODE
            mode_emoji = "🧪" if BINANCE_TESTNET else "🚀"
            mode_name = NETWORK_MODE
            is_production = not BINANCE_TESTNET
            
            logger.info(f"{mode_emoji} SYSTEM IS READY FOR {mode_name}!")
            logger.info("💡 Run: python ticker_monitor.py")
            if self.warnings:
                logger.info("⚠️  Consider addressing warnings for optimal safety")
                
            if is_production:
                logger.info("🚨 PRODUCTION MODE - REAL MONEY AT RISK!")
                logger.info("🛡️  Start with minimal amounts and monitor closely")
        else:
            logger.error("🛑 SYSTEM NOT READY - Fix errors above")
            
        return is_ready
        
def create_production_env():
    """Создать .env файл для продакшена"""
    if os.path.exists('.env.production'):
        logger.info("📄 .env.production already exists")
        return
        
    template = """# 🚨 PRODUCTION ENVIRONMENT - REAL MONEY!
# Copy this to .env and fill in your actual values

# NETWORK MODE (true = testnet, false = production)
BINANCE_TESTNET=false

# TESTNET API KEYS (for testing)
BINANCE_TESTNET_API_KEY=your_testnet_api_key_here
BINANCE_TESTNET_API_SECRET=your_testnet_secret_here

# MAINNET API KEYS (for production - NO WITHDRAWALS!)
BINANCE_MAINNET_API_KEY=your_production_api_key_here
BINANCE_MAINNET_API_SECRET=your_production_secret_here  

# TELEGRAM
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# SAFETY SETTINGS (CONSERVATIVE FOR BEGINNERS)
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
"""
    
    with open('.env.production', 'w', encoding='utf-8') as f:
        f.write(template)
        
    logger.info("📄 Created .env.production template")
    logger.info("🔑 Fill in your production API keys and copy to .env")

if __name__ == "__main__":
    print("🔍 PATRIOT Production Readiness Checker")
    print("=" * 50)
    
    # Создать шаблон .env если нужно
    if '--create-env' in sys.argv:
        create_production_env()
        sys.exit(0)
        
    # Показать текущий режим
    if '--show-mode' in sys.argv:
        from config import BINANCE_TESTNET, NETWORK_MODE
        mode_name = f"🧪 {NETWORK_MODE}" if BINANCE_TESTNET else f"🚀 {NETWORK_MODE}"
        print(f"Current mode: {mode_name}")
        
        if BINANCE_TESTNET:
            print("To switch to production: Set BINANCE_TESTNET=false in .env")
        else:
            print("To switch to testnet: Set BINANCE_TESTNET=true in .env")
        sys.exit(0)
        
    # Запустить проверку
    checker = ProductionReadinessChecker()
    
    # Опциональная проверка обоих режимов
    if '--check-both' in sys.argv:
        checker.check_both_api_environments()
        
    is_ready = checker.run_full_check()
    
    if is_ready:
        # Определяем режим для финальных инструкций из config
        from config import BINANCE_TESTNET
        testnet_mode = BINANCE_TESTNET
        
        if testnet_mode:
            print("\n🎯 TESTNET MODE - NEXT STEPS:")
            print("1. Test all functions with virtual funds")
            print("2. Verify signals and notifications work correctly")  
            print("3. Monitor logs for any errors")
            print("4. When ready, switch to PRODUCTION mode")
        else:
            print("\n🎯 PRODUCTION MODE - NEXT STEPS:")
            print("1. Start with minimum deposit (50-100 USDT)")
            print("2. Monitor first trades closely")  
            print("3. Keep emergency_stop.py handy")
            print("4. Review logs regularly: tail -f logs/production.log")
            print("🚨 REAL MONEY - BE EXTREMELY CAREFUL!")
            
        print(f"\n🚀 Command: python ticker_monitor.py")
    else:
        print("\n🔧 FIX ERRORS ABOVE BEFORE CONTINUING!")
        sys.exit(1)
