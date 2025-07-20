# PATRIOT Production Deployment Guide - Configuration Management

## Конфигурация и переменные окружения

### Архитектурный принцип
PATRIOT система использует **централизованную конфигурацию** через `config.py`. Это обеспечивает:
- Единую точку управления настройками
- Правильную загрузку переменных окружения  
- Консистентность между модулями
- Безопасность и отладочность

### Файловая структура конфигурации
```
.env                    # Секретные переменные (не в git)
env_loader.py           # Загрузка .env файла
config.py              # Центральная конфигурация 
├── все модули системы # Импортируют ТОЛЬКО из config.py
```

## Правила для разработки

### ✅ ПРАВИЛЬНО - Используйте config.py
```python
from config import (
    BINANCE_TESTNET,
    NETWORK_MODE, 
    BINANCE_API_KEY,
    BINANCE_SECRET_KEY
)

# Определение режима
if BINANCE_TESTNET:
    print("🔧 TESTNET режим - безопасное тестирование")
else:
    print("🚀 MAINNET режим - боевое окружение")
```

### ❌ НЕПРАВИЛЬНО - Прямой доступ к os.getenv()
```python
import os

# НЕ ДЕЛАЙТЕ ТАК!
testnet = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
api_key = os.getenv('BINANCE_API_KEY')
```

**Проблема**: Прямые вызовы `os.getenv()` могут возвращать `None` или неправильные значения, 
если `.env` файл не загружен через `env_loader`.

## Настройка продакшн окружения

### 1. Создание .env файла
```bash
# Режим работы
BINANCE_TESTNET=false

# MAINNET API ключи (для продакшена)
BINANCE_API_KEY=your_production_api_key_here
BINANCE_SECRET_KEY=your_production_secret_key_here

# TESTNET API ключи (для тестирования)
BINANCE_TESTNET_API_KEY=your_testnet_api_key_here  
BINANCE_TESTNET_SECRET_KEY=your_testnet_secret_key_here

# Telegram бот
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Дополнительные настройки
LOG_LEVEL=INFO
MAX_CONCURRENT_ORDERS=3
```

### 2. Проверка конфигурации
Запустите диагностический скрипт:
```powershell
python debug_env.py
```

Ожидаемый вывод для продакшена:
```
=== CONFIG.PY ===
BINANCE_TESTNET: False
NETWORK_MODE: MAINNET  
BINANCE_API_KEY: your_production_key...
```

### 3. Валидация режима перед деплоем
```python
from config import BINANCE_TESTNET, NETWORK_MODE

assert not BINANCE_TESTNET, f"❌ Обнаружен TESTNET режим! Измените BINANCE_TESTNET=false"
assert NETWORK_MODE == "MAINNET", f"❌ Неправильный режим: {NETWORK_MODE}"
print("✅ Конфигурация готова для продакшена")
```

## Переключение режимов

### Переход в TESTNET (для тестирования)
```bash
# В .env файле
BINANCE_TESTNET=true
```

### Переход в MAINNET (для продакшена)  
```bash
# В .env файле
BINANCE_TESTNET=false
```

После изменения перезапустите систему.

## Безопасность

### Защита .env файла
- ✅ Добавьте `.env` в `.gitignore`
- ✅ Установите права доступа: `chmod 600 .env`
- ✅ Создайте резервные копии в защищенном месте
- ✅ Используйте разные ключи для testnet/mainnet

### Мониторинг конфигурации
Система автоматически логирует:
```
INFO: 🚀 PATRIOT запущен в MAINNET режиме
INFO: 🔧 API ключи загружены для продакшена
```

## Устранение проблем

### Проблема: "Raw BINANCE_TESTNET: 'None'"
**Причина**: Попытка прямого доступа к `os.getenv()` без инициализации
**Решение**: Используйте импорт из `config.py`

### Проблема: Неправильный режим
**Причина**: Конфликт между разными способами определения режима  
**Решение**: Проверьте все модули на использование `config.py`

### Проблема: API ключи не найдены
**Причина**: Неправильные имена переменных или отсутствие `.env`
**Решение**: Проверьте содержимое `.env` файла и его загрузку

---

## История изменений
- **20.07.2025**: Создан после обнаружения конфликта конфигурации
- Исправлены множественные файлы с неправильным доступом к переменным окружения
- Добавлена централизованная система конфигурации
