#!/usr/bin/env python3
"""
Тестирование callback модального окна напрямую
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_performance_data, get_employee_modal_detail, get_employee_operations_by_type, get_employee_idle_intervals

def test_modal_callback():
    """Тестирование логики callback модального окна"""
    
    print("=== ТЕСТИРОВАНИЕ CALLBACK МОДАЛЬНОГО ОКНА ===\n")
    
    try:
        # Тестовые данные
        start_date = "2026-01-27"
        end_date = "2026-02-03"
        
        print(f"Период: {start_date} - {end_date}\n")
        
        # 1. Получаем данные производительности (как в performance_data-cache)
        print("1. ПОЛУЧЕНИЕ ДАННЫХ ПРОИЗВОДИТЕЛЬНОСТИ:")
        performance_data = get_performance_data(start_date, end_date)
        print(f"  Получено записей: {len(performance_data)}")
        
        if not performance_data:
            print("  ❌ Нет данных производительности!")
            return False
        
        # 2. Берем первого сотрудника для теста
        employee_name = performance_data[0]['Сотрудник']
        print(f"  Тестируем для сотрудника: {employee_name}")
        
        # 3. Получаем детальные данные (get_employee_modal_detail)
        print("\n2. ПОЛУЧЕНИЕ ДЕТАЛЬНЫХ ДАННЫХ:")
        detail_data = get_employee_modal_detail(employee_name, start_date, end_date)
        print(f"  Получено записей: {len(detail_data)}")
        
        if not detail_data:
            print("  ❌ Нет детальных данных!")
            return False
        
        # 4. Агрегируем данные (как в callback)
        print("\n3. АГРЕГАЦИЯ ДАННЫХ:")
        total_operations = sum(d['total_operations'] for d in detail_data)
        total_earnings = sum(d['total_earnings'] for d in detail_data)
        total_idle_minutes = sum(d['total_idle_minutes'] for d in detail_data)
        orders_completed = sum(d['orders_completed'] for d in detail_data)
        fines_count = sum(d['fines_count'] for d in detail_data)
        fines_amount = sum(d['fines_amount'] for d in detail_data)
        reception_count = sum(d['reception_count'] for d in detail_data)
        
        print(f"  Всего операций: {total_operations}")
        print(f"  Всего заработок: {total_earnings}")
        print(f"  Всего простои: {total_idle_minutes} минут")
        print(f"  Заказов выполнено: {orders_completed}")
        print(f"  Штрафов: {fines_count} на сумму {fines_amount}")
        print(f"  Приемка: {reception_count}")
        
        # 5. Получаем данные для диаграмм
        print("\n4. ПОЛУЧЕНИЕ ДАННЫХ ДЛЯ ДИАГРАММ:")
        
        operations_by_type = get_employee_operations_by_type(employee_name, start_date, end_date)
        print(f"  Типов операций: {len(operations_by_type)}")
        
        idle_intervals = get_employee_idle_intervals(employee_name, start_date, end_date)
        print(f"  Интервалов простоев: {sum(idle_intervals.values())}")
        
        # 6. Создаем диаграммы (как в callback)
        print("\n5. СОЗДАНИЕ ДИАГРАММ:")
        
        # Столбчатая диаграмма типов операций
        operations_chart = {
            "title": {"text": "Типы операций", "left": "center"},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "xAxis": {
                "type": "category",
                "data": [op['operation_type'] for op in operations_by_type],
                "axisLabel": {"rotate": 45, "fontSize": 10}
            },
            "yAxis": {"type": "value", "name": "Количество операций"},
            "series": [{
                "type": "bar",
                "data": [op['total_operations'] for op in operations_by_type],
                "itemStyle": {"color": "#4CAF50"},
                "label": {"show": True, "position": "top"}
            }]
        }
        print("  ✅ Столбчатая диаграмма создана")
        
        # Диаграмма простоев
        from components.charts import create_idle_intervals_bar_echarts
        idle_intervals_bar = create_idle_intervals_bar_echarts(idle_intervals)
        print("  ✅ Диаграмма простоев создана")
        
        # 7. Расчет KPI
        print("\n6. РАСЧЕТ KPI:")
        work_hours = 8.0
        ops_per_hour = total_operations / work_hours if total_operations > 0 else 0.0
        earnings_per_hour = total_earnings / work_hours if work_hours > 0 else 0.0
        work_duration = f"{int(work_hours)}ч 0м"
        
        print(f"  Операций в час: {ops_per_hour:.1f}")
        print(f"  Заработок в час: {earnings_per_hour:.2f} ₽/час")
        print(f"  Время работы: {work_duration}")
        
        print(f"\n🎉 Callback модального окна работает корректно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании callback: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_modal_callback()
    if success:
        print(f"\n🎉 Модальное окно должно работать!")
    else:
        print(f"\n❌ Проблемы в логике модального окна")
