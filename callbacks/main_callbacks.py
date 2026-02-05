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
        
        # 2. Получаем данные по ошибкам размещения за выбранный период
        placement_stats = get_placement_errors(start_date, end_date)
        
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

# Callback для обновления времени последнего обновления
@callback(
    Output('last-update-time', 'children'),
    [Input('global-date-range-picker', 'start_date')]
)
def update_last_update_time(start_date):
    return f"Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"

# Callback для обновления данных при изменении фильтра дат
@callback(
    [Output('global-date-range', 'data'),
     Output('performance-data-cache', 'data'),
     Output('shift-comparison-cache', 'data'),
     Output('problematic-hours-cache', 'data'),
     Output('error-hours-cache', 'data')],
    [Input('global-date-range-picker', 'start_date'),
     Input('global-date-range-picker', 'end_date')]
)
def update_global_date_range_and_data(start_date, end_date):
    """Обновление глобального фильтра дат и загрузка данных"""
    if start_date and end_date:
        start_str = start_date[:10] if isinstance(start_date, str) else start_date
        end_str = end_date[:10] if isinstance(end_date, str) else end_date
        
        refresh_data(start_str, end_str)
        
        # Получаем актуальные данные
        performance_data_cache = get_performance_data(start_str, end_str)
        shift_comparison_cache = get_shift_comparison(start_str, end_str)
        problematic_hours_cache = get_problematic_hours(start_str, end_str)
        error_hours_cache = get_error_hours_top_data(start_str, end_str)
        
        return {
            'start_date': start_str,
            'end_date': end_str
        }, performance_data_cache, shift_comparison_cache, problematic_hours_cache, error_hours_cache
    
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

# Callback для открытия/закрытия модального окна ячеек хранения
@callback(
    [Output("storage-cells-modal", "className"),
     Output("storage-modal-content", "className")],
    [Input("open-storage-modal", "n_clicks"),
     Input("close-storage-modal", "n_clicks")],
    [State("storage-cells-modal", "className"),
     State("storage-modal-content", "className")],
    prevent_initial_call=True
)
def toggle_storage_modal(open_clicks, close_clicks, modal_class, content_class):
    ctx = dash.callback_context
    if not ctx.triggered:
        return modal_class, content_class
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'open-storage-modal':
        return 'modal-visible', 'modal-content-visible'
    elif button_id == 'close-storage-modal':
        return 'modal-hidden', 'modal-content'
    
    return modal_class, content_class

# Callback для загрузки данных по ячейкам хранения
@callback(
    Output("storage-all-data", "data"),
    Input("storage-cells-modal", "className")
)
def load_storage_data(modal_class):
    """Загрузка всех данных по ячейкам при открытии модального окна"""
    if modal_class == 'modal-visible':
        all_data = get_all_storage_data()
        return {'all_data': all_data}
    return dash.no_update

