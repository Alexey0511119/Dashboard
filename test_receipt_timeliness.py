#!/usr/bin/env python3
"""
Тестирование функции get_arrival_timeliness с данными из v_receipt_timeliness
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_arrival_timeliness

def test_receipt_timeliness():
    """Тестирование получения данных о своевременности приходов"""
    
    print("=== ТЕСТИРОВАНИЕ СВОЕВРЕМЕННОСТИ ПРИХОДОВ ===\n")
    
    # Тестовые периоды
    test_periods = [
        ("2026-02-01", "2026-02-03", "Последние 3 дня"),
        ("2026-01-01", "2026-01-31", "Январь 2026"),
        ("2025-01-01", "2025-12-31", "Весь 2025 год"),
        ("2023-09-05", "2026-02-03", "Весь период")
    ]
    
    for start_date, end_date, period_name in test_periods:
        print(f"📅 Период: {period_name} ({start_date} - {end_date})")
        
        try:
            timely_count, delayed_count = get_arrival_timeliness(start_date, end_date)
            total_count = timely_count + delayed_count
            
            print(f"  ✅ Приходов принято в срок: {timely_count:,}")
            print(f"  ❌ Просроченных приходов: {delayed_count:,}")
            print(f"  📊 Всего приходов: {total_count:,}")
            
            if total_count > 0:
                timely_percent = (timely_count / total_count) * 100
                print(f"  📈 Процент своевременности: {timely_percent:.1f}%")
            else:
                print(f"  📈 Процент своевременности: 0%")
            
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
        
        print("-" * 60)
    
    print("\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    test_receipt_timeliness()
