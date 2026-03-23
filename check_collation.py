# -*- coding: utf-8 -*-
"""
Проверка коллации колонок
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
print("ПРОВЕРКА КОЛЛАЦИИ КОЛОНОК")
print("=" * 80)

# Проверяем коллацию в WORK_INSTRUCTION_VIEW2
query = """
SELECT COLUMN_NAME, COLLATION_NAME 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'WORK_INSTRUCTION_VIEW2'
AND COLUMN_NAME IN ('COMPLETED_BY_USER', 'USER_ASSIGNED', 'USER_STAMP', 'WORK_TYPE')
"""
df = execute_query(query)
print("\n[INFO] WORK_INSTRUCTION_VIEW2 коллация:")
if not df.empty:
    print(df.to_string(index=False))

# Проверяем коллацию в labor_management
query = """
SELECT COLUMN_NAME, COLLATION_NAME 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'labor_management'
AND COLUMN_NAME IN ('USER_NAME', 'USER_STAMP', 'activity_type', 'user_def1', 'user_def2')
"""
df = execute_query(query)
print("\n[INFO] labor_management коллация:")
if not df.empty:
    print(df.to_string(index=False))

# Проверяем коллацию в USER_CADR_EDIT
query = """
SELECT COLUMN_NAME, COLLATION_NAME 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'USER_CADR_EDIT'
AND COLUMN_NAME IN ('user_name', 'fio', 'smena')
"""
df = execute_query(query)
print("\n[INFO] USER_CADR_EDIT коллация:")
if not df.empty:
    print(df.to_string(index=False))

# Проверяем коллацию в sdelka_price
query = """
SELECT COLUMN_NAME, COLLATION_NAME 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'sdelka_price'
AND COLUMN_NAME IN ('work_type')
"""
df = execute_query(query)
print("\n[INFO] sdelka_price коллация:")
if not df.empty:
    print(df.to_string(index=False))

print("\n" + "=" * 80)
print("ПРОВЕРКА ЗАВЕРШЕНА")
print("=" * 80)