# Callback для обновления фильтров и диаграмм
@callback(
    [Output("filter-storage-type", "options"),
     Output("filter-locating-zone", "options"),
     Output("filter-allocation-zone", "options"),
     Output("filter-location-type", "options"),
     Output("filter-work-zone", "options"),
     Output("storage-total-cells", "children"),
     Output("storage-occupied-cells", "children"),
     Output("storage-free-cells", "children"),
     Output("storage-occupied-percent", "children"),
     Output("storage-empty-chart", "option"),
     Output("storage-types-pie-chart", "option"),
     Output("storage-types-bar-chart", "option"),
     Output("storage-current-filters", "data")],
    [Input("filter-storage-type", "value"),
     Input("filter-locating-zone", "value"),
     Input("filter-allocation-zone", "value"),
     Input("filter-location-type", "value"),
     Input("filter-work-zone", "value"),
     Input("filter-only-empty", "value"),
     Input("storage-all-data", "data")]
)
def update_storage_filters_and_charts(storage_type_val, locating_zone_val, allocation_zone_val, 
                                     location_type_val, work_zone_val, only_empty_val, all_data):
    """Обновление фильтров и диаграмм на основе выбранных значений"""
    
    if not all_data or 'all_data' not in all_data:
        empty_options = [{'label': 'Все', 'value': 'Все'}]
        empty_chart = {"title": {"text": "Нет данных", "left": "center"}}
        return (
            empty_options, empty_options, empty_options, empty_options, empty_options,
            "0", "0", "0", "0%", empty_chart, empty_chart, empty_chart,
            {'storage_type': 'Все', 'locating_zone': 'Все', 'allocation_zone': 'Все', 
             'location_type': 'Все', 'work_zone': 'Все', 'only_empty': False}
        )
    
    try:
        # Текущие фильтры
        is_only_empty = True if only_empty_val and 'empty' in only_empty_val else False
        
        current_filters = {
            'storage_type': storage_type_val if storage_type_val != 'Все' else None,
            'locating_zone': locating_zone_val if locating_zone_val != 'Все' else None,
            'allocation_zone': allocation_zone_val if allocation_zone_val != 'Все' else None,
            'location_type': location_type_val if location_type_val != 'Все' else None,
            'work_zone': work_zone_val if work_zone_val != 'Все' else None,
            'only_empty': is_only_empty
        }
        
        # Фильтруем данные
        filtered_result = filter_storage_data(all_data['all_data'], current_filters)
        
        # Формируем опции для фильтров
        available_filters = filtered_result['available_filters']
        
        # Функция для создания опций dropdown
        def create_options(values):
            options = [{'label': 'Все', 'value': 'Все'}]
            for value in values:
                if value and value.strip():  # Проверяем что значение не пустое
                    options.append({'label': value, 'value': value})
            return options
        
        # Опции для каждого фильтра
        storage_type_options = create_options(available_filters['storage_type'])
        locating_zone_options = create_options(available_filters['locating_zone'])
        allocation_zone_options = create_options(available_filters['allocation_zone'])
        location_type_options = create_options(available_filters['location_type'])
        work_zone_options = create_options(available_filters['work_zone'])
        
        # Форматируем KPI
        summary = filtered_result['summary']
        
        # Показываем данные в зависимости от фильтра "только пустые"
        if is_only_empty:
            total_cells = f"{summary['empty']:,}"
            occupied_cells = "0"
            free_cells = f"{summary['empty']:,}"
            occupied_percent = 0
        else:
            total_cells = f"{summary['total']:,}"
            occupied_cells = f"{summary['occupied']:,}"
            free_cells = f"{summary['empty']:,}"
            occupied_percent = 0
            if summary['total'] > 0:
                occupied_percent = round((summary['occupied'] / summary['total']) * 100, 1)
        
        occupied_percent_str = f"{occupied_percent}%"
        
        # Создаем диаграммы
        empty_chart = create_empty_pie_chart(summary, current_filters)
        types_pie_chart = create_types_pie_chart(filtered_result['chart_data'], current_filters)
        types_bar_chart = create_types_bar_chart(filtered_result['chart_data'], current_filters)
        
        # Текущие значения фильтров для сохранения
        current_filter_values = {
            'storage_type': storage_type_val or 'Все',
            'locating_zone': locating_zone_val or 'Все',
            'allocation_zone': allocation_zone_val or 'Все',
            'location_type': location_type_val or 'Все',
            'work_zone': work_zone_val or 'Все',
            'only_empty': is_only_empty
        }
        
        return (
            storage_type_options,
            locating_zone_options,
            allocation_zone_options,
            location_type_options,
            work_zone_options,
            total_cells,
            occupied_cells,
            free_cells,
            occupied_percent_str,
            empty_chart,
            types_pie_chart,
            types_bar_chart,
            current_filter_values
        )
        
    except Exception as e:
        print(f"ERROR in callback: {e}")
        
        empty_options = [{'label': 'Все', 'value': 'Все'}]
        empty_chart = {"title": {"text": "Ошибка", "left": "center"}}
        return (
            empty_options, empty_options, empty_options, empty_options, empty_options,
            "0", "0", "0", "0%", empty_chart, empty_chart, empty_chart,
            {'storage_type': 'Все', 'locating_zone': 'Все', 'allocation_zone': 'Все', 
             'location_type': 'Все', 'work_zone': 'Все', 'only_empty': False}
        )

# Callback для сброса фильтров
@callback(
    [Output("filter-storage-type", "value"),
     Output("filter-locating-zone", "value"),
     Output("filter-allocation-zone", "value"),
     Output("filter-location-type", "value"),
     Output("filter-work-zone", "value")],
    [Input("reset-all-filters-btn", "n_clicks"),
     Input("reset-storage-type-btn", "n_clicks"),
     Input("reset-locating-zone-btn", "n_clicks"),
     Input("reset-allocation-zone-btn", "n_clicks"),
     Input("reset-location-type-btn", "n_clicks"),
     Input("reset-work-zone-btn", "n_clicks")],
    [State("filter-storage-type", "value"),
     State("filter-locating-zone", "value"),
     State("filter-allocation-zone", "value"),
     State("filter-location-type", "value"),
     State("filter-work-zone", "value")],
    prevent_initial_call=True
)
def reset_filters(all_clicks, storage_clicks, locating_clicks, allocation_clicks, location_clicks, work_clicks,
                  current_storage, current_locating, current_allocation, current_location, current_work):
    """Сброс фильтров при нажатии кнопок"""
    ctx = dash.callback_context
    
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Начальные значения
    new_storage = current_storage
    new_locating = current_locating
    new_allocation = current_allocation
    new_location = current_location
    new_work = current_work
    
    # Если нажата кнопка "Сбросить все"
    if button_id == "reset-all-filters-btn":
        return ['Все', 'Все', 'Все', 'Все', 'Все']
    
    # Если нажата кнопка сброса конкретного фильтра
    if button_id == "reset-storage-type-btn":
        new_storage = 'Все'
    elif button_id == "reset-locating-zone-btn":
        new_locating = 'Все'
    elif button_id == "reset-allocation-zone-btn":
        new_allocation = 'Все'
    elif button_id == "reset-location-type-btn":
        new_location = 'Все'
    elif button_id == "reset-work-zone-btn":
        new_work = 'Все'
    
    return new_storage, new_locating, new_allocation, new_location, new_work

