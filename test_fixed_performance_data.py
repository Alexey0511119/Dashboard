#!/usr/bin/env python3
"""
Тестирование исправленной функции get_performance_data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_performance_data

def test_fixed_performance_data():
    """Тестирование исправленной функции получения данных производительности"""
    
    print("=== ТЕСТИРОВАНИЕ ИСПРАВЛЕННОЙ ФУНКЦИИ get_performance_data ===\n")
    
    # Тестовые даты
    start_date = "2026-01-27"
    end_date = "2026-02-03"
    
    print(f"Тестовые даты: {start_date} - {end_date}")
    
    # Получаем данные производительности
    performance_data = get_performance_data(start_date, end_date)
    
    print(f"\n1. ОБЩАЯ ИНФОРМАЦИЯ:")
    print("-" * 50)
    print(f"  Всего записей: {len(performance_data)}")
    
    if performance_data:
        print(f"  Примеры первых записей:")
        for i, record in enumerate(performance_data[:5]):
            print(f"    {i+1}. {record}")
    
    print(f"\n2. АНАЛИЗ СОТРУДНИКОВ:")
    print("-" * 50)
    
    # Подсчитаем количество записей для каждого сотрудника
    employee_counts = {}
    for record in performance_data:
        employee = record.get('Сотрудник', 'Неизвестно')
        if employee in employee_counts:
            employee_counts[employee] += 1
        else:
            employee_counts[employee] = 1
    
    # Найдем сотрудников с несколькими записями (их не должно быть)
    multi_record_employees = {emp: count for emp, count in employee_counts.items() if count > 1}
    
    print(f"  Всего уникальных сотрудников: {len(employee_counts)}")
    print(f"  Сотрудников с несколькими записями: {len(multi_record_employees)}")
    
    if multi_record_employees:
        print(f"  ERROR: НАЙДЕНЫ СОТРУДНИКИ С НЕСКОЛЬКИМИ ЗАПИСЯМИ:")
        for emp, count in sorted(multi_record_employees.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    - {emp}: {count} записей")
    else:
        print(f"  SUCCESS: ВСЕ СОТРУДНИКИ ИМЕЮТ ТОЛЬКО ОДНУ ЗАПИСЬ")
    
    # Проверим конкретного сотрудника (например, Плевако)
    plevako_records = [rec for rec in performance_data if 'Плевако' in rec.get('Сотрудник', '')]
    if plevako_records:
        print(f"\n3. АНАЛИЗ КОНКРЕТНОГО СОТРУДНИКА (Плевако):")
        print("-" * 50)
        print(f"  Найдено записей для Плевако: {len(plevako_records)}")
        for i, record in enumerate(plevako_records):
            print(f"    Запись {i+1}: {record}")
    else:
        print(f"\n3. АНАЛИЗ КОНКРЕТНОГО СОТРУДНИКА (Плевако):")
        print("-" * 50)
        print(f"  INFO: Не найдено записей для сотрудника с фамилией Плевако")
    
    print(f"\n4. АНАЛИЗ СТРУКТУРЫ ДАННЫХ:")
    print("-" * 50)
    
    # Проверим, какие поля есть в данных
    if performance_data:
        first_record = performance_data[0]
        print("  Поля в данных:")
        for key, value in first_record.items():
            print(f"    - {key}: {type(value).__name__} = {value}")
    
    print(f"\n5. РЕЗУЛЬТАТ:")
    print("-" * 50)
    if len(multi_record_employees) == 0:
        print("  SUCCESS: Функция теперь корректно агрегирует данные по сотруднику")
        print("  SUCCESS: Каждый сотрудник представлен только одной записью")
        print("  SUCCESS: Проблема с дублированием записей решена")
        print("  SUCCESS: Данные готовы для корректного отображения в таблице")
    else:
        print("  ERROR: Проблема с дублированием записей НЕ решена")
        print(f"  ERROR: Всё ещё есть {len(multi_record_employees)} сотрудников с несколькими записями")


if __name__ == "__main__":
    test_fixed_performance_data()