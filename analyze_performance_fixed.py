#!/usr/bin/env python3
"""
Исправленный анализ view для производительности с правильными именами колонок
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.mssql_client import execute_query_cached

def analyze_performance_views_fixed():
    """Анализ view с правильными именами колонок"""
    
    print("=== АНАЛИЗ VIEW ДЛЯ ПРОИЗВОДИТЕЛЬНОСТИ (ИСПРАВЛЕННЫЙ) ===\n")
    
    try:
        # 1. Анализ dm.v_performance_detailed
        print("1. DM.V_PERFORMANCE_DETAILED:")
        print("-" * 40)
        
        # Получаем примеры данных с правильными колонками
        sample_query = """
        SELECT TOP 5 * FROM dm.v_performance_detailed
        ORDER BY Общее_кол_операций DESC
        """
        
        sample_result = execute_query_cached(sample_query)
        if sample_result:
            print("  Примеры данных:")
            for i, row in enumerate(sample_result, 1):
                print(f"\n    Запись {i}:")
                if hasattr(row, '__getitem__'):
                    print(f"      Сотрудник: {row[0]}")
                    print(f"      date_key: {row[1]}")
                    print(f"      Общее_кол_операций: {row[2]}")
                    print(f"      Ср_время_на_операцию: {row[3]}")
                    print(f"      Заработок: {row[4]}")
                    print(f"      Операций_в_час: {row[5]}")
                    print(f"      Время_работы: {row[6]}")
                    print(f"      Время_первой_операции: {row[7]}")
                    print(f"      Обычные_операции: {row[8]}")
                    print(f"      Приемка: {row[9]}")
        
        # Анализ уникальных сотрудников
        unique_query = """
        SELECT 
            COUNT(DISTINCT Сотрудник) as unique_employees,
            COUNT(DISTINCT date_key) as unique_dates
        FROM dm.v_performance_detailed
        """
        
        unique_result = execute_query_cached(unique_query)
        if unique_result:
            row = unique_result[0]
            unique_employees = row[0] if row[0] else 0
            unique_dates = row[1] if row[1] else 0
            
            print(f"\n  Уникальных сотрудников: {unique_employees}")
            print(f"  Уникальных дат: {unique_dates}")
        
        print("\n" + "="*50 + "\n")
        
        # 2. Анализ dm.v_employee_modal_detail
        print("2. DM.V_EMPLOYEE_MODAL_DETAIL:")
        print("-" * 40)
        
        # Получаем примеры данных
        sample_query = """
        SELECT TOP 3 
            fio,
            smena,
            date_key,
            total_operations,
            total_earnings,
            total_idle_minutes,
            orders_completed,
            timely_percentage,
            fines_count,
            fines_amount,
            operations_by_type,
            reception_count
        FROM dm.v_employee_modal_detail
        ORDER BY date_key DESC, total_operations DESC
        """
        
        sample_result = execute_query_cached(sample_query)
        if sample_result:
            print("  Примеры данных:")
            for i, row in enumerate(sample_result, 1):
                print(f"\n    Запись {i}:")
                if hasattr(row, '__getitem__'):
                    print(f"      fio: {row[0]}")
                    print(f"      smena: {row[1]}")
                    print(f"      date_key: {row[2]}")
                    print(f"      total_operations: {row[3]}")
                    print(f"      total_earnings: {row[4]}")
                    print(f"      total_idle_minutes: {row[5]}")
                    print(f"      orders_completed: {row[6]}")
                    print(f"      timely_percentage: {row[7]}")
                    print(f"      fines_count: {row[8]}")
                    print(f"      fines_amount: {row[9]}")
                    print(f"      operations_by_type: {row[10]}")
                    print(f"      reception_count: {row[11]}")
        
        # 3. Сравнение с текущими функциями
        print("\n3. СРАВНЕНИЕ С ТЕКУЩИМИ ФУНКЦИЯМИ:")
        print("-" * 40)
        
        try:
            from data.queries_mssql import get_performance_data
            current_data = get_performance_data()
            print(f"  Текущая функция get_performance_data(): {len(current_data)} записей")
            
            if current_data:
                print("  Поля в текущих данных:")
                first_record = current_data[0]
                for key, value in first_record.items():
                    print(f"    {key}: {value}")
        except Exception as e:
            print(f"  Ошибка при вызове текущей функции: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при анализе: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    analyze_performance_views_fixed()
