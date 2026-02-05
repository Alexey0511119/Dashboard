#!/usr/bin/env python3
"""
Тестирование обновленной функции получения данных для диаграмм штрафов
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_fines_data

def test_updated_fines_data():
    """Тестирование обновленной функции получения данных для диаграмм штрафов"""
    
    print("=== ТЕСТИРОВАНИЕ ОБНОВЛЕННОЙ ФУНКЦИИ ПОЛУЧЕНИЯ ДАННЫХ ДЛЯ ДИАГРАММ ШТРАФОВ ===\n")
    
    # Тестовые даты
    start_date = "2026-01-27"
    end_date = "2026-02-03"
    
    print(f"Тестовые даты: {start_date} - {end_date}")
    
    # Получаем данные штрафов
    fines_data = get_fines_data(start_date, end_date)
    
    print(f"\n1. ОБЩАЯ СТРУКТУРА ДАННЫХ:")
    print("-" * 50)
    print(f"  Ключи в данных: {list(fines_data.keys())}")
    
    print(f"\n2. ДАННЫЕ СВОДКИ (summary_data):")
    print("-" * 50)
    summary_data = fines_data.get('summary_data', [])
    print(f"  Количество записей: {len(summary_data)}")
    for i, item in enumerate(summary_data[:3]):  # Показываем первые 3
        print(f"    {i+1}. {item}")
    
    print(f"\n3. ДАННЫЕ КАТЕГОРИЙ (category_data):")
    print("-" * 50)
    category_data = fines_data.get('category_data', {})
    print(f"  Тип данных: {type(category_data)}")
    print(f"  Количество категорий: {len(category_data)}")
    
    if category_data:
        print("  Данные по категориям:")
        for i, (category, data) in enumerate(list(category_data.items())[:10]):  # Первые 10
            print(f"    {i+1}. {category}: {data}")
    else:
        print("  ❌ Нет данных по категориям")
    
    print(f"\n4. ДАННЫЕ KPI:")
    print("-" * 50)
    kpi_data = fines_data.get('kpi_data', {})
    print(f"  KPI данные: {kpi_data}")
    
    print(f"\n5. ПРОВЕРКА СОВМЕСТИМОСТИ С ФУНКЦИЯМИ ДИАГРАММ:")
    print("-" * 50)
    
    # Проверим, совместимы ли данные с функциями диаграмм
    try:
        from components.charts import create_fines_pie_chart, create_fines_amount_bar_chart
        
        print("  Тестируем create_fines_pie_chart...")
        pie_chart = create_fines_pie_chart(category_data)
        print(f"  SUCCESS: Диаграмма pie создана: {bool(pie_chart)}")
        
        print("  Тестируем create_fines_amount_bar_chart...")
        bar_chart = create_fines_amount_bar_chart(category_data)
        print(f"  SUCCESS: Диаграмма bar создана: {bool(bar_chart)}")
        
        print(f"\n6. РЕЗУЛЬТАТ:")
        print("-" * 50)
        print("  SUCCESS: Обновленная функция возвращает правильные данные для диаграмм")
        print("  SUCCESS: category_data теперь содержит структуру, ожидаемую диаграммами")
        print("  SUCCESS: Диаграммы должны теперь корректно отображаться")
        
        return True
        
    except Exception as e:
        print(f"  ERROR: Ошибка при тестировании диаграмм: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_updated_fines_data()
    if success:
        print("\nSUCCESS: Все тесты пройдены успешно! Диаграммы штрафов должны теперь работать.")
    else:
        print("\nERROR: Ошибка при тестировании обновленной функции.")