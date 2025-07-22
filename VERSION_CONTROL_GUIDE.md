# Система контроля версий PATRIOT - Работа на нескольких компьютерах

## 🖥️ **Стратегия синхронизации**

### 1️⃣ **Основные принципы**
- **GitHub** - единственный источник истины (Single Source of Truth)
- **Всегда pull перед работой** - получайте актуальные изменения
- **Регулярные commit'ы** - фиксируйте прогресс часто
- **Осмысленные commit message** - понятные описания изменений

### 2️⃣ **Ежедневный workflow**

#### Начало работы на любом компьютере:
```bash
# 1. Переходим в папку проекта
cd "d:\!PATRIOT"

# 2. ОБЯЗАТЕЛЬНО получаем последние изменения
git pull origin main

# 3. Проверяем статус
git status

# 4. Если есть конфликты - разрешаем их
# 5. Начинаем работу
```

#### Завершение работы:
```bash
# 1. Добавляем все изменения
git add .

# 2. Коммитим с описанием
git commit -m "Computer-X: [описание изменений]

- Что именно изменено
- Какие файлы затронуты
- Результат изменений"

# 3. Отправляем в GitHub
git push origin main
```

### 3️⃣ **Проверка актуальности версий**

#### Создайте файл version_check.py:
```python
#!/usr/bin/env python3
"""
Version Check - Проверка актуальности локальной версии
=====================================================
Сравнивает локальный и удаленный commit'ы
"""

import subprocess
import platform
from datetime import datetime

def get_local_commit():
    """Получает локальный commit hash"""
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()[:8]
    except:
        return "UNKNOWN"

def get_remote_commit():
    """Получает удаленный commit hash"""
    try:
        subprocess.run(['git', 'fetch', 'origin'], 
                      capture_output=True, check=True)
        result = subprocess.run(['git', 'rev-parse', 'origin/main'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()[:8]
    except:
        return "UNKNOWN"

def check_version_status():
    """Проверяет статус синхронизации"""
    print("🔍 PATRIOT Version Check")
    print("=" * 40)
    
    computer = platform.node()
    local_commit = get_local_commit()
    remote_commit = get_remote_commit()
    
    print(f"💻 Computer: {computer}")
    print(f"📅 Check time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"🏠 Local commit:  {local_commit}")
    print(f"☁️  Remote commit: {remote_commit}")
    
    if local_commit == remote_commit:
        print("✅ STATUS: UP TO DATE")
    else:
        print("⚠️  STATUS: OUT OF SYNC")
        print("💡 Run: git pull origin main")
    
    print("=" * 40)

if __name__ == "__main__":
    check_version_status()
```

### 4️⃣ **Автоматизация проверок**

#### В start_patriot.bat добавьте проверку:
```batch
@echo off
echo 🔍 Checking version sync...
python version_check.py
echo.
echo 🚀 Starting PATRIOT system...
python main_launcher.py
```

### 5️⃣ **Система тегов для релизов**

#### Создание версий:
```bash
# При важных milestone'ах
git tag -a v1.5.0 -m "Stage 1.5: Production Ready
- Symbol cache system
- Order execution
- Production deployment tools"

# Отправка тегов
git push origin --tags
```

#### Проверка версий:
```bash
# Показать все версии
git tag -l

# Показать последнюю версию
git describe --tags --abbrev=0
```

## 🔧 **Практические команды для каждого компьютера**

### Компьютер A (основной):
```bash
# Утром
git pull origin main
# ... работа ...
git add .
git commit -m "PC-A: Enhanced signal processor improvements"
git push origin main
```

### Компьютер B (второй):
```bash
# Перед работой
git pull origin main  # Получаем изменения с PC-A
# ... работа ...
git add .
git commit -m "PC-B: Added new websocket monitoring"
git push origin main
```

### Компьютер C (тестовый):
```bash
# Всегда актуальная версия
git pull origin main
# ... тестирование ...
git add .
git commit -m "PC-C: Test results and bug fixes"
git push origin main
```

## 🚨 **Частые проблемы и решения**

### Проблема: "Updates were rejected"
```bash
# Решение:
git pull origin main  # Получаем изменения
# Разрешаем конфликты если есть
git add .
git commit -m "Merge remote changes"
git push origin main
```

### Проблема: Конфликты в файлах
```bash
# 1. Посмотреть конфликтные файлы
git status

# 2. Редактировать файлы (убрать <<<< ==== >>>>)
# 3. Добавить исправленные файлы
git add conflicted_file.py

# 4. Завершить merge
git commit -m "Resolved merge conflicts"
```

### Проблема: Случайно отправили .env файл
```bash
# Если еще не push'нули:
git rm --cached .env
git commit -m "Remove .env from tracking"

# Если уже push'нули:
git rm .env
git commit -m "Remove sensitive .env file"
git push origin main
```

## 📊 **Мониторинг изменений**

### Быстрый статус:
```bash
# Что изменилось с последнего pull
git log --oneline -10

# Сравнение с удаленной веткой
git diff origin/main

# Статус файлов
git status --short
```

### Детальная история:
```bash
# История коммитов с компьютерами
git log --oneline --graph --all

# Изменения за последний день
git log --since="1 day ago" --oneline

# Кто что менял
git log --pretty=format:"%h %an %ar %s"
```

## 🎯 **Best Practices**

1. **Каждое утро**: `git pull origin main`
2. **Перед обедом**: commit + push промежуточных результатов
3. **Конец дня**: обязательный push всех изменений
4. **Перед выходными**: создание backup тега
5. **Осмысленные коммиты**: каждый commit = законченная мысль

## 🔐 **Безопасность**

### Что НИКОГДА не коммитить:
- `.env` файлы с API ключами
- `*.log` файлы
- `signals.db` с торговыми данными
- Персональные конфиги

### Проверка перед commit:
```bash
# Посмотреть что добавляется
git diff --cached

# Исключить конфиденциальные файлы
git reset HEAD .env
```

---

**💡 Главное правило**: Всегда начинайте с `git pull`, всегда заканчивайте с `git push`!
