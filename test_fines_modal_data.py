#!/usr/bin/env python3
"""
Тестирование данных для модального окна штрафов
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_fines_data, get_employee_fines_details

def test_fines_modal_data():
    """Тестирование данных для модального окна штрафов"""
    
    print("=== ТЕСТИРОВАНИЕ ДАННЫХ ДЛЯ МОДАЛЬНОГО ОКНА ШТРАФОВ ===\n")
    
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
    for i, item in enumerate(summary_data[:5]):  # Показываем первые 5
        print(f"    {i}. {item}")
    
    print(f"\n3. ТЕСТИРОВАНИЕ ПОЛУЧЕНИЯ ДЕТАЛЕЙ ДЛЯ ПЕРВОГО СОТРУДНИКА:")
    print("-" * 50)
    
    if summary_data:
        first_employee = summary_data[0]
        employee_name = first_employee.get('Сотрудник', '')
        print(f"  Имя сотрудника: {employee_name}")
        
        # Получаем детали для сотрудника
        try:
            from data.queries_mssql import get_employee_fines_details
            employee_fines_details = get_employee_fines_details(employee_name, start_date, end_date)
            print(f"  Детали штрафов: {len(employee_fines_details) if employee_fines_details else 0} записей")
            
            if employee_fines_details:
                print("  Примеры деталей:")
                for i, detail in enumerate(employee_fines_details[:3]):
                    print(f"    {i+1}. {detail}")
            else:
                print("  ❌ Нет деталей штрафов для сотрудника")
                
        except Exception as e:
            print(f"  ERROR: Ошибка при получении деталей штрафов: {e}")
            print("  Возможно, функция get_employee_fines_details не реализована")
    
    print(f"\n4. АНАЛИЗ ПРОБЛЕМЫ:")
    print("-" * 50)
    
    # Проверим, есть ли функция get_employee_fines_details
    try:
        from data.queries_mssql import get_employee_fines_details
        print("  SUCCESS: Функция get_employee_fines_details импортирована")
    except ImportError:
        print("  ERROR: Функция get_employee_fines_details не найдена")
    
    # Проверим, как должна работать логика в модальном окне
    print(f"\n  Логика модального окна:")
    print(f"  1. Клик по сотруднику в таблице -> вызов handle_fines_modal")
    print(f"  2. handle_fines_modal получает индекс сотрудника из {{'type': 'fines-employee', 'index': idx}}")
    print(f"  3. Использует этот индекс для получения данных из sorted_summary_data")
    print(f"  4. Вызывает get_employee_fines_details для получения деталей")
    print(f"  5. Создает диаграмму и открывает модальное окно")
    
    if not summary_data:
        print(f"\n  ERROR: Нет данных для отображения в модальном окне")
    else:
        print(f"\n  SUCCESS: Данные для сотрудников доступны")
        
        # Проверим, есть ли проблема с индексами
        print(f"  Индексы сотрудников в таблице: 0 до {len(summary_data)-1}")
        print(f"  Пример: сотрудник с индексом 0: {summary_data[0].get('Сотрудник', 'N/A') if summary_data else 'N/A'}")


if __name__ == "__main__":
    test_fines_modal_data()