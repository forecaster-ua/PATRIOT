# 🚀 PATRIOT Price Monitor

Веб-интерфейс для мониторинга цен криптовалют в реальном времени с поддержкой WebSocket подключений.

## 📋 Файлы системы

### 🎯 **Основные интерфейсы:**

#### 1. `price_monitor_direct.html` ⭐ **Рекомендуется**
- **Прямое подключение** к Binance WebSocket API
- **Самый простой** и надежный вариант
- Работает без дополнительных серверов
- Минимальные зависимости

#### 2. `price_monitor.html`
- Подключение через **PATRIOT WebSocket сервер**
- Расширенные возможности обработки данных
- Требует запуска Python WebSocket сервера

#### 3. `websocket_test.html`
- **Тестовая страница** для диагностики WebSocket подключений
- Полезна для отладки проблем с подключением

### 🖥️ **Серверные компоненты:**

#### 4. `start_price_monitor.py`
- **HTTP сервер** для обслуживания HTML файлов
- Автоматически открывает браузер
- Порт по умолчанию: 8080
- Поддерживает все HTML файлы

#### 5. `websocket_price_server.py`
- **Python WebSocket сервер** (промежуточный)
- Получает данные от Binance и передает в браузер
- Дополнительная обработка и логирование
- Порт: 8765

### � **Вспомогательные файлы:**

#### 6. `fetch_signal_example.py`
- Скрипт для получения торговых сигналов
- Использует инфраструктуру проекта

#### 7. `simple_signal_fetch.py`
- Автономный скрипт для получения сигналов
- Без зависимостей от других модулей

## 🚀 Варианты запуска

### ⭐ **Вариант 1: Прямое подключение (Рекомендуется)**

```bash
# 1. Запуск HTTP сервера
cd /home/alexross/patriot/production_bot
python3 start_price_monitor.py

# 2. Откроется браузер на http://localhost:8080/price_monitor_direct.html
# 3. Нажмите START для подключения к Binance
```

**Преимущества:**
- ✅ Самый простой способ
- ✅ Не требует дополнительных серверов
- ✅ Прямая связь с Binance
- ✅ Минимум точек отказа

### 🔧 **Вариант 2: Через PATRIOT WebSocket сервер**

```bash
# Терминал 1: Запуск WebSocket сервера
cd /home/alexross/patriot/production_bot
/home/alexross/patriot/venv/bin/python websocket_price_server.py

# Терминал 2: Запуск HTTP сервера  
python3 start_price_monitor.py

# 3. Откройте http://localhost:8080/price_monitor.html
# 4. Нажмите START для подключения к PATRIOT серверу
```

**Преимущества:**
- 🔄 Централизованное управление
- 📊 Расширенная обработка данных
- 📝 Детальное логирование
- 🛡️ Дополнительная обработка ошибок

### 🔍 **Вариант 3: Тестирование подключений**

```bash
# Запуск HTTP сервера
python3 start_price_monitor.py

# Откройте http://localhost:8080/websocket_test.html
# Протестируйте подключение к WebSocket серверу
```

## 📊 Мониторируемые тикеры

Система отслеживает следующие криптовалютные пары:

```
BTCUSDT, ETHUSDT, BNBUSDT, ADAUSDT, ALGOUSDT, 
APTUSDT, AVAXUSDT, SOLUSDT, CLVUSDT, BCHUSDT, 
WIFUSDT, XLMUSDT, XRPUSDT, XTZUSDT
```

*Список берется из файла `tickers.txt` и дублируется в JavaScript коде*

## 🎛️ Функции интерфейса

### Основные элементы:
- **START** - начать мониторинг цен
- **STOP** - остановить мониторинг  
- **Статус подключения** - индикация состояния (🟢🟡🔴):
  - 🟢 **Connected** - активное подключение
  - 🟡 **Connecting** - процесс подключения
  - 🔴 **Disconnected** - нет подключения

### Таблица данных:
- **Symbol** - символ криптовалютной пары
- **Current Price** - текущая цена (до 8 знаков после запятой)
- **24h Change** - изменение цены за последние 24 часа (%)
- **Last Update** - время последнего обновления данных

