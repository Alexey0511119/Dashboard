#!/usr/bin/env python3
"""
Тестирование обновленных функций get_problematic_hours и get_error_hours_top_data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_problematic_hours, get_error_hours_top_data

def test_updated_functions():
    """Тестирование обновленных функций"""
    
    print("=== ТЕСТИРОВАНИЕ ОБНОВЛЕННЫХ ФУНКЦИЙ ===\n")
    
    # Тестовые периоды
    test_periods = [
        ("2026-01-27", "2026-02-03", "Текущий период"),
        ("2026-01-01", "2026-01-31", "Январь 2026")
    ]
    
    for start_date, end_date, period_name in test_periods:
        print(f"PERIOD: {period_name} ({start_date} - {end_date})")
        
        # Тестирование get_problematic_hours
        print("\n1. ТЕСТИРОВАНИЕ get_problematic_hours:")
        print("-" * 50)
        
        problematic_hours = get_problematic_hours(start_date, end_date)
        print(f"  Всего записей: {len(problematic_hours)}")
        
        if problematic_hours:
            print("  Топ-5 проблемных часов:")
            for i, item in enumerate(problematic_hours, 1):
                print(f"    {i}. {item['hour']}:00 - {item['delay_percentage']}% просрочек ({item['delayed_orders']}/{item['total_orders']} заказов)")
        else:
            print("  ❌ Нет данных")
        
        # Тестирование get_error_hours_top_data
        print("\n2. ТЕСТИРОВАНИЕ get_error_hours_top_data:")
        print("-" * 50)
        
        error_hours = get_error_hours_top_data(start_date, end_date)
        print(f"  Всего записей: {len(error_hours)}")
        
        if error_hours:
            print("  Топ-5 часов с ошибками:")
            for i, item in enumerate(error_hours, 1):
                print(f"    {i}. {item['hour']}:00 - {item['error_percentage']}% ошибок ({item['error_orders_count']}/{item['total_orders_in_hour']} заказов)")
        else:
            print("  ❌ Нет данных")
        
        print("\n" + "="*80 + "\n")
    
    # Проверка структуры данных для диаграмм
    print("3. СТРУКТУРА ДАННЫХ ДЛЯ ДИАГРАММ:")
    print("-" * 50)
    
    # Пример данных для диаграммы проблемных часов
    print("  Пример данных для диаграммы проблемных часов:")
    if problematic_hours:
        for item in problematic_hours[:1]:  # Показываем структуру одной записи
            print(f"    Час: {item['hour']}")
            print(f"    Всего заказов: {item['total_orders']}")
            print(f"    Просрочено: {item['delayed_orders']}")
            print(f"    Процент просрочек: {item['delay_percentage']}")
    
    print("\n  Пример данных для диаграммы часов с ошибками:")
    if error_hours:
        for item in error_hours[:1]:  # Показываем структуру одной записи
            print(f"    Час: {item['hour']}")
            print(f"    Всего заказов: {item['total_orders_in_hour']}")
            print(f"    С ошибками: {item['error_orders_count']}")
            print(f"    Процент ошибок: {item['error_percentage']}")
            print(f"    Типы ошибок: {item['error_types']}")


if __name__ == "__main__":
    test_updated_functions()