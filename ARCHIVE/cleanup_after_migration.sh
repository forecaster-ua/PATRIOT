#!/bin/bash
# Скрипт очистки проекта после миграции на order_ID и жизненный цикл

echo "🧹 Начинаем очистку проекта после миграции..."

# Создаем папку для финального архива
mkdir -p FINAL_CLEANUP_$(date +%Y%m%d_%H%M%S)

# 1. Архивируем отчеты о миграции
echo "📦 Архивируем отчеты о миграции..."
mv CRITICAL_MIGRATION_ISSUES_REPORT.md FINAL_CLEANUP_*/
mv INTEGRATION_SUCCESS_REPORT.md FINAL_CLEANUP_*/
mv MIGRATION_CHECKLIST.md FINAL_CLEANUP_*/
mv ORDER_EXECUTION_ANALYSIS_REPORT.md FINAL_CLEANUP_*/
mv ORDERS_STUCK_CRITICAL_REPORT.md FINAL_CLEANUP_*/

# 2. Удаляем скрипты миграции
echo "🗑️ Удаляем скрипты миграции..."
rm -f migrate_sync.py
rm -f migrate_to_unified.sh  
rm -f stop_system_for_migration.sh
rm -f check_migration_readiness.py

# 3. Удаляем старые sync компоненты
echo "🔄 Удаляем устаревшие sync компоненты..."
rm -f order_sync_service_backup.py
rm -f order_sync_service_main.py
rm -f orders_synchronizer.py
rm -f state_synchronizer.py
rm -f sync_monitor.py
rm -f sync_check.py
rm -f sync.ps1

# 4. Удаляем устаревшие утилиты
echo "🛠️ Удаляем устаревшие утилиты..."
rm -f orders_cleaner.py
rm -f production_readiness_check.py
rm -f production_safety.py
rm -f emergency_stop.py
rm -f state_recovery.py

# 5. Удаляем временные файлы
echo "🧹 Удаляем временные файлы..."
rm -f orders_watchdog_state_backup.json
rm -f sync_log.json
# rm -f tickers_full_copy.txt
rm -f watchdog_cleaner.sh
rm -f version_check.py

# 6. Удаляем backup папки (после подтверждения)
echo "⚠️ ВНИМАНИЕ: Backup папки НЕ удалены автоматически"
echo "Если система работает стабильно, можете удалить:"
echo "  - BACKUP_20250726_212550/"
echo "  - PRE_MIGRATION_BACKUP_20250726_212212/"

# 7. Показываем что осталось важного
echo ""
echo "✅ Очистка завершена! Активные компоненты:"
echo "📊 Основные модули:"
echo "  - orders_watchdog.py (новая версия с lifecycle)"
echo "  - ticker_monitor.py"
echo "  - order_executor.py"
echo "  - unified_sync.py"
echo "  - signal_analyzer.py"
echo ""
echo "🎛️ Управление:"
echo "  - watchdog.sh"
echo "  - start_patriot.sh"
echo "  - restart_patriot.sh"
echo ""
echo "📱 Уведомления:"
echo "  - telegram_bot.py"
echo "  - telegram_balance_bot.py"
echo ""
echo "🗂️ Архивировано в: FINAL_CLEANUP_*/"

# 8. Полностью удаляем ARCHIVE (после подтверждения)
echo ""
read -p "Удалить папку ARCHIVE полностью? [y/N]: " confirm
if [[ $confirm == [yY] ]]; then
    rm -rf ARCHIVE/
    echo "✅ Папка ARCHIVE удалена"
else
    echo "ℹ️ Папка ARCHIVE сохранена"
fi

echo ""
echo "🎉 Проект очищен и готов к production!"
