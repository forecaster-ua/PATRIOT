import logging
import os
from pathlib import Path
from typing import List

# Загружаем переменные окружения из .env файла (только один раз)
_ENV_LOADED = False
if not _ENV_LOADED:
    try:
        from env_loader import load_env_file
        load_env_file()
        _ENV_LOADED = True
    except ImportError:
        print("Environment loader not available - using system environment variables only")

# Add UTC timezone setting
USE_UTC = True

# --- Directory Configuration ---
LOG_DIR = Path('logs')
LOG_FILE = LOG_DIR / 'signals.log'
BINANCE_LOG_FILE = LOG_DIR / 'binance.log'
LOG_LEVEL = logging.INFO

# Create logs directory if not exists
LOG_DIR.mkdir(exist_ok=True, mode=0o755)  # Secure directory permissions

# Logging configuration with UTF-8 encoding
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': str(LOG_FILE),
            'formatter': 'standard',
            'encoding': 'utf-8',
        },
        'binance_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': str(BINANCE_LOG_FILE),
            'formatter': 'standard',
            'encoding': 'utf-8',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        'binance_factory': {
            'level': 'INFO',
            'handlers': ['binance_file', 'console'],
            'propagate': False,
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file', 'console'],
    },
}

# --- API Configuration ---
API_BASE_URL = "http://194.135.94.212:8001/confirm-trade" # Base URL for the API
API_ENDPOINT = "/signal"
API_KEY = os.getenv("API_KEY", "maxa-secret-123")  # Prefer environment variable
API_TIMEOUT = 10  # seconds - increased for XGBoost latency (avg 7s)

# Специально для SignalProcessor
API_CLIENT_CONFIG = {  
    'base_url': API_BASE_URL,
    'api_key': API_KEY,
    'timeout': API_TIMEOUT
}

# --- Trading Configuration ---
TIMEFRAMES: List[str] = ['1h','4h']  # Consistent lowercase timeframe format '15m'

# --- Binance Configuration ---
# Определяем режим работы (testnet или mainnet)
BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

# Загружаем соответствующие API ключи в зависимости от режима
if BINANCE_TESTNET:
    # Режим тестовой сети
    BINANCE_API_KEY = os.getenv("BINANCE_TESTNET_API_KEY", "")
    BINANCE_API_SECRET = os.getenv("BINANCE_TESTNET_API_SECRET", "")
    NETWORK_MODE = "TESTNET"
else:
    # Боевой режим  
    BINANCE_API_KEY = os.getenv("BINANCE_MAINNET_API_KEY", "")
    BINANCE_API_SECRET = os.getenv("BINANCE_MAINNET_API_SECRET", "")
    NETWORK_MODE = "MAINNET"

# Проверяем наличие ключей для выбранного режима
if not BINANCE_API_KEY or not BINANCE_API_SECRET:
    missing_env = "TESTNET" if BINANCE_TESTNET else "MAINNET"
    print(f"⚠️  WARNING: Binance {missing_env} API keys not configured!")
    print(f"Required environment variables: BINANCE_{missing_env}_API_KEY, BINANCE_{missing_env}_API_SECRET")

# Настройки торговли фьючерсами
RISK_PERCENT = float(os.getenv("RISK_PERCENT", "2.0"))  # Процент от капитала на сделку (по умолчанию 2%)
FUTURES_LEVERAGE = int(os.getenv("FUTURES_LEVERAGE", "20"))  # Плечо для фьючерсов (по умолчанию 30x)
FUTURES_MARGIN_TYPE = os.getenv("FUTURES_MARGIN_TYPE", "CROSS")  # Режим маржи: CROSS или ISOLATED (по умолчанию CROSS)
PRICE_TOLERANCE_PERCENT = float(os.getenv("PRICE_TOLERANCE_PERCENT", "0.5"))  # 1% допустимое отклонение цены

# 🔧 Настройки управления позициями
MULTIPLE_ORDERS = os.getenv("MULTIPLE_ORDERS", "false").lower() == "true"  # Разрешить несколько ордеров на один тикер
MAX_CONCURRENT_ORDERS = int(os.getenv("MAX_CONCURRENT_ORDERS","3"))  # Максимум одновременных ордеров на инструмент

# --- Telegram Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "7948515996:AAHg9Tnvex3xyRc0rjnMscYTbHM1EUU5-d4")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1002693639183")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
TELEGRAM_PARSE_MODE = "Markdown"  # Форматирование сообщений
TELEGRAM_DISABLE_NOTIFICATION = False  # Включение/отключение уведомлени

