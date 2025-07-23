import logging
from logging.handlers import RotatingFileHandler  # Fixed import
import sys
from pathlib import Path
from typing import Optional
from config import LOG_DIR, LOG_FILE, LOG_LEVEL

def setup_logger(name: str = 'signals') -> logging.Logger:
    """Centralized logging setup"""
    try:
        LOG_DIR.mkdir(exist_ok=True, parents=True)
        
        logger = logging.getLogger(name)
        logger.setLevel(LOG_LEVEL)

        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-7s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # File handler (rotating)
        file_handler = RotatingFileHandler(  # Now using properly imported class
            LOG_FILE, 
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        # Remove existing handlers if any
        logger.handlers.clear()
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger

    except Exception as e:
        print(f"CRITICAL: Failed to initialize logger: {str(e)}")
        raise

logger = setup_logger()