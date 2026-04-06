import logging
from functools import lru_cache

import dash
from dash import Input, Output, State, callback, html
import pandas as pd
from datetime import datetime, timedelta
import json
import random

logger = logging.getLogger(__name__)

from data.queries_mssql import (
    get_orders_timely, get_avg_operation_time, get_total_earnings, get_order_accuracy,
    get_avg_productivity, get_performance_data, get_shift_comparison,
    get_problematic_hours, get_fines_data,
    get_employees_on_shift, get_employees_on_shift_new, refresh_data, get_error_hours_top_data,
    get_storage_cells_stats, get_all_storage_data, get_revision_stats, get_placement_errors,
    filter_storage_data, get_group_load_monitor
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
     Output('storage-cells-kpi', 'children'),
     Output('storage-cells-detail', 'children'),
     Output('order-accuracy-kpi', 'children')],
    [Input('global-date-range', 'data')],
    prevent_initial_call=False
)
def update_main_kpi_cards(date_range):
    """Обновление KPI карточек на главной вкладке"""
    # Получаем данные по ревизиям и ячейкам хранения (не зависят от дат)
    try:
        revision_stats = get_revision_stats()
        storage_stats = get_storage_cells_stats()

        # Форматируем KPI значения для ревизий - защищаемся от None
        total_revisions = f"{revision_stats.get('total_revisions') or 0:,}"
        open_revisions = f"{revision_stats.get('open_revisions') or 0:,}"
        in_process_revisions = f"{revision_stats.get('in_process_revisions') or 0:,}"

        # Форматируем KPI значения для ячеек - защищаемся от None
        occupied = storage_stats.get('occupied_cells') or 0
        free = storage_stats.get('free_cells') or 0
        storage_kpi = f"{occupied}/{free}"
        
        occ_pct = storage_stats.get('occupied_percent') or 0
        free_pct = storage_stats.get('free_percent') or 0
        storage_detail = f"{occ_pct}% занято | {free_pct}% своб."
    except Exception as e:
        logger.error(f"Error getting revision/storage stats: {e}")
        total_revisions = "0"
        open_revisions = "0"
        in_process_revisions = "0"
        storage_kpi = "0/0"
        storage_detail = "0% занято | 0% своб."

    # Если date_range пустой, возвращаем данные только для карточек, не зависящих от дат
    if not date_range:
        return (
            total_revisions,
            open_revisions,
            in_process_revisions,
            "0%", "0", "0",
            storage_kpi,
            storage_detail,
            "100%"
        )

    start_date = date_range['start_date']
    end_date = date_range['end_date']

    try:
        # Получаем данные по ошибкам размещения за выбранный период
        placement_stats = get_placement_errors(start_date, end_date)

        # Получаем остальные данные
        accuracy, orders_without_errors, total_orders_accuracy, error_orders = get_order_accuracy(start_date, end_date)

        # Форматируем KPI значения - защищаемся от None

        # Ошибки размещения
        error_pct = placement_stats.get('error_percentage') or 0
        error_percentage = f"{error_pct}%"
        correct_count = f"{placement_stats.get('correct_count') or 0:,}"
        error_count = f"{placement_stats.get('error_count') or 0:,}"

        # Точность заказов - защищаемся от None
        accuracy_val = accuracy if accuracy is not None else 0
        accuracy_str = f"{accuracy_val:.1f}%"

        return (
            total_revisions,
            open_revisions,
            in_process_revisions,
            error_percentage,
            correct_count,
            error_count,
            storage_kpi,
            storage_detail,
            accuracy_str
        )
    except Exception as e:
        logger.error(f"Error in update_main_kpi_cards: {e}")
        return ("0", "0", "0", "0%", "0", "0", "0/0",
                "0% занято | 0% своб.", "100%")

# Callback для обновления времени последнего обновления
@callback(
    Output('last-update-time', 'children'),
    [Input('global-date-range', 'data')]
)
def update_last_update_time(date_range):
    return f"Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"

# Кэшируемая функция для получения данных при заданных датах
@lru_cache(maxsize=32)
def _get_cached_data_for_dates(start_str, end_str):
    """Кэширует все данные для заданной пары дат, чтобы избежать повторных запросов к БД."""
    performance_data_cache = get_performance_data(start_str, end_str)
    shift_comparison_cache = get_shift_comparison(start_str, end_str)
    problematic_hours_cache = get_problematic_hours(start_str, end_str)
    error_hours_cache = get_error_hours_top_data(start_str, end_str)
    return performance_data_cache, shift_comparison_cache, problematic_hours_cache, error_hours_cache