# --- Data Validation ---
VALID_TIMEFRAMES = {'15m','1h', '4h', '1d'}  # For input validation '15m'
MAX_PAIRS_PER_REQUEST = 1  # Safety limit

# Retry configuration
MAX_API_RETRIES = 3  # Total attempts (initial + retries)
RETRY_DELAY_SEC = 1  # Seconds between tries

# ========================================
# TICKER MONITOR CONFIGURATION  
# ========================================

# Настройки обработки тикеров
TICKER_DELAY = 7.0              # Задержка между обработкой тикеров (секунды)
MAX_WORKERS = 1                 # Максимальное количество рабочих потоков
PROCESSING_TIMEOUT = 900        # Максимальное время обработки батча (секунды) - reduced from 1800

# Настройки планировщика
SCHEDULE_INTERVAL_MINUTES = 15  # Интервал запуска обработки (минуты)
SCHEDULE_AT_SECOND = ":00"      # На какой секунде запускать

# Настройки файлов
DEFAULT_TICKERS_FILE = 'tickers.txt'  # Файл с тикерами по умолчанию

# Настройки статистики и логирования
BATCH_LOG_FREQUENCY = 50        # Логировать каждые N оставшихся тикеров (увеличено для меньшего шума)

def reload_trading_config():
    """
    Динамически перезагружает критические торговые параметры из переменных окружения
    Вызывается перед каждым batch'ом обработки тикеров для применения новых настроек
    """
    global RISK_PERCENT, FUTURES_LEVERAGE, FUTURES_MARGIN_TYPE, PRICE_TOLERANCE_PERCENT
    global MULTIPLE_ORDERS, MAX_CONCURRENT_ORDERS
    global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_API_URL
    global BINANCE_TESTNET, BINANCE_API_KEY, BINANCE_API_SECRET
    
    # Торговые параметры
    old_risk = RISK_PERCENT
    old_leverage = FUTURES_LEVERAGE
    old_max_orders = MAX_CONCURRENT_ORDERS
    old_testnet = BINANCE_TESTNET
    
    RISK_PERCENT = float(os.getenv("RISK_PERCENT", "2.0"))
    FUTURES_LEVERAGE = int(os.getenv("FUTURES_LEVERAGE", "20"))
    FUTURES_MARGIN_TYPE = os.getenv("FUTURES_MARGIN_TYPE", "CROSS")
    PRICE_TOLERANCE_PERCENT = float(os.getenv("PRICE_TOLERANCE_PERCENT", "0.5"))
    MULTIPLE_ORDERS = os.getenv("MULTIPLE_ORDERS", "false").lower() == "true"
    MAX_CONCURRENT_ORDERS = int(os.getenv("MAX_CONCURRENT_ORDERS", "3"))
    
    # Binance настройки
    BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
    
    if BINANCE_TESTNET:
        BINANCE_API_KEY = os.getenv("BINANCE_TESTNET_API_KEY", "")
        BINANCE_API_SECRET = os.getenv("BINANCE_TESTNET_API_SECRET", "")
    else:
        BINANCE_API_KEY = os.getenv("BINANCE_MAINNET_API_KEY", "")
        BINANCE_API_SECRET = os.getenv("BINANCE_MAINNET_API_SECRET", "")
    
    # Telegram настройки
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "7948515996:AAHg9Tnvex3xyRc0rjnMscYTbHM1EUU5-d4")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1002693639183")
    TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Логируем важные изменения
    changes = []
    if old_risk != RISK_PERCENT:
        changes.append(f"RISK_PERCENT: {old_risk}% → {RISK_PERCENT}%")
    if old_leverage != FUTURES_LEVERAGE:
        changes.append(f"FUTURES_LEVERAGE: {old_leverage}x → {FUTURES_LEVERAGE}x")
    if old_max_orders != MAX_CONCURRENT_ORDERS:
        changes.append(f"MAX_CONCURRENT_ORDERS: {old_max_orders} → {MAX_CONCURRENT_ORDERS}")
    if old_testnet != BINANCE_TESTNET:
        changes.append(f"BINANCE_TESTNET: {old_testnet} → {BINANCE_TESTNET}")
    
    if changes:
        print("🔄 Trading config reloaded with changes:")
        for change in changes:
            print(f"   • {change}")
    
    return len(changes) > 0