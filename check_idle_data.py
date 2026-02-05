#!/usr/bin/env python3
"""
Проверка данных о простоях в dm.v_employee_modal_detail
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.mssql_client import execute_query_cached

def check_idle_data():
    """Проверка данных о простоях"""
    
    print("=== ПРОВЕРКА ДАННЫХ О ПРОСТОЯХ ===\n")
    
    try:
        # 1. Проверяем общие данные о простоях
        print("1. ОБЩИЕ ДАННЫЕ О ПРОСТОЯХ:")
        idle_query = """
        SELECT 
            COUNT(*) as total_records,
            COUNT(CASE WHEN total_idle_minutes > 0 THEN 1 END) as with_idle,
            SUM(total_idle_minutes) as total_idle_minutes,
            AVG(total_idle_minutes) as avg_idle_minutes,
            MAX(total_idle_minutes) as max_idle_minutes
        FROM dm.v_employee_modal_detail
        """
        
        idle_result = execute_query_cached(idle_query)
        if idle_result:
            row = idle_result[0]
            total_records = row[0] if row[0] else 0
            with_idle = row[1] if row[1] else 0
            total_idle = row[2] if row[2] else 0
            avg_idle = row[3] if row[3] else 0
            max_idle = row[4] if row[4] else 0
            
            print(f"  Всего записей: {total_records}")
            print(f"  С простоями: {with_idle}")
            print(f"  Всего минут простоя: {total_idle}")
            print(f"  Средний простой: {avg_idle:.1f} минут")
            print(f"  Максимальный простой: {max_idle} минут")
        
        # 2. Проверяем детализацию по интервалам
        print("\n2. ДЕТАЛИЗАЦИЯ ПО ИНТЕРВАЛАМ ПРОСТОЯ:")
        
        # Проверяем, есть ли детализация в данных
        sample_query = """
        SELECT TOP 10 
            fio,
            date_key,
            total_idle_minutes,
            operations_by_type
        FROM dm.v_employee_modal_detail
        WHERE total_idle_minutes > 0
        ORDER BY total_idle_minutes DESC
        """
        
        sample_result = execute_query_cached(sample_query)
        if sample_result:
            print("  Примеры записей с простоями:")
            for i, row in enumerate(sample_result, 1):
                if hasattr(row, '__getitem__'):
                    fio = row[0]
                    date_key = row[1]
                    idle_minutes = row[2]
                    operations_by_type = row[3]
                    
                    print(f"\n    Запись {i}:")
                    print(f"      ФИО: {fio}")
                    print(f"      Дата: {date_key}")
                    print(f"      Простой: {idle_minutes} минут")
                    print(f"      Операции: {operations_by_type[:100]}..." if len(str(operations_by_type)) > 100 else f"      Операции: {operations_by_type}")
        
        # 3. Проверяем распределение по интервалам
        print("\n3. РАСПРЕДЕЛЕНИЕ ПО ИНТЕРВАЛАМ:")
        
        # Создаем интервалы вручную
        interval_query = """
        SELECT 
            CASE 
                WHEN total_idle_minutes > 0 AND total_idle_minutes <= 10 THEN '5-10 мин'
                WHEN total_idle_minutes > 10 AND total_idle_minutes <= 30 THEN '10-30 мин'
                WHEN total_idle_minutes > 30 AND total_idle_minutes <= 60 THEN '30-60 мин'
                WHEN total_idle_minutes > 60 THEN '>1 часа'
                ELSE 'Нет простоя'
            END as interval_group,
            COUNT(*) as count,
            SUM(total_idle_minutes) as total_minutes
        FROM dm.v_employee_modal_detail
        GROUP BY 
            CASE 
                WHEN total_idle_minutes > 0 AND total_idle_minutes <= 10 THEN '5-10 мин'
                WHEN total_idle_minutes > 10 AND total_idle_minutes <= 30 THEN '10-30 мин'
                WHEN total_idle_minutes > 30 AND total_idle_minutes <= 60 THEN '30-60 мин'
                WHEN total_idle_minutes > 60 THEN '>1 часа'
                ELSE 'Нет простоя'
            END
        ORDER BY 
            CASE 
                WHEN total_idle_minutes > 0 AND total_idle_minutes <= 10 THEN 1
                WHEN total_idle_minutes > 10 AND total_idle_minutes <= 30 THEN 2
                WHEN total_idle_minutes > 30 AND total_idle_minutes <= 60 THEN 3
                WHEN total_idle_minutes > 60 THEN 4
                ELSE 0
            END
        """
        
        interval_result = execute_query_cached(interval_query)
        if interval_result:
            print("  Распределение по интервалам:")
            for row in interval_result:
                if hasattr(row, '__getitem__'):
                    interval = row[0]
                    count = row[1]
                    minutes = row[2]
                    
                    print(f"    {interval}: {count} записей, {minutes} минут")
        
        # 4. Проверяем для конкретного сотрудника
        print("\n4. ПРОВЕРКА ДЛЯ КОНКРЕТНОГО СОТРУДНИКА:")
        employee_query = """
        SELECT TOP 5 
            fio,
            date_key,
            total_idle_minutes,
            total_operations,
            operations_by_type
        FROM dm.v_employee_modal_detail
        WHERE fio LIKE '%Хорошилов%' AND total_idle_minutes > 0
        ORDER BY date_key DESC
        """
        
        employee_result = execute_query_cached(employee_query)
        if employee_result:
            print("  Данные для сотрудника с простоями:")
            for i, row in enumerate(employee_result, 1):
                if hasattr(row, '__getitem__'):
                    fio = row[0]
                    date_key = row[1]
                    idle_minutes = row[2]
                    total_ops = row[3]
                    operations_by_type = row[4]
                    
                    print(f"\n    Запись {i}:")
                    print(f"      ФИО: {fio}")
                    print(f"      Дата: {date_key}")
                    print(f"      Простой: {idle_minutes} минут")
                    print(f"      Операции: {total_ops}")
                    print(f"      Детали: {operations_by_type[:100]}..." if len(str(operations_by_type)) > 100 else f"      Детали: {operations_by_type}")
        else:
            print("  ❌ Нет данных о простоях для тестового сотрудника")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке данных о простоях: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_idle_data()
