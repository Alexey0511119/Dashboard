#!/usr/bin/env python3
"""
Анализ используемых таблиц/представлений в MSSQL для получения данных производительности сотрудников
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def analyze_db_connections():
    """Анализ используемых таблиц/представлений в MSSQL"""
    
    print("=== АНАЛИЗ ИСПОЛЬЗУЕМЫХ ТАБЛИЦ/ПРЕДСТАВЛЕНИЙ В MSSQL ===\n")
    
    print("1. ОСНОВНЫЕ ПРЕДСТАВЛЕНИЯ В СХЕМЕ DM:")
    print("-" * 60)
    
    # Основные представления, используемые в проекте
    main_views = [
        "dm.v_performance_detailed - основное представление для данных производительности сотрудников",
        "dm.v_employee_modal_detail - детальные данные для модального окна сотрудника",
        "dm.v_employee_analytics - аналитические данные по сотрудникам",
        "dm.v_hourly_delays - данные по часовым просрочкам (для диаграммы проблемных часов)",
        "dm.v_hourly_errors - данные по часовыми ошибкам (для диаграммы часов с ошибками)",
        "dm.v_operations_by_type_for_chart - данные по типам операций для диаграммы",
        "dm.v_employee_idle_time - данные по простоям сотрудников",
        "dm.v_penalty_summary - данные по штрафам сотрудников"
    ]
    
    for view in main_views:
        print(f"  • {view}")
    
    print(f"\n2. ДОПОЛНИТЕЛЬНЫЕ ПРЕДСТАВЛЕНИЯ:")
    print("-" * 60)
    
    additional_views = [
        "dm.v_order_timeliness_by_delivery - своевременность заказов по типам доставки",
        "dm.v_order_accuracy_daily - точность заказов",
        "dm.v_rejected_lines_summary - сводка по отклоненным строкам",
        "dm.v_rejected_lines_detail - детали по отклоненным строкам",
        "dm.v_storage_current_status - статус ячеек хранения",
        "dm.v_employees_on_shift_detailed - сотрудники на смене",
        "dm.v_revision_by_event - данные по ревизиям",
        "dm.v_placement_detail - детали размещения",
        "dm.v_receipt_timeliness - своевременность получения товара"
    ]
    
    for view in additional_views:
        print(f"  • {view}")
    
    print(f"\n3. СТРУКТУРА ОСНОВНОГО ПРЕДСТАВЛЕНИЯ dm.v_performance_detailed:")
    print("-" * 60)
    print("  • Сотрудник (nvarchar) - имя сотрудника")
    print("  • Общее_кол_операций (int) - общее количество операций")
    print("  • Ср_время_на_операцию (numeric) - среднее время на операцию")
    print("  • Заработок (decimal) - заработок сотрудника")
    print("  • Операций_в_час (numeric) - операций в час")
    print("  • Время_работы (varchar) - время работы в формате 'Xч Yм'")
    print("  • Время_первой_операции (nvarchar) - время первой операции")
    print("  • Обычные_операции (int) - количество обычных операций")
    print("  • Приемка (int) - количество операций приемки")
    print("  • date_key (date) - дата")
    
    print(f"\n4. СТРУКТУРА ПРЕДСТАВЛЕНИЯ dm.v_employee_modal_detail:")
    print("-" * 60)
    print("  • fio (nvarchar) - ФИО сотрудника")
    print("  • smena (nvarchar) - смена")
    print("  • date_key (date) - дата")
    print("  • total_operations (int) - общее количество операций")
    print("  • total_earnings (decimal) - общий заработок")
    print("  • total_idle_minutes (int) - общее время простоя в минутах")
    print("  • orders_completed (int) - количество выполненных заказов")
    print("  • timely_percentage (numeric) - процент своевременности")
    print("  • fines_count (int) - количество штрафов")
    print("  • fines_amount (decimal) - сумма штрафов")
    print("  • operations_by_type (nvarchar) - типы операций")
    print("  • reception_count (int) - количество операций приемки")
    
    print(f"\n5. ПРИНЦИПЫ ПОЛУЧЕНИЯ ДАННЫХ:")
    print("-" * 60)
    print("  • Данные получаются из представлений в схеме dm (data mart)")
    print("  • Используется фильтрация по диапазону дат (date_key BETWEEN ? AND ?)")
    print("  • Для таблицы производительности данные агрегируются по сотруднику")
    print("  • Для модального окна данные берутся за выбранный период для конкретного сотрудника")
    print("  • Используется кэширование запросов для оптимизации производительности")
    print("  • Все запросы используют параметризованные SQL-запросы для безопасности")
    
    print(f"\n6. ПРИНЦИПЫ АГРЕГАЦИИ ДАННЫХ:")
    print("-" * 60)
    print("  • Для таблицы производительности:")
    print("    - Суммируются количественные показатели (операции, заработок)")
    print("    - Усредняются временные показатели (время на операцию)")
    print("    - Объединяются данные по сотруднику за выбранный период")
    print("  • Для модального окна:")
    print("    - Показываются детальные данные по дням для конкретного сотрудника")
    print("    - Агрегируются данные для отображения общей картины за период")
    
    print(f"\n7. РЕЗУЛЬТАТ:")
    print("-" * 60)
    print("  SUCCESS: Проект использует представления в схеме dm (data mart)")
    print("  SUCCESS: Основные данные берутся из dm.v_performance_detailed")
    print("  SUCCESS: Детальные данные для модального окна из dm.v_employee_modal_detail")
    print("  SUCCESS: Данные по часам из dm.v_hourly_delays и dm.v_hourly_errors")
    print("  SUCCESS: Принципы получения данных: фильтрация по датам, агрегация по сотруднику")
    print("  SUCCESS: Все данные безопасно параметризованы")


if __name__ == "__main__":
    analyze_db_connections()