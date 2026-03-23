# -*- coding: utf-8 -*-
"""
Проверка структур таблиц
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
print("ПРОВЕРКА СТРУКТУР ТАБЛИЦ")
print("=" * 80)

# Проверяем labor_management
query = """
SELECT COLUMN_NAME 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'labor_management'
AND COLUMN_NAME IN ('USER_NAME', 'COMPLETED_BY_USER', 'USER_STAMP')
ORDER BY COLUMN_NAME
"""
df = execute_query(query)
print("\n[INFO] labor_management - колонки пользователя:")
if not df.empty:
    print(df.to_string(index=False))
else:
    print("Не найдены")

# Проверяем WORK_INSTRUCTION_VIEW2
query = """
SELECT COLUMN_NAME 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'WORK_INSTRUCTION_VIEW2'
AND COLUMN_NAME IN ('USER_NAME', 'COMPLETED_BY_USER', 'USER_STAMP', 'USER_ASSIGNED')
ORDER BY COLUMN_NAME
"""
df = execute_query(query)
print("\n[INFO] WORK_INSTRUCTION_VIEW2 - колонки пользователя:")
if not df.empty:
    print(df.to_string(index=False))
else:
    print("Не найдены")

# Проверяем TRANSACTION_HISTORY
query = """
SELECT COLUMN_NAME 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'TRANSACTION_HISTORY'
AND COLUMN_NAME IN ('USER_NAME', 'USER_STAMP')
ORDER BY COLUMN_NAME
"""
df = execute_query(query)
print("\n[INFO] TRANSACTION_HISTORY - колонки пользователя:")
if not df.empty:
    print(df.to_string(index=False))

print("\n" + "=" * 80)
print("ПРОВЕРКА ЗАВЕРШЕНА")
print("=" * 80)
