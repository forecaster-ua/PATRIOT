# 🔄 Динамическая перезагрузка параметров - Архитектурные решения

## 🎯 **Цель**: Перезагрузка критических параметров без остановки торговых процессов

---

## 📋 **Анализ критических параметров**

### 🔴 **Требуют немедленной перезагрузки:**
- `RISK_PERCENT` - процент риска на сделку
- `MAX_CONCURRENT_ORDERS` - лимит ордеров
- `FUTURES_LEVERAGE` - торговое плечо
- `MULTIPLE_ORDERS` - разрешение множественных ордеров
- `PRICE_TOLERANCE_PERCENT` - допустимое отклонение цены

### 🟡 **Могут ждать перезапуска:**
- `BINANCE_API_KEY/SECRET` - смена требует переподключения
- `TELEGRAM_TOKEN` - смена требует нового бота
- `TIMEFRAMES` - изменение архитектуры анализа

### 🟢 **Динамические по природе:**
- `tickers.txt` - список торговых пар
- Логические флаги и переключатели

---

## 🏗️ **Подход 1: ConfigManager (Рекомендуемый)**

### **Архитектура:**
```python
class ConfigManager:
    """Управляет динамической перезагрузкой конфигурации"""
    
    def __init__(self):
        self.config_file = Path(".env")
        self.tickers_file = Path("tickers.txt")
        self.last_env_modified = 0
        self.last_tickers_modified = 0
        self.cache = {}
    
    def get_param(self, key: str, default=None, param_type=str):
        """Получает параметр с автоматической перезагрузкой"""
        if self._should_reload_env():
            self._reload_env()
        return self._parse_value(self.cache.get(key, default), param_type)
    
    def get_tickers(self) -> List[str]:
        """Получает список тикеров с автоматической перезагрузкой"""
        if self._should_reload_tickers():
            self._reload_tickers()
        return self.cache.get('tickers', [])
```

### **Интеграция:**
```python
# В config.py - заменяем статические переменные
config_manager = ConfigManager()

# Динамические геттеры
def get_risk_percent() -> float:
    return config_manager.get_param('RISK_PERCENT', 2.0, float)

def get_max_concurrent_orders() -> int:
    return config_manager.get_param('MAX_CONCURRENT_ORDERS', 3, int)

def get_futures_leverage() -> int:
    return config_manager.get_param('FUTURES_LEVERAGE', 20, int)
```

---

## 🏗️ **Подход 2: Decorator Pattern**

### **Архитектура:**
```python
def dynamic_config(param_name: str, default_value, param_type=str):
    """Декоратор для динамической загрузки параметров"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            current_value = ConfigManager.instance().get_param(
                param_name, default_value, param_type
            )
            return func(current_value, *args, **kwargs)
        return wrapper
    return decorator

# Использование:
@dynamic_config('RISK_PERCENT', 2.0, float)
def calculate_position_size(risk_percent: float, balance: float) -> float:
    return balance * (risk_percent / 100)
```

---

## 🏗️ **Подход 3: Event-Driven Reloading**

### **Архитектура:**
```python
class ConfigWatcher:
    """Отслеживает изменения файлов и уведомляет компоненты"""
    
    def __init__(self):
        self.subscribers = {}
        self.file_watcher = None
    
    def subscribe(self, file_path: str, callback):
        """Подписка на изменения файла"""
        if file_path not in self.subscribers:
            self.subscribers[file_path] = []
        self.subscribers[file_path].append(callback)
    
    def start_watching(self):
        """Запуск мониторинга файлов"""
        # Используем watchdog library для мониторинга
        pass

# Использование:
config_watcher = ConfigWatcher()
config_watcher.subscribe('.env', lambda: reload_trading_params())
config_watcher.subscribe('tickers.txt', lambda: reload_tickers())
```

---

## 🏗️ **Подход 4: Hot-Reload Module**

### **Архитектура:**
```python
class HotReloadManager:
    """Горячая перезагрузка модулей и конфигурации"""
    
    def __init__(self):
        self.reload_callbacks = []
        self.check_interval = 5  # секунд
        
    def register_reload_callback(self, callback, priority=0):
        """Регистрирует callback для перезагрузки"""
        self.reload_callbacks.append((priority, callback))
        self.reload_callbacks.sort(key=lambda x: x[0])
    
    def trigger_reload(self, reload_type: str = "config"):
        """Триггерит перезагрузку всех зарегистрированных компонентов"""
        for priority, callback in self.reload_callbacks:
            try:
                callback(reload_type)
            except Exception as e:
                logger.error(f"Reload callback failed: {e}")
```

---

## 🏗️ **Подход 5: Configuration Service**

### **Архитектура:**
```python
class ConfigurationService:
    """Централизованный сервис конфигурации"""
    
    def __init__(self):
        self._config = {}
        self._lock = threading.RLock()
        self._listeners = defaultdict(list)
    
    def set(self, key: str, value, notify=True):
        """Устанавливает значение конфигурации"""
        with self._lock:
            old_value = self._config.get(key)
            self._config[key] = value
            
            if notify and old_value != value:
                self._notify_listeners(key, old_value, value)
    
    def get(self, key: str, default=None):
        """Получает значение конфигурации"""
        with self._lock:
            return self._config.get(key, default)
    
    def listen(self, key: str, callback):
        """Подписка на изменения параметра"""
        self._listeners[key].append(callback)
```

