#!/usr/bin/env python3
"""
Тестирование данных для диаграмм штрафов
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_fines_data

def test_fines_data():
    """Тестирование данных для диаграмм штрафов"""
    
    print("=== ТЕСТИРОВАНИЕ ДАННЫХ ДЛЯ ДИАГРАММ ШТРАФОВ ===\n")
    
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
    print(f"  Значение: {category_data}")
    
    print(f"\n4. ДАННЫЕ KPI:")
    print("-" * 50)
    kpi_data = fines_data.get('kpi_data', {})
    print(f"  KPI данные: {kpi_data}")
    
    print(f"\n5. АНАЛИЗ ПРОБЛЕМЫ:")
    print("-" * 50)
    
    # Проверяем, что функции диаграмм ожидают
    print("  Функции create_fines_pie_chart и create_fines_amount_bar_chart ожидают:")
    print("  - category_data в формате словаря: {")
    print("      'категория1': {'count': число, 'total_amount': сумма},")
    print("      'категория2': {'count': число, 'total_amount': сумма},")
    print("    }")
    print(f"  ")
    print(f"  Но получают: {category_data} (тип: {type(category_data)})")
    
    if not category_data:
        print("  ERROR: category_data пустой, поэтому диаграммы показывают 'Ошибка загрузки'")
    
    # Проверим, есть ли данные о категориях штрафов в базе
    print(f"\n6. ПРОВЕРКА НАЛИЧИЯ ДАННЫХ О КАТЕГОРИЯХ В БАЗЕ:")
    print("-" * 50)
    
    from data.mssql_client import execute_query_cached
    
    # Проверим, есть ли колонка с категориями в v_penalty_summary
    check_columns_query = """
    SELECT COLUMN_NAME, DATA_TYPE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'dm' AND TABLE_NAME = 'v_penalty_summary'
    """
    
    columns_result = execute_query_cached(check_columns_query)
    print("  Колонки в v_penalty_summary:")
    for col in columns_result:
        print(f"    - {col[0]} ({col[1]})")
    
    # Проверим, есть ли данные о категориях
    check_categories_query = """
    SELECT DISTINCT fine_category
    FROM dm.v_penalty_summary
    WHERE fine_category IS NOT NULL AND fine_category != ''
    """
    
    categories_result = execute_query_cached(check_categories_query)
    if categories_result:
        print(f"  Найдено категорий штрафов: {len(categories_result)}")
        for i, cat in enumerate(categories_result[:10]):  # Первые 10
            print(f"    {i+1}. {cat[0]}")
    else:
        print("  ❌ Не найдено категорий штрафов в базе")
        print("  Возможно, колонка fine_category не существует или пуста")


if __name__ == "__main__":
    test_fines_data()