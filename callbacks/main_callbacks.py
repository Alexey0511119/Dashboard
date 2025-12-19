import dash
from dash import Input, Output, State, callback, html
import pandas as pd
from datetime import datetime, timedelta
import json
from data.queries import (
    get_orders_timely, get_avg_operation_time, get_total_earnings, get_order_accuracy,
    get_avg_productivity, get_performance_data, get_shift_comparison, 
    get_problematic_hours, get_orders_table, get_arrival_timeliness,
    get_order_timeliness, get_fines_data, get_employee_analytics,
    get_employee_operations_detail, get_employee_fines_details,
    get_employees_on_shift, refresh_data, get_error_hours_top_data,
    get_storage_cells_stats
)
from components.charts import (
    create_order_accuracy_chart, create_problematic_hours_chart,
    create_timeliness_chart, create_operations_type_chart,
    create_time_distribution_pie_echarts, create_idle_intervals_bar_echarts,
    create_fines_pie_chart, create_fines_amount_bar_chart,
    create_employee_fines_chart
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
    [Output('orders-timely-kpi', 'children'),
     Output('orders-percentage-kpi', 'children'),
     Output('avg-operation-time-kpi', 'children'),
     Output('avg-productivity-kpi', 'children'),
     Output('storage-cells-kpi', 'children'),
     Output('storage-cells-detail', 'children'),
     Output('order-accuracy-kpi', 'children'),
     Output('order-accuracy-detail', 'children')],
    [Input('global-date-range', 'data')]
)
def update_main_kpi_cards(date_range):
    """Обновление KPI карточек на главной вкладке"""
    if not date_range:
        return "0", "0%", "0 мин", "0 оп/ч", "0/0", "0% занято | 0% своб.", "100%", "0 заказов без ошибок"
    
    start_date = date_range['start_date']
    end_date = date_range['end_date']
    
    try:
        timely_orders, delayed_orders, total_orders, percentage = get_orders_timely(start_date, end_date)
        avg_time = get_avg_operation_time(start_date, end_date)
        accuracy, orders_without_errors, total_orders_accuracy, error_orders = get_order_accuracy(start_date, end_date)
        avg_productivity, active_employees = get_avg_productivity(start_date, end_date)
        
        # Получаем статистику по ячейкам хранения
        storage_stats = get_storage_cells_stats()
        
        # ИСПРАВЛЕННЫЙ ФОРМАТ: занято/свободно
        storage_kpi = f"{storage_stats['occupied_cells']}/{storage_stats['free_cells']}"
        storage_detail = f"{storage_stats['occupied_percent']}% занято | {storage_stats['free_percent']}% своб."
        
        return (
            f"{timely_orders:,}",
            f"↗ {percentage}% ({total_orders} всего)",
            f"{avg_time:.1f} мин",
            f"↗ {avg_productivity} оп/ч",
            storage_kpi,  # ИСПРАВЛЕНО: занято/свободно
            storage_detail,
            f"{accuracy:.1f}%",
            f"↗ {orders_without_errors:,} заказов без ошибок"
        )
    except Exception as e:
        print(f"Error in update_main_kpi_cards: {e}")
        return "0", "0%", "0 мин", "0 оп/ч", "0/0", "0% занято | 0% своб.", "100%", "0 заказов без ошибок"

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

# Новый callback для обновления информации о смене в общей сводке
@callback(
    Output('shift-stats-info', 'children'),
    [Input('global-date-range', 'data')]
)
def update_shift_stats_info(date_range):
    """Обновление информации о смене в общей сводке"""
    
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
        
        # Создаем визуализацию (ОТРЕГУЛИРОВАННЫЕ РАЗМЕРЫ - шрифт как в таблице)
        position_cards = []
        for position, stats in position_analysis.items():
            if position != 'Не указана':
                position_cards.append(
                    html.Div([
                        html.Div([
                            html.Strong(position, style={'fontSize': '14px', 'color': '#333'}),  # ТАКОЙ ЖЕ как в таблице
                            html.Span(f" ({stats['total']} чел.)", style={'fontSize': '12px', 'color': '#666'})  # Немного меньше
                        ], style={'marginBottom': '6px'}),  # Немного отступа
                        
                        html.Div([
                            html.Div([
                                html.Span("✅", style={'marginRight': '4px', 'fontSize': '12px'}),
                                html.Span(f"{stats['on_work']} на работе", 
                                        style={'color': '#4CAF50', 'fontWeight': 'bold', 'fontSize': '12px'})  # 12px для компактности
                            ], style={'flex': '1', 'textAlign': 'center'}),
                            
                            html.Div([
                                html.Span("❌", style={'marginRight': '4px', 'fontSize': '12px'}),
                                html.Span(f"{stats['not_come']} не вышли", 
                                        style={'color': '#F44336', 'fontWeight': 'bold', 'fontSize': '12px'})  # 12px для компактности
                            ], style={'flex': '1', 'textAlign': 'center'})
                        ], style={'display': 'flex', 'justifyContent': 'space-between'})
                    ], style={
                        'background': '#fff',
                        'border': '1px solid #e0e0e0',
                        'borderRadius': '6px',
                        'padding': '10px',  # Увеличено для лучшего отображения текста
                        'marginBottom': '8px',
                        'boxShadow': '0 1px 2px rgba(0,0,0,0.1)'
                    })
                )
        
        return html.Div([
            # Общая статистика (ШРИФТ КАК В ТАБЛИЦЕ)
            html.Div([
                html.H4("Общая статистика смены", 
                       style={'marginBottom': '12px', 'color': '#1976d2', 'fontSize': '18px', 'fontWeight': 'bold'}),  # Заголовок побольше
                
                html.Div([
                    html.Div([
                        html.Div(f"{len(employees)}", 
                               style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#1976d2', 'textAlign': 'center'}),  # Увеличен
                        html.Div("Всего сотрудников", 
                               style={'fontSize': '12px', 'color': '#666', 'textAlign': 'center'})  # 12px как в таблице
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
            ], style={'marginBottom': '16px'}),
            
            # Анализ по должностям
            html.Div([
                html.H4("Анализ по должностям", 
                       style={'marginBottom': '12px', 'color': '#ed6c02', 'fontSize': '18px', 'fontWeight': 'bold'}),
                
                html.Div(position_cards, style={'maxHeight': '380px', 'overflowY': 'auto'})  # Оставили прокрутку на случай большого количества должностей
            ])
        ], style={'height': '100%', 'overflow': 'hidden'})
        
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