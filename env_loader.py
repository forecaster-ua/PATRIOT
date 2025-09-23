"""
Environment loader for PATRIOT Trading System
============================================

Loads environment variables from .env file if available
"""

import os
from pathlib import Path

def load_env_file(env_file_path: str = ".env"):
    """
    Загружает переменные окружения из файла
    
    Args:
        env_file_path: Путь к файлу с переменными окружения
    """
    env_file = Path(env_file_path)
    
    if not env_file.exists():
        print(f"⚠️  Environment file not found: {env_file_path}")
        return False
    
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Пропускаем комментарии и пустые строки
                if not line or line.startswith('#'):
                    continue
                
                # Парсим переменную окружения
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Устанавливаем переменную окружения, если она не установлена
                    if key and not os.getenv(key):
                        os.environ[key] = value
        
        print(f"✅ Environment variables loaded from {env_file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error loading environment file: {e}")
        return False

def reload_env_config(env_file_path: str = ".env") -> bool:
    """
    Принудительно перезагружает переменные окружения из файла
    Перезаписывает существующие значения для динамического обновления конфигурации
    
    Args:
        env_file_path: Путь к файлу с переменными окружения
    
    Returns:
        bool: True если загрузка успешна, False в случае ошибки
    """
    env_file = Path(env_file_path)
    
    if not env_file.exists():
        print(f"⚠️  Environment file not found for reload: {env_file_path}")
        return False
    
    try:
        updated_vars = []
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Пропускаем комментарии и пустые строки
                if not line or line.startswith('#'):
                    continue
                
                # Парсим переменную окружения
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key:
                        old_value = os.getenv(key)
                        os.environ[key] = value
                        
                        # Логируем изменения
                        if old_value != value:
                            updated_vars.append(f"{key}: {old_value} → {value}")
        
        if updated_vars:
            print(f"🔄 Environment config reloaded with changes:")
            for change in updated_vars:
                print(f"   • {change}")
        else:
            print(f"✅ Environment config reloaded (no changes)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reloading environment file: {e}")
        return False

# Автоматическая загрузка только при прямом запуске
if __name__ == "__main__":
    load_env_file()
