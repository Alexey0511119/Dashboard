# -*- coding: utf-8 -*-
"""
Диагностический скрипт для сравнения данных сделки
Сравнивает данные из БД с файлом Копия Сделка0101.csv
"""

import pyodbc
import pandas as pd
from datetime import datetime
import os
import sys

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
        print(f"Запрос: {query[:200]}...")
        return pd.DataFrame()

print("=" * 80)
print("ДИАГНОСТИКА РАСЧЕТА СДЕЛКИ")
print("=" * 80)

# ============================================================================
# 1. ПРОВЕРКА ИСХОДНЫХ ДАННЫХ
# ============================================================================
print("\n" + "=" * 80)
print("1. ПРОВЕРКА ИСХОДНЫХ ДАННЫХ")
print("=" * 80)

query = """
SELECT 
    COUNT(*) as total_operations,
    COUNT(DISTINCT date_key) as total_days,
    MIN(date_key) as min_date,
    MAX(date_key) as max_date
FROM dwh.fact_operation
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] fact_operation:")
    print(f"   Всего операций: {df['total_operations'].iloc[0]:,}")
    print(f"   Дней данных: {df['total_days'].iloc[0]}")
    print(f"   Период: {df['min_date'].iloc[0]} - {df['max_date'].iloc[0]}")
else:
    print("\n[ERROR] fact_operation пуста или не существует!")

# ============================================================================
# 2. ОБЩЕЕ КОЛИЧЕСТВО ОПЕРАЦИЙ ПО ТИПАМ РАБОТ
# ============================================================================
print("\n" + "=" * 80)
print("2. КОЛИЧЕСТВО ОПЕРАЦИЙ ПО ТИПАМ РАБОТ")
print("=" * 80)

query = """
SELECT 
    wt.work_type_name,
    COUNT(*) as kol_operatsiy
FROM dwh.fact_operation f
JOIN dm.dim_work_type wt ON f.work_type_id = wt.work_type_id
GROUP BY wt.work_type_name
ORDER BY kol_operatsiy DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] Операции из БД (fact_operation):")
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', None)
    print(df.to_string(index=False))
    df.to_csv('диагностика_операции_из_БД.csv', index=False, encoding='utf-8-sig')
    print("\n[INFO] Сохранено в: диагностика_операции_из_БД.csv")

# ============================================================================
# 3. КОЛИЧЕСТВО ОПЕРАЦИЙ ПО СОТРУДНИКАМ И ТИПАМ (ЯНВАРЬ)
# ============================================================================
print("\n" + "=" * 80)
print("3. ОПЕРАЦИИ ПО СОТРУДНИКАМ И ТИПАМ (ЯНВАРЬ 2026)")
print("=" * 80)

query = """
SELECT TOP 100
    e.fio,
    wt.work_type_name,
    COUNT(*) as kol
FROM dwh.fact_operation f
JOIN dm.dim_employee e ON f.employee_id = e.employee_id
JOIN dm.dim_work_type wt ON f.work_type_id = wt.work_type_id
WHERE f.date_key BETWEEN '2026-01-01' AND '2026-01-31'
GROUP BY e.fio, wt.work_type_name
ORDER BY kol DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] Топ-100 операций сотрудников (Январь 2026):")
    print(df.to_string(index=False))
    df.to_csv('диагностика_операции_сотрудники.csv', index=False, encoding='utf-8-sig')
    print("\n[INFO] Сохранено в: диагностика_операции_сотрудники.csv")

# ============================================================================
# 4. СУММА СДЕЛКИ ПО СОТРУДНИКАМ (ЯНВАРЬ)
# ============================================================================
print("\n" + "=" * 80)
print("4. СУММА СДЕЛКИ ПО СОТРУДНИКАМ (ЯНВАРЬ 2026)")
print("=" * 80)

query = """
SELECT 
    e.fio,
    COUNT(*) as total_operations,
    SUM(f.price_per_op) as total_summa