# Callback для обновления таблицы сотрудников на смене
@callback(
    Output('shift-employees-table-body', 'children'),
    [Input('position-filter', 'value'),
     Input('brigade-filter', 'value')]
)
def update_shift_employees_table(position_filter, brigade_filter):
    """Обновление таблицы сотрудников на смене"""
    
    try:
        from data.queries_mssql import get_employees_on_shift
        employees, position_stats = get_employees_on_shift()
        
        # Применяем фильтры
        filtered_employees = employees
        
        if position_filter and position_filter != 'all':
            filtered_employees = [e for e in filtered_employees if e.get('Должность') == position_filter]
        
        if brigade_filter and brigade_filter != 'all':
            filtered_employees = [e for e in filtered_employees if e.get('Бригада') == brigade_filter]
        
        # Создаем строки таблицы
        rows = []
        for employee in filtered_employees:
            status = employee.get('Статус', 'Не вышел')
            status_color = '#F44336' if status == 'Не вышел' else '#4CAF50'
            
            rows.append(
                html.Tr([
                    html.Td(employee.get('ФИО', ''), 
                           style={'padding': '8px', 'borderBottom': '1px solid #eee'}),
                    html.Td(employee.get('Должность', ''), 
                           style={'padding': '8px', 'borderBottom': '1px solid #eee'}),
                    html.Td(employee.get('Бригада', ''), 
                           style={'padding': '8px', 'borderBottom': '1px solid #eee'}),
                    html.Td(status, 
                           style={'padding': '8px', 'borderBottom': '1px solid #eee', 
                                 'color': status_color, 'fontWeight': 'bold'}),
                    html.Td(employee.get('Время_первой_операции', '--:--'), 
                           style={'padding': '8px', 'borderBottom': '1px solid #eee', 
                                 'color': '#666', 'textAlign': 'center'})
                ])
            )
        
        return rows
        
    except Exception as e:
        print(f"Error in update_shift_employees_table: {e}")
        return [
            html.Tr([
                html.Td(f"Ошибка загрузки данных: {str(e)}", colSpan=5,
                       style={'padding': '20px', 'textAlign': 'center', 
                             'color': '#F44336', 'fontSize': '14px'})
            ])
        ]

# Callback для обновления таблиц производительности
@callback(
    [Output('table-all-employees', 'children'),
     Output('table-top-best', 'children'),
     Output('table-top-worst', 'children')],
    [Input('performance-data-cache', 'data'),
     Input('current-table-view', 'data')]
)
def update_performance_tables(data, current_view):
    """Обновление таблиц производительности на вкладке производительности"""
    if not data:
        empty_table = html.Table([
            html.Thead(html.Tr([
                html.Th('Сотрудник', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                html.Th('Операции', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                html.Th('Время', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                html.Th('Заработок', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                html.Th('Оп/час', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                html.Th('Время работы', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'})
            ])),
            html.Tbody([
                html.Tr([
                    html.Td("Нет данных", colSpan=6, style={'textAlign': 'center', 'padding': '20px', 'color': '#666'})
                ])
            ])
        ], style={'width': '100%', 'borderCollapse': 'collapse'})
        return empty_table, empty_table, empty_table
    
    df = pd.DataFrame(data)
    
    all_employees_table = create_performance_table(df, title="Все сотрудники")
    
    if len(df) > 0:
        # Топ-5 лучших по заработку
        top_best = df.nlargest(5, 'Заработок')
        best_table = create_performance_table(top_best, title="Топ-5 лучших", is_best=True)
    else:
        best_table = all_employees_table
    
    if len(df) > 0:
        # Топ-5 худших по заработку
        top_worst = df.nsmallest(min(5, len(df)), 'Заработок')
        worst_table = create_performance_table(top_worst, title="Топ-5 худших", is_worst=True)
    else:
        worst_table = all_employees_table
    
    return all_employees_table, best_table, worst_table
