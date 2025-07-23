# PATRIOT State Recovery System v1.0
## Система восстановления состояния торговой системы

### 🎯 ЦЕЛЬ СИСТЕМЫ
Обеспечить полную синхронизацию состояния между компонентами торговой системы при перезапуске `ticker_monitor.py`, предотвращая дублирование ордеров и обеспечивая целостность данных.

---

## 📋 АРХИТЕКТУРА СИСТЕМЫ

### 1. Основные Компоненты

#### 🔄 StateRecoveryManager (`state_recovery.py`)
- **Назначение**: Центральный менеджер восстановления состояния
- **Функции**:
  - Восстановление данных с биржи (позиции, ордера)
  - Синхронизация с Orders Watchdog
  - Анализ расхождений состояния
  - Блокировка символов с активными позициями

#### 🔗 OrdersSynchronizer (`orders_synchronizer.py`)
- **Назначение**: Синхронизация между ticker_monitor и orders_watchdog
- **Функции**:
  - Проверка статуса ордеров перед исполнением
  - Получение списка наблюдаемых символов
  - Валидация конфликтов ордеров

#### 📊 SyncMonitor (`sync_monitor.py`)
- **Назначение**: Диагностический инструмент
- **Функции**:
  - Мониторинг коммуникации между компонентами
  - Анализ конфликтов синхронизации
  - Тестирование системы

---

## 🚀 ИНТЕГРАЦИЯ В TICKER_MONITOR

### Startup Sequence (Последовательность запуска)

1. **Инициализация системы**
   ```python
   logger.info("🎼 Ticker Monitor Orchestra started!")
   ```

2. **State Recovery** 
   ```python
   logger.info("🔄 Starting system state recovery...")
   system_state = recover_system_state()
   ```

3. **Анализ состояния**
   - Проверка синхронизации
   - Вывод активных позиций 
   - Логирование проблем

4. **Обработка тикеров**
   - Проверка доступности символа перед анализом
   - Блокировка символов с активными позициями

### Worker Integration (Интеграция в Worker)

```python
# Проверка доступности символа
is_available, availability_reason = is_symbol_available_for_trading(ticker)
if not is_available:
    logger.warning(f"🚫 {ticker} blocked for trading: {availability_reason}")
    continue

# Продолжение анализа только для доступных символов
analyzer = SignalAnalyzer(ticker)
```

---

## 📊 СТРУКТУРЫ ДАННЫХ

### ActivePosition (Активная позиция)
```python
@dataclass
class ActivePosition:
    symbol: str                    # Символ
    side: str                      # LONG/SHORT
    size: float                    # Размер позиции
    entry_price: float            # Цена входа
    unrealized_pnl: float         # Нереализованная P&L
    margin_type: str              # Тип маржи
    isolated_wallet: float        # Изолированный кошелек
    has_sl: bool = False          # Есть Stop Loss
    has_tp: bool = False          # Есть Take Profit
    sl_order_id: Optional[str] = None
    tp_order_id: Optional[str] = None
    main_order_id: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
```

### SystemState (Состояние системы)
```python
@dataclass  
class SystemState:
    timestamp: datetime                                    # Время состояния
    active_positions: Dict[str, ActivePosition]          # Активные позиции
    watchdog_orders: Dict[str, Dict[str, Any]]           # Ордера Watchdog
    exchange_positions: Dict[str, Dict[str, Any]]        # Позиции с биржи  
    exchange_orders: Dict[str, List[Dict[str, Any]]]     # Ордера с биржи
    synchronization_issues: List[str]                    # Проблемы синхронизации
    recovery_actions: List[str]                          # Действия восстановления
    is_synchronized: bool = True                         # Статус синхронизации
```

---

## 🔧 ОСНОВНЫЕ ФУНКЦИИ

