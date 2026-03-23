# -*- coding: utf-8 -*-
"""
Проверка структуры WORK_INSTRUCTION_VIEW2
"""

import pyodbc
import pandas as pd

CONNECTION_STRING = (
    "DRIVER={SQL Server};"
    "SERVER=10.7.0.48,1433;"
    "DATABASE=olap2_fixed;"
    "UID=sa;"
    "PWD=Rdflhfn600;"
    "TrustServerCertificate=yes;"
)

def get_connection():
    return pyodbc.connect(CONNECTION_STRING, timeout=60)

def execute_query(query):
    try:
        conn = get_connection()
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Ошибка: {e}")
        return pd.DataFrame()

print("=" * 80)
print("СТРУКТУРА WORK_INSTRUCTION_VIEW2")
print("=" * 80)

query = """
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'WORK_INSTRUCTION_VIEW2'
ORDER BY ORDINAL_POSITION
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] Колонки WORK_INSTRUCTION_VIEW2:")
    print(df.to_string(index=False))
else:
    print("\n[ERROR] Не удалось получить структуру")

# Проверяем данные
query = """
SELECT TOP 5 * FROM raw_.WORK_INSTRUCTION_VIEW2
WHERE CONDITION = 'closed' AND INSTRUCTION_TYPE = 'Detail'
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] Пример данных:")
    print(df.to_string(index=False))

print("\n" + "=" * 80)
print("ПРОВЕРКА ЗАВЕРШЕНА")
print("=" * 80)
