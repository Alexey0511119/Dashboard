#!/usr/bin/env python3
"""
Проверка структуры таблицы штрафов для детализации
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.mssql_client import execute_query_cached

def check_fines_table_structure():
    """Проверка структуры таблицы штрафов"""
    
    print("=== ПРОВЕРКА СТРУКТУРЫ ТАБЛИЦЫ ШТРАФОВ ===\n")
    
    # Проверим структуру v_penalty_summary
    print("1. СТРУКТУРА dm.v_penalty_summary:")
    print("-" * 50)
    
    columns_query = """
    SELECT
        COLUMN_NAME,
        DATA_TYPE,
        IS_NULLABLE,
        CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'dm' AND TABLE_NAME = 'v_penalty_summary'
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
    
    # Получим примеры данных для конкретного сотрудника
    print("\n2. ПРИМЕР ДАННЫХ ДЛЯ КОНКРЕТНОГО СОТРУДНИКА:")
    print("-" * 50)
    
    employee_sample_query = """
    SELECT TOP 10 *
    FROM dm.v_penalty_summary
    WHERE fio IS NOT NULL AND fio != ''
    ORDER BY date_key DESC
    """
    
    sample_result = execute_query_cached(employee_sample_query)
    if sample_result:
        print("  Примеры записей:")
        for i, row in enumerate(sample_result[:3]):  # Показываем первые 3
            print(f"\n    Запись {i+1}:")
            if hasattr(row, '__getitem__'):
                for j, value in enumerate(row):
                    if columns_result and j < len(columns_result):
                        col_name = columns_result[j][0] if hasattr(columns_result[j], '__getitem__') else columns_result[j].COLUMN_NAME
                    else:
                        col_name = f"Колонка {j}"
                    print(f"      {col_name}: {value}")
    
    # Проверим, есть ли другие таблицы, связанные со штрафами
    print("\n3. ДРУГИЕ ТАБЛИЦЫ СО ШТРАФАМИ:")
    print("-" * 50)
    
    tables_query = """
    SELECT TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'dm' AND TABLE_NAME LIKE '%fine%' OR TABLE_NAME LIKE '%penalty%'
    """
    
    tables_result = execute_query_cached(tables_query)
    if tables_result:
        print("  Найденные таблицы:")
        for table in tables_result:
            print(f"    - {table[0]}")


if __name__ == "__main__":
    check_fines_table_structure()