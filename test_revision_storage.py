#!/usr/bin/env python3
"""
Тестирование функций get_revision_stats и get_storage_cells_stats
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_revision_and_storage_stats():
    """Тестирование функций get_revision_stats и get_storage_cells_stats"""
    
    print("=== ТЕСТИРОВАНИЕ ФУНКЦИЙ GET_REVISION_STATS И GET_STORAGE_CELLS_STATS ===\n")
    
    try:
        from data.queries_mssql import get_revision_stats, get_storage_cells_stats
        print("SUCCESS: Функции импортированы")
    except ImportError as e:
        print(f"ERROR: Ошибка импорта: {e}")
        return False
    
    print("\n1. ТЕСТИРОВАНИЕ get_revision_stats:")
    print("-" * 50)
    
    try:
        revision_stats = get_revision_stats()
        print(f"  SUCCESS: get_revision_stats выполнена")
        print(f"  Результат: {revision_stats}")
        
        if revision_stats and revision_stats.get('total_revisions', 0) > 0:
            print(f"  SUCCESS: Данные по ревизиям получены корректно")
        else:
            print(f"  WARNING: Данные по ревизиям пустые или нулевые")
        
    except Exception as e:
        print(f"  ERROR: Ошибка get_revision_stats: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n2. ТЕСТИРОВАНИЕ get_storage_cells_stats:")
    print("-" * 50)
    
    try:
        storage_stats = get_storage_cells_stats()
        print(f"  SUCCESS: get_storage_cells_stats выполнена")
        print(f"  Результат: {storage_stats}")
        
        if storage_stats and storage_stats.get('total_cells', 0) > 0:
            print(f"  ✅ Данные по ячейкам получены корректно")
            print(f"  Занято: {storage_stats.get('occupied_cells', 0)}, Свободно: {storage_stats.get('free_cells', 0)}")
            print(f"  Процент занятости: {storage_stats.get('occupied_percent', 0)}%")
        else:
            print(f"  ⚠️  Данные по ячейкам пустые или нулевые")
        
    except Exception as e:
        print(f"  ERROR: Ошибка get_storage_cells_stats: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n3. АНАЛИЗ ПРОБЛЕМ:")
    print("-" * 50)
    print("  Возможные причины проблем:")
    print("  1. Проблема с подключением к базе данных (10.7.0.48)")
    print("  2. Проблема с кэшированием данных")
    print("  3. Проблема с самими представлениями в БД")
    print("  4. Проблема с правами доступа к данным")
    
    print("\n4. РЕЗУЛЬТАТ:")
    print("-" * 50)
    if revision_stats and storage_stats:
        print("  SUCCESS: Обе функции работают корректно")
        print("  SUCCESS: Данные извлекаются из базы данных")
        return True
    else:
        print("  ERROR: Одна или обе функции не работают")
        return False


if __name__ == "__main__":
    success = test_revision_and_storage_stats()
    if success:
        print(f"\nSUCCESS: Функции работают корректно!")
    else:
        print(f"\nERROR: Проблемы с функциями!")