# Callback для автоматического обновления данных при изменении дат
@callback(
    [Output('global-date-range', 'data'),
     Output('performance-data-cache', 'data'),
     Output('shift-comparison-cache', 'data'),
     Output('problematic-hours-cache', 'data'),
     Output('error-hours-cache', 'data')],
    [Input('global-date-start', 'value'),
     Input('global-date-end', 'value')],
    prevent_initial_call=False
)
def update_global_date_range_and_data(start_date, end_date):
    """Автоматическое обновление данных при изменении дат в полях ввода"""
    if not start_date or not end_date:
        raise dash.exceptions.PreventUpdate

    # Преобразуем даты в строки
    if isinstance(start_date, str):
        start_str = start_date[:10]
    else:
        start_str = start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date)[:10]

    if isinstance(end_date, str):
        end_str = end_date[:10]
    else:
        end_str = end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date)[:10]

    try:
        refresh_data(start_str, end_str)

        # Получаем актуальные данные из кэша
        performance_data_cache, shift_comparison_cache, problematic_hours_cache, error_hours_cache = \
            _get_cached_data_for_dates(start_str, end_str)

        return {
            'start_date': start_str,
            'end_date': end_str
        }, performance_data_cache, shift_comparison_cache, problematic_hours_cache, error_hours_cache
    except Exception as e:
        logger.error(f"Error in update_global_date_range_and_data: {e}")
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

# Callback для открытия/закрытия модального окна ревизий по событию
@callback(
    [Output("revision-detail-modal", "className"),
     Output("revision-detail-modal-content", "className"),
     Output("revision-detail-table-body", "children")],
    [Input("open-revision-info", "n_clicks"),
     Input("close-revision-detail-modal", "n_clicks")],
    [State("revision-detail-modal", "className"),
     State("revision-detail-modal-content", "className")],
    prevent_initial_call=True
)
def toggle_revision_detail_modal(open_clicks, close_clicks, modal_class, content_class):
    """Открытие/закрытие модального окна ревизий по событию"""
    ctx = dash.callback_context
    if not ctx.triggered:
        return modal_class, content_class, []
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'close-revision-detail-modal':
        return 'modal-hidden', 'modal-content', []
    
    if button_id == 'open-revision-info' and open_clicks:
        # Получаем данные
        from data.queries_mssql import get_revision_detail_data
        detail_data = get_revision_detail_data()
        
        # Создаем строки таблицы
        table_rows = []
        for item in detail_data:
            # Цвет статуса
            status_color = '#4CAF50' if item['status_rus'] == 'Открыто' else '#FF9800'
            
            # Цвет расхождения
            variance_color = '#4CAF50' if item['variance'] == 0 else '#F44336'
            
            table_rows.append(
                html.Tr([
                    html.Td(str(item['internal_count_num']), style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '12px', 'fontWeight': 'bold'}),
                    html.Td(html.Span(item['status_rus'], style={'padding': '4px 8px', 'borderRadius': '4px', 'fontSize': '11px', 'fontWeight': 'bold', 'color': 'white', 'backgroundColor': status_color}), style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '12px'}),
                    html.Td(item['item'], style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '12px'}),
                    html.Td(item['lot'], style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '12px'}),
                    html.Td(item['location'], style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '12px'}),
                    html.Td(f"{item['quantity_counted']:,.2f}", style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '12px', 'textAlign': 'right'}),
                    html.Td(f"{item['system_quantity']:,.2f}", style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '12px', 'textAlign': 'right'}),
                    html.Td(html.Span(f"{item['variance']:+,.2f}", style={'color': variance_color, 'fontWeight': 'bold'}), style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '12px', 'textAlign': 'right'})
                ])
            )
        
        if not table_rows:
            table_rows = [html.Tr([html.Td("Нет данных", colSpan=8, style={'textAlign': 'center', 'padding': '20px', 'color': '#666'})])]
        
        return 'modal-visible', 'modal-content-visible', table_rows
    
    return modal_class, content_class, []

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
        logger.error(f"ERROR in callback: {e}")

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
    [Output('shift-employees-table-body', 'children'),
     Output('shift-table-sort-state', 'data'),
     Output('sort-status-icon', 'style'),
     Output('sort-time-icon', 'style')],
    [Input('position-filter', 'value'),
     Input('brigade-filter', 'value')]
)
def update_shift_employees_table(position_filter, brigade_filter):
    """Обновление таблицы сотрудников на смене (сбрасывает сортировку при изменении фильтров)"""

    try:
        employees, position_stats = get_employees_on_shift_new()

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
            # Определяем цвет статуса
            if status in ['На смене', 'Вышел', 'Работает']:
                status_color = '#4CAF50'  # Зеленый
            else:
                status_color = '#F44336'  # Красный

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

        # Сбрасываем состояние сортировки при изменении фильтров
        default_sort_state = {'column': None, 'direction': None}
        default_icon_style = {'marginLeft': '5px', 'fontSize': '12px', 'opacity': '0.5'}

        return rows, default_sort_state, default_icon_style, default_icon_style

    except Exception as e:
        logger.error("Error in update_shift_employees_table: %s", e)
        default_icon_style = {'marginLeft': '5px', 'fontSize': '12px', 'opacity': '0.5'}
        return [
            html.Tr([
                html.Td(f"Ошибка загрузки данных: {str(e)}", colSpan=5,
                       style={'padding': '20px', 'textAlign': 'center',
                             'color': '#F44336', 'fontSize': '14px'})
            ])
        ], {'column': None, 'direction': None}, default_icon_style, default_icon_style

