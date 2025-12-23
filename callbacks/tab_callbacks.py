import dash
from dash import Input, Output, callback, html
from datetime import datetime, timedelta
from data.queries import (
    get_orders_table, get_arrival_timeliness, get_order_timeliness,
    get_fines_data, get_shift_comparison, get_timeliness_chart_data
)
from components.charts import (
    create_order_accuracy_chart, create_problematic_hours_chart,
    create_timeliness_chart, create_fines_pie_chart, create_fines_amount_bar_chart
)

# Callback для обновления таблицы заказов
@callback(
    Output('orders-table-body', 'children'),
    [Input('global-date-range', 'data')]
)
def update_orders_table(date_range):
    """Обновление таблицы заказов"""
    if not date_range:
        return []
    
    start_date = date_range['start_date']
    end_date = date_range['end_date']
    
    orders = get_orders_table(start_date, end_date)
    
    table_rows = []
    for idx, order in enumerate(orders):
        row_class = ''
        status_color = '#9E9E9E'
        
        if order['status'] == 'В процессе':
            row_class = 'orders-table-row-in-process'
            status_color = '#2196F3'
        elif order['status'] == 'Просрочено':
            row_class = 'orders-table-row-overdue'
            status_color = '#F44336'
        elif order['status'] == 'Выполнено':
            row_class = 'orders-table-row-completed'
            status_color = '#4CAF50'
        elif order['status'] == 'Без статуса':
            row_class = 'orders-table-row-no-status'
            status_color = '#9E9E9E'
        
        table_rows.append(
            html.Tr([
                html.Td(
                    order['id'],
                    style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px'}
                ),
                html.Td(
                    order['type'],
                    style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px'}
                ),
                html.Td(
                    html.Span(
                        order['status'],
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
                ),
                html.Td(
                    order['create_date'],
                    style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px'}
                ),
                html.Td(
                    "",
                    style={
                        'padding': '12px', 
                        'borderBottom': '1px solid #eee', 
                        'fontSize': '14px',
                        'color': '#F44336'
                    }
                )
            ], className=row_class)
        )
    
    return table_rows

# Callback для обновления KPI своевременности
@callback(
    [Output('timely-arrivals-kpi', 'children'),
     Output('timely-orders-kpi', 'children'),
     Output('delayed-arrivals-kpi', 'children'),
     Output('delayed-orders-kpi', 'children')],
    [Input('global-date-range', 'data')]
)
def update_timeliness_kpi(date_range):
    """Обновление KPI своевременности"""
    if not date_range:
        return "0", "0", "0", "0"
    
    start_date = date_range['start_date']
    end_date = date_range['end_date']
    
    try:
        timely_arrivals, delayed_arrivals = get_arrival_timeliness(start_date, end_date)
        timely_orders, delayed_orders = get_order_timeliness(start_date, end_date)
        
        return (
            str(timely_arrivals),
            str(timely_orders),
            str(delayed_arrivals),
            str(delayed_orders)
        )
    except Exception as e:
        print(f"Error in update_timeliness_kpi: {e}")
        return "0", "0", "0", "0"

# Callback для обновления диаграмм своевременности
@callback(
    [Output('timely-client-chart', 'option'),
     Output('delayed-client-chart', 'option')],
    [Input('global-date-range', 'data')]
)
def update_timeliness_charts(date_range):
    """Обновление диаграмм своевременности"""
    if not date_range:
        return {}, {}
    
    start_date = date_range['start_date']
    end_date = date_range['end_date']
    
    try:
        timely_data = get_timeliness_chart_data(start_date, end_date, 'timely')
        delayed_data = get_timeliness_chart_data(start_date, end_date, 'delayed')
        
        timely_chart = create_timeliness_chart(timely_data, 'timely')
        delayed_chart = create_timeliness_chart(delayed_data, 'delayed')
        
        return timely_chart, delayed_chart
    except Exception as e:
        print(f"Error in update_timeliness_charts: {e}")
        return {}, {}

# Callback для обновления данных штрафов
@callback(
    [Output('fines-data', 'data'),
     Output('fines-table-body', 'children'),
     Output('max-fines-employee-kpi', 'children'),
     Output('max-fines-count-kpi', 'children'),
     Output('max-amount-employee-kpi', 'children'),
     Output('max-amount-kpi', 'children'),
     Output('total-fines-kpi', 'children'),
     Output('avg-fine-amount-kpi', 'children')],
    [Input('global-date-range', 'data')]
)
def update_fines_data(date_range):
    """Обновление данных штрафов"""
    if not date_range:
        return {}, [], "Нет данных", "0 шт", "Нет данных", "0 руб", "0", "0 руб"
    
    start_date = date_range['start_date']
    end_date = date_range['end_date']
    
    try:
        fines_data = get_fines_data(start_date, end_date)
        
        if not fines_data:
            return {}, [], "Нет данных", "0 шт", "Нет данных", "0 руб", "0", "0 руб"
        
        summary_data = fines_data.get('summary_data', [])
        table_rows = []
        for idx, item in enumerate(sorted(summary_data, key=lambda x: x.get('Количество_штрафов', 0), reverse=True)):
            table_rows.append(
                html.Tr([
                    html.Td(
                        html.A(
                            item.get('Сотрудник', 'Неизвестно'),
                            href='#',
                            id={'type': 'fines-employee', 'index': idx},
                            className='fines-employee-link'
                        ),
                        style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px'}
                    ),
                    html.Td(str(item.get('Количество_штрафов', 0)), 
                           style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'fontWeight': 'bold', 'color': '#B71C1C'}),
                    html.Td(f"{item.get('Сумма_штрафов', 0):,.0f} руб", 
                           style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'fontWeight': 'bold', 'color': '#D32F2F'})
                ])
            )
        
        kpi = fines_data.get('kpi_data', {})
        
        return (
            fines_data,
            table_rows,
            kpi.get('max_fines_employee', 'Нет данных'),
            f"{kpi.get('max_fines_count', 0)} шт",
            kpi.get('max_amount_employee', 'Нет данных'),
            f"{kpi.get('max_amount', 0):,.0f} руб",
            str(kpi.get('total_fines', 0)),
            f"{kpi.get('avg_fine_amount', 0):,.0f} руб"
        )
    except Exception as e:
        print(f"Error in update_fines_data: {e}")
        return {}, [], "Нет данных", "0 шт", "Нет данных", "0 руб", "0", "0 руб"

