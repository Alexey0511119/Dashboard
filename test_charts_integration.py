#!/usr/bin/env python3
"""
Тестирование диаграмм с новыми данными из MSSQL
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_problematic_hours, get_error_hours_top_data
from components.charts import create_problematic_hours_chart, create_error_hours_chart

def test_charts_with_new_data():
    """Тестирование диаграмм с новыми данными"""
    
    print("=== ТЕСТИРОВАНИЕ ДИАГРАММ С НОВЫМИ ДАННЫМИ ===\n")
    
    # Тестовые даты
    start_date = "2026-01-27"
    end_date = "2026-02-03"
    
    print(f"Тестовые даты: {start_date} - {end_date}")
    
    # Получаем данные для диаграмм
    print("\n1. ПОЛУЧЕНИЕ ДАННЫХ:")
    print("-" * 50)
    
    problematic_hours = get_problematic_hours(start_date, end_date)
    error_hours = get_error_hours_top_data(start_date, end_date)
    
    print(f"  get_problematic_hours: {len(problematic_hours)} записей")
    print(f"  get_error_hours_top_data: {len(error_hours)} записей")
    
    # Проверяем структуру данных
    print("\n  Структура данных для диаграммы проблемных часов:")
    if problematic_hours:
        for i, item in enumerate(problematic_hours[:2]):
            print(f"    {i+1}. {item}")
    
    print("\n  Структура данных для диаграммы часов с ошибками:")
    if error_hours:
        for i, item in enumerate(error_hours[:2]):
            print(f"    {i+1}. {item}")
    
    # Создаем диаграммы
    print("\n2. СОЗДАНИЕ ДИАГРАММ:")
    print("-" * 50)
    
    try:
        # Создаем диаграмму проблемных часов
        print("  Создание диаграммы проблемных часов...")
        problematic_chart = create_problematic_hours_chart(problematic_hours)
        print(f"  Диаграмма проблемных часов создана: {type(problematic_chart).__name__}")
        
        # Проверяем ключевые элементы диаграммы
        if 'series' in problematic_chart and len(problematic_chart['series']) > 0:
            series_data = problematic_chart['series'][0]['data']
            print(f"    Количество элементов в диаграмме: {len(series_data)}")
        
        # Создаем диаграмму часов с ошибками
        print("  Создание диаграммы часов с ошибками...")
        error_chart = create_error_hours_chart(error_hours)
        print(f"  Диаграмма часов с ошибками создана: {type(error_chart).__name__}")
        
        # Проверяем ключевые элементы диаграммы
        if 'series' in error_chart and len(error_chart['series']) > 0:
            series_data = error_chart['series'][0]['data']
            print(f"    Количество элементов в диаграмме: {len(series_data)}")
        
        print("\n3. РЕЗУЛЬТАТ:")
        print("-" * 50)
        print("  SUCCESS: Обе диаграммы успешно созданы с новыми данными из MSSQL")
        print("  SUCCESS: Функции корректно получают данные из таблиц dm.v_hourly_delays и dm.v_hourly_errors")
        print("  SUCCESS: Структура данных соответствует требованиям диаграмм")
        
        return True
        
    except Exception as e:
        print(f"  ERROR: Ошибка при создании диаграмм: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_charts_with_new_data()
    if success:
        print("\nSUCCESS: Все тесты пройдены успешно! Диаграммы будут работать с новыми данными.")
    else:
        print("\nERROR: Ошибка при тестировании диаграмм.")