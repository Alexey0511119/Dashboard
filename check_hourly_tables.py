#!/usr/bin/env python3
"""
Проверка структуры таблиц dm.v_hourly_errors и dm.v_hourly_delays
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.mssql_client import execute_query_cached

def check_hourly_tables():
    """Проверка структуры таблиц dm.v_hourly_errors и dm.v_hourly_delays"""
    
    print("=== ПРОВЕРКА СТРУКТУРЫ ТАБЛИЦ DM.V_HOURLY_ERRORS И DM.V_HOURLY_DELAYS ===\n")
    
    # Проверяем существование таблиц
    tables_to_check = ['v_hourly_errors', 'v_hourly_delays']
    
    for table_name in tables_to_check:
        print(f"1. ПРОВЕРКА ТАБЛИЦЫ {table_name}:")
        print("-" * 40)
        
        # Проверяем существование
        check_query = f"""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.VIEWS
        WHERE TABLE_SCHEMA = 'dm' AND TABLE_NAME = '{table_name}'
        """
        
        check_result = execute_query_cached(check_query)
        if check_result:
            print(f"  EXISTS View dm.{table_name} exists")
        else:
            print(f"  NOT FOUND View dm.{table_name} not found")
            continue
        
        # Получаем структуру
        columns_query = f"""
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dm' AND TABLE_NAME = '{table_name}'
        ORDER BY ORDINAL_POSITION
        """
        
        columns_result = execute_query_cached(columns_query)
        if columns_result:
            print("  Columns:")
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
        count_query = f"SELECT COUNT(*) as total FROM dm.{table_name}"
        count_result = execute_query_cached(count_query)
        if count_result:
            total_count = count_result[0][0] if count_result[0] else 0
            print(f"  Total records: {total_count}")
        
        # Получаем примеры данных
        print("  Sample data:")
        sample_query = f"""
        SELECT TOP 5 * FROM dm.{table_name}
        """
        
        sample_result = execute_query_cached(sample_query)
        if sample_result:
            for i, row in enumerate(sample_result, 1):
                print(f"\n    Record {i}:")
                if hasattr(row, '__getitem__'):
                    for j, value in enumerate(row):
                        if columns_result and j < len(columns_result):
                            col_name = columns_result[j][0] if hasattr(columns_result[j], '__getitem__') else columns_result[j].COLUMN_NAME
                        else:
                            col_name = f"Column {j}"
                        print(f"      {col_name}: {value}")
        
        print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    check_hourly_tables()