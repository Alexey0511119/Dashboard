#!/usr/bin/env python3
"""
Анализ данных производительности сотрудников
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_performance_data

def analyze_performance_data():
    """Анализ данных производительности сотрудников"""
    
    print("=== АНАЛИЗ ДАННЫХ ПРОИЗВОДИТЕЛЬНОСТИ СОТРУДНИКОВ ===\n")
    
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
    
    # Найдем сотрудников с несколькими записями
    multi_record_employees = {emp: count for emp, count in employee_counts.items() if count > 1}
    
    print(f"  Всего уникальных сотрудников: {len(employee_counts)}")
    print(f"  Сотрудников с несколькими записями: {len(multi_record_employees)}")
    
    if multi_record_employees:
        print(f"  Сотрудники с несколькими записями:")
        for emp, count in sorted(multi_record_employees.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    - {emp}: {count} записей")
    
    # Проверим конкретного сотрудника (например, если есть Плевако в данных)
    plevakos = [emp for emp in employee_counts.keys() if 'Плевако' in emp]
    if plevakos:
        print(f"\n3. АНАЛИЗ КОНКРЕТНОГО СОТРУДНИКА (Плевако):")
        print("-" * 50)
        for plevako in plevakos:
            print(f"  {plevako}: {employee_counts[plevako]} записей")
            
            # Показываем детали для этого сотрудника
            plevakos_records = [rec for rec in performance_data if rec.get('Сотрудник') == plevako]
            for i, record in enumerate(plevakos_records):
                print(f"    Запись {i+1}: {record}")
    
    print(f"\n4. АНАЛИЗ СТРУКТУРЫ ДАННЫХ:")
    print("-" * 50)
    
    # Проверим, какие поля есть в данных
    if performance_data:
        first_record = performance_data[0]
        print("  Поля в данных:")
        for key, value in first_record.items():
            print(f"    - {key}: {type(value).__name__} = {value}")
    
    print(f"\n5. ВЫЯВЛЕННАЯ ПРОБЛЕМА:")
    print("-" * 50)
    print("  Проблема в том, что представление dm.v_performance_detailed")
    print("  возвращает данные по дням для каждого сотрудника, а не агрегированные")
    print("  данные за весь период.")
    print("  ")
    print("  Решение: Нужно агрегировать данные по сотруднику в функции")
    print("  get_performance_data, суммируя/усредняя значения за весь период.")


if __name__ == "__main__":
    analyze_performance_data()