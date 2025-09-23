# 🖥️ PATRIOT Multi-Computer Quick Reference

## 🚀 **Ежедневные команды**

### Утром (начало работы):
```bash
# Проверка статуса
python version_check.py
# или
.\sync.ps1 check

# Получение последних изменений
git pull origin main
# или
.\sync.ps1 pull
```

### В течение дня (сохранение прогресса):
```bash
# Быстрый commit
.\sync.ps1 commit -Message "Added new feature X"

# Отправка в GitHub
.\sync.ps1 push

# Или все сразу
.\sync.ps1 sync -Message "Daily progress: improved signal processing"
```

### Вечером (окончание работы):
```bash
# Полная синхронизация
.\sync.ps1 sync -Message "End of day: completed feature Y"
```

## 🎯 **Быстрые сценарии**

### Сценарий 1: Переключение между компьютерами
```bash
# На компьютере A (завершение работы)
git add .
git commit -m "PC-A: Work in progress on order execution"
git push origin main

# На компьютере B (начало работы)
git pull origin main
# Продолжаем работу...
```

### Сценарий 2: Синхронизация после выходных
```bash
# Проверяем что пропустили
python version_check.py

# Получаем все изменения
git pull origin main

# Проверяем что все работает
python enhanced_signal_processor.py --test
```

### Сценарий 3: Экстренная синхронизация
```bash
# Сохраняем все как есть
git add .
git commit -m "URGENT: Save current state"
git push origin main --force
```

## 🔧 **Инструменты проекта**

### version_check.py
```bash
python version_check.py          # Полный отчет
```
**Показывает:**
- Статус синхронизации
- Незакоммиченные файлы
- Последние коммиты
- Рекомендации по действиям

### sync.ps1 (PowerShell)
```powershell
.\sync.ps1 check                 # Проверка статуса
.\sync.ps1 pull                  # Получить изменения
.\sync.ps1 commit -Message "..."  # Закоммитить
.\sync.ps1 push                  # Отправить
.\sync.ps1 sync -Message "..."   # Полная синхронизация
```

### start_patriot.bat (улучшенный)
- Автоматически проверяет версию
- Предупреждает о несинхронизированных изменениях
- Позволяет продолжить или отменить запуск

## 🏷️ **Система тегов**

### Создание важных версий:
```bash
# Milestone версия
git tag -a v1.5.1 -m "Stage 1.5.1: Added multi-computer sync"
git push origin v1.5.1

# Просмотр версий
git tag -l
git show v1.5.1
```

## 📊 **Мониторинг состояния**

### Ежедневная проверка:
```bash
# Быстрый статус
git status --short

# Что изменилось за день
git log --since="1 day ago" --oneline

# Сравнение с remote
git diff origin/main --name-only
```

### Еженедельный аудит:
```bash
# История по авторам
git shortlog --summary --numbered --since="1 week ago"

# Активность по дням
git log --since="1 week ago" --pretty=format:"%cd %s" --date=short

# Статистика изменений
git diff --stat origin/main
```

## 🚨 **Частые проблемы**

### Проблема: "already up to date" но версии разные
```bash
# Решение:
git fetch origin
git reset --hard origin/main
# ОСТОРОЖНО: теряются локальные изменения!
```

### Проблема: Merge conflicts
```bash
# 1. Посмотреть конфликты
git status

# 2. Редактировать файлы (убрать <<<< ==== >>>>)
# 3. Завершить merge
git add .
git commit -m "Resolved merge conflicts"
```

### Проблема: Забыли закоммитить на другом компьютере
```bash
# На текущем компьютере:
git stash                    # Сохраняем текущие изменения
git pull origin main        # Получаем изменения
git stash pop               # Восстанавливаем свои изменения
# Решаем конфликты если есть
```

## 💡 **Best Practices**

### ✅ **Делайте:**
- Проверяйте версию перед началом работы
- Коммитьте часто с понятными сообщениями
- Отправляйте изменения в конце рабочего дня
- Используйте префиксы компьютеров в commit message

### ❌ **Не делайте:**
- Не редактируйте одни файлы одновременно на разных компьютерах
- Не используйте `git push --force` без крайней необходимости
- Не коммитьте .env файлы или логи
- Не оставляйте незакоммиченные изменения надолго

## 🎨 **Цветовые коды статуса**

- 🟢 **Зеленый**: Версия актуальна
- 🟡 **Желтый**: Требуется синхронизация
- 🔴 **Красный**: Конфликты или ошибки
- 🔵 **Синий**: Информационные сообщения

---

## 📞 **Если что-то пошло не так**

1. **Сохраните текущее состояние:**
   ```bash
   git add .
   git commit -m "EMERGENCY: Save before fixing sync issues"
   ```

2. **Создайте backup ветку:**
   ```bash
   git branch backup-$(date +%Y%m%d)
   git push origin backup-$(date +%Y%m%d)
   ```

3. **Восстановите из remote:**
   ```bash
   git fetch origin
   git reset --hard origin/main
   ```

4. **Проверьте что все работает:**
   ```bash
   python version_check.py
   python enhanced_signal_processor.py --test
   ```