---

## 🎯 **Рекомендуемое решение: Hybrid Approach**

### **Комбинация подходов для оптимальной производительности:**

```python
class PatriotConfigManager:
    """
    Гибридный подход для PATRIOT Trading System:
    - ConfigManager для базовой функциональности
    - Event-driven для критических параметров
    - Thread-safe для многопоточности
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self.config_file = Path(".env")
        self.tickers_file = Path("tickers.txt")
        self.cache = {}
        self.file_stats = {}
        self.lock = threading.RLock()
        self.listeners = defaultdict(list)
        self._initialized = True
    
    def get_dynamic_param(self, key: str, default=None, param_type=str):
        """Получение параметра с проверкой обновлений"""
        with self.lock:
            if self._file_changed('.env'):
                self._reload_env_cache()
            
            raw_value = self.cache.get(key, default)
            return self._convert_type(raw_value, param_type)
    
    def get_tickers(self) -> List[str]:
        """Получение списка тикеров с проверкой обновлений"""
        with self.lock:
            if self._file_changed('tickers.txt'):
                self._reload_tickers_cache()
            
            return self.cache.get('tickers', [])
    
    def listen_for_changes(self, param_name: str, callback):
        """Подписка на изменения параметра"""
        self.listeners[param_name].append(callback)
    
    def _file_changed(self, filename: str) -> bool:
        """Проверка изменения файла по mtime"""
        file_path = Path(filename)
        if not file_path.exists():
            return False
        
        current_mtime = file_path.stat().st_mtime
        last_mtime = self.file_stats.get(filename, 0)
        
        if current_mtime > last_mtime:
            self.file_stats[filename] = current_mtime
            return True
        return False
```

---

## 🚀 **Интеграция в существующую систему**

### **1. Модификация config.py:**
```python
# Создаем глобальный менеджер
config_manager = PatriotConfigManager()

# Заменяем статические переменные на динамические функции
def RISK_PERCENT() -> float:
    return config_manager.get_dynamic_param('RISK_PERCENT', 2.0, float)

def MAX_CONCURRENT_ORDERS() -> int:
    return config_manager.get_dynamic_param('MAX_CONCURRENT_ORDERS', 3, int)

def FUTURES_LEVERAGE() -> int:
    return config_manager.get_dynamic_param('FUTURES_LEVERAGE', 20, int)
```

### **2. Модификация order_executor.py:**
```python
# Вместо импорта константы:
# from config import RISK_PERCENT

# Используем динамическую функцию:
from config import RISK_PERCENT

def calculate_position_size(self, ticker: str, entry_price: float, stop_loss: float):
    risk_percent = RISK_PERCENT()  # ← Динамическое получение
    # ... остальная логика
```

### **3. Модификация ticker_monitor.py:**
```python
def process_tickers(self) -> None:
    # Перезагружаем тикеры автоматически
    self.tickers = config_manager.get_tickers()  # ← Автоматическая перезагрузка
    
    # ... остальная логика
```

---

## ⚡ **Оптимизация производительности**

### **Кеширование с TTL:**
```python
def get_cached_param(self, key: str, ttl: int = 5):
    """Получение с кешированием на N секунд"""
    cache_key = f"{key}_cached"
    cache_time_key = f"{key}_cache_time"
    
    now = time.time()
    if (now - self.cache.get(cache_time_key, 0)) > ttl:
        self.cache[cache_key] = self._read_from_file(key)
        self.cache[cache_time_key] = now
    
    return self.cache[cache_key]
```

### **Асинхронная перезагрузка:**
```python
def schedule_background_reload(self):
    """Фоновая перезагрузка конфигурации"""
    def reload_worker():
        while not self.stop_event.is_set():
            try:
                self._check_and_reload_files()
                time.sleep(2)  # Проверка каждые 2 секунды
            except Exception as e:
                logger.error(f"Config reload error: {e}")
                time.sleep(10)
    
    reload_thread = threading.Thread(target=reload_worker, daemon=True)
    reload_thread.start()
```

---

## 📊 **Сравнение подходов**

| Подход | Производительность | Сложность | Надежность | Гибкость |
|--------|-------------------|-----------|------------|----------|
| ConfigManager | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Decorator | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Event-Driven | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Hot-Reload | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Service | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Hybrid** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 🎯 **Итоговые рекомендации**

### **Для PATRIOT Trading System:**

1. **Используйте Hybrid Approach** (PatriotConfigManager)
2. **Приоритет на безопасность** - thread-safe операции
3. **Кеширование с проверкой mtime** - баланс производительности
4. **Постепенная миграция** - не ломать существующий код
5. **Логирование изменений** - для отладки и аудита

### **Следующие шаги:**

1. Реализовать базовый PatriotConfigManager
2. Протестировать на критических параметрах
3. Постепенно мигрировать существующие константы
4. Добавить мониторинг и метрики
5. Документировать новый подход

**Хотите реализовать конкретное решение?**
