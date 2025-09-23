#!/usr/bin/env python3
"""
Migration Script - Переход на унифицированную систему синхронизации
================================================================

Скрипт для миграции с множественных компонентов синхронизации 
на единую унифицированную систему.

Заменяет:
- state_recovery.py -> unified_sync.py
- orders_synchronizer.py -> unified_sync.py (частично)
- sync_check.py -> unified_sync.py
- sync_monitor.py -> unified_sync.py

Author: HEDGER
Version: 1.0 - Migration to Unified System
"""

import os
import shutil
from pathlib import Path
from utils import logger


def migrate_to_unified_sync():
    """Миграция на унифицированную систему синхронизации"""
    
    print("🔄 ПЕРЕХОД НА УНИФИЦИРОВАННУЮ СИСТЕМУ СИНХРОНИЗАЦИИ")
    print("=" * 80)
    
    # Файлы для архивирования
    files_to_archive = [
        'state_recovery.py',
        'sync_check.py', 
        'sync_monitor.py',
        'state_synchronizer.py'
    ]
    
    # Создаем папку для архива
    archive_dir = Path('ARCHIVE/deprecated_sync_components')
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    archived_count = 0
    
    for filename in files_to_archive:
        file_path = Path(filename)
        if file_path.exists():
            archive_path = archive_dir / filename
            
            # Создаем резервную копию если файл уже существует в архиве
            if archive_path.exists():
                counter = 1
                while (archive_dir / f"{filename}.{counter}").exists():
                    counter += 1
                archive_path = archive_dir / f"{filename}.{counter}"
            
            try:
                shutil.move(str(file_path), str(archive_path))
                print(f"📦 {filename} -> ARCHIVE/deprecated_sync_components/{archive_path.name}")
                archived_count += 1
            except Exception as e:
                print(f"❌ Ошибка архивирования {filename}: {e}")
        else:
            print(f"⚠️ {filename} не найден - пропускаем")
    
    print(f"\n✅ Архивировано {archived_count} файлов")
    
    # Проверяем наличие unified_sync.py
    if Path('unified_sync.py').exists():
        print("✅ unified_sync.py уже существует")
    else:
        print("❌ unified_sync.py не найден!")
        print("   Убедитесь, что файл создан корректно")
        return False
    
    # Создаем алиасы для обратной совместимости
    create_compatibility_aliases()
    
    print("\n🎯 РЕКОМЕНДАЦИИ ПО ИСПОЛЬЗОВАНИЮ:")
    print("-" * 50)
    print("1. Вместо state_recovery.py используйте:")
    print("   python3 unified_sync.py --status")
    print("   python3 unified_sync.py --force")
    print("")
    print("2. Вместо sync_check.py используйте:")
    print("   python3 unified_sync.py --status")
    print("")
    print("3. Вместо sync_monitor.py используйте:")
    print("   python3 unified_sync.py --status")
    print("")
    print("4. В коде замените импорты:")
    print("   from state_recovery import ... -> from unified_sync import ...")
    print("   from orders_synchronizer import ... -> from unified_sync import ...")
    print("")
    print("✅ Миграция завершена успешно!")
    
    return True


def create_compatibility_aliases():
    """Создает алиасы для обратной совместимости"""
    
    aliases = {
        'state_recovery.py': '''#!/usr/bin/env python3
"""
DEPRECATED: Этот модуль заменен на unified_sync.py
Используйте: python3 unified_sync.py --status или --force
"""
import sys
print("⚠️ state_recovery.py устарел!")
print("✅ Используйте: python3 unified_sync.py --status")
sys.exit(1)
''',
        
        'sync_check.py': '''#!/usr/bin/env python3
"""
DEPRECATED: Этот модуль заменен на unified_sync.py
Используйте: python3 unified_sync.py --status
"""
import sys
print("⚠️ sync_check.py устарел!")
print("✅ Используйте: python3 unified_sync.py --status")
sys.exit(1)
''',
        
        'sync_monitor.py': '''#!/usr/bin/env python3
"""
DEPRECATED: Этот модуль заменен на unified_sync.py
Используйте: python3 unified_sync.py --status
"""
import sys
print("⚠️ sync_monitor.py устарел!")
print("✅ Используйте: python3 unified_sync.py --status")
sys.exit(1)
'''
    }
    
    for filename, content in aliases.items():
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"🔗 Создан алиас: {filename}")
        except Exception as e:
            print(f"❌ Ошибка создания алиаса {filename}: {e}")


def update_imports_in_files():
    """Обновляет импорты в основных файлах системы"""
    
    files_to_update = [
        'ticker_monitor.py',
        'order_executor.py', 
        'orders_watchdog.py'
    ]
    
    import_replacements = {
        'from state_recovery import': 'from unified_sync import',
        'from orders_synchronizer import': 'from unified_sync import',
        'from sync_check import': 'from unified_sync import',
        'from sync_monitor import': 'from unified_sync import',
        'state_recovery.': 'unified_sync.',
        'orders_sync.': 'unified_sync.',
        'StateRecoveryManager': 'UnifiedSynchronizer',
        'synchronize_before_startup': 'sync_before_startup'
    }
    
    print("\n🔄 Обновление импортов в файлах...")
    
    updated_files = 0
    
    for filename in files_to_update:
        file_path = Path(filename)
        if not file_path.exists():
            print(f"⚠️ {filename} не найден - пропускаем")
            continue
        
        try:
            # Читаем файл
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Применяем замены
            for old_import, new_import in import_replacements.items():
                if old_import in content:
                    content = content.replace(old_import, new_import)
                    print(f"   📝 {filename}: {old_import} -> {new_import}")
            
            # Сохраняем файл если были изменения
            if content != original_content:
                # Создаем резервную копию
                backup_path = file_path.with_suffix(f'{file_path.suffix}.backup')
                shutil.copy2(file_path, backup_path)
                
                # Сохраняем обновленный файл
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✅ {filename} обновлен (резервная копия: {backup_path.name})")
                updated_files += 1
            else:
                print(f"📄 {filename} не требует обновления")
                
        except Exception as e:
            print(f"❌ Ошибка обновления {filename}: {e}")
    
    print(f"\n✅ Обновлено {updated_files} файлов")


if __name__ == "__main__":
    """Запуск миграции"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--update-imports":
        update_imports_in_files()
    else:
        print("🚀 Миграция на унифицированную систему синхронизации")
        print("")
        
        user_input = input("Продолжить миграцию? (y/N): ")
        if user_input.lower() in ['y', 'yes', 'да', 'д']:
            if migrate_to_unified_sync():
                print("\n🔄 Обновить импорты в файлах? (рекомендуется)")
                user_input2 = input("Обновить импорты? (y/N): ")
                if user_input2.lower() in ['y', 'yes', 'да', 'д']:
                    update_imports_in_files()
                    
                print("\n🎉 Миграция завершена!")
                print("📋 Проверьте работу системы командой:")
                print("   python3 unified_sync.py --status")
            else:
                print("\n❌ Миграция прервана из-за ошибок")
        else:
            print("❌ Миграция отменена")
