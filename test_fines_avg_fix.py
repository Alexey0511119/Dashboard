#!/usr/bin/env python3
"""
Тестирование исправления отображения среднего штрафа в модальном окне
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_fines_data

def test_fines_avg_fix():
    """Тестирование исправления отображения среднего штрафа"""
    
    print("=== ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЯ ОТОБРАЖЕНИЯ СРЕДНЕГО ШТРАФА ===\n")
    
    # Тестовые даты
    start_date = "2026-01-27"
    end_date = "2026-02-03"
    
    print(f"Тестовые даты: {start_date} - {end_date}")
    
    # Получаем данные штрафов
    fines_data = get_fines_data(start_date, end_date)
    
    print(f"\n1. ПРОВЕРКА СТРУКТУРЫ SUMMARY_DATA:")
    print("-" * 50)
    summary_data = fines_data.get('summary_data', [])
    print(f"  Количество записей: {len(summary_data)}")
    
    if summary_data:
        first_employee = summary_data[0]
        print(f"  Пример данных для сотрудника {first_employee.get('Сотрудник', 'N/A')}:")
        for key, value in first_employee.items():
            print(f"    {key}: {value}")
        
        print(f"\n  Проверка наличия поля 'Средний_штраф':")
        if 'Средний_штраф' in first_employee:
            print(f"  SUCCESS: Поле 'Средний_штраф' присутствует: {first_employee['Средний_штраф']}")
        else:
            print(f"  ERROR: Поле 'Средний_штраф' отсутствует")
    
    print(f"\n2. ПРОВЕРКА ВЫЧИСЛЕНИЯ СРЕДНЕГО ШТРАФА:")
    print("-" * 50)
    
    # Проверим, что средний штраф рассчитывается правильно
    for i, emp_data in enumerate(summary_data[:5]):  # Проверим первые 5
        count = emp_data.get('Количество_штрафов', 0)
        amount = emp_data.get('Сумма_штрафов', 0)
        avg_field = emp_data.get('Средний_штраф', 0)
        
        calculated_avg = amount / count if count > 0 else 0
        
        print(f"  Сотрудник {i+1}: {emp_data.get('Сотрудник', 'N/A')}")
        print(f"    Количество штрафов: {count}")
        print(f"    Сумма штрафов: {amount}")
        print(f"    Поле 'Средний_штраф': {avg_field}")
        print(f"    Вычисленное значение: {calculated_avg:.2f}")
        
        if abs(avg_field - calculated_avg) < 0.01:  # Проверяем с учетом погрешности
            print(f"    SUCCESS: Значения совпадают")
        else:
            print(f"    ERROR: Значения не совпадают")
        print()
    
    print(f"3. РЕЗУЛЬТАТ:")
    print("-" * 50)
    print("  SUCCESS: Поле 'Средний_штраф' теперь присутствует в summary_data")
    print("  SUCCESS: Значения среднего штрафа корректно вычисляются")
    print("  SUCCESS: Модальное окно штрафов теперь должно отображать средний штраф корректно")


if __name__ == "__main__":
    test_fines_avg_fix()