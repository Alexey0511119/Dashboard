# -*- coding: utf-8 -*-
"""
Проверка структуры таблиц для грузчиков
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
print("ПРОВЕРКА ТАБЛИЦ ДЛЯ ГРУЗЧИКОВ")
print("=" * 80)

# Проверяем наличие таблиц
query = """
SELECT TABLE_NAME 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_NAME LIKE '%labor%'
ORDER BY TABLE_NAME
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] Таблицы с 'labor' в названии:")
    print(df.to_string(index=False))
else:
    print("\n[WARN] Таблицы с 'labor' не найдены")

# Проверяем labor_management
query = """
SELECT TOP 5 * FROM raw_.labor_management
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] labor_management (топ-5):")
    print(df.to_string(index=False))
else:
    print("\n[WARN] labor_management пуста")

# Проверяем структуру labor_management
query = """
SELECT COLUMN_NAME, DATA_TYPE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'labor_management'
ORDER BY ORDINAL_POSITION
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] Структура labor_management:")
    print(df.to_string(index=False))

# Проверяем данные для грузчиков за январь
query = """
SELECT 
    user_def1,
    user_def2,
    activity_type,
    COUNT(*) as kol,
    MIN(date_time_stamp) as min_date,
    MAX(date_time_stamp) as max_date
FROM raw_.labor_management
WHERE CAST(date_time_stamp AS DATE) BETWEEN '2026-01-01' AND '2026-01-31'
    AND activity_type IN (N'Разгрузка механизмами', N'Разгрузка ручная', N'Загрузка механизмами', N'Загрузка ручная', N'Сортировка товаров')
GROUP BY user_def1, user_def2, activity_type
ORDER BY kol DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] labor_management за январь (топ-20):")
    print(df.head(20).to_string(index=False))
    df.to_csv('диагностика_labor_management.csv', index=False, encoding='utf-8-sig')
    print("\n[INFO] Сохранено в: диагностика_labor_management.csv")

# Проверяем дублирование в fact_operation
print("\n" + "=" * 80)
print("ПРОВЕРКА ДУБЛИРОВАНИЯ В fact_operation")
print("=" * 80)

query = """
SELECT TOP 20
    e.fio,
    wt.work_type_name,
    f.date_key,
    f.reference_id,
    f.start_time,
    f.end_time,
    COUNT(*) as dup_count
FROM dwh.fact_operation f
JOIN dm.dim_employee e ON f.employee_id = e.employee_id
JOIN dm.dim_work_type wt ON f.work_type_id = wt.work_type_id
WHERE f.date_key = '2026-01-18'
    AND wt.work_type_name = 'Погрузка EU-паллет'
GROUP BY e.fio, wt.work_type_name, f.date_key, f.reference_id, f.start_time, f.end_time
HAVING COUNT(*) > 1
ORDER BY dup_count DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[WARN] Дублирование 2026-01-18 Погрузка EU-паллет:")
    print(df.to_string(index=False))
else:
    print("\n[OK] Дублирования не найдено на эту дату")

# Проверяем source_system
query = """
SELECT 
    source_system,
    COUNT(*) as kol,
    COUNT(DISTINCT date_key) as days
FROM dwh.fact_operation
WHERE date_key BETWEEN '2026-01-01' AND '2026-01-31'
GROUP BY source_system
ORDER BY kol DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] fact_operation по source_system (Январь):")
    print(df.to_string(index=False))

print("\n" + "=" * 80)
print("ПРОВЕРКА ЗАВЕРШЕНА")
print("=" * 80)