# Callback для сортировки таблицы сотрудников по статусу
@callback(
    [Output('shift-employees-table-body', 'children', allow_duplicate=True),
     Output('shift-table-sort-state', 'data'),
     Output('sort-status-icon', 'style'),
     Output('sort-time-icon', 'style')],
    [Input('sort-status-header', 'n_clicks')],
    [State('shift-table-sort-state', 'data'),
     State('position-filter', 'value'),
     State('brigade-filter', 'value')],
    prevent_initial_call=True
)
def sort_by_status(n_clicks, sort_state, position_filter, brigade_filter):
    """Сортировка таблицы сотрудников по статусу: asc → desc → сброс"""
    if not n_clicks:
        raise dash.exceptions.PreventUpdate

    # Трехпозиционный цикл: None → asc → desc → None
    current_column = sort_state.get('column') if sort_state else None
    current_direction = sort_state.get('direction') if sort_state else None
    
    if current_column == 'status':
        if current_direction == 'asc':
            direction = 'desc'
        elif current_direction == 'desc':
            direction = None  # Сброс
        else:
            direction = 'asc'
    else:
        direction = 'asc'

    # Получаем данные
    try:
        employees, position_stats = get_employees_on_shift_new()

        # Применяем фильтры
        filtered_employees = employees
        if position_filter and position_filter != 'all':
            filtered_employees = [e for e in filtered_employees if e.get('Должность') == position_filter]
        if brigade_filter and brigade_filter != 'all':
            filtered_employees = [e for e in filtered_employees if e.get('Бригада') == brigade_filter]

        # Сортируем или сбрасываем
        if direction is None:
            # Сброс сортировки - исходный порядок
            new_sort_state = {'column': None, 'direction': None}
        else:
            # Сортировка по статусу: "На смене" сначала, потом "Не вышел"
            def status_sort_key(emp):
                status = emp.get('Статус', '')
                # Проверяем разные варианты написания статуса
                if status in ['На смене', 'Вышел', 'Работает']:
                    return 0 if direction == 'asc' else 1
                else:
                    return 1 if direction == 'asc' else 0

            filtered_employees.sort(key=status_sort_key)
            new_sort_state = {'column': 'status', 'direction': direction}

        # Создаем строки таблицы
        rows = []
        for employee in filtered_employees:
            status = employee.get('Статус', 'Не вышел')
            # Определяем цвет статуса
            if status in ['На смене', 'Вышел', 'Работает']:
                status_color = '#4CAF50'  # Зеленый
            else:
                status_color = '#F44336'  # Красный

            rows.append(
                html.Tr([
                    html.Td(employee.get('ФИО', ''), style={'padding': '8px', 'borderBottom': '1px solid #eee'}),
                    html.Td(employee.get('Должность', ''), style={'padding': '8px', 'borderBottom': '1px solid #eee'}),
                    html.Td(employee.get('Бригада', ''), style={'padding': '8px', 'borderBottom': '1px solid #eee'}),
                    html.Td(status, style={'padding': '8px', 'borderBottom': '1px solid #eee', 'color': status_color, 'fontWeight': 'bold'}),
                    html.Td(employee.get('Время_первой_операции', '--:--'), style={'padding': '8px', 'borderBottom': '1px solid #eee', 'color': '#666', 'textAlign': 'center'})
                ])
            )

        # Обновляем стили иконок - только одна активна, другая сбрасывается
        if new_sort_state.get('column') == 'status' and new_sort_state.get('direction'):
            # Статус активен - время сброшено
            status_icon_style = {'marginLeft': '5px', 'fontSize': '12px', 'opacity': '1', 'fontWeight': 'bold'}
            time_icon_style = {'marginLeft': '5px', 'fontSize': '12px', 'opacity': '0.3'}
        else:
            # Статус не активен - сбрасываем обе иконки
            status_icon_style = {'marginLeft': '5px', 'fontSize': '12px', 'opacity': '0.5'}
            time_icon_style = {'marginLeft': '5px', 'fontSize': '12px', 'opacity': '0.5'}

        return rows, new_sort_state, status_icon_style, time_icon_style

    except Exception as e:
        logger.error("Error in sort_by_status: %s", e)
        raise dash.exceptions.PreventUpdate


