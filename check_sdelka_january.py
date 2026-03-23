# -*- coding: utf-8 -*-
"""
Скрипт для проверки данных расчета сделки за январь 2026
Сравнение данных из БД с файлом Копия Сделка0101.csv
"""

import pyodbc
import pandas as pd
from datetime import datetime
import re

# Подключение к БД
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
    """Выполнение SQL запроса и возврат DataFrame"""
    try:
        conn = get_connection()
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Ошибка запроса: {e}")
        return pd.DataFrame()

print("=" * 80)
print("ПРОВЕРКА ДАННЫХ СДЕЛКИ ЗА ЯНВАРЬ 2026 (01.01.2026-31.01.2026)")
print("=" * 80)

# ============================================================================
# 1. ЗАГРУЗКА ФАЙЛА КОПИЯ СДЕЛКА0101.CSV
# ============================================================================
print("\n" + "=" * 80)
print("1. ЗАГРУЗКА ФАЙЛА КОПИЯ СДЕЛКА0101.CSV")
print("=" * 80)

try:
    # Пробуем разные кодировки
    for encoding in ['utf-8', 'cp1251', 'utf-8-sig']:
        try:
            df_csv = pd.read_csv(
                'Скрипты операций и суммы сделки/Копия Сделка0101.csv',
                sep=';',
                encoding=encoding
            )
            print(f"\n[OK] Загружен файл: {len(df_csv)} строк, кодировка: {encoding}")
            break
        except UnicodeDecodeError:
            continue
    else:
        # Если не получилось, пробуем без указания кодировки
        df_csv = pd.read_csv(
            'Скрипты операций и суммы сделки/Копия Сделка0101.csv',
            sep=';'
        )
        print(f"\n[WARN] Загружен файл с кодировкой по умолчанию: {len(df_csv)} строк")
    
    print(f"\n[INFO] Столбцы файла (первые 20): {list(df_csv.columns)[:20]}")
    print(f"[INFO] Количество столбцов: {len(df_csv.columns)}")
    
    # Определяем столбцы с операциями (числовые)
    numeric_cols = df_csv.select_dtypes(include=['float64', 'int64']).columns.tolist()
    print(f"[INFO] Числовые столбцы: {len(numeric_cols)}")
    
except Exception as e:
    print(f"\n[ERROR] Не удалось загрузить CSV: {e}")
    df_csv = pd.DataFrame()

# ============================================================================
# 2. ПРОВЕРКА ДАННЫХ ИЗ БД ЗА ЯНВАРЬ 2026
# ============================================================================
print("\n" + "=" * 80)
print("2. ПРОВЕРКА ДАННЫХ ИЗ БД ЗА ЯНВАРЬ 2026")
print("=" * 80)

# Проверяем период данных в БД
query = """
SELECT
    MIN(date_key) as min_date,
    MAX(date_key) as max_date,
    COUNT(DISTINCT date_key) as total_days
FROM dwh.fact_operation
"""
df = execute_query(query)
if not df.empty:
    print(f"\n[INFO] Период данных в БД: {df['min_date'].iloc[0]} - {df['max_date'].iloc[0]}")
    print(f"[INFO] Всего дней: {df['total_days'].iloc[0]}")

# ============================================================================
# 3. СУММА СДЕЛКИ ПО СОТРУДНИКАМ (ЯНВАРЬ 2026)
# ============================================================================
print("\n" + "=" * 80)
print("3. СУММА СДЕЛКИ ПО СОТРУДНИКАМ (ЯНВАРЬ 2026)")
print("=" * 80)

query = """
SELECT
    e.user_name,
    e.fio,
    COUNT(*) as total_operations,
    SUM(f.price_per_op) as total_summa
FROM dwh.fact_operation f
JOIN dm.dim_employee e ON f.employee_id = e.employee_id
WHERE f.date_key BETWEEN '2026-01-01' AND '2026-01-31'
GROUP BY e.user_name, e.fio
ORDER BY total_summa DESC
"""
df_bd = execute_query(query)
if not df_bd.empty:
    print(f"\n[INFO] Всего сотрудников в БД: {len(df_bd)}")
    print("\nТоп-20 сотрудников:")
    print(df_bd.head(20).to_string(index=False))

# ============================================================================
# 4. СРАВНЕНИЕ СУММЫ СДЕЛКИ С ФАЙЛОМ
# ============================================================================
print("\n" + "=" * 80)
print("4. СРАВНЕНИЕ СУММЫ СДЕЛКИ С ФАЙЛОМ КОПИЯ СДЕЛКА0101.CSV")
print("=" * 80)

