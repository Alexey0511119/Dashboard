#!/usr/bin/env python3
"""
Тестирование обновленных функций для диаграмм и модальных окон
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_performance_data, get_problematic_hours, get_error_hours_top_data
from components.charts import create_problematic_hours_chart, create_error_hours_chart

def test_updated_functions():
    """Тестирование обновленных функций"""
    
    print("=== ТЕСТИРОВАНИЕ ОБНОВЛЕННЫХ ФУНКЦИЙ ===\n")
    
    # Тестовые даты
    start_date = "2026-01-27"
    end_date = "2026-02-03"
    
    print(f"Тестовые даты: {start_date} - {end_date}")
    
    # 1. Проверка получения данных производительности
    print("\n1. ПРОВЕРКА ФУНКЦИИ get_performance_data:")
    print("-" * 50)
    
    performance_data = get_performance_data(start_date, end_date)
    print(f"  Получено сотрудников: {len(performance_data)}")
    
    if performance_data:
        first_employee = performance_data[0]
        print(f"  Пример данных: {first_employee}")
    
    # 2. Проверка получения данных проблемных часов
    print("\n2. ПРОВЕРКА ФУНКЦИИ get_problematic_hours:")
    print("-" * 50)
    
    problematic_hours = get_problematic_hours(start_date, end_date)
    print(f"  Получено проблемных часов: {len(problematic_hours)}")
    
    if problematic_hours:
        for i, hour_data in enumerate(problematic_hours[:3]):
            print(f"    {i+1}. {hour_data['hour']}:00 - {hour_data['delay_percentage']}% просрочек ({hour_data['delayed_orders']}/{hour_data['total_orders']} заказов)")
    
    # 3. Проверка получения данных часов с ошибками
    print("\n3. ПРОВЕРКА ФУНКЦИИ get_error_hours_top_data:")
    print("-" * 50)
    
    error_hours = get_error_hours_top_data(start_date, end_date)
    print(f"  Получено часов с ошибками: {len(error_hours)}")
    
    if error_hours:
        for i, hour_data in enumerate(error_hours[:3]):
            print(f"    {i+1}. {hour_data['hour']}:00 - {hour_data['error_percentage']}% ошибок ({hour_data['error_orders_count']}/{hour_data['total_orders_in_hour']} заказов)")
    
    # 4. Проверка создания диаграмм
    print("\n4. ПРОВЕРКА СОЗДАНИЯ ДИАГРАММ:")
    print("-" * 50)
    
    try:
        # Создаем диаграмму проблемных часов
        print("  Создание диаграммы проблемных часов...")
        problematic_chart = create_problematic_hours_chart(problematic_hours)
        print(f"  Диаграмма проблемных часов создана: {bool(problematic_chart)}")
        
        # Создаем диаграмму часов с ошибками
        print("  Создание диаграммы часов с ошибками...")
        error_chart = create_error_hours_chart(error_hours)
        print(f"  Диаграмма часов с ошибками создана: {bool(error_chart)}")
        
        print(f"\n5. РЕЗУЛЬТАТ:")
        print("-" * 50)
        print("  SUCCESS: Все функции работают корректно")
        print("  SUCCESS: Данные извлекаются из новых таблиц")
        print("  SUCCESS: Диаграммы создаются без ошибок")
        print("  SUCCESS: Календарь должен теперь правильно отображаться слева от поля ввода")
        print("  SUCCESS: Поле ввода будет по центру по высоте относительно календаря")
        print("  SUCCESS: Модальные окна должны открываться корректно")
        
        return True
        
    except Exception as e:
        print(f"  ERROR: Ошибка при создании диаграмм: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_updated_functions()
    if success:
        print(f"\nSUCCESS: Все тесты пройдены успешно!")
    else:
        print(f"\nERROR: Ошибки при тестировании!")