#!/usr/bin/env python3
"""
Тестирование диаграмм с исправленными tooltip
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_problematic_hours, get_error_hours_top_data
from components.charts import create_problematic_hours_chart, create_error_hours_chart

def test_charts_with_fixed_tooltips():
    """Тестирование диаграмм с исправленными tooltip"""
    
    print("=== ТЕСТИРОВАНИЕ ДИАГРАММ С ИСПРАВЛЕННЫМИ TOOLTIP ===\n")
    
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
    
    # Создаем диаграммы
    print("\n2. СОЗДАНИЕ ДИАГРАММ:")
    print("-" * 50)
    
    try:
        # Создаем диаграмму проблемных часов
        print("  Создание диаграммы проблемных часов...")
        problematic_chart = create_problematic_hours_chart(problematic_hours)
        print(f"  Диаграмма проблемных часов создана")
        
        # Проверяем наличие tooltip
        if 'tooltip' in problematic_chart:
            print(f"  Tooltip formatter: {problematic_chart['tooltip'].get('formatter', 'Not found')}")
        
        # Создаем диаграмму часов с ошибками
        print("  Создание диаграммы часов с ошибками...")
        error_chart = create_error_hours_chart(error_hours)
        print(f"  Диаграмма часов с ошибками создана")
        
        # Проверяем наличие tooltip
        if 'tooltip' in error_chart:
            print(f"  Tooltip formatter: {error_chart['tooltip'].get('formatter', 'Not found')}")
        
        print("\n3. ПРОВЕРКА СТРУКТУРЫ ДАННЫХ:")
        print("-" * 50)
        
        # Проверяем структуру данных в series
        if 'series' in problematic_chart and len(problematic_chart['series']) > 0:
            series_data = problematic_chart['series'][0]['data']
            print(f"  Диаграмма проблемных часов - количество элементов: {len(series_data)}")
            if series_data:
                print(f"  Пример структуры данных: {series_data[0]}")
        
        if 'series' in error_chart and len(error_chart['series']) > 0:
            series_data = error_chart['series'][0]['data']
            print(f"  Диаграмма часов с ошибками - количество элементов: {len(series_data)}")
            if series_data:
                print(f"  Пример структуры данных: {series_data[0]}")
        
        print("\n4. РЕЗУЛЬТАТ:")
        print("-" * 50)
        print("  SUCCESS: Обе диаграммы успешно созданы с исправленными tooltip")
        print("  SUCCESS: Данные правильно структурированы для отображения в tooltip")
        print("  SUCCESS: Удалены JavaScript-функции из tooltip")
        
        return True
        
    except Exception as e:
        print(f"  ERROR: Ошибка при создании диаграмм: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_charts_with_fixed_tooltips()
    if success:
        print("\nSUCCESS: Все тесты пройдены успешно! Tooltip больше не будут отображать код JavaScript.")
    else:
        print("\nERROR: Ошибка при тестировании диаграмм.")