### 🎨 Цветовая схема:
- **🟢 Зеленый текст** - цена выросла с последнего обновления
- **🔴 Красный текст** - цена упала с последнего обновления  
- **⚫ Серый текст** - цена не изменилась или первое обновление
- **🟢 Положительные изменения** за 24ч отображаются зеленым
- **🔴 Отрицательные изменения** за 24ч отображаются красным

## 🔧 Технические детали

### Архитектура подключений:

#### Прямое подключение (price_monitor_direct.html):
```
Браузер → wss://stream.binance.com:9443/ws/ → Обновление UI
```

#### Через PATRIOT сервер (price_monitor.html):
```
Браузер → ws://localhost:8765 → Python сервер → Binance API → Обратно в браузер
```

### WebSocket спецификации:
- **Binance Endpoint**: `wss://stream.binance.com:9443/ws/`
- **Тип потока**: `@ticker` (24hr ticker statistics)
- **Формат стрима**: `symbol1@ticker/symbol2@ticker/...`
- **Частота обновлений**: В реальном времени (обычно <1 секунды)

### Браузерная совместимость:
- ✅ **Chrome/Chromium** 88+
- ✅ **Firefox** 85+
- ✅ **Safari** 14+
- ✅ **Edge** 88+
- ✅ **VS Code Simple Browser**

### Системные требования:
```bash
# Минимальные:
- Python 3.8+
- Интернет соединение
- Современный браузер

# Для WebSocket сервера (опционально):
pip install websockets aiohttp

# Базовый HTTP сервер использует встроенные модули Python
```

## 📝 Примеры использования

### Запуск на другом порту:
```bash
python3 start_price_monitor.py 8090
# HTTP сервер запустится на http://localhost:8090
# Все HTML файлы будут доступны на новом порту
```

### Доступ к различным интерфейсам:
```bash
# После запуска HTTP сервера:
http://localhost:8080/price_monitor_direct.html  # Прямое подключение
http://localhost:8080/price_monitor.html         # Через PATRIOT сервер  
http://localhost:8080/websocket_test.html        # Тестирование WebSocket
```

### Остановка серверов:
```bash
# В терминале с запущенным сервером
Ctrl+C

# Для принудительной остановки всех Python процессов (осторожно!)
pkill -f "python.*price_monitor"
```

### Тестирование сигналов:
```bash
# Получение данных сигнала BTCUSDT 15M
python3 fetch_signal_example.py          # Через инфраструктуру проекта
python3 simple_signal_fetch.py           # Автономный скрипт
```

## 🔍 Устранение неполадок

### 🚨 **Проблема: "Address already in use"**
```bash
# Найти процесс, занимающий порт
sudo lsof -i :8080
# или
ss -tulpn | grep :8080

# Остановить процесс (замените PID на актуальный)
kill -9 <PID>

# Или использовать другой порт
python3 start_price_monitor.py 8081
```

### 🌐 **Проблема: WebSocket не подключается к Binance**
1. **Проверьте интернет соединение:**
   ```bash
   ping 8.8.8.8
   ```

2. **Тестируйте доступность Binance API:**
   ```bash
   curl -I https://api.binance.com/api/v3/ping
   ```

3. **Проверьте брандмауэр/антивирус** - они могут блокировать WebSocket соединения

4. **Попробуйте другой браузер** - некоторые браузеры имеют строгие политики безопасности

### 🔧 **Проблема: Python WebSocket сервер не запускается**
```bash
# Проверьте установку зависимостей
/home/alexross/patriot/venv/bin/python -c "import websockets; print('OK')"

# Переустановите зависимости если нужно
/home/alexross/patriot/venv/bin/pip install --upgrade websockets aiohttp
```

### 📊 **Проблема: Данные не обновляются**
1. **Откройте консоль разработчика** (F12 в браузере)
2. **Проверьте вкладку Network** на наличие ошибок WebSocket
3. **Перезапустите подключение:** STOP → START
4. **Обновите страницу** (F5) и попробуйте снова
5. **Попробуйте прямое подключение** (`price_monitor_direct.html`)

### 🕸️ **Проблема: WebSocket подключение обрывается**
- Это нормальное поведение - Binance периодически сбрасывает соединения
- Интерфейс автоматически показывает статус "Disconnected"
- Просто нажмите START снова для переподключения

