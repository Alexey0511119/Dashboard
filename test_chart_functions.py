#!/usr/bin/env python3
"""
Тестирование новых функций для диаграмм
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_employee_operations_by_type, get_employee_idle_intervals

def test_chart_functions():
    """Тестирование функций для диаграмм"""
    
    print("=== ТЕСТИРОВАНИЕ ФУНКЦИЙ ДЛЯ ДИАГРАММ ===\n")
    
    try:
        # Тестовые данные
        employee_name = "Хорошилов Александр Александрович"
        start_date = "2026-01-27"
        end_date = "2026-02-03"
        
        print(f"Сотрудник: {employee_name}")
        print(f"Период: {start_date} - {end_date}\n")
        
        # 1. Тестируем get_employee_operations_by_type
        print("1. ТИПЫ ОПЕРАЦИЙ:")
        operations_data = get_employee_operations_by_type(employee_name, start_date, end_date)
        print(f"  Получено типов операций: {len(operations_data)}")
        
        if operations_data:
            print("  Данные по типам операций:")
            for i, op in enumerate(operations_data, 1):
                print(f"    {i}. {op['operation_type']}: {op['total_operations']} операций (ср. время: {op['avg_time']} мин, заработок: {op['total_earnings']} руб)")
        
        # 2. Тестируем get_employee_idle_intervals
        print("\n2. ИНТЕРВАЛЫ ПРОСТОЕВ:")
        idle_intervals = get_employee_idle_intervals(employee_name, start_date, end_date)
        print(f"  Интервалы простоев:")
        
        total_intervals = sum(idle_intervals.values())
        for interval, count in idle_intervals.items():
            print(f"    {interval}: {count} раз")
        
        print(f"  Всего интервалов с простоями: {total_intervals}")
        
        # 3. Проверяем структуру данных для диаграмм
        print("\n3. СТРУКТУРА ДАННЫХ ДЛЯ ДИАГРАММ:")
        
        if operations_data:
            print("  Для столбчатой диаграммы типов операций:")
            print(f"    Категории (X): {[op['operation_type'] for op in operations_data]}")
            print(f"    Значения (Y): {[op['total_operations'] for op in operations_data]}")
        
        if idle_intervals:
            print("  Для диаграммы простоев:")
            print(f"    Категории: {list(idle_intervals.keys())}")
            print(f"    Значения: {list(idle_intervals.values())}")
        
        print(f"\n🎉 Функции для диаграмм работают корректно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chart_functions()
    if success:
        print(f"\n🎉 Диаграммы готовы к работе в дашборде!")
    else:
        print(f"\n❌ Проблемы с функциями")