# Callback для обновления диаграмм штрафов
@callback(
    [Output('fines-pie-chart', 'option'),
     Output('fines-amount-chart', 'option')],
    [Input('fines-data', 'data')]
)
def update_fines_charts(fines_data):
    """Обновление диаграмм штрафов"""
    if not fines_data or 'category_data' not in fines_data:
        empty_pie = create_fines_pie_chart({})
        empty_bar = create_fines_amount_bar_chart({})
        return empty_pie, empty_bar
    
    category_data = fines_data['category_data']
    pie_chart = create_fines_pie_chart(category_data)
    amount_chart = create_fines_amount_bar_chart(category_data)
    
    return pie_chart, amount_chart

# Callback для обновления таблицы сравнения смен
@callback(
    Output('shift-comparison-table-body', 'children'),
    [Input('shift-comparison-cache', 'data')]
)
def update_shift_comparison_table(data):
    """Обновление таблицы сравнения смен"""
    if not data:
        return []
    
    table_rows = []
    for idx, row in enumerate(data):
        # Определяем цвет для операций в час
        ops_per_hour = row.get('Операций_в_час', 0)
        if ops_per_hour >= 15:
            ops_color = 'good-performance'
        elif ops_per_hour >= 10:
            ops_color = 'medium-performance'
        else:
            ops_color = 'poor-performance'
        
        # Определяем цвет для своевременности
        timely_percent = row.get('Вовремя_процент', 100)
        if timely_percent >= 95:
            timely_color = 'good-performance'
        elif timely_percent >= 90:
            timely_color = 'medium-performance'
        else:
            timely_color = 'poor-performance'
        
        # Определяем цвет для штрафов
        fines_count = row.get('Штрафы_кол', 0)
        if fines_count == 0:
            fines_color = 'good-performance'
        elif fines_count <= 2:
            fines_color = 'medium-performance'
        else:
            fines_color = 'poor-performance'
        
        # Определяем цвет для занятости
        busy_percent = row.get('Занятость_процент', 0)
        if busy_percent >= 80:
            busy_color = 'good-performance'
        elif busy_percent >= 60:
            busy_color = 'medium-performance'
        else:
            busy_color = 'poor-performance'
        
        table_rows.append(
            html.Tr([
                html.Td(
                    row.get('Сотрудник', 'Неизвестно'),
                    style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px'}
                ),
                html.Td(
                    f"{ops_per_hour:.1f}",
                    style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'fontWeight': 'bold', 'className': ops_color}
                ),
                html.Td(
                    row.get('Время_работы', '--:--'),
                    style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'color': '#9c27b0', 'fontWeight': 'bold'}
                ),
                html.Td(
                    f"{busy_percent:.1f}%",
                    style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'fontWeight': 'bold', 'className': busy_color}
                ),
                html.Td(
                    f"{timely_percent:.1f}%",
                    style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'fontWeight': 'bold', 'className': timely_color}
                ),
                html.Td(
                    f"{fines_count} шт ({row.get('Штрафы_сумма', 0):,.0f} руб)",
                    style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'fontWeight': 'bold', 'className': fines_color}
                )
            ])
        )
    
    return table_rows

