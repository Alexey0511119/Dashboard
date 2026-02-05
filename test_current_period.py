#!/usr/bin/env python3
"""
Проверка загрузки данных производительности для текущего периода
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_performance_data

def test_current_period_data():
    """Проверка данных за текущий период"""
    
    print("=== ПРОВЕРКА ДАННЫХ ЗА ТЕКУЩИЙ ПЕРИОД ===\n")
    
    try:
        # Текущий период из лога дашборда
        start_date = "2026-01-27"
        end_date = "2026-02-03"
        
        print(f"Период: {start_date} - {end_date}")
        
        # Получаем данные
        performance_data = get_performance_data(start_date, end_date)
        
        print(f"Получено записей: {len(performance_data)}")
        
        if performance_data:
            print("\nПример данных:")
            for i, record in enumerate(performance_data[:3], 1):
                print(f"\nЗапись {i}:")
                for key, value in record.items():
                    print(f"  {key}: {value}")
        else:
            print("❌ Данные не получены!")
        
        # Проверим структуру данных
        if performance_data:
            print(f"\nСтруктура данных:")
            first_record = performance_data[0]
            required_fields = ['Сотрудник', 'Общее_кол_операций', 'Заработок', 'Операций_в_час']
            
            for field in required_fields:
                if field in first_record:
                    print(f"  ✅ {field}: {first_record[field]}")
                else:
                    print(f"  ❌ {field}: отсутствует")
        
        return performance_data
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    data = test_current_period_data()
    print(f"\nРезультат: {len(data)} записей")
