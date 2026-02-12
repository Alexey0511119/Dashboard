import dash
from dash import Input, Output, State, callback, html
import pandas as pd
from datetime import datetime, timedelta
import json
import random

from data.queries_mssql import (
    get_orders_timely, get_avg_operation_time, get_total_earnings, get_order_accuracy,
    get_avg_productivity, get_performance_data, get_shift_comparison, 
    get_problematic_hours, get_fines_data,
    get_employees_on_shift, refresh_data, get_error_hours_top_data,
    get_storage_cells_stats, get_all_storage_data, get_revision_stats, get_placement_errors,
    filter_storage_data
)
from components.charts import (
    create_order_accuracy_chart, create_problematic_hours_chart,
    create_timeliness_chart, create_operations_type_chart,
    create_time_distribution_pie_echarts, create_idle_intervals_bar_echarts,
    create_fines_pie_chart, create_fines_amount_bar_chart,
    create_employee_fines_chart,
    create_empty_pie_chart, create_types_pie_chart, create_types_bar_chart
)
from components.tables import create_performance_table

# Callback для обновления KPI карточек на главной вкладке
@callback(
    [Output('total-revisions-kpi', 'children'),
     Output('open-revisions-kpi', 'children'),
     Output('in-process-revisions-kpi', 'children'),
     Output('placement-errors-kpi', 'children'),
     Output('placement-correct-kpi', 'children'),
     Output('placement-errors-count-kpi', 'children'),
     Output('placement-percentage-kpi', 'children'),
     Output('storage-cells-kpi', 'children'),
     Output('storage-cells-detail', 'children'),
     Output('order-accuracy-kpi', 'children'),
     Output('order-accuracy-detail', 'children')],
    [Input('global-date-range', 'data')]
)
def update_main_kpi_cards(date_range):
    """Обновление KPI карточек на главной вкладке"""
    if not date_range:
        return ("0", "0", "0", "0%", "0", "0", "Нет данных", "0/0", 
                "0% занято | 0% своб.", "100%", "0 заказов без ошибок")
    
    start_date = date_range['start_date']
    end_date = date_range['end_date']
    
    try:
        # 1. Получаем данные по ревизиям
        revision_stats = get_revision_stats()
        
        # 2. Получаем данные по ошибкам размещения
        placement_stats = get_placement_errors()
        
        # 3. Получаем остальные данные
        accuracy, orders_without_errors, total_orders_accuracy, error_orders = get_order_accuracy(start_date, end_date)
        storage_stats = get_storage_cells_stats()
        
        # 4. Форматируем KPI значения
        
        # Ревизии
        total_revisions = f"{revision_stats['total_revisions']:,}"
        open_revisions = f"{revision_stats['open_revisions']:,}"
        in_process_revisions = f"{revision_stats['in_process_revisions']:,}"
        
        # Ошибки размещения
        error_percentage = f"{placement_stats['error_percentage']}%"
        correct_count = f"{placement_stats['correct_count']:,}"
        error_count = f"{placement_stats['error_count']:,}"
        
        # Формируем детали для ошибок размещения
        placement_detail = ""
        if placement_stats['total_count'] > 0:
            placement_detail = f"{placement_stats['total_count']:,} всего"
            if placement_stats['unique_users'] > 0:
                placement_detail += f" | {placement_stats['unique_users']} пользователей"
            if placement_stats['unique_items'] > 0:
                placement_detail += f" | {placement_stats['unique_items']} позиций"
        else:
            placement_detail = "Нет данных за 2025"
        
        # Ячейки хранения
        storage_kpi = f"{storage_stats['occupied_cells']}/{storage_stats['free_cells']}"
        storage_detail = f"{storage_stats['occupied_percent']}% занято | {storage_stats['free_percent']}% своб."
        
        # Точность заказов
        accuracy_str = f"{accuracy:.1f}%"
        accuracy_detail = f"↗ {orders_without_errors:,} заказов без ошибок"
        
        return (
            total_revisions,
            open_revisions,
            in_process_revisions,
            error_percentage,
            correct_count,
            error_count,
            placement_detail,
            storage_kpi,
            storage_detail,
            accuracy_str,
            accuracy_detail
        )
    except Exception as e:
        print(f"Error in update_main_kpi_cards: {e}")
        return ("0", "0", "0", "0%", "0", "0", "Ошибка загрузки", "0/0", 
                "0% занято | 0% своб.", "100%", "0 заказов без ошибок")