FROM dwh.fact_operation f
JOIN dm.dim_employee e ON f.employee_id = e.employee_id
WHERE f.date_key BETWEEN '2026-01-01' AND '2026-01-31'
GROUP BY e.fio
ORDER BY total_summa DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] Сумма сделки по сотрудникам (Январь 2026):")
    print(df.to_string(index=False))
    df.to_csv('диагностика_сумма_сделки.csv', index=False, encoding='utf-8-sig')
    print("\n[INFO] Сохранено в: диагностика_сумма_сделки.csv")

# ============================================================================
# 5. ПРОВЕРКА ПРИЕМКИ
# ============================================================================
print("\n" + "=" * 80)
print("5. ПРОВЕРКА ПРИЕМКИ")
print("=" * 80)

query = """
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT user_name) as total_users,
    COUNT(DISTINCT date_key) as total_days
FROM dwh.transaction_events
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] dwh.transaction_events:")
    print(f"   Всего записей: {df['total_records'].iloc[0]:,}")
    print(f"   Сотрудников: {df['total_users'].iloc[0]}")
    print(f"   Дней: {df['total_days'].iloc[0]}")

query = """
SELECT 
    e.fio,
    COUNT(*) as priemka_count
FROM dwh.fact_operation f
JOIN dm.dim_employee e ON f.employee_id = e.employee_id
WHERE f.reference_type = 'Приемка' OR f.work_type_id IN (
    SELECT work_type_id FROM dm.dim_work_type WHERE work_type_name = 'Приемка'
)
GROUP BY e.fio
ORDER BY priemka_count DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] Приемка по сотрудникам:")
    print(df.to_string(index=False))
    df.to_csv('диагностика_приемка.csv', index=False, encoding='utf-8-sig')
    print("\n[INFO] Сохранено в: диагностика_приемка.csv")

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
    SUM([Загрузка ручная]) as total_load_ruk,
    SUM([Сортировка товаров приемка]) as total_sort_priem,
    SUM([Сортировка товаров отгрузка]) as total_sort_otgr
FROM raw_.gruz_operations
GROUP BY user_name
ORDER BY total_meh DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] Грузчики - объемы операций:")
    print(df.to_string(index=False))
    df.to_csv('диагностика_грузчики.csv', index=False, encoding='utf-8-sig')
    print("\n[INFO] Сохранено в: диагностика_грузчики.csv")

# ============================================================================
# 7. ДЕТАЛЬНАЯ ПРОВЕРКА ЗА ЯНВАРЬ
# ============================================================================
print("\n" + "=" * 80)
print("7. ДЕТАЛЬНАЯ СТАТИСТИКА ЗА ЯНВАРЬ 2026")
print("=" * 80)

query = """
SELECT 
    wt.work_type_name,
    COUNT(*) as kol,
    COUNT(DISTINCT f.date_key) as days_with_work,
    COUNT(DISTINCT f.employee_id) as employees_count,
    AVG(f.price_per_op) as avg_price,
    SUM(f.price_per_op) as total_sum
FROM dwh.fact_operation f
JOIN dm.dim_work_type wt ON f.work_type_id = wt.work_type_id
WHERE f.date_key BETWEEN '2026-01-01' AND '2026-01-31'
GROUP BY wt.work_type_name
ORDER BY kol DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] Январь 2026 - детально по операциям:")
    print(df.to_string(index=False))
    df.to_csv('диагностика_январь_детально.csv', index=False, encoding='utf-8-sig')
    print("\n[INFO] Сохранено в: диагностика_январь_детально.csv")

# ============================================================================
# 8. ПРОВЕРКА НА ДУБЛИРОВАНИЕ
# ============================================================================
print("\n" + "=" * 80)
print("8. ПРОВЕРКА НА ДУБЛИРОВАНИЕ ОПЕРАЦИЙ")
print("=" * 80)

query = """
SELECT TOP 20
    e.fio,
    wt.work_type_name,
    f.date_key,
    COUNT(*) as duplicate_count
