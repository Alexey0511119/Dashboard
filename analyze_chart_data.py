#!/usr/bin/env python3
"""
Анализ данных для диаграмм своевременности
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_orders_timeliness_by_delivery

def analyze_chart_data():
    """Анализ данных для диаграмм"""
    
    print('=== АНАЛИЗ ДАННЫХ ДЛЯ ДИАГРАММ ===')
    start_date = '2026-01-27'
    end_date = '2026-02-04'

    chart_data = get_orders_timeliness_by_delivery(start_date, end_date)
    print(f'Всего записей: {len(chart_data)}')

    print('\nДетализация по датам и типам:')
    for item in chart_data:
        print(f'  {item["date"]} - {item["delivery_type"]}: в срок={item["timely_count"]}, просрочено={item["delayed_count"]}')

    print('\nАнализ пропущенных дат:')
    # Получаем все даты в периоде
    all_dates = set()
    for item in chart_data:
        all_dates.add(item['date'])

    # Проверяем, для каких дат нет данных по каждому типу
    rc_dates = set(item['date'] for item in chart_data if item['delivery_type'] == 'РЦ')
    client_dates = set(item['date'] for item in chart_data if item['delivery_type'] == 'Доставка клиенту')

    print(f'Даты с данными РЦ: {sorted(rc_dates)}')
    print(f'Даты с данными Доставка клиенту: {sorted(client_dates)}')
    print(f'Даты без данных Доставка клиенту: {sorted(all_dates - client_dates)}')

if __name__ == "__main__":
    analyze_chart_data()
