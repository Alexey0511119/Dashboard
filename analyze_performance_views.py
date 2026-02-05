#!/usr/bin/env python3
"""
Анализ view для вкладки "Производительность": dm.v_performance_detailed и dm.v_employee_modal_detail
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.mssql_client import execute_query_cached

def analyze_performance_views():
    """Анализ view для производительности"""
    
    print("=== АНАЛИЗ VIEW ДЛЯ ВКЛАДКИ 'ПРОИЗВОДИТЕЛЬНОСТЬ' ===\n")
    
    try:
        # 1. Анализ dm.v_performance_detailed
        print("1. АНАЛИЗ DM.V_PERFORMANCE_DETAILED:")
        print("-" * 50)
        
        # Проверяем существование
        check_query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.VIEWS 
        WHERE TABLE_SCHEMA = 'dm' AND TABLE_NAME = 'v_performance_detailed'
        """
        
        check_result = execute_query_cached(check_query)
        if check_result:
            print("  ✅ View dm.v_performance_detailed существует")
        else:
            print("  ❌ View dm.v_performance_detailed не найдена")
            return False
        
        # Получаем структуру
        columns_query = """
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'dm' AND TABLE_NAME = 'v_performance_detailed'
        ORDER BY ORDINAL_POSITION
        """
        
        columns_result = execute_query_cached(columns_query)
        if columns_result:
            print("  Колонки:")
            for row in columns_result:
                if hasattr(row, '__getitem__'):
                    col_name = row[0]
                    data_type = row[1]
                    is_nullable = row[2]
                    max_length = row[3]
                else:
                    col_name = getattr(row, 'COLUMN_NAME', 'N/A')
                    data_type = getattr(row, 'DATA_TYPE', 'N/A')
                    is_nullable = getattr(row, 'IS_NULLABLE', 'N/A')
                    max_length = getattr(row, 'CHARACTER_MAXIMUM_LENGTH', 'N/A')
                
                length_str = f"({max_length})" if max_length else ""
                nullable_str = "NULL" if is_nullable == "YES" else "NOT NULL"
                print(f"    - {col_name}: {data_type}{length_str} {nullable_str}")
        
        # Получаем количество записей
        count_query = "SELECT COUNT(*) as total FROM dm.v_performance_detailed"
        count_result = execute_query_cached(count_query)
        if count_result:
            total_count = count_result[0][0] if count_result[0] else 0
            print(f"  Всего записей: {total_count}")
        
        # Получаем примеры данных
        print("  Примеры данных:")
        sample_query = """
        SELECT TOP 3 * FROM dm.v_performance_detailed
        ORDER BY total_operations DESC
        """
        
        sample_result = execute_query_cached(sample_query)
        if sample_result:
            for i, row in enumerate(sample_result, 1):
                print(f"\n    Запись {i}:")
                if hasattr(row, '__getitem__'):
                    for j, value in enumerate(row):
                        if columns_result and j < len(columns_result):
                            col_name = columns_result[j][0] if hasattr(columns_result[j], '__getitem__') else columns_result[j].COLUMN_NAME
                        else:
                            col_name = f"Колонка {j}"
                        print(f"      {col_name}: {value}")
        
        print("\n" + "="*60 + "\n")
        
        # 2. Анализ dm.v_employee_modal_detail
        print("2. АНАЛИЗ DM.V_EMPLOYEE_MODAL_DETAIL:")
        print("-" * 50)
        
        # Проверяем существование
        check_query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.VIEWS 
        WHERE TABLE_SCHEMA = 'dm' AND TABLE_NAME = 'v_employee_modal_detail'
        """
        
        check_result = execute_query_cached(check_query)
        if check_result:
            print("  ✅ View dm.v_employee_modal_detail существует")
        else:
            print("  ❌ View dm.v_employee_modal_detail не найдена")
            return False
        
        # Получаем структуру
        columns_query = """
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'dm' AND TABLE_NAME = 'v_employee_modal_detail'
        ORDER BY ORDINAL_POSITION
        """
        
        columns_result = execute_query_cached(columns_query)
        if columns_result:
            print("  Колонки:")
            for row in columns_result:
                if hasattr(row, '__getitem__'):
                    col_name = row[0]
                    data_type = row[1]
                    is_nullable = row[2]
                    max_length = row[3]
                else:
                    col_name = getattr(row, 'COLUMN_NAME', 'N/A')
                    data_type = getattr(row, 'DATA_TYPE', 'N/A')
                    is_nullable = getattr(row, 'IS_NULLABLE', 'N/A')
                    max_length = getattr(row, 'CHARACTER_MAXIMUM_LENGTH', 'N/A')
                
                length_str = f"({max_length})" if max_length else ""
                nullable_str = "NULL" if is_nullable == "YES" else "NOT NULL"
                print(f"    - {col_name}: {data_type}{length_str} {nullable_str}")
        
        # Получаем количество записей
        count_query = "SELECT COUNT(*) as total FROM dm.v_employee_modal_detail"
        count_result = execute_query_cached(count_query)
        if count_result:
            total_count = count_result[0][0] if count_result[0] else 0
            print(f"  Всего записей: {total_count}")
        
        # Получаем примеры данных
        print("  Примеры данных:")
        sample_query = """
        SELECT TOP 3 * FROM dm.v_employee_modal_detail
        ORDER BY date_key DESC
        """
        
        sample_result = execute_query_cached(sample_query)
        if sample_result:
            for i, row in enumerate(sample_result, 1):
                print(f"\n    Запись {i}:")
                if hasattr(row, '__getitem__'):
                    for j, value in enumerate(row):
                        if columns_result and j < len(columns_result):
                            col_name = columns_result[j][0] if hasattr(columns_result[j], '__getitem__') else columns_result[j].COLUMN_NAME
                        else:
                            col_name = f"Колонка {j}"
                        print(f"      {col_name}: {value}")
        
        # 3. Анализ уникальных сотрудников
        print("\n3. АНАЛИЗ УНИКАЛЬНЫХ СОТРУДНИКОВ:")
        print("-" * 50)
        
        unique_query = """
        SELECT 
            COUNT(DISTINCT fio) as unique_employees,
            COUNT(DISTINCT date_key) as unique_dates
        FROM dm.v_performance_detailed
        """
        
        unique_result = execute_query_cached(unique_query)
        if unique_result:
            row = unique_result[0]
            unique_employees = row[0] if row[0] else 0
            unique_dates = row[1] if row[1] else 0
            
            print(f"  Уникальных сотрудников: {unique_employees}")
            print(f"  Уникальных дат: {unique_dates}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при анализе view: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    analyze_performance_views()
