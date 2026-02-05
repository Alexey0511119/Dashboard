#!/usr/bin/env python3
"""
Тестирование получения данных из новых таблиц dm.v_hourly_errors и dm.v_hourly_delays
для диаграмм "Топ 5 проблемных часов" и "Топ 5 часов с ошибками"
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.mssql_client import execute_query_cached

def test_hourly_data():
    """Тестирование получения данных из новых таблиц"""
    
    print("=== ТЕСТИРОВАНИЕ НОВЫХ ТАБЛИЦ DM.V_HOURLY_ERRORS И DM.V_HOURLY_DELAYS ===\n")
    
    # Тестовые периоды
    test_periods = [
        ("2026-01-27", "2026-02-03", "Текущий период"),
        ("2026-01-01", "2026-01-31", "Январь 2026"),
        ("2025-01-01", "2025-12-31", "Весь 2025 год")
    ]
    
    for start_date, end_date, period_name in test_periods:
        print(f"PERIOD: {period_name} ({start_date} - {end_date})")
        
        # Тестирование dm.v_hourly_delays (проблемные часы/просрочки)
        print("\n1. ТАБЛИЦА DM.V_HOURLY_DELAYS (проблемные часы/просрочки):")
        print("-" * 60)
        
        delays_query = """
        SELECT 
            hour,
            total_orders,
            delayed_orders,
            pct_delayed
        FROM dm.v_hourly_delays
        ORDER BY pct_delayed DESC
        """
        
        delays_result = execute_query_cached(delays_query)
        if delays_result:
            print(f"  Всего записей: {len(delays_result)}")
            print("  Топ-5 часов с наибольшим процентом просрочек:")
            
            for i, row in enumerate(delays_result[:5], 1):
                hour = row[0] if row[0] is not None else 0
                total_orders = row[1] if row[1] is not None else 0
                delayed_orders = row[2] if row[2] is not None else 0
                pct_delayed = row[3] if row[3] is not None else 0.0
                
                print(f"    {i}. {hour}:00 - {pct_delayed}% просрочек ({delayed_orders}/{total_orders} заказов)")
        else:
            print("  ❌ Нет данных")
        
        # Тестирование dm.v_hourly_errors (часы с ошибками)
        print("\n2. ТАБЛИЦА DM.V_HOURLY_ERRORS (часы с ошибками):")
        print("-" * 60)
        
        errors_query = """
        SELECT 
            hour,
            total_orders,
            error_orders,
            pct_errors
        FROM dm.v_hourly_errors
        ORDER BY pct_errors DESC
        """
        
        errors_result = execute_query_cached(errors_query)
        if errors_result:
            print(f"  Всего записей: {len(errors_result)}")
            print("  Топ-5 часов с наибольшим процентом ошибок:")
            
            for i, row in enumerate(errors_result[:5], 1):
                hour = row[0] if row[0] is not None else 0
                total_orders = row[1] if row[1] is not None else 0
                error_orders = row[2] if row[2] is not None else 0
                pct_errors = row[3] if row[3] is not None else 0.0
                
                print(f"    {i}. {hour}:00 - {pct_errors}% ошибок ({error_orders}/{total_orders} заказов)")
        else:
            print("  ❌ Нет данных")
        
        print("\n" + "="*80 + "\n")
    
    # Тестирование структуры данных для функций
    print("3. СТРУКТУРА ДАННЫХ ДЛЯ ФУНКЦИЙ:")
    print("-" * 60)
    
    # Пример данных для get_problematic_hours (должна возвращать top 5 часов с просрочками)
    print("  Пример данных для get_problematic_hours:")
    if delays_result:
        for i, row in enumerate(delays_result[:5], 1):
            hour = row[0] if row[0] is not None else 0
            total_orders = row[1] if row[1] is not None else 0
            delayed_orders = row[2] if row[2] is not None else 0
            pct_delayed = row[3] if row[3] is not None else 0.0
            
            print(f"    {{'hour': {hour}, 'total_orders': {total_orders}, 'delayed_orders': {delayed_orders}, 'delay_percentage': {pct_delayed}}}")
    
    print("\n  Пример данных для get_error_hours_top_data:")
    if errors_result:
        for i, row in enumerate(errors_result[:5], 1):
            hour = row[0] if row[0] is not None else 0
            total_orders = row[1] if row[1] is not None else 0
            error_orders = row[2] if row[2] is not None else 0
            pct_errors = row[3] if row[3] is not None else 0.0
            
            print(f"    {{'hour': {hour}, 'total_orders_in_hour': {total_orders}, 'error_orders_count': {error_orders}, 'error_percentage': {pct_errors}, 'error_types': ''}}")

if __name__ == "__main__":
    test_hourly_data()