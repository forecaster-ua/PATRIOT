#!/usr/bin/env python3
"""
Утилита для управления сжатием файлов анализа
"""

import gzip
import os
from pathlib import Path
from datetime import datetime

def compress_history_files():
    """Сжимает все текстовые файлы в HISTORY/"""
    history_dir = Path('HISTORY')
    
    if not history_dir.exists():
        print("❌ Папка HISTORY не найдена")
        return
    
    txt_files = list(history_dir.glob("*.txt"))
    
    if not txt_files:
        print("ℹ️ Файлы .txt для сжатия не найдены")
        return
    
    total_original = 0
    total_compressed = 0
    compressed_count = 0
    
    print(f"🗜️ Найдено {len(txt_files)} файлов для сжатия...")
    
    for txt_file in txt_files:
        try:
            # Читаем содержимое
            content = txt_file.read_text(encoding='utf-8')
            original_size = len(content.encode('utf-8'))
            
            # Сжимаем
            compressed_path = txt_file.with_suffix(txt_file.suffix + '.gz')
            with gzip.open(compressed_path, 'wt', encoding='utf-8') as f:
                f.write(content)
            
            compressed_size = compressed_path.stat().st_size
            compression_ratio = original_size / compressed_size
            
            # Удаляем оригинал
            txt_file.unlink()
            
            total_original += original_size
            total_compressed += compressed_size
            compressed_count += 1
            
            print(f"✅ {txt_file.name} -> {compressed_path.name} ({compression_ratio:.1f}x)")
            
        except Exception as e:
            print(f"❌ Ошибка при сжатии {txt_file.name}: {e}")
    
    if compressed_count > 0:
        overall_ratio = total_original / total_compressed
        savings_mb = (total_original - total_compressed) / 1024 / 1024
        
        print(f"\n📊 ИТОГИ СЖАТИЯ:")
        print(f"   Файлов сжато: {compressed_count}")
        print(f"   Исходный размер: {total_original:,}б")
        print(f"   Сжатый размер: {total_compressed:,}б")
        print(f"   Коэффициент сжатия: {overall_ratio:.1f}x")
        print(f"   Экономия: {savings_mb:.2f} МБ")

def decompress_history_files():
    """Распаковывает все .gz файлы в HISTORY/"""
    history_dir = Path('HISTORY')
    
    if not history_dir.exists():
        print("❌ Папка HISTORY не найдена")
        return
    
    gz_files = list(history_dir.glob("*.gz"))
    
    if not gz_files:
        print("ℹ️ Файлы .gz для распаковки не найдены")
        return
    
    decompressed_count = 0
    
    print(f"📂 Найдено {len(gz_files)} файлов для распаковки...")
    
    for gz_file in gz_files:
        try:
            # Читаем сжатое содержимое
            with gzip.open(gz_file, 'rt', encoding='utf-8') as f:
                content = f.read()
            
            # Записываем распакованный файл
            txt_file = gz_file.with_suffix('')  # убираем .gz
            txt_file.write_text(content, encoding='utf-8')
            
            # Удаляем сжатый файл
            gz_file.unlink()
            
            decompressed_count += 1
            print(f"✅ {gz_file.name} -> {txt_file.name}")
            
        except Exception as e:
            print(f"❌ Ошибка при распаковке {gz_file.name}: {e}")
    
    print(f"\n📊 Распаковано файлов: {decompressed_count}")

def show_history_stats():
    """Показывает статистику файлов в HISTORY/"""
    history_dir = Path('HISTORY')
    
    if not history_dir.exists():
        print("❌ Папка HISTORY не найдена")
        return
    
    txt_files = list(history_dir.glob("*.txt"))
    gz_files = list(history_dir.glob("*.gz"))
    
    txt_size = sum(f.stat().st_size for f in txt_files)
    gz_size = sum(f.stat().st_size for f in gz_files)
    total_size = txt_size + gz_size
    
    print(f"📁 СТАТИСТИКА ПАПКИ HISTORY:")
    print(f"   📄 .txt файлов: {len(txt_files)} ({txt_size:,}б)")
    print(f"   🗜️ .gz файлов: {len(gz_files)} ({gz_size:,}б)")
    print(f"   📊 Общий размер: {total_size:,}б ({total_size/1024/1024:.2f} МБ)")
    
    if txt_files and gz_files:
        print(f"   ⚠️ Смешанные форматы - рекомендуется привести к единому")

def enable_compression():
    """Включает автоматическое сжатие в коде"""
    filepath = Path('get_hedge_entry_generator.py')
    
    if not filepath.exists():
        print("❌ Файл get_hedge_entry_generator.py не найден")
        return
    
    content = filepath.read_text(encoding='utf-8')
    
    # Ищем закомментированную строку сжатия
    if '# self._compress_file(filepath)' in content:
        # Заменяем на активную
        new_content = content.replace(
            '# self._compress_file(filepath)',
            'self._compress_file(filepath)'
        )
        
        filepath.write_text(new_content, encoding='utf-8')
        print("✅ Автоматическое сжатие ВКЛЮЧЕНО")
        print("   Новые файлы будут автоматически сжиматься")
    else:
        print("ℹ️ Автоматическое сжатие уже включено или строка не найдена")

def disable_compression():
    """Отключает автоматическое сжатие в коде"""
    filepath = Path('get_hedge_entry_generator.py')
    
    if not filepath.exists():
        print("❌ Файл get_hedge_entry_generator.py не найден")
        return
    
    content = filepath.read_text(encoding='utf-8')
    
    # Ищем активную строку сжатия
    if 'self._compress_file(filepath)' in content and '# self._compress_file(filepath)' not in content:
        # Комментируем
        new_content = content.replace(
            'self._compress_file(filepath)',
            '# self._compress_file(filepath)'
        )
        
        filepath.write_text(new_content, encoding='utf-8')
        print("✅ Автоматическое сжатие ОТКЛЮЧЕНО") 
        print("   Новые файлы будут сохраняться в текстовом формате")
    else:
        print("ℹ️ Автоматическое сжатие уже отключено")

def main():
    """Главное меню"""
    while True:
        print("\n🗜️ УПРАВЛЕНИЕ СЖАТИЕМ ФАЙЛОВ АНАЛИЗА")
        print("="*50)
        print("1. 📊 Показать статистику")
        print("2. 🗜️ Сжать все .txt файлы") 
        print("3. 📂 Распаковать все .gz файлы")
        print("4. ✅ Включить автосжатие")
        print("5. ❌ Отключить автосжатие")
        print("0. 🚪 Выход")
        
        choice = input("\n👉 Выберите действие: ").strip()
        
        if choice == '1':
            show_history_stats()
        elif choice == '2':
            compress_history_files()
        elif choice == '3':
            decompress_history_files()
        elif choice == '4':
            enable_compression()
        elif choice == '5':
            disable_compression()
        elif choice == '0':
            print("👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор")

if __name__ == "__main__":
    main()