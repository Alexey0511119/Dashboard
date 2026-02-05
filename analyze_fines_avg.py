#!/usr/bin/env python3
"""
Анализ проблемы с отображением среднего штрафа в модальном окне
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_fines_data

def analyze_fines_data_structure():
    """Анализ структуры данных штрафов"""
    
    print("=== АНАЛИЗ СТРУКТУРЫ ДАННЫХ ШТРАФОВ ===\n")
    
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
        print(f"    {i}. {item}")
        print(f"       Ключи: {list(item.keys())}")
    
    print(f"\n3. ДАННЫЕ ПОЛНОЙ ИНФОРМАЦИИ (fines_data возвращаемый из get_fines_data):")
    print("-" * 50)
    # Проверим, есть ли в основном ответе данные с полным набором полей
    print("  В текущей реализации get_fines_data возвращает summary_data без поля 'Средний_штраф'")
    
    print(f"\n4. АНАЛИЗ ПРОБЛЕМЫ:")
    print("-" * 50)
    print("  В функции handle_fines_modal используется sorted_summary_data")
    print("  В summary_data есть поля: ['Сотрудник', 'Количество_штрафов', 'Сумма_штрафов']")
    print("  Но НЕТ поля: 'Средний_штраф'")
    print("  ")
    print("  Однако в модальном окне используется:")
    print("    avg_amount = employee_data.get('Средний_штраф', 0)")
    print("  ")
    print("  РЕШЕНИЕ:")
    print("  1. Нужно добавить поле 'Средний_штраф' в summary_data в функции get_fines_data")
    print("  2. Или изменить логику в handle_fines_modal, чтобы вычислять средний штраф из доступных данных")
    
    # Проверим, можно ли вычислить средний штраф из имеющихся данных
    if summary_data:
        first_employee = summary_data[0]
        print(f"\n  Пример для сотрудника {first_employee.get('Сотрудник', 'N/A')}:")
        count = first_employee.get('Количество_штрафов', 0)
        amount = first_employee.get('Сумма_штрафов', 0)
        if count > 0:
            avg_calc = amount / count
            print(f"    Количество штрафов: {count}")
            print(f"    Сумма штрафов: {amount}")
            print(f"    Вычисленный средний штраф: {avg_calc}")
        else:
            print(f"    Нет штрафов для вычисления среднего")


if __name__ == "__main__":
    analyze_fines_data_structure()