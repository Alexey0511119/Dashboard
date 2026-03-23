# -*- coding: utf-8 -*-
"""
Проверка выполнения скрипта передел_ИСПРАВЛЕННЫЙ.sql
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
print("ПРОВЕРКА ВЫПОЛНЕНИЯ СКРИПТА")
print("=" * 80)

# Проверяем gruz_operations
query = """
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT user_name) as users,
    SUM([Разгрузка механизмами]) as total_meh,
    SUM([Загрузка механизмами]) as total_load_meh
FROM raw_.gruz_operations
WHERE date_key BETWEEN '2026-01-01' AND '2026-01-31'
"""
df = execute_query(query)
print("\n[INFO] raw_.gruz_operations за Январь 2026:")
if not df.empty:
    print(df.to_string(index=False))
else:
    print("[ERROR] Таблица пуста!")

# Проверяем fact_operation с GRUZ
query = """
SELECT 
    source_system,
    COUNT(*) as kol,
    SUM(price_per_op) as total_sum
FROM dwh.fact_operation
WHERE date_key BETWEEN '2026-01-01' AND '2026-01-31'
GROUP BY source_system
"""
df = execute_query(query)
print("\n[INFO] fact_operation по source_system (Январь):")
if not df.empty:
    print(df.to_string(index=False))
else:
    print("[ERROR] Пусто!")

# Проверяем sdelka_price
query = """
SELECT work_type, price 
FROM raw_.sdelka_price 
WHERE work_type IN (N'Погрузка EU-паллет', N'Погрузка NG', N'Отбор KSP', N'Ревизия по событию')
"""
df = execute_query(query)
print("\n[INFO] sdelka_price (проверка цен):")
if not df.empty:
    print(df.to_string(index=False))
else:
    print("[WARN] Этих операций нет в sdelka_price!")

# Проверяем dim_work_type
query = """
SELECT work_type_name, work_category 
FROM dm.dim_work_type 
WHERE work_type_name IN (N'Погрузка EU-паллет', N'Погрузка NG', N'Отбор KSP')
"""
df = execute_query(query)
print("\n[INFO] dim_work_type:")
if not df.empty:
    print(df.to_string(index=False))
else:
    print("[WARN] Этих операций нет в dim_work_type!")

# Проверяем операции с нулевой ценой
query = """
SELECT TOP 20
    wt.work_type_name,
    COUNT(*) as kol,
    AVG(f.price_per_op) as avg_price,
    SUM(f.price_per_op) as total_sum
FROM dwh.fact_operation f
JOIN dm.dim_work_type wt ON f.work_type_id = wt.work_type_id
WHERE f.date_key BETWEEN '2026-01-01' AND '2026-01-31'
    AND f.price_per_op = 0
GROUP BY wt.work_type_name
ORDER BY kol DESC
"""
df = execute_query(query)
print("\n[WARN] Операции с нулевой ценой (Январь):")
if not df.empty:
    print(df.to_string(index=False))
else:
    print("[OK] Нет операций с нулевой ценой")

print("\n" + "=" * 80)
print("ПРОВЕРКА ЗАВЕРШЕНА")
print("=" * 80)
