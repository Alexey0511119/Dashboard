#!/usr/bin/env python3
"""
Анализ view v_operations_by_type_for_chart для диаграммы типов операций
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.mssql_client import execute_query_cached

def analyze_operations_by_type_view():
    """Анализ view для диаграммы типов операций"""
    
    print("=== АНАЛИЗ VIEW V_OPERATIONS_BY_TYPE_FOR_CHART ===\n")
    
    try:
        # 1. Проверяем существование view
        print("1. ПРОВЕРКА СУЩЕСТВОВАНИЯ VIEW:")
        check_query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.VIEWS 
        WHERE TABLE_SCHEMA = 'dm' AND TABLE_NAME = 'v_operations_by_type_for_chart'
        """
        
        check_result = execute_query_cached(check_query)
        if check_result:
            print("  ✅ View dm.v_operations_by_type_for_chart существует")
        else:
            print("  ❌ View dm.v_operations_by_type_for_chart не найдена")
            return False
        
        # 2. Получаем структуру view
        print("\n2. СТРУКТУРА VIEW:")
        columns_query = """
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'dm' AND TABLE_NAME = 'v_operations_by_type_for_chart'
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
        
        # 3. Получаем количество записей
        print("\n3. ОБЩЕЕ КОЛИЧЕСТВО ЗАПИСЕЙ:")
        count_query = "SELECT COUNT(*) as total FROM dm.v_operations_by_type_for_chart"
        count_result = execute_query_cached(count_query)
        if count_result:
            total_count = count_result[0][0] if count_result[0] else 0
            print(f"  Всего записей: {total_count}")
        
        # 4. Получаем примеры данных
        print("\n4. ПРИМЕРЫ ДАННЫХ:")
        sample_query = """
        SELECT TOP 10 * FROM dm.v_operations_by_type_for_chart
        ORDER BY operation_count DESC
        """
        
        sample_result = execute_query_cached(sample_query)
        if sample_result:
            print("  Примеры данных:")
            for i, row in enumerate(sample_result, 1):
                print(f"\n    Запись {i}:")
                if hasattr(row, '__getitem__'):
                    for j, value in enumerate(row):
                        if columns_result and j < len(columns_result):
                            col_name = columns_result[j][0] if hasattr(columns_result[j], '__getitem__') else columns_result[j].COLUMN_NAME
                        else:
                            col_name = f"Колонка {j}"
                        print(f"      {col_name}: {value}")
        
        # 5. Проверяем для конкретного сотрудника
        print("\n5. ПРОВЕРКА ДЛЯ КОНКРЕТНОГО СОТРУДНИКА:")
        employee_query = """
        SELECT TOP 5 * FROM dm.v_operations_by_type_for_chart
        WHERE fio IS NOT NULL AND fio != ''
        ORDER BY operation_count DESC
        """
        
        employee_result = execute_query_cached(employee_query)
        if employee_result:
            print("  Данные для сотрудников:")
            for i, row in enumerate(employee_result, 1):
                print(f"\n    Запись {i}:")
                if hasattr(row, '__getitem__'):
                    for j, value in enumerate(row):
                        if columns_result and j < len(columns_result):
                            col_name = columns_result[j][0] if hasattr(columns_result[j], '__getitem__') else columns_result[j].COLUMN_NAME
                        else:
                            col_name = f"Колонка {j}"
                        print(f"      {col_name}: {value}")
        
        # 6. Анализ уникальных типов операций
        print("\n6. УНИКАЛЬНЫЕ ТИПЫ ОПЕРАЦИЙ:")
        unique_types_query = """
        SELECT DISTINCT operation_type, COUNT(*) as count, SUM(operation_count) as total_ops
        FROM dm.v_operations_by_type_for_chart
        WHERE operation_type IS NOT NULL AND operation_type != ''
        GROUP BY operation_type
        ORDER BY total_ops DESC
        """
        
        unique_types_result = execute_query_cached(unique_types_query)
        if unique_types_result:
            print("  Типы операций:")
            for row in unique_types_result:
                if hasattr(row, '__getitem__'):
                    op_type = row[0]
                    count = row[1]
                    total_ops = row[2]
                else:
                    op_type = getattr(row, 'operation_type', 'N/A')
                    count = getattr(row, 'count', 0)
                    total_ops = getattr(row, 'total_ops', 0)
                
                print(f"    - {op_type}: {count} записей, {total_ops} операций")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при анализе view: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    analyze_operations_by_type_view()
