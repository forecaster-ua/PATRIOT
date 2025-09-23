# 🧹 ПЛАН ОЧИСТКИ ПРОЕКТА PATRIOT

## 📋 ФАЙЛЫ ДЛЯ УДАЛЕНИЯ/АРХИВИРОВАНИЯ

### 🗑️ ФАЙЛЫ ДЛЯ ПОЛНОГО УДАЛЕНИЯ (тестовые/отладочные)
- `test_api_keys.py` - тест API ключей
- `test_binance.py` - тест подключения к Binance
- `test_btc_leverage.py` - тест левеража BTC
- `test_positions.py` - тест позиций
- `test_simple.py` - простой тест
- `debug_detailed.py` - детальная отладка
- `debug_positions.py` - отладка позиций
- `debug_processor.py` - отладка процессора
- `mainnet_debug.py` - отладка mainnet
- `mini_test.py` - мини тест
- `leverage_test.py` - тест левеража
- `check_leverage.py` - проверка левеража
- `leverage_issue.txt` - описание проблем с леверажем

### 📦 ФАЙЛЫ ДЛЯ АРХИВИРОВАНИЯ (могут пригодиться)
- `quick_test.py` → `ARCHIVE/quick_test.py` (рабочий код для trading_engine)
- `quick_test_fixed.py` → `ARCHIVE/quick_test_fixed.py`
- `enhanced_signal_processor_backup.py` → `ARCHIVE/`
- `get_entry_generator.py` → `ARCHIVE/` (старый генератор)
- `get_leverage_function.py` → `ARCHIVE/` (функции левеража)
- `tickers_cut.txt` → `ARCHIVE/` (усеченный список тикеров)
- `simple_launcher.py` → `ARCHIVE/` (старый лаунчер)
- `ticker_monitor_runner.py` → `ARCHIVE/` (старый раннер)

### 📁 ФАЙЛЫ ДЛЯ УДАЛЕНИЯ (пустые/устаревшие)
- `binance_factory.py` (пустой файл)
- `main_launcher.py` (пустой файл, архивная версия есть в ARCHIVE)

### 🧹 ОЧИСТКА СЛУЖЕБНЫХ ФАЙЛОВ
- `__pycache__/` - папка с кешем Python
- `logs/` - старые логи (оставить только последние)
- `signals.db` - база сигналов (можем оставить или архивировать)

## ✅ ДЕЙСТВИЯ ПО ОЧИСТКЕ

### Этап 1: Архивирование важных файлов
### Этап 2: Удаление тестовых файлов  
### Этап 3: Удаление пустых файлов
### Этап 4: Очистка служебных папок
### Этап 5: Обновление .gitignore

---
**Результат**: Чистый проект с только необходимыми файлами для рефакторинга
