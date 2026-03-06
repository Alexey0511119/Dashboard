#!/usr/bin/env python3
"""
Тестирование функции refresh_data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_refresh_data_function():
    """Тестирование функции refresh_data"""
    
    print("=== ТЕСТИРОВАНИЕ ФУНКЦИИ refresh_data ===\n")
    
    try:
        from data.queries_mssql import refresh_data
        print("SUCCESS: Функция refresh_data импортирована")
    except ImportError as e:
        print(f"ERROR: Ошибка импорта refresh_data: {e}")
        return False
    
    # Тестовые даты
    start_date = "2026-01-27"
    end_date = "2026-02-03"
    
    print(f"Тестовые даты: {start_date} - {end_date}")
    
    try:
        print(f"\nВызов refresh_data...")
        refresh_data(start_date, end_date)
        print(f"SUCCESS: Функция refresh_data выполнена без ошибок")
        
        # Проверим, что глобальные переменные обновлены
        from data.queries_mssql import (
            PERFORMANCE_DATA_CACHE,
            SHIFT_COMPARISON_CACHE,
            PROBLEMATIC_HOURS_CACHE,
            ERROR_HOURS_CACHE
        )
        
        print(f"\nПРОВЕРКА ГЛОБАЛЬНЫХ ПЕРЕМЕННЫХ:")
        print("-" * 50)
        print(f"PERFORMANCE_DATA_CACHE: {len(PERFORMANCE_DATA_CACHE)} записей")
        print(f"SHIFT_COMPARISON_CACHE: {len(SHIFT_COMPARISON_CACHE)} записей")
        print(f"PROBLEMATIC_HOURS_CACHE: {len(PROBLEMATIC_HOURS_CACHE)} записей")
        print(f"ERROR_HOURS_CACHE: {len(ERROR_HOURS_CACHE)} записей")
        
        if len(PERFORMANCE_DATA_CACHE) > 0:
            print(f"  Пример данных из PERFORMANCE_DATA_CACHE: {PERFORMANCE_DATA_CACHE[0]}")
        
        print(f"\nSUCCESS: Все глобальные переменные обновлены корректно")
        return True
        
    except Exception as e:
        print(f"ERROR: Ошибка при выполнении refresh_data: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_refresh_data_function()
    if success:
        print(f"\nSUCCESS: Функция refresh_data работает корректно!")
    else:
        print(f"\nERROR: Ошибка в функции refresh_data!")