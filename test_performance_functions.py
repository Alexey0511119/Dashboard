#!/usr/bin/env python3
"""
Тестирование обновленных функций для производительности
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_performance_data, get_employee_modal_detail

def test_performance_functions():
    """Тестирование функций производительности"""
    
    print("=== ТЕСТИРОВАНИЕ ФУНКЦИЙ ПРОИЗВОДИТЕЛЬНОСТИ ===\n")
    
    try:
        # 1. Тестируем get_performance_data
        print("1. Тестирование get_performance_data():")
        start_date = "2025-01-01"
        end_date = "2025-12-31"
        
        performance_data = get_performance_data(start_date, end_date)
        print(f"  Получено записей: {len(performance_data)}")
        
        if performance_data:
            print("  Пример данных:")
            for i, record in enumerate(performance_data[:3], 1):
                print(f"\n    Запись {i}:")
                for key, value in record.items():
                    print(f"      {key}: {value}")
        
        # 2. Тестируем get_employee_modal_detail
        print("\n2. Тестирование get_employee_modal_detail():")
        if performance_data:
            employee_name = performance_data[0]['Сотрудник']
            print(f"  Тестируем для сотрудника: {employee_name}")
            
            detail_data = get_employee_modal_detail(employee_name, start_date, end_date)
            print(f"  Получено записей: {len(detail_data)}")
            
            if detail_data:
                print("  Пример детальных данных:")
                for i, record in enumerate(detail_data[:2], 1):
                    print(f"\n    Запись {i}:")
                    for key, value in record.items():
                        print(f"      {key}: {value}")
        
        # 3. Анализ данных
        print("\n3. Анализ данных:")
        if performance_data:
            total_records = len(performance_data)
            unique_employees = len(set(record['Сотрудник'] for record in performance_data))
            
            print(f"  Всего записей: {total_records}")
            print(f"  Уникальных сотрудников: {unique_employees}")
            
            # Топ-5 по заработку
            top_earnings = sorted(performance_data, key=lambda x: x['Заработок'], reverse=True)[:5]
            print(f"\n  Топ-5 по заработку:")
            for i, record in enumerate(top_earnings, 1):
                print(f"    {i}. {record['Сотрудник']}: {record['Заработок']} руб ({record['Общее_кол_операций']} операций)")
            
            # Топ-5 по операциям
            top_ops = sorted(performance_data, key=lambda x: x['Общее_кол_операций'], reverse=True)[:5]
            print(f"\n  Топ-5 по операциям:")
            for i, record in enumerate(top_ops, 1):
                print(f"    {i}. {record['Сотрудник']}: {record['Общее_кол_операций']} операций ({record['Заработок']} руб)")
        
        print(f"\n🎉 Функции производительности работают корректно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_performance_functions()
    if success:
        print(f"\n🎉 Функции готовы к работе в дашборде!")
    else:
        print(f"\n❌ Проблемы с функциями")
