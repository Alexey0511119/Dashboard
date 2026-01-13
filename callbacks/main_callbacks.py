import dash
from dash import Input, Output, State, callback, html
import pandas as pd
from datetime import datetime, timedelta
import json
import random  # Добавим для генерации тестовых данных
from data.queries import (
    get_orders_timely, get_avg_operation_time, get_total_earnings, get_order_accuracy,
    get_avg_productivity, get_performance_data, get_shift_comparison, 
    get_problematic_hours, get_orders_table, get_arrival_timeliness,
    get_order_timeliness, get_fines_data, get_employee_analytics,
    get_employee_operations_detail, get_employee_fines_details,
    get_employees_on_shift, refresh_data, get_error_hours_top_data,
    get_storage_cells_stats, get_all_storage_data, filter_storage_data,
    get_revision_stats, get_placement_errors  # НОВЫЕ ИМПОРТЫ
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
        import traceback
        traceback.print_exc()
        return ("0", "0", "0", "0%", "0", "0", "Ошибка загрузки", "0/0", 
                "0% занято | 0% своб.", "100%", "0 заказов без ошибок")

# Callback для обновления таблицы сотрудников на смене
@callback(
    Output('shift-employees-table-body', 'children'),
    [Input('position-filter', 'value'),
     Input('brigade-filter', 'value')]
)
def update_shift_employees_table(position_filter, brigade_filter):
    """Обновление таблицы сотрудников на смене - ТОЛЬКО СЕГОДНЯШНЯЯ СМЕНА"""
    
    try:
        employees, position_stats = get_employees_on_shift()
        
        # Применяем фильтры
        filtered_employees = employees
        
        if position_filter and position_filter != 'all':
            filtered_employees = [e for e in filtered_employees if e['Должность'] == position_filter]
        
        if brigade_filter and brigade_filter != 'all':
            filtered_employees = [e for e in filtered_employees if e['Бригада'] == brigade_filter]
        
        # Статистика по статусам
        status_stats = {
            'На работе': 0,
            'Не вышел': 0
        }
        
        for emp in filtered_employees:
            status = emp.get('Статус', 'Не вышел')
            if status in status_stats:
                status_stats[status] += 1
        
        # Создаем строки таблицы
        rows = []
        for employee in filtered_employees:
            status = employee.get('Статус', 'Не вышел')
            status_color = '#F44336' if status == 'Не вышел' else '#4CAF50'
            
            first_op_time = employee.get('Время_первой_операции', '--:--')
            time_color = '#1976d2'
            if first_op_time == '--:--' and status == 'На работе':
                time_color = '#F44336'
            
            rows.append(
                html.Tr([
                    html.Td(
                        employee['ФИО'], 
                        style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px'}
                    ),
                    html.Td(
                        employee['Должность'], 
                        style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px'}
                    ),
                    html.Td(
                        html.Span(
                            first_op_time,
                            style={'color': time_color, 'fontWeight': 'bold'}
                        ), 
                        style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px'}
                    ),
                    html.Td(
                        html.Span(
                            status,
                            style={
                                'padding': '4px 8px',
                                'borderRadius': '4px',
                                'fontSize': '12px',
                                'fontWeight': 'bold',
                                'color': 'white',
                                'backgroundColor': status_color
                            }
                        ),
                        style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px'}
                    )
                ])
            )
        
        if not rows:
            rows.append(
                html.Tr([
                    html.Td("Сегодня смена отдыхает или нет данных", colSpan=4,
                           style={'textAlign': 'center', 'padding': '20px', 'color': '#666'})
                ])
            )
        else:
            # Итоговая строка
            rows.append(
                html.Tr([
                    html.Td(
                        html.Strong("ИТОГО по фильтру:"),
                        colSpan=2,
                        style={'padding': '12px', 'borderTop': '2px solid #ddd', 'fontSize': '14px', 'fontWeight': 'bold', 'textAlign': 'right'}
                    ),
                    html.Td(
                        "",
                        style={'padding': '12px', 'borderTop': '2px solid #ddd', 'fontSize': '14px'}
                    ),
                    html.Td(
                        html.Div([
                            html.Span("На работе: ", style={'color': '#4CAF50', 'fontWeight': 'bold'}),
                            html.Span(f"{status_stats['На работе']}", style={'marginRight': '10px'}),
                            html.Span("Не вышел: ", style={'color': '#F44336', 'fontWeight': 'bold'}),
                            html.Span(f"{status_stats['Не вышел']}")
                        ]),
                        style={'padding': '12px', 'borderTop': '2px solid #ddd', 'fontSize': '12px'}
                    )
                ])
            )
        
        return rows
        
    except Exception as e:
        print(f"Error in update_shift_employees_table: {e}")
        return [
            html.Tr([
                html.Td(f"Ошибка загрузки данных: {str(e)}", colSpan=4,
                       style={'textAlign': 'center', 'padding': '20px', 'color': '#F44336'})
            ])
        ]

# НОВЫЙ ВАРИАНТ: Callback для обновления информации о смене в общей сводке
@callback(
    Output('shift-stats-info', 'children'),
    [Input('global-date-range', 'data')]
)
def update_shift_stats_info(date_range):
    """Обновление информации о смене в общей сводке - ТАБЛИЦА С ЦВЕТОВОЙ ИНДИКАЦИЕЙ"""
    
    from data.queries import get_employees_on_shift
    
    try:
        employees, position_stats = get_employees_on_shift()
        
        if not employees:
            return html.Div("Сегодня смена отдыхает", 
                          style={'color': '#666', 'textAlign': 'center', 'padding': '20px', 'fontSize': '14px'})
        
        # Статистика по статусам
        status_stats = {
            'На работе': 0,
            'Не вышел': 0
        }
        
        for emp in employees:
            status = emp.get('Статус', 'Не вышел')
            if status in status_stats:
                status_stats[status] += 1
        
        # Анализ по должностям
        position_analysis = {}
        for emp in employees:
            position = emp.get('Должность', 'Не указана')
            status = emp.get('Статус', 'Не вышел')
            
            if position not in position_analysis:
                position_analysis[position] = {
                    'total': 0,
                    'on_work': 0,
                    'not_come': 0,
                    'employees': []
                }
            
            position_analysis[position]['total'] += 1
            if status == 'На работе':
                position_analysis[position]['on_work'] += 1
            else:
                position_analysis[position]['not_come'] += 1
            
            position_analysis[position]['employees'].append({
                'name': emp.get('ФИО', 'Неизвестно'),
                'status': status,
                'time': emp.get('Время_первой_операции', '--:--')
            })
        
        # ГЕНЕРИРУЕМ ТЕСТОВЫЕ ДАННЫЕ ДЛЯ ОТКРЫТЫХ ЗАДАНИЙ
        # Создаем словарь с тестовыми данными для каждой должности
        test_open_tasks = {}
        for position in position_analysis.keys():
            if position != 'Не указана':
                # Генерируем случайное количество открытых заданий от 1 до 20
                test_open_tasks[position] = random.randint(1, 20)
        
        # Создаем таблицу вместо карточек
        table_rows = []
        
        # Создаем заголовок таблицы (УПРОЩЕННЫЙ - 5 колонок)
        table_header = html.Tr([
            html.Th("Должность", style={'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #ddd', 'background': '#f8f9fa'}),
            html.Th("На работе", style={'padding': '12px', 'textAlign': 'center', 'fontSize': '14px', 'borderBottom': '2px solid #ddd', 'background': '#f8f9fa'}),
            html.Th("Не вышли", style={'padding': '12px', 'textAlign': 'center', 'fontSize': '14px', 'borderBottom': '2px solid #ddd', 'background': '#f8f9fa'}),
            html.Th("Открытые задания", style={'padding': '12px', 'textAlign': 'center', 'fontSize': '14px', 'borderBottom': '2px solid #ddd', 'background': '#f8f9fa'}),
            html.Th("Индикация", style={'padding': '12px', 'textAlign': 'center', 'fontSize': '14px', 'borderBottom': '2px solid #ddd', 'background': '#f8f9fa'})
        ])
        table_rows.append(table_header)
        
        # Заполняем таблицу данными
        for position, stats in position_analysis.items():
            if position != 'Не указана':
                total = stats['total']
                on_work = stats['on_work']
                not_come = stats['not_come']
                
                # Рассчитываем процент сотрудников на смене
                percentage_on_work = 0
                if total > 0:
                    percentage_on_work = round((on_work / total) * 100, 1)
                
                # Получаем количество открытых заданий (тестовые данные)
                open_tasks = test_open_tasks.get(position, 0)
                
                # Определяем цвет индикации на основе процента сотрудников на смене
                indicator_color = ''
                indicator_text = ''
                
                if percentage_on_work >= 90:
                    indicator_color = '#4CAF50'  # зеленый
                    indicator_text = '✓'
                elif percentage_on_work >= 70:
                    indicator_color = '#FFC107'  # желтый
                    indicator_text = '⚠'
                elif percentage_on_work >= 65:
                    indicator_color = '#FF9800'  # оранжевый
                    indicator_text = '⚠'
                else:
                    indicator_color = '#F44336'  # красный
                    indicator_text = '✗'
                
                # Создаем строку таблицы (УПРОЩЕННАЯ - 5 колонок)
                row = html.Tr([
                    html.Td(
                        html.Strong(position),
                        style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px'}
                    ),
                    html.Td(
                        html.Span(str(on_work), style={'color': '#4CAF50', 'fontWeight': 'bold', 'fontSize': '16px'}),
                        style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'textAlign': 'center'}
                    ),
                    html.Td(
                        html.Span(str(not_come), style={'color': '#F44336', 'fontWeight': 'bold', 'fontSize': '16px'}),
                        style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'textAlign': 'center'}
                    ),
                    html.Td(
                        html.Span(str(open_tasks), style={'color': '#1976d2', 'fontWeight': 'bold', 'fontSize': '16px'}),
                        style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'textAlign': 'center'}
                    ),
                    html.Td(
                        html.Div(
                            style={
                                'width': '30px',
                                'height': '30px',
                                'borderRadius': '50%',
                                'backgroundColor': indicator_color,
                                'display': 'flex',
                                'alignItems': 'center',
                                'justifyContent': 'center',
                                'margin': '0 auto',
                                'color': 'white',
                                'fontWeight': 'bold',
                                'fontSize': '16px'
                            },
                            children=indicator_text
                        ),
                        style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'textAlign': 'center'}
                    )
                ])
                table_rows.append(row)
        
        # Итоговая строка (УПРОЩЕННАЯ)
        if position_analysis:
            total_on_work = sum(stats['on_work'] for stats in position_analysis.values() if 'on_work' in stats)
            total_not_come = sum(stats['not_come'] for stats in position_analysis.values() if 'not_come' in stats)
            total_open_tasks = sum(test_open_tasks.values())
            total_all = total_on_work + total_not_come
            
            # Рассчитываем общий процент
            total_percentage = 0
            if total_all > 0:
                total_percentage = round((total_on_work / total_all) * 100, 1)
            
            # Определяем цвет для общего индикатора
            total_indicator_color = ''
            total_indicator_text = ''
            if total_percentage >= 90:
                total_indicator_color = '#4CAF50'
                total_indicator_text = '✓'
            elif total_percentage >= 70:
                total_indicator_color = '#FFC107'
                total_indicator_text = '⚠'
            elif total_percentage >= 65:
                total_indicator_color = '#FF9800'
                total_indicator_text = '⚠'
            else:
                total_indicator_color = '#F44336'
                total_indicator_text = '✗'
            
            total_row = html.Tr([
                html.Td(
                    html.Strong("ИТОГО"),
                    style={'padding': '12px', 'borderTop': '2px solid #ddd', 'fontSize': '14px', 'fontWeight': 'bold'}
                ),
                html.Td(
                    html.Span(html.Strong(str(total_on_work)), style={'color': '#4CAF50', 'fontSize': '16px'}),
                    style={'padding': '12px', 'borderTop': '2px solid #ddd', 'fontSize': '14px', 'textAlign': 'center', 'fontWeight': 'bold'}
                ),
                html.Td(
                    html.Span(html.Strong(str(total_not_come)), style={'color': '#F44336', 'fontSize': '16px'}),
                    style={'padding': '12px', 'borderTop': '2px solid #ddd', 'fontSize': '14px', 'textAlign': 'center', 'fontWeight': 'bold'}
                ),
                html.Td(
                    html.Strong(str(total_open_tasks)),
                    style={'padding': '12px', 'borderTop': '2px solid #ddd', 'fontSize': '14px', 'textAlign': 'center', 'fontWeight': 'bold', 'color': '#1976d2'}
                ),
                html.Td(
                    html.Div(
                        style={
                            'width': '30px',
                            'height': '30px',
                            'borderRadius': '50%',
                            'backgroundColor': total_indicator_color,
                            'display': 'flex',
                            'alignItems': 'center',
                            'justifyContent': 'center',
                            'margin': '0 auto',
                            'color': 'white',
                            'fontWeight': 'bold',
                            'fontSize': '16px'
                        },
                        children=total_indicator_text
                    ),
                    style={'padding': '12px', 'borderTop': '2px solid #ddd', 'fontSize': '14px', 'textAlign': 'center'}
                )
            ])
            table_rows.append(total_row)
        
        # Создаем контейнер таблицы
        table_container = html.Table(
            table_rows,
            style={
                'width': '100%',
                'borderCollapse': 'collapse',
                'marginTop': '10px',
                'backgroundColor': 'white',
                'borderRadius': '8px',
                'overflow': 'hidden',
                'boxShadow': '0 1px 3px rgba(0,0,0,0.1)'
            }
        )
        
        # Примечание о тестовых данных
        test_note = html.Div([
            html.P(
                "Данные в колонке 'Открытые задания' являются тестовыми и генерируются случайным образом. "
                "После подключения к реальным данным они будут заменены актуальной информацией.",
                style={'fontSize': '12px', 'color': '#666', 'fontStyle': 'italic', 'margin': '10px 0 0 0', 'textAlign': 'center'}
            )
        ])
        
        return html.Div([
            # Общая статистика смены (оставляем как было)
            html.Div([
                html.H4("Общая статистика смены", 
                       style={'marginBottom': '12px', 'color': '#1976d2', 'fontSize': '18px', 'fontWeight': 'bold'}),
                
                html.Div([
                    html.Div([
                        html.Div(f"{len(employees)}", 
                               style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#1976d2', 'textAlign': 'center'}),
                        html.Div("Всего сотрудников", 
                               style={'fontSize': '12px', 'color': '#666', 'textAlign': 'center'})
                    ], style={'flex': '1', 'padding': '8px'}),
                    
                    html.Div([
                        html.Div(f"{status_stats['На работе']}", 
                               style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#4CAF50', 'textAlign': 'center'}),
                        html.Div("На работе", 
                               style={'fontSize': '12px', 'color': '#666', 'textAlign': 'center'})
                    ], style={'flex': '1', 'padding': '8px'}),
                    
                    html.Div([
                        html.Div(f"{status_stats['Не вышел']}", 
                               style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#F44336', 'textAlign': 'center'}),
                        html.Div("Не вышли", 
                               style={'fontSize': '12px', 'color': '#666', 'textAlign': 'center'})
                    ], style={'flex': '1', 'padding': '8px'})
                ], style={'display': 'flex', 'justifyContent': 'space-around', 'marginBottom': '16px'}),
            ], style={'marginBottom': '20px'}),
            
            # Новая упрощенная таблица
            html.Div([
                html.H4("Анализ по должностям с открытыми заданиями", 
                       style={'marginBottom': '12px', 'color': '#ed6c02', 'fontSize': '18px', 'fontWeight': 'bold'}),
                
                table_container,
                test_note
            ])
        ], style={'height': '100%', 'overflowY': 'auto'})
        
    except Exception as e:
        print(f"Error in update_shift_stats_info: {e}")
        return html.Div(f"Ошибка загрузки данных: {str(e)}", 
                       style={'color': '#F44336', 'padding': '15px', 'textAlign': 'center', 'fontSize': '14px'})

# Callback для обновления таблиц производительности (перенесены на вкладку Производительность)
@callback(
    [Output('table-all-employees', 'children'),
     Output('table-top-best', 'children'),
     Output('table-top-worst', 'children'),
     Output('table-title', 'children')],
    [Input('performance-data-cache', 'data'),
     Input('current-table-view', 'data')]
)
def update_performance_tables(data, current_view):
    """Обновление таблиц производительности на вкладке Производительность"""
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
        
        return empty_table, empty_table, empty_table, "Все сотрудники"
    
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
    
    titles = {
        'all': 'Все сотрудники',
        'best': 'Топ-5 лучших',
        'worst': 'Топ-5 худших'
    }
    current_title = titles.get(current_view, 'Все сотрудники')
    
    return all_employees_table, best_table, worst_table, current_title

# Callback для переключения таблиц производительности
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
def switch_table_view(prev_clicks, next_clicks, current_view):
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
        print(f"DEBUG: Открытие модального окна")
        return 'modal-visible', 'modal-content-visible'
    elif button_id == 'close-storage-modal':
        print(f"DEBUG: Закрытие модального окна")
        return 'modal-hidden', 'modal-content'
    
    return modal_class, content_class
    
@callback(
    Output("storage-all-data", "data"),
    Input("storage-cells-modal", "className")
)
def load_storage_data(modal_class):
    """Загрузка всех данных по ячейкам при открытии модального окна"""
    if modal_class == 'modal-visible':
        print("Загрузка данных по ячейкам хранения...")
        all_data = get_all_storage_data()
        return all_data
    return dash.no_update

# Добавьте новый Input в callback update_storage_filters_and_charts:

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
    
    print(f"=== DEBUG update_storage_filters_and_charts ===")
    print(f"Only empty checkbox value: {only_empty_val}")
    print(f"Is only empty active: {'empty' in only_empty_val if only_empty_val else False}")
    
    if not all_data or 'all_data' not in all_data:
        # Возвращаем пустые опции если данных нет
        empty_options = [{'label': 'Все', 'value': 'Все'}]
        empty_chart = {"title": {"text": "Нет данных", "left": "center"}}
        return (
            empty_options, empty_options, empty_options, empty_options, empty_options,
            "0", "0", "0", "0%", empty_chart, empty_chart, empty_chart,
            {'storage_type': 'Все', 'locating_zone': 'Все', 'allocation_zone': 'Все', 
             'location_type': 'Все', 'work_zone': 'Все', 'only_empty': False}
        )
    
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
        # Если выбрана галочка "только пустые", показываем только пустые ячейки
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
    
    # ВАЖНОЕ ИЗМЕНЕНИЕ: Добавляем timestamp к диаграмме чтобы избежать кэширования
    import time
    timestamp = int(time.time() * 1000)
    
    # Добавляем timestamp к конфигурации диаграммы
    if 'title' in types_bar_chart:
        original_title = types_bar_chart['title'].get('text', '')
        types_bar_chart['title']['text'] = f"{original_title}"
        types_bar_chart['_timestamp'] = timestamp  # Скрытый параметр для обновления
    
    # Текущие значения фильтров для сохранения
    current_filter_values = {
        'storage_type': storage_type_val,
        'locating_zone': locating_zone_val,
        'allocation_zone': allocation_zone_val,
        'location_type': location_type_val,
        'work_zone': work_zone_val,
        'only_empty': is_only_empty
    }
    
    print(f"Returning chart with series count: {len(types_bar_chart.get('series', []))}")
    
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
    
    print(f"DEBUG: Кнопка сброса нажата: {button_id}")
    print(f"DEBUG: Текущие значения фильтров:")
    print(f"  storage: {current_storage}")
    print(f"  locating: {current_locating}")
    print(f"  allocation: {current_allocation}")
    print(f"  location: {current_location}")
    print(f"  work: {current_work}")
    
    # Начальные значения
    new_storage = current_storage
    new_locating = current_locating
    new_allocation = current_allocation
    new_location = current_location
    new_work = current_work
    
    # Если нажата кнопка "Сбросить все"
    if button_id == "reset-all-filters-btn":
        print("Сброс ВСЕХ фильтров")
        return ['Все', 'Все', 'Все', 'Все', 'Все']
    
    # Если нажата кнопка сброса конкретного фильтра
    if button_id == "reset-storage-type-btn":
        new_storage = 'Все'
        print("Сброс только фильтра: Тип хранения")
    elif button_id == "reset-locating-zone-btn":
        new_locating = 'Все'
        print("Сброс только фильтра: Зона размещения")
    elif button_id == "reset-allocation-zone-btn":
        new_allocation = 'Все'
        print("Сброс только фильтра: Зона резервирования")
    elif button_id == "reset-location-type-btn":
        new_location = 'Все'
        print("Сброс только фильтра: Тип МХ")
    elif button_id == "reset-work-zone-btn":
        new_work = 'Все'
        print("Сброс только фильтра: Рабочая зона")
    
    print(f"DEBUG: Новые значения фильтров:")
    print(f"  storage: {new_storage}")
    print(f"  locating: {new_locating}")
    print(f"  allocation: {new_allocation}")
    print(f"  location: {new_location}")
    print(f"  work: {new_work}")
    
    return new_storage, new_locating, new_allocation, new_location, new_work