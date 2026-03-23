# -*- coding: utf-8 -*-
"""
Сравнение данных из БД с файлом Копия Сделка0101.csv
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
print("СРАВНЕНИЕ ДАННЫХ С ФАЙЛОМ КОПИЯ СДЕЛКА0101")
print("=" * 80)

# Загружаем файл сравнения
try:
    df_csv = pd.read_csv(
        'Скрипты операций и суммы сделки/Копия Сделка0101.csv',
        sep=';',
        encoding='utf-8'
    )
    print(f"\n[INFO] Загружен файл Копия Сделка0101.csv: {len(df_csv)} строк")
except Exception as e:
    print(f"\n[WARN] Не удалось загрузить CSV: {e}")
    df_csv = pd.DataFrame()

# ============================================================================
# 1. ОБЩЕЕ КОЛИЧЕСТВО ОПЕРАЦИЙ ПО ТИПАМ
# ============================================================================
print("\n" + "=" * 80)
print("1. ОБЩЕЕ КОЛИЧЕСТВО ОПЕРАЦИЙ ПО ТИПАМ (fact_operation)")
print("=" * 80)

query = """
SELECT 
    wt.work_type_name,
    COUNT(*) as kol_iz_bd
FROM dwh.fact_operation f
JOIN dm.dim_work_type wt ON f.work_type_id = wt.work_type_id
GROUP BY wt.work_type_name
ORDER BY kol_iz_bd DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] Операции из БД:")
    print(df.to_string(index=False))

# ============================================================================
# 2. СУММА СДЕЛКИ ПО СОТРУДНИКАМ
# ============================================================================
print("\n" + "=" * 80)
print("2. СУММА СДЕЛКИ ПО СОТРУДНИКАМ")
print("=" * 80)

query = """
SELECT 
    e.user_name,
    e.fio,
    COUNT(*) as total_operations,
    SUM(f.price_per_op) as total_summa
FROM dwh.fact_operation f
JOIN dm.dim_employee e ON f.employee_id = e.employee_id
GROUP BY e.user_name, e.fio
ORDER BY total_summa DESC
"""
df_bd = execute_query(query)
if not df_bd.empty:
    print("\n[INFO] Сумма сделки из БД (топ-20):")
    print(df_bd.head(20).to_string(index=False))

# Сравниваем с CSV
if not df_csv.empty and 'User name' in df_csv.columns and 'Мотивация' in df_csv.columns:
    df_csv_compare = df_csv[['User name', 'Мотивация']].dropna()
    df_csv_compare.columns = ['user_name', 'summa_csv']
    df_csv_compare['user_name'] = df_csv_compare['user_name'].astype(str).str.strip()
    df_csv_compare['summa_csv'] = pd.to_numeric(df_csv_compare['summa_csv'], errors='coerce')
    
    # Объединяем с БД
    df_bd['user_name'] = df_bd['user_name'].astype(str).str.strip()
    df_compare = pd.merge(df_bd, df_csv_compare, on='user_name', how='outer')
    
    # Считаем разницу
    df_compare['raznica'] = df_compare['total_summa'] - df_compare['summa_csv']
    df_compare['raznica_pct'] = (df_compare['raznica'] / df_compare['summa_csv'] * 100).round(2)
    
    # Сортируем по наибольшей разнице
    df_compare = df_compare.dropna(subset=['summa_csv'])
    df_compare = df_compare.sort_values('raznica_pct', key=abs, ascending=False)
    
    print("\n[INFO] Сравнение с файлом Копия Сделка0101.csv:")
    print(df_compare[['user_name', 'fio', 'total_summa', 'summa_csv', 'raznica', 'raznica_pct']].head(30).to_string(index=False))
    
    # Сохраняем
    df_compare.to_csv('диагностика_сравнение_с_файлом.csv', index=False, encoding='utf-8-sig')
    print("\n[INFO] Сохранено в: диагностика_сравнение_с_файлом.csv")

# ============================================================================
# 3. ГРУЗЧИКИ - СРАВНЕНИЕ
# ============================================================================
print("\n" + "=" * 80)
print("3. ГРУЗЧИКИ - СРАВНЕНИЕ")
print("=" * 80)

query = """
SELECT 
    user_name,
    SUM([Разгрузка механизмами]) as meh,
    SUM([Разгрузка ручная]) as ruk,
    SUM([Загрузка механизмами]) as load_meh,
    SUM([Загрузка ручная]) as load_ruk
FROM raw_.gruz_operations
GROUP BY user_name
ORDER BY meh DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] Грузчики из БД:")
    print(df.to_string(index=False))

# ============================================================================
# 4. ОПЕРАЦИИ ПО СОТРУДНИКАМ И ТИПАМ
# ============================================================================
print("\n" + "=" * 80)
print("4. ОПЕРАЦИИ ПО СОТРУДНИКАМ И ТИПАМ (ВЫБОРОЧНО)")
print("=" * 80)

query = """
SELECT TOP 50
    e.user_name,
    wt.work_type_name,
    COUNT(*) as kol
FROM dwh.fact_operation f
JOIN dm.dim_employee e ON f.employee_id = e.employee_id
JOIN dm.dim_work_type wt ON f.work_type_id = wt.work_type_id
GROUP BY e.user_name, wt.work_type_name
ORDER BY kol DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] Топ-50 операций:")
    print(df.to_string(index=False))

print("\n" + "=" * 80)
print("СРАВНЕНИЕ ЗАВЕРШЕНО")
print("=" * 80)
