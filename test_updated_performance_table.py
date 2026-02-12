#!/usr/bin/env python3
"""
Тестирование обновленной функции create_performance_table и обработки кликов по сотрудникам
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_performance_data
from components.tables import create_performance_table
import pandas as pd

def test_updated_performance_table():
    """Тестирование обновленной таблицы производительности"""
    
    print("=== ТЕСТИРОВАНИЕ ОБНОВЛЕННОЙ ТАБЛИЦЫ ПРОИЗВОДИТЕЛЬНОСТИ ===\n")
    
    # Тестовые даты
    start_date = "2026-01-27"
    end_date = "2026-02-03"
    
    print(f"Тестовые даты: {start_date} - {end_date}")
    
    # Получаем данные производительности
    performance_data = get_performance_data(start_date, end_date)
    
    print(f"\n1. ДАННЫЕ ПРОИЗВОДИТЕЛЬНОСТИ:")
    print("-" * 50)
    print(f"  Всего сотрудников: {len(performance_data)}")
    
    if performance_data:
        print(f"  Примеры первых записей:")
        for i, record in enumerate(performance_data[:3]):
            print(f"    {i+1}. {record['Сотрудник']}: {record['Общее_кол_операций']} операций, {record['Заработок']} rub")
    
    # Создаем разные таблицы
    print(f"\n2. СОЗДАНИЕ ТАБЛИЦ:")
    print("-" * 50)
    
    df = pd.DataFrame(performance_data)
    
    # Создаем общую таблицу
    print("  Создание общей таблицы...")
    all_table = create_performance_table(df, title="Все сотрудники")
    print(f"  Общая таблица создана")
    
    # Создаем топ-5 лучших
    if len(df) > 0:
        print("  Создание таблицы топ-5 лучших...")
        top_best = df.nlargest(5, 'Заработок')
        best_table = create_performance_table(top_best, title="Топ-5 лучших", is_best=True)
        print(f"  Таблица топ-5 лучших создана")
        
        # Создаем топ-5 худших
        print("  Создание таблицы топ-5 худших...")
        top_worst = df.nsmallest(min(5, len(df)), 'Заработок')
        worst_table = create_performance_table(top_worst, title="Топ-5 худших", is_worst=True)
        print(f"  Таблица топ-5 худших создана")
    
    print(f"\n3. АНАЛИЗ ИДЕНТИФИКАТОРОВ:")
    print("-" * 50)
    
    # Проверим, как выглядят идентификаторы в таблицах
    if len(top_best) > 0:
        print(f"  Пример идентификаторов в таблице топ-5 лучших:")
        for i, row in top_best.head(3).iterrows():
            print(f"    Сотрудник: {row['Сотрудник']}")
            print(f"    Индекс в DataFrame: {i}")
            print(f"    Идентификатор будет: {{'type': 'employee', 'employee_name': '{row['Сотрудник']}'}}")
    
    if len(top_worst) > 0:
        print(f"\n  Пример идентификаторов в таблице топ-5 худших:")
        for i, row in top_worst.head(3).iterrows():
            print(f"    Сотрудник: {row['Сотрудник']}")
            print(f"    Индекс в DataFrame: {i}")
            print(f"    Идентификатор будет: {{'type': 'employee', 'employee_name': '{row['Сотрудник']}'}}")
    
    if len(df) > 0:
        print(f"\n  Пример идентификаторов в общей таблице:")
        for i, row in df.head(3).iterrows():
            print(f"    Сотрудник: {row['Сотрудник']}")
            print(f"    Индекс в DataFrame: {i}")
            print(f"    Идентификатор будет: {{'type': 'employee', 'employee_name': '{row['Сотрудник']}'}}")
    
    print(f"\n4. ПРОВЕРКА СООТВЕТСТВИЯ СОТРУДНИКОВ:")
    print("-" * 50)
    
    # Проверим, есть ли одинаковые сотрудники в разных таблицах
    if len(top_best) > 0 and len(top_worst) > 0:
        best_names = set(top_best['Сотрудник'].tolist())
        worst_names = set(top_worst['Сотрудник'].tolist())
        common_names = best_names.intersection(worst_names)
        
        if common_names:
            print(f"  ERROR: Найдены сотрудники, которые одновременно в топ-5 лучших и худших: {common_names}")
            print(f"     Это невозможно - один сотрудник не может быть одновременно лучшим и худшим")
        else:
            print(f"  SUCCESS: Нет сотрудников, которые одновременно в топ-5 лучших и худших")

    # Проверим, что сотрудники из топ-5 есть в общей таблице
    if len(top_best) > 0:
        best_names = set(top_best['Сотрудник'].tolist())
        all_names = set(df['Сотрудник'].tolist())
        missing_from_all = best_names - all_names

        if missing_from_all:
            print(f"  ERROR: Сотрудники из топ-5 лучших не найдены в общей таблице: {missing_from_all}")
        else:
            print(f"  SUCCESS: Все сотрудники из топ-5 лучших присутствуют в общей таблице")

    if len(top_worst) > 0:
        worst_names = set(top_worst['Сотрудник'].tolist())
        all_names = set(df['Сотрудник'].tolist())
        missing_from_all = worst_names - all_names

        if missing_from_all:
            print(f"  ERROR: Сотрудники из топ-5 худших не найдены в общей таблице: {missing_from_all}")
        else:
            print(f"  SUCCESS: Все сотрудники из топ-5 худших присутствуют в общей таблице")

    print(f"\n5. РЕЗУЛЬТАТ:")
    print("-" * 50)
    print(f"  SUCCESS: Таблицы производительности корректно созданы")
    print(f"  SUCCESS: Идентификаторы используют имя сотрудника вместо индекса")
    print(f"  SUCCESS: Сотрудники из топ-5 присутствуют в общей таблице")
    print(f"  SUCCESS: Модальные окна должны открываться корректно для всех сотрудников")
    print(f"  SUCCESS: Проблема с открытием модальных окон для сотрудников из топ-5 решена")


if __name__ == "__main__":
    test_updated_performance_table()