### 🔌 **Диагностика подключений:**
```bash
# Проверка портов
netstat -tulpn | grep -E ":8080|:8765"

# Тест WebSocket сервера
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" \
     http://localhost:8765/
```

## 🎯 Возможности расширения

### 📈 **Добавление новых тикеров:**
```javascript
// В HTML файлах найдите массив tickers и добавьте новые пары:
this.tickers = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT',
    // Добавьте здесь новые тикеры
    'DOGEUSDT', 'MATICUSDT'
];
```

### 🔔 **Уведомления о ценах:**
```javascript
// Добавить алерты при значительных изменениях
if (Math.abs(change) > 5) {  // Изменение больше 5%
    new Notification(`${symbol}: ${change.toFixed(2)}%`);
}
```

### 📊 **Интеграция графиков:**
```html
<!-- Добавить Chart.js для отображения графиков -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
```

### 💾 **Сохранение исторических данных:**
```python
# В websocket_price_server.py добавить логирование в базу данных
async def log_price_data(self, symbol, price, timestamp):
    # Сохранение в SQLite/PostgreSQL/MongoDB
    pass
```

### 🔍 **Фильтры и поиск:**
```javascript
// Добавить поиск по тикерам
function filterTickers(searchTerm) {
    const rows = document.querySelectorAll('#tableBody tr');
    rows.forEach(row => {
        const symbol = row.querySelector('.symbol').textContent;
        row.style.display = symbol.includes(searchTerm.toUpperCase()) ? '' : 'none';
    });
}
```

### 📱 **Мобильная адаптация:**
```css
/* Добавить медиа-запросы для мобильных устройств */
@media (max-width: 768px) {
    .table-container { overflow-x: auto; }
    .header h1 { font-size: 1.8rem; }
}
```

### 🔐 **Добавление аутентификации:**
```python
# В websocket_price_server.py
async def authenticate_client(self, websocket, credentials):
    # Проверка токена/пароля
    return is_valid_user(credentials)
```

### 📊 **Интеграция с торговыми сигналами:**
```python
# Объединение с существующими сигналами PATRIOT
from signal_analyzer import get_signal
signal = get_signal(symbol, timeframe)
# Отправка торговых рекомендаций в интерфейс
```

## 🏗️ Архитектура системы

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Браузер       │    │   HTTP Server    │    │   WebSocket     │
│                 │    │   (port 8080)    │    │   Server        │
│ ┌─────────────┐ │    │                  │    │   (port 8765)   │
│ │ HTML/JS/CSS │ │◄──►│ start_price_     │    │                 │
│ │ Interface   │ │    │ monitor.py       │    │ websocket_      │
│ └─────────────┘ │    │                  │    │ price_server.py │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                                               │
         │              Direct Connection                │
         ▼                                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Binance WebSocket API                        │
│              wss://stream.binance.com:9443/ws/                  │
└─────────────────────────────────────────────────────────────────┘
```

## 📚 Дополнительные ресурсы

### Документация API:
- [Binance WebSocket API](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md)
- [WebSocket в JavaScript](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Python websockets library](https://websockets.readthedocs.io/)

### Связанные файлы проекта:
- `tickers.txt` - список отслеживаемых криптовалютных пар
- `api_client.py` - клиент для получения торговых сигналов
- `signal_analyzer.py` - анализ торговых сигналов
- `telegram_bot.py` - Telegram уведомления

## 🎬 Заключение

PATRIOT Price Monitor предоставляет гибкую и надежную систему для мониторинга криптовалютных цен в реальном времени. 

**Рекомендации по использованию:**
- 🥇 **Для простого мониторинга**: используйте `price_monitor_direct.html`
- 🔧 **Для расширенной функциональности**: используйте связку `websocket_price_server.py` + `price_monitor.html`
- 🧪 **Для разработки и отладки**: используйте `websocket_test.html`

Система спроектирована с учетом модульности и легкости расширения, что позволяет адаптировать её под специфические потребности торгового процесса.

---

**🚀 PATRIOT Trading System - Price Monitor Module**  
*Создано: September 2025*  
*Версия: 2.0*  
*Статус: Production Ready* ✅