### 1. `recover_system_state() -> SystemState`
Главная функция восстановления состояния:
- Загружает состояние Orders Watchdog из `orders_watchdog_state.json`
- Получает позиции и ордера с биржи Binance
- Анализирует расхождения
- Возвращает полное состояние системы

### 2. `is_symbol_available_for_trading(symbol: str) -> Tuple[bool, str]`
Проверка доступности символа для торговли:
- Проверяет наличие активных позиций
- Блокирует символы с открытыми позициями  
- Возвращает статус и причину блокировки

### 3. `is_symbol_blocked_for_new_orders(symbol: str) -> Tuple[bool, str]`
Детальная проверка блокировки символа:
- Анализирует типы позиций (LONG/SHORT)
- Проверяет наличие связанных ордеров
- Предоставляет подробную информацию о блокировке

---

## 📝 ЛОГИРОВАНИЕ И МОНИТОРИНГ

### Startup Logs
```
🔄 Starting system state recovery...
📂 Загружаем состояние Orders Watchdog...
✅ Загружено 39 отслеживаемых ордеров
🌐 Получаем данные с биржи...
✅ С биржи: 17 позиций, 51 символов с ордерами
🔍 Анализ состояния и поиск расхождений...
✅ System state is synchronized
📊 Found 17 active positions:
   • MANAUSDT: LONG 309.0
   • BTCUSDT: SHORT 0.002
```

### Runtime Logs  
```
🚫 BTCUSDT blocked for trading: Активная позиция SHORT 0.002 (PnL: +0.00)
📂 Загружено состояние системы: 17 позиций
```

---

## 🛡️ МЕХАНИЗМ ЗАЩИТЫ

### 1. Предотвращение дублирования ордеров
- Символы с активными позициями автоматически блокируются
- Проверка происходит перед каждым анализом сигналов
- Детальная информация о причинах блокировки

### 2. Восстановление после сбоев
- Автоматическое восстановление состояния при старте
- Синхронизация с Orders Watchdog
- Получение актуальных данных с биржи

### 3. Обработка ошибок
- Graceful degradation при недоступности компонентов
- Mock функции для тестирования
- Подробное логирование проблем

---

## 🧪 ТЕСТИРОВАНИЕ

### Тест State Recovery
```bash
python state_recovery.py
```

### Тест Orders Synchronizer
```bash
python orders_synchronizer.py
```

### Тест Sync Monitor
```bash
python sync_monitor.py
```

### Интеграционный тест
```bash
python ticker_monitor.py
```

---

## 📁 ФАЙЛЫ СОСТОЯНИЯ

### `system_state.json`
Сохраненное состояние системы после восстановления

### `orders_watchdog_state.json`
Состояние Orders Watchdog с отслеживаемыми ордерами

### `orders_watchdog_requests.json` / `orders_watchdog_responses.json`
Файлы коммуникации между компонентами

---

## ✅ РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ

### State Recovery ✅
- ✅ Загрузка состояния Orders Watchdog (39 ордеров)
- ✅ Получение данных с биржи (17 позиций)
- ✅ Анализ расхождений (2 проблемы синхронизации)
- ✅ Сохранение состояния в system_state.json

### Symbol Blocking ✅
- ✅ BTCUSDT заблокирован (активная позиция SHORT)
- ✅ Остальные символы доступны для анализа
- ✅ Подробная информация о причинах блокировки

### Integration ✅
- ✅ Интеграция в ticker_monitor startup
- ✅ Проверка доступности в worker потоках
- ✅ Корректное логирование и мониторинг

---

## 🔮 PRODUCTION READY

Система готова к продакшену и обеспечивает:

1. **Полная синхронизация** при перезапуске ticker_monitor
2. **Предотвращение дублирования** ордеров
3. **Автоматическое восстановление** состояния
4. **Детальный мониторинг** и логирование
5. **Graceful degradation** при сбоях компонентов

**Статус: ✅ PRODUCTION READY**

*Created: January 23, 2025*  
*Author: HEDGER*  
*Version: 1.0*
