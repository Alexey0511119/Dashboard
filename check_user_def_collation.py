# -*- coding: utf-8 -*-
"""
Проверка коллации user_def колонок
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
print("ПРОВЕРКА КОЛЛАЦИИ USER_DEF КОЛОНОК")
print("=" * 80)

# Проверяем коллацию в labor_management
query = """
SELECT COLUMN_NAME, COLLATION_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'labor_management'
AND COLUMN_NAME IN ('user_def1', 'user_def2', 'user_def5', 'user_def6')
"""
df = execute_query(query)
print("\n[INFO] labor_management user_def коллация:")
if not df.empty:
    print(df.to_string(index=False))

# Проверяем коллацию в UPLOAD_RECEIPT_HEADER
query = """
SELECT COLUMN_NAME, COLLATION_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'UPLOAD_RECEIPT_HEADER'
AND COLUMN_NAME IN ('user_def1', 'user_def2', 'user_def5', 'user_def6')
"""
df = execute_query(query)
print("\n[INFO] UPLOAD_RECEIPT_HEADER user_def коллация:")
if not df.empty:
    print(df.to_string(index=False))

# Проверяем коллацию в UPLOAD_ORDER_HEADER
query = """
SELECT COLUMN_NAME, COLLATION_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'UPLOAD_ORDER_HEADER'
AND COLUMN_NAME IN ('user_def1', 'user_def2', 'user_def5', 'user_def6')
"""
df = execute_query(query)
print("\n[INFO] UPLOAD_ORDER_HEADER user_def коллация:")
if not df.empty:
    print(df.to_string(index=False))

print("\n" + "=" * 80)
print("ПРОВЕРКА ЗАВЕРШЕНА")
print("=" * 80)