FROM dwh.fact_operation f
JOIN dm.dim_employee e ON f.employee_id = e.employee_id
JOIN dm.dim_work_type wt ON f.work_type_id = wt.work_type_id
WHERE f.date_key BETWEEN '2026-01-01' AND '2026-01-31'
GROUP BY e.fio, wt.work_type_name, f.date_key
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[WARN] Найдены дубликаты операций:")
    print(df.to_string(index=False))
else:
    print("\n[OK] Дубликатов не найдено")

# ============================================================================
# 9. ПРОВЕРКА ОРИГИНАЛЬНЫХ ТАБЛИЦ WMS
# ============================================================================
print("\n" + "=" * 80)
print("9. ПРОВЕРКА ОРИГИНАЛЬНЫХ ТАБЛИЦ WMS")
print("=" * 80)

query = """
SELECT 
    WORK_TYPE,
    COUNT(*) as kol,
    COUNT(DISTINCT COMPLETED_BY_USER) as users_count
FROM raw_.WORK_INSTRUCTION_VIEW2
WHERE CONDITION = 'closed'
    AND INSTRUCTION_TYPE = 'Detail'
    AND CAST(END_DATE_TIME AS DATE) BETWEEN '2026-01-01' AND '2026-01-31'
GROUP BY WORK_TYPE
ORDER BY kol DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] WORK_INSTRUCTION_VIEW2 (оригинал, Январь 2026):")
    print(df.to_string(index=False))
    df.to_csv('диагностика_wms_оригинал.csv', index=False, encoding='utf-8-sig')
    print("\n[INFO] Сохранено в: диагностика_wms_оригинал.csv")

# ============================================================================
# 10. СРАВНЕНИЕ С ГРУЗЧИКАМИ ИЗ ОРИГИНАЛЬНОЙ ПРОЦЕДУРЫ
# ============================================================================
print("\n" + "=" * 80)
print("10. ПРОВЕРКА LABOR_MANAGEMENT_DETAIL_VIEW")
print("=" * 80)

query = """
SELECT TOP 50
    user_def1,
    user_def2,
    activity_type,
    COUNT(*) as kol
FROM raw_.labor_management_detail_view
WHERE CAST(date_time_stamp AS DATE) BETWEEN '2026-01-01' AND '2026-01-31'
GROUP BY user_def1, user_def2, activity_type
ORDER BY kol DESC
"""
df = execute_query(query)
if not df.empty:
    print("\n[INFO] labor_management_detail_view (топ-50):")
    print(df.to_string(index=False))
    df.to_csv('диагностика_labor_management.csv', index=False, encoding='utf-8-sig')
    print("\n[INFO] Сохранено в: диагностика_labor_management.csv")

# ============================================================================
# 11. ВЫВОДЫ
# ============================================================================
print("\n" + "=" * 80)
print("11. ВЫВОДЫ")
print("=" * 80)

print("""
Созданы файлы для сравнения:
   1. диагностика_операции_из_БД.csv - все операции по типам
   2. диагностика_операции_сотрудники.csv - операции по сотрудникам
   3. диагностика_сумма_сделки.csv - сумма сделки по сотрудникам
   4. диагностика_приемка.csv - приемка по сотрудникам
   5. диагностика_грузчики.csv - данные по грузчикам
   6. диагностика_январь_детально.csv - детальная статистика за январь
   7. диагностика_wms_оригинал.csv - оригинальные данные из WMS
   8. диагностика_labor_management.csv - labor_management_detail_view

Для сравнения:
   1. Откройте файл 'Копия Сделка0101.csv' 
   2. Сравните с соответствующими файлами диагностики
   3. Найдите расхождения в количествах операций и суммах

На что обратить внимание:
   - Расхождения в общем количестве операций по типам работ
   - Расхождения в количестве операций по сотрудникам
   - Расхождения в сумме сделки
   - Наличие/отсутствие дубликатов
""")

print("\n" + "=" * 80)
print("ДИАГНОСТИКА ЗАВЕРШЕНА")
print("=" * 80)
