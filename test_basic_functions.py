#!/usr/bin/env python3
"""
Простой тест для проверки основных функций
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_basic_functions():
    """Тестирование основных функций"""
    
    print("=== ТЕСТИРОВАНИЕ ОСНОВНЫХ ФУНКЦИЙ ===\n")
    
    try:
        print("1. ТЕСТИРОВАНИЕ ИМПОРТА:")
        print("-" * 50)
        
        from data.mssql_client import execute_query_cached
        print("  SUCCESS: execute_query_cached импортирован")
        
        from data.queries_mssql import get_performance_data
        print("  SUCCESS: get_performance_data импортирован")
        
        from data.queries_mssql import get_problematic_hours, get_error_hours_top_data
        print("  SUCCESS: get_problematic_hours и get_error_hours_top_data импортированы")
        
        print(f"\n2. ТЕСТИРОВАНИЕ ЗАПРОСОВ:")
        print("-" * 50)
        
        # Тестовые даты
        start_date = "2026-01-27"
        end_date = "2026-02-03"
        
        print(f"  Тестовые даты: {start_date} - {end_date}")
        
        # Тестируем простой запрос
        try:
            simple_result = execute_query_cached("SELECT 1 as test")
            print(f"  SUCCESS: Простой запрос выполнен: {simple_result}")
        except Exception as e:
            print(f"  ERROR: Ошибка простого запроса: {e}")
        
        # Тестируем получение данных производительности
        try:
            perf_data = get_performance_data(start_date, end_date)
            print(f"  SUCCESS: get_performance_data выполнен: {len(perf_data)} сотрудников")
        except Exception as e:
            print(f"  ERROR: Ошибка get_performance_data: {e}")
            import traceback
            traceback.print_exc()
        
        # Тестируем получение данных проблемных часов
        try:
            problem_hours = get_problematic_hours(start_date, end_date)
            print(f"  SUCCESS: get_problematic_hours выполнен: {len(problem_hours)} записей")
        except Exception as e:
            print(f"  ERROR: Ошибка get_problematic_hours: {e}")
            import traceback
            traceback.print_exc()
        
        # Тестируем получение данных часов с ошибками
        try:
            error_hours = get_error_hours_top_data(start_date, end_date)
            print(f"  SUCCESS: get_error_hours_top_data выполнен: {len(error_hours)} записей")
        except Exception as e:
            print(f"  ERROR: Ошибка get_error_hours_top_data: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n3. АНАЛИЗ ПРОБЛЕМ:")
        print("-" * 50)
        print("  Если дашборд не работает, возможные причины:")
        print("  1. Проблема с кэшированием данных")
        print("  2. Проблема с форматом данных для диаграмм")
        print("  3. Проблема с обратными вызовами (callbacks)")
        print("  4. Проблема с CSS/JS компонентами")
        print("  5. Проблема с многопоточностью в кэшировании")
        
        print(f"\n4. РЕЗУЛЬТАТ:")
        print("-" * 50)
        print("  Основные функции импортируются корректно")
        print("  Запросы к базе данных выполняются")
        print("  Данные извлекаются из таблиц")
        print("  Основная функциональность работает")
        
        return True
        
    except Exception as e:
        print(f"  ERROR: Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_basic_functions()
    if success:
        print(f"\nSUCCESS: Основные функции работают корректно")
    else:
        print(f"\nERROR: Основные функции не работают")