# Callback для сортировки таблицы сотрудников по времени первой операции
@callback(
    [Output('shift-employees-table-body', 'children', allow_duplicate=True),
     Output('shift-table-sort-state', 'data'),
     Output('sort-status-icon', 'style'),
     Output('sort-time-icon', 'style')],
    [Input('sort-time-header', 'n_clicks')],
    [State('shift-table-sort-state', 'data'),
     State('position-filter', 'value'),
     State('brigade-filter', 'value')],
    prevent_initial_call=True
)
def sort_by_time(n_clicks, sort_state, position_filter, brigade_filter):
    """Сортировка таблицы сотрудников по времени: asc → desc → сброс"""
    if not n_clicks:
        raise dash.exceptions.PreventUpdate

    # Трехпозиционный цикл: None → asc → desc → None
    current_column = sort_state.get('column') if sort_state else None
    current_direction = sort_state.get('direction') if sort_state else None
    
    if current_column == 'time':
        if current_direction == 'asc':
            direction = 'desc'
        elif current_direction == 'desc':
            direction = None  # Сброс
        else:
            direction = 'asc'
    else:
        direction = 'asc'

    # Получаем данные
    try:
        employees, position_stats = get_employees_on_shift_new()

        # Применяем фильтры
        filtered_employees = employees
        if position_filter and position_filter != 'all':
            filtered_employees = [e for e in filtered_employees if e.get('Должность') == position_filter]
        if brigade_filter and brigade_filter != 'all':
            filtered_employees = [e for e in filtered_employees if e.get('Бригада') == brigade_filter]

        # Сортируем или сбрасываем
        if direction is None:
            # Сброс сортировки - исходный порядок
            new_sort_state = {'column': None, 'direction': None}
        else:
            # Сортировка по времени первой операции
            def time_sort_key(emp):
                time_str = emp.get('Время_первой_операции', '--:--')
                if time_str == '--:--':
                    # Сотрудники без времени всегда в конце
                    return '99:99' if direction == 'asc' else '00:00'
                return time_str

            filtered_employees.sort(key=time_sort_key)
            new_sort_state = {'column': 'time', 'direction': direction}

        # Создаем строки таблицы
        rows = []
        for employee in filtered_employees:
            status = employee.get('Статус', 'Не вышел')
            # Определяем цвет статуса
            if status in ['На смене', 'Вышел', 'Работает']:
                status_color = '#4CAF50'  # Зеленый
            else:
                status_color = '#F44336'  # Красный

            rows.append(
                html.Tr([
                    html.Td(employee.get('ФИО', ''), style={'padding': '8px', 'borderBottom': '1px solid #eee'}),
                    html.Td(employee.get('Должность', ''), style={'padding': '8px', 'borderBottom': '1px solid #eee'}),
                    html.Td(employee.get('Бригада', ''), style={'padding': '8px', 'borderBottom': '1px solid #eee'}),
                    html.Td(status, style={'padding': '8px', 'borderBottom': '1px solid #eee', 'color': status_color, 'fontWeight': 'bold'}),
                    html.Td(employee.get('Время_первой_операции', '--:--'), style={'padding': '8px', 'borderBottom': '1px solid #eee', 'color': '#666', 'textAlign': 'center'})
                ])
            )

        # Обновляем стили иконок - только одна активна, другая сбрасывается
        if new_sort_state.get('column') == 'time' and new_sort_state.get('direction'):
            # Время активно - статус сброшен
            status_icon_style = {'marginLeft': '5px', 'fontSize': '12px', 'opacity': '0.3'}
            time_icon_style = {'marginLeft': '5px', 'fontSize': '12px', 'opacity': '1', 'fontWeight': 'bold'}
        else:
            # Время не активно - сбрасываем обе иконки
            status_icon_style = {'marginLeft': '5px', 'fontSize': '12px', 'opacity': '0.5'}
            time_icon_style = {'marginLeft': '5px', 'fontSize': '12px', 'opacity': '0.5'}

        return rows, new_sort_state, status_icon_style, time_icon_style

    except Exception as e:
        logger.error("Error in sort_by_time: %s", e)
        raise dash.exceptions.PreventUpdate

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
                html.Th('Оп/час', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'})
            ])),
            html.Tbody([
                html.Tr([
                    html.Td("Нет данных", colSpan=5, style={'textAlign': 'center', 'padding': '20px', 'color': '#666'})
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

# Callback для переключения между таблицами производительности
@callback(
    [Output('table-all-employees', 'className'),
     Output('table-top-best', 'className'),
     Output('table-top-worst', 'className'),
     Output('current-table-view', 'data')],
    [Input('prev-table', 'n_clicks'),
     Input('next-table', 'n_clicks')],
    [State('current-table-view', 'data')],
    prevent_initial_call=True
)
def switch_performance_table_view(prev_clicks, next_clicks, current_view):
    """Переключение между таблицами: все сотрудники, топ-5 лучших, топ-5 худших"""
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    views = ['all', 'best', 'worst']
    current_index = views.index(current_view) if current_view in views else 0

    if button_id == 'next-table':
        current_index = (current_index + 1) % len(views)
    elif button_id == 'prev-table':
        current_index = (current_index - 1) % len(views)

    new_view = views[current_index]
    classes = ['table-view', 'table-view', 'table-view']

    for i in range(len(views)):
        if i == current_index:
            classes[i] = 'table-view active'

    return classes[0], classes[1], classes[2], new_view


# Callback для обновления статистики смены на главной вкладке
@callback(
    Output('shift-stats-info', 'children'),
    [Input('global-date-range', 'data')]
)
def update_shift_stats_info(date_range):
    """Обновление информации о смене в общей сводке с данными мониторинга нагрузки групп"""
    
    try:
        # Получаем данные мониторинга нагрузки групп из VIEW
        groups_data = get_group_load_monitor()
        
        if not groups_data:
            return html.Div("Смена отдыхает или нет данных о нагрузке",
                          style={'color': '#666', 'textAlign': 'center', 'padding': '20px', 'fontSize': '14px'})
        
        # Цветовая карта
        color_map = {
            'GREEN': '#4CAF50',
            'YELLOW': '#FF9800',
            'RED': '#F44336',
            'GRAY': '#9E9E9E'
        }
        
        # Создаем строки таблицы
        table_rows = []
        
        # Заголовок таблицы
        table_rows.append(
            html.Thead([
                html.Tr([
                    html.Th('Группа', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                    html.Th('Тип работы', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                    html.Th('Статус', style={'color': '#666', 'padding': '12px', 'textAlign': 'center', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'})
                ])
            ])
        )
        
        # Данные таблицы
        tbody_rows = []
        for item in groups_data:
            group_name = item.get('group_name', '')
            work_type = item.get('work_type', '')
            status_color = item.get('status_color', 'GRAY')
            
            color = color_map.get(status_color, '#9E9E9E')
            
            tbody_rows.append(
                html.Tr([
                    html.Td(group_name, style={'padding': '10px 12px', 'fontSize': '13px', 'borderBottom': '1px solid #f0f0f0'}),
                    html.Td(work_type, style={'padding': '10px 12px', 'fontSize': '13px', 'borderBottom': '1px solid #f0f0f0'}),
                    html.Td(
                        html.Span(
                            '●',
                            style={
                                'color': color,
                                'fontSize': '28px',
                                'fontWeight': 'bold'
                            }
                        ),
                        style={'padding': '10px 12px', 'textAlign': 'center', 'borderBottom': '1px solid #f0f0f0'}
                    )
                ], className='table-row-hover')
            )
        
        table_rows.append(html.Tbody(tbody_rows))
        
        # Создаем таблицу
        stats_table = html.Table(
            table_rows,
            style={'width': '100%', 'borderCollapse': 'collapse'}
        )
        
        return html.Div([
            html.H4("Мониторинг нагрузки групп",
                   style={'marginBottom': '12px', 'color': '#1976d2', 'fontSize': '18px', 'fontWeight': 'bold'}),
            
            html.Div(stats_table, style={'maxHeight': '450px', 'overflowY': 'auto'})
        ], style={'height': '100%', 'overflow': 'hidden'})
        
    except Exception as e:
        logger.error(f"Error in update_shift_stats_info: {e}")
        return html.Div(f"Ошибка загрузки данных: {str(e)}",
                       style={'color': '#F44336', 'padding': '15px', 'textAlign': 'center', 'fontSize': '14px'})