# Callback для обновления диаграммы точности заказов
@callback(
    Output('order-accuracy-chart', 'option'),
    [Input('global-date-range', 'data')]
)
def update_order_accuracy_chart(date_range):
    """Обновление диаграммы точности заказов"""
    if not date_range:
        return create_order_accuracy_chart(
            (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            datetime.now().strftime('%Y-%m-%d')
        )
    
    start_date = date_range['start_date']
    end_date = date_range['end_date']
    
    try:
        return create_order_accuracy_chart(start_date, end_date)
    except Exception as e:
        print(f"Error in update_order_accuracy_chart: {e}")
        return create_order_accuracy_chart(
            (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            datetime.now().strftime('%Y-%m-%d')
        )

# Callback для обновления диаграммы проблемных часов
@callback(
    Output('problematic-hours-chart', 'option'),
    [Input('problematic-hours-cache', 'data')]
)
def update_problematic_hours_chart(problematic_hours):
    """Обновление диаграммы проблемных часов"""
    if not problematic_hours:
        return create_problematic_hours_chart([])
    
    return create_problematic_hours_chart(problematic_hours)

# Callback для обновления диаграммы часов с ошибками
@callback(
    Output('error-hours-chart', 'option'),
    [Input('error-hours-cache', 'data')]
)
def update_error_hours_chart(error_hours):
    """Обновление диаграммы часов с ошибками"""
    print(f"DEBUG: Колбэк update_error_hours_chart вызван с данными: {error_hours}")
    
    if not error_hours:
        print("DEBUG: error_hours пуст, возвращаем пустую диаграмму")
        # Импортируем функцию здесь чтобы избежать циклических импортов
        from components.charts import create_error_hours_chart
        return create_error_hours_chart([])
    
    # Импортируем функцию здесь чтобы избежать циклических импортов
    from components.charts import create_error_hours_chart
    result = create_error_hours_chart(error_hours)
    print(f"DEBUG: Диаграмма создана, возвращаем результат")
    return result

# Callback для обновления KPI отклоненных строк
@callback(
    [Output('rejected-lines-kpi', 'children'),
     Output('rejected-lines-detail', 'children')],
    [Input('global-date-range', 'data')]
)
def update_rejected_lines_kpi(date_range):
    """Обновление KPI отклоненных строк"""
    if not date_range:
        return "0", ""
    
    start_date = date_range['start_date']
    end_date = date_range['end_date']
    
    try:
        # Нужно будет импортировать функцию get_rejected_lines_count
        from data.queries import get_rejected_lines_count
        rejected_count = get_rejected_lines_count(start_date, end_date)
        
        return str(rejected_count), f"1 строка = 1 отмененный заказ"
    except Exception as e:
        print(f"Error in update_rejected_lines_kpi: {e}")
        return "0", ""