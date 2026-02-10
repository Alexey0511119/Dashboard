#!/usr/bin/env python3
"""
Проверка структуры и данных в представлении dm.v_performance_detailed
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.mssql_client import execute_query_cached

def check_performance_detailed_view():
    """Проверка структуры и данных в представлении dm.v_performance_detailed"""
    
    print("=== ПРОВЕРКА ПРЕДСТАВЛЕНИЯ DM.V_PERFORMANCE_DETAILED ===\n")
    
    # Проверим структуру представления
    print("1. СТРУКТУРА ПРЕДСТАВЛЕНИЯ:")
    print("-" * 50)
    
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
    
    print(f"\n2. ПРИМЕР ДАННЫХ:")
    print("-" * 50)
    
    # Получим пример данных для одного сотрудника за короткий период
    sample_query = """
    SELECT TOP 10 *
    FROM dm.v_performance_detailed
    WHERE date_key BETWEEN '2026-01-27' AND '2026-02-03'
    ORDER BY Сотрудник, date_key
    """
    
    sample_result = execute_query_cached(sample_query)
    if sample_result:
        print(f"  Найдено {len(sample_result)} записей")
        print("  Примеры данных:")
        
        # Получим названия колонок для отображения
        if columns_result:
            col_names = [col[0] if hasattr(col, '__getitem__') else col.COLUMN_NAME for col in columns_result]
        else:
            # Если не удалось получить из INFORMATION_SCHEMA, используем известные колонки
            col_names = ['Сотрудник', 'date_key', 'Общее_кол_операций', 'Ср_время_на_операцию', 
                        'Заработок', 'Операций_в_час', 'Время_работы', 'Время_первой_операции', 
                        'Обычные_операции', 'Приемка']
        
        for i, row in enumerate(sample_result):
            print(f"\n    Запись {i+1}:")
            for j, value in enumerate(row):
                if j < len(col_names):
                    col_name = col_names[j]
                else:
                    col_name = f"Колонка_{j}"
                print(f"      {col_name}: {value}")
    
    print(f"\n3. АНАЛИЗ ПРОБЛЕМЫ:")
    print("-" * 50)
    print("  Текущий запрос использует:")
    print("  - SUM(Общее_кол_операций) - правильно, суммирует операции")
    print("  - AVG(Ср_время_на_операцию) - НЕПРАВИЛЬНО, нужно пересчитать как общее время / общее кол-во операций")
    print("  - SUM(Заработок) - правильно, суммирует заработок")
    print("  - AVG(Операций_в_час) - НЕПРАВИЛЬНО, нужно пересчитать как общее кол-во операций / общее рабочее время")
    print("  - MAX(Время_работы) - НЕПРАВИЛЬНО, нужно суммировать время работы")
    print("  - MIN(Время_первой_операции) - может быть корректно для определения начала работы")
    print("  - SUM(Обычные_операции) - правильно")
    print("  - SUM(Приемка) - правильно")
    
    print(f"\n4. РЕКОМЕНДАЦИИ:")
    print("-" * 50)
    print("  Для корректного расчета нужно:")
    print("  - 'Ср_время_на_операцию': (сумма общего времени работы) / (сумма операций)")
    print("  - 'Операций_в_час': (сумма операций) / (сумма рабочего времени в часах)")
    print("  - 'Время_работы': суммировать время работы за все дни периода")
    print("  - 'Время_первой_операции': брать минимальное значение")
    
    # Проверим, есть ли колонки с временем в секундах для корректного расчета
    print(f"\n5. ПРОВЕРКА НАЛИЧИЯ КОЛОНКИ С ВРЕМЕНЕМ:")
    print("-" * 50)
    
    time_related_cols = [col for col in col_names if 'время' in col.lower() or 'duration' in col.lower() or 'seconds' in col.lower() or 'minutes' in col.lower()]
    if time_related_cols:
        print(f"  Найдены потенциально связанные с временем колонки: {time_related_cols}")
    else:
        print(f"  Не найдено колонок, явно связанных со временем выполнения")


if __name__ == "__main__":
    check_performance_detailed_view()