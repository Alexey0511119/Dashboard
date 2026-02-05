#!/usr/bin/env python3
"""
Тестирование новых функций для работы с dm.v_order_timeliness_by_delivery
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_orders_timely, get_orders_timeliness_by_delivery

def test_new_order_functions():
    """Тестирование новых функций заказов"""
    
    print("=== ТЕСТИРОВАНИЕ НОВЫХ ФУНКЦИЙ ЗАКАЗОВ ===\n")
    
    # Тестовые периоды
    test_periods = [
        ("2026-02-01", "2026-02-04", "Последние 4 дня"),
        ("2026-01-01", "2026-01-31", "Январь 2026"),
        ("2025-01-01", "2025-12-31", "Весь 2025 год")
    ]
    
    for start_date, end_date, period_name in test_periods:
        print(f"📅 Период: {period_name} ({start_date} - {end_date})")
        
        try:
            # Тестируем get_orders_timely (для карточек)
            timely_orders, delayed_orders, total_orders, percentage = get_orders_timely(start_date, end_date)
            print(f"  ✅ Карточки заказов:")
            print(f"    Выполнено в срок: {timely_orders:,}")
            print(f"    Просрочено: {delayed_orders:,}")
            print(f"    Всего: {total_orders:,}")
            print(f"    % своевременности: {percentage}%")
            
            # Тестируем get_orders_timeliness_by_delivery (для диаграмм)
            chart_data = get_orders_timeliness_by_delivery(start_date, end_date)
            print(f"  ✅ Диаграммы: {len(chart_data)} записей")
            
            if chart_data:
                # Группировка по типам доставки
                rc_data = [item for item in chart_data if item['delivery_type'] == 'РЦ']
                client_data = [item for item in chart_data if item['delivery_type'] == 'Доставка клиенту']
                
                print(f"    📦 РЦ: {len(rc_data)} записей")
                if rc_data:
                    rc_timely = sum(item['timely_count'] for item in rc_data)
                    rc_delayed = sum(item['delayed_count'] for item in rc_data)
                    print(f"      В срок: {rc_timely:,}, Просрочено: {rc_delayed:,}")
                
                print(f"    🚚 Доставка клиенту: {len(client_data)} записей")
                if client_data:
                    client_timely = sum(item['timely_count'] for item in client_data)
                    client_delayed = sum(item['delayed_count'] for item in client_data)
                    print(f"      В срок: {client_timely:,}, Просрочено: {client_delayed:,}")
                
                # Показываем последние даты
                dates = sorted(set(item['date'] for item in chart_data))
                print(f"    📅 Даты: {dates[-3:] if len(dates) > 3 else dates}")
            
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
        
        print("-" * 60)
    
    print("\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    test_new_order_functions()