if not df_csv.empty and len(df_csv) > 0:
    # Определяем столбец с суммой сделки (Мотивация)
    summa_col = None
    for col in df_csv.columns:
        if 'Мотивация' in col or 'сумма' in col.lower() or 'Сделка' in col:
            summa_col = col
            break
    
    # Если не нашли, пробуем последние столбцы
    if summa_col is None:
        # Ищем столбец с числами в конце
        for col in reversed(df_csv.columns):
            if df_csv[col].dtype in ['float64', 'int64']:
                # Проверяем, содержит ли столбец большие числа (суммы)
                if df_csv[col].max() > 1000:
                    summa_col = col
                    break
    
    if summa_col:
        print(f"\n[INFO] Столбец с суммой сделки: '{summa_col}'")
        
        # Создаем DataFrame для сравнения
        df_csv_compare = df_csv[['User name', summa_col]].copy()
        df_csv_compare.columns = ['user_name', 'summa_csv']
        df_csv_compare['user_name'] = df_csv_compare['user_name'].astype(str).str.strip()
        df_csv_compare['summa_csv'] = pd.to_numeric(df_csv_compare['summa_csv'], errors='coerce')
        df_csv_compare = df_csv_compare.dropna(subset=['summa_csv'])
        
        print(f"[INFO] Строк в CSV с суммой: {len(df_csv_compare)}")
        
        # Объединяем с БД
        df_bd['user_name'] = df_bd['user_name'].astype(str).str.strip()
        df_compare = pd.merge(df_bd, df_csv_compare, on='user_name', how='outer')
        
        # Считаем разницу
        df_compare['raznica'] = df_compare['total_summa'] - df_compare['summa_csv']
        df_compare['raznica_pct'] = (df_compare['raznica'] / df_compare['summa_csv'].replace(0, 1) * 100).round(2)
        
        # Сортируем по наибольшей разнице
        df_compare = df_compare.sort_values('raznica_pct', key=abs, ascending=False)
        
        print("\n[INFO] Сравнение с файлом (топ-30 по разнице):")
        print(df_compare[['user_name', 'fio', 'total_summa', 'summa_csv', 'raznica', 'raznica_pct']].head(30).to_string(index=False))
        
        # Сохраняем
        df_compare.to_csv('диагностика_сравнение_январь_2026.csv', index=False, encoding='utf-8-sig')
        print("\n[INFO] Сохранено в: диагностика_сравнение_январь_2026.csv")
        
        # Статистика расхождений
        print("\n" + "=" * 80)
        print("СТАТИСТИКА РАСХОЖДЕНИЙ")
        print("=" * 80)
        total_employees = len(df_compare)
        employees_with_diff = len(df_compare[df_compare['raznica'].abs() > 0.01])
        employees_with_big_diff = len(df_compare[df_compare['raznica'].abs() > 100])
        print(f"Всего сотрудников: {total_employees}")
        print(f"Сотрудников с расхождениями (>0.01): {employees_with_diff} ({employees_with_diff/total_employees*100:.1f}%)")
        print(f"Сотрудников с большими расхождениями (>100): {employees_with_big_diff}")
        print(f"Суммарная разница: {df_compare['raznica'].sum():.2f}")
    else:
        print("\n[WARN] Не удалось найти столбец с суммой сделки в CSV")

# ============================================================================
# 5. КОЛИЧЕСТВО ОПЕРАЦИЙ ПО ТИПАМ (ЯНВАРЬ 2026)
# ============================================================================
print("\n" + "=" * 80)
print("5. КОЛИЧЕСТВО ОПЕРАЦИЙ ПО ТИПАМ (ЯНВАРЬ 2026)")
print("=" * 80)

query = """
SELECT
    wt.work_type_name,
    COUNT(*) as kol_operatsiy,
    SUM(f.price_per_op) as total_summa
FROM dwh.fact_operation f
JOIN dm.dim_work_type wt ON f.work_type_id = wt.work_type_id
WHERE f.date_key BETWEEN '2026-01-01' AND '2026-01-31'
GROUP BY wt.work_type_name
ORDER BY kol_operatsiy DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] Операции из БД (Январь 2026):")
    print(df.to_string(index=False))
    df.to_csv('диагностика_операции_январь_2026.csv', index=False, encoding='utf-8-sig')
    print("\n[INFO] Сохранено в: диагностика_операции_январь_2026.csv")

# ============================================================================
# 6. ПРОВЕРКА ГРУЗЧИКОВ
# ============================================================================
print("\n" + "=" * 80)
print("6. ПРОВЕРКА ГРУЗЧИКОВ")
print("=" * 80)

query = """
SELECT
    user_name,
    SUM([Разгрузка механизмами]) as total_meh,
    SUM([Разгрузка ручная]) as total_ruk,
    SUM([Загрузка механизмами]) as total_load_meh,
    SUM([Загрузка ручная]) as total_load_ruk
FROM raw_.gruz_operations
GROUP BY user_name
ORDER BY total_meh DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] Грузчики - объемы операций:")
    print(df.to_string(index=False))

# ============================================================================
# 7. ДЕТАЛЬНОЕ СРАВНЕНИЕ ПО СТОЛБЦАМ CSV
# ============================================================================
print("\n" + "=" * 80)
print("7. АНАЛИЗ СТРУКТУРЫ ФАЙЛА CSV")
print("=" * 80)

if not df_csv.empty:
    # Выводим первые несколько строк для анализа
    print("\n[INFO] Первые 3 строки файла:")
    for idx, row in df_csv.head(3).iterrows():
        print(f"\nСтрока {idx}:")
        for col_idx, (col, val) in enumerate(row.items()):
            if col_idx < 15:  # Первые 15 столбцов
                print(f"  {col}: {val}")
    
    # Ищем столбцы с названиями операций
    print("\n[INFO] Поиск столбцов с операциями:")
    operation_keywords = ['ZX', 'ME', 'NG', 'KC', 'WH2', 'KSP', 'Приемка', 'Отбор', 'Погрузка', 'Разгрузка', 'Загрузка']
    for col in df_csv.columns:
        for keyword in operation_keywords:
            if keyword in str(col):
                print(f"  Найден столбец с '{keyword}': {col}")
                break

print("\n" + "=" * 80)
print("ПРОВЕРКА ЗАВЕРШЕНА")
print("=" * 80)
