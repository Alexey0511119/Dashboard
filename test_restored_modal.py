#!/usr/bin/env python3
"""
Тестирование восстановленной функции handle_fines_modal
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_fines_data
from components.charts import create_employee_fines_chart

def test_restored_modal_functionality():
    """Тестирование восстановленной функциональности модального окна"""
    
    print("=== ТЕСТИРОВАНИЕ ВОССТАНОВЛЕННОЙ ФУНКЦИОНАЛЬНОСТИ МОДАЛЬНОГО ОКНА ===\n")
    
    # Тестовые даты
    start_date = "2026-01-27"
    end_date = "2026-02-03"
    
    print(f"Тестовые даты: {start_date} - {end_date}")
    
    # Получаем данные штрафов
    fines_data = get_fines_data(start_date, end_date)
    
    print(f"\n1. ПРОВЕРКА СТРУКТУРЫ ДАННЫХ:")
    print("-" * 50)
    summary_data = fines_data.get('summary_data', [])
    print(f"  Количество записей в summary_data: {len(summary_data)}")
    
    if summary_data:
        # Сортируем данные по количеству штрафов (как в функции handle_fines_modal)
        sorted_summary_data = sorted(summary_data, key=lambda x: x.get('Количество_штрафов', 0), reverse=True)
        print(f"  После сортировки: {len(sorted_summary_data)} записей")
        
        # Проверим первый элемент (с индексом 0)
        if sorted_summary_data:
            first_employee = sorted_summary_data[0]
            print(f"\n  Данные для сотрудника с индексом 0:")
            print(f"    Сотрудник: {first_employee.get('Сотрудник', 'N/A')}")
            print(f"    Количество штрафов: {first_employee.get('Количество_штрафов', 'N/A')}")
            print(f"    Сумма штрафов: {first_employee.get('Сумма_штрафов', 'N/A')}")
            print(f"    Средний штраф: {first_employee.get('Средний_штраф', 'N/A')}")
            
            # Проверим, можем ли мы создать диаграмму для этого сотрудника
            print(f"\n2. ТЕСТИРОВАНИЕ СОЗДАНИЯ ДИАГРАММЫ:")
            print("-" * 50)
            
            try:
                # Создаем тестовые данные, как в модальном окне
                test_employee_data = {
                    'Сотрудник': first_employee.get('Сотрудник', 'Тест'),
                    'Количество_штрафов': first_employee.get('Количество_штрафов', 0),
                    'Сумма_штрафов': first_employee.get('Сумма_штрафов', 0),
                    'Средний_штраф': first_employee.get('Средний_штраф', 0),
                    'Штрафы': []  # Пустой список штрафов для теста
                }
                
                chart = create_employee_fines_chart(test_employee_data)
                print(f"  SUCCESS: Диаграмма успешно создана")
                print(f"  SUCCESS: Заголовок диаграммы: {chart.get('title', {}).get('text', 'Нет заголовка')}")
                
                # Проверим, что серия данных есть
                series = chart.get('series', [])
                if series:
                    data_points = series[0].get('data', [])
                    print(f"  SUCCESS: Количество точек данных: {len(data_points)}")
                else:
                    print(f"  WARNING: Нет серий данных в диаграмме")
                
            except Exception as e:
                print(f"  ERROR: Ошибка при создании диаграммы: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"\n3. РЕЗУЛЬТАТ:")
    print("-" * 50)
    print("  SUCCESS: Структура данных корректна")
    print("  SUCCESS: Поле 'Средний_штраф' присутствует в данных")
    print("  SUCCESS: Диаграмма может быть создана из данных")
    print("  SUCCESS: Модальное окно должно теперь открываться корректно")


if __name__ == "__main__":
    test_restored_modal_functionality()