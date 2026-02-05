#!/usr/bin/env python3
"""
Тестирование функции handle_fines_modal
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_fines_data

def test_handle_fines_modal_logic():
    """Тестирование логики функции handle_fines_modal"""
    
    print("=== ТЕСТИРОВАНИЕ ЛОГИКИ ФУНКЦИИ HANDLE_FINES_MODAL ===\n")
    
    # Тестовые даты
    start_date = "2026-01-27"
    end_date = "2026-02-03"
    
    print(f"Тестовые даты: {start_date} - {end_date}")
    
    # Получаем данные штрафов
    fines_data = get_fines_data(start_date, end_date)
    
    print(f"\n1. ПРОВЕРКА ДАННЫХ:")
    print("-" * 50)
    summary_data = fines_data.get('summary_data', [])
    print(f"  Количество записей в summary_data: {len(summary_data)}")
    
    if summary_data:
        print(f"  Пример данных для индекса 0:")
        first_employee = summary_data[0]
        print(f"    Сотрудник: {first_employee.get('Сотрудник', 'N/A')}")
        print(f"    Количество штрафов: {first_employee.get('Количество_штрафов', 'N/A')}")
        print(f"    Сумма штрафов: {first_employee.get('Сумма_штрафов', 'N/A')}")
        print(f"    Средний штраф: {first_employee.get('Средний_штраф', 'N/A')}")
    
    print(f"\n2. ТЕСТИРОВАНИЕ СОРТИРОВКИ:")
    print("-" * 50)
    
    # Сортируем данные по количеству штрафов (как в оригинальной функции)
    sorted_summary_data = sorted(summary_data, key=lambda x: x.get('Количество_штрафов', 0), reverse=True)
    print(f"  После сортировки: {len(sorted_summary_data)} записей")
    
    # Проверим, что данные корректно сортируются
    for i, emp in enumerate(sorted_summary_data[:5]):  # Проверим первые 5
        print(f"    {i}. {emp.get('Сотрудник', 'N/A')} - {emp.get('Количество_штрафов', 0)} штрафов")
    
    print(f"\n3. АНАЛИЗ ПРОБЛЕМЫ:")
    print("-" * 50)
    print("  В оригинальной функции handle_fines_modal использовалась переменная fines_data")
    print("  из параметров функции, а не перезапрашивались данные через get_fines_data")
    print("  ")
    print("  Проблема может быть в том, что я изменил логику и теперь функция пытается")
    print("  получить данные дважды - сначала из параметра, потом снова запрашивает")
    print("  ")
    print("  Нужно вернуть оригинальную логику, но сохранить добавление поля 'Средний_штраф'")
    
    print(f"\n4. ПРОВЕРКА СТРУКТУРЫ ДАННЫХ:")
    print("-" * 50)
    
    # Проверим, что структура данных корректна
    if summary_data:
        for i, emp in enumerate(summary_data[:3]):
            print(f"  Сотрудник {i}: {emp}")
            expected_keys = ['Сотрудник', 'Количество_штрафов', 'Сумма_штрафов', 'Средний_штраф']
            missing_keys = [key for key in expected_keys if key not in emp]
            if missing_keys:
                print(f"    ERROR: Отсутствуют ключи: {missing_keys}")
            else:
                print(f"    SUCCESS: Все ключи присутствуют")


if __name__ == "__main__":
    test_handle_fines_modal_logic()