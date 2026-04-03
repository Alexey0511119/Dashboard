import logging
import dash
from dash import Input, Output, callback, html, State
from datetime import datetime, timedelta
from data.queries_mssql import (
    get_orders_table, get_arrival_timeliness, get_order_timeliness, get_orders_timeliness_by_delivery,
    get_fines_data, get_shift_comparison, get_orders_timely
)
from components.charts import (
    create_order_accuracy_chart, create_problematic_hours_chart,
    create_timeliness_chart, create_fines_pie_chart, create_fines_amount_bar_chart
)

logger = logging.getLogger(__name__)

# Константы для стилей
RECEIPT_STATUS_COLORS = {
    'Ожидает приема': '#FF9800',
    'Размещается': '#2196F3',
    'Принимается': '#4CAF50',
    'Просрочено': '#F44336',
}
DEFAULT_STATUS_COLOR = '#9E9E9E'

RECEIPT_TABLE_CELL_STYLE = {'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '12px'}
RECEIPT_TABLE_NO_DATA_ROW = [html.Tr([html.Td("Нет данных", colSpan=9, style={'textAlign': 'center', 'padding': '20px', 'color': '#666'})])]


def _build_receipt_table_rows(receipt_list):
    """Вспомогательная функция для создания строк таблицы приходов"""
    if not receipt_list:
        return RECEIPT_TABLE_NO_DATA_ROW

    table_rows = []
    for item in receipt_list:
        status_color = RECEIPT_STATUS_COLORS.get(item.get('status', ''), DEFAULT_STATUS_COLOR)

        creation_date = item.get('creation_date')
        if creation_date:
            if hasattr(creation_date, 'strftime'):
                creation_date = creation_date.strftime('%d.%m.%Y %H:%M')
            else:
                creation_date = str(creation_date)[:16]

        overdue_in = item.get('overdue_in', '')
        table_rows.append(
            html.Tr([
                html.Td(item.get('receipt_id', ''), style={**RECEIPT_TABLE_CELL_STYLE, 'fontWeight': 'bold'}),
                html.Td(item.get('erp_order_num', ''), style=RECEIPT_TABLE_CELL_STYLE),
                html.Td(item.get('source_name', ''), style=RECEIPT_TABLE_CELL_STYLE),
                html.Td(item.get('receipt_type', ''), style=RECEIPT_TABLE_CELL_STYLE),
                html.Td(creation_date or '', style=RECEIPT_TABLE_CELL_STYLE),
                html.Td(str(item.get('total_lines', '')), style={**RECEIPT_TABLE_CELL_STYLE, 'textAlign': 'center'}),
                html.Td(item.get('execution_time', ''), style={**RECEIPT_TABLE_CELL_STYLE, 'textAlign': 'center'}),
                html.Td(overdue_in, style={**RECEIPT_TABLE_CELL_STYLE, 'textAlign': 'center', 'color': '#F44336' if overdue_in == 'Просрочено' else '#666'}),
                html.Td(
                    html.Span(
                        item.get('status', ''),
                        style={
                            'padding': '4px 8px',
                            'borderRadius': '4px',
                            'fontSize': '11px',
                            'fontWeight': 'bold',
                            'color': 'white',
                            'backgroundColor': status_color,
                            'display': 'inline-block',
                            'minWidth': '100px',
                            'textAlign': 'center'
                        }
                    ),
                    style=RECEIPT_TABLE_CELL_STYLE
                )
            ])
        )

    return table_rows if table_rows else RECEIPT_TABLE_NO_DATA_ROW

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
                    order['date'],
                    style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px'}
                ),
                html.Td(
                    order['overdue_in'],
                    style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'textAlign': 'center'}
                )
            ], className=row_class)
        )

    return table_rows

# Callback для обновления списка приходов
@callback(
    Output('receipt-list-table-body', 'children'),
    [Input('global-date-range', 'data')]
)
def update_receipt_list_table(date_range):
    """Обновление таблицы списка приходов"""
    from data.queries_mssql import get_receipt_list_data

    receipt_list = get_receipt_list_data()
    return _build_receipt_table_rows(receipt_list)

# Callback для разворачивания/сворачивания таблицы приходов
@callback(
    [Output('expanded-receipt-table-container', 'style'),
     Output('expanded-receipt-table-container', 'className'),
     Output('receipt-list-table-body-expanded', 'children')],
    [Input('expand-receipt-table-btn', 'n_clicks'),
     Input('collapse-receipt-table-btn', 'n_clicks')],
    [State('global-date-range', 'data')]
)
def toggle_expanded_receipt_table(expand_clicks, collapse_clicks, date_range):
    """Развернуть/свернуть таблицу приходов с анимацией (как в модальных окнах)"""
    ctx = dash.callback_context
    if not ctx.triggered:
        return {'display': 'none'}, '', []

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    from data.queries_mssql import get_receipt_list_data
    receipt_list = get_receipt_list_data()
    table_rows = _build_receipt_table_rows(receipt_list)

    if button_id == 'expand-receipt-table-btn':
        return {
            'display': 'block',
            'width': '95%',
            'height': '90vh',
            'backgroundColor': 'white',
            'borderRadius': '12px',
            'boxShadow': '0 10px 50px rgba(0,0,0,0.3)',
            'zIndex': '9999'
        }, 'table-visible', table_rows
    elif button_id == 'collapse-receipt-table-btn':
        return {
            'display': 'block'
        }, 'table-hiding', table_rows

    return {'display': 'none'}, '', []

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
        # Получаем данные по приходам из v_receipt_timeliness
        timely_arrivals, delayed_arrivals = get_arrival_timeliness(start_date, end_date)
        # Получаем данные по заказам из v_order_timeliness (возвращает 4 значения)
        timely_orders, delayed_orders, total_orders, orders_percentage = get_order_timeliness(start_date, end_date)
        
        return (
            str(timely_arrivals),
            str(timely_orders),
            str(delayed_arrivals),
            str(delayed_orders)
        )
    except Exception as e:
        logger.error(f"Error in update_timeliness_kpi: {e}")
        return "0", "0", "0", "0"

# Callback для обновления диаграмм своевременности
@callback(
    [Output('timely-client-chart', 'option'),
     Output('delayed-client-chart', 'option')],
    [Input('global-date-range', 'data')]
)
def update_timeliness_charts(date_range):
    """Обновление диаграмм своевременности с разбивкой по типам доставки"""
    if not date_range:
        return {}, {}
    
    start_date = date_range['start_date']
    end_date = date_range['end_date']
    
    try:
        # Получаем данные с разбивкой по типам доставки
        chart_data = get_orders_timeliness_by_delivery(start_date, end_date)
        
        if not chart_data:
            return {}, {}
        
        # Собираем все уникальные даты и сортируем их
        all_dates = sorted(set(item['date'] for item in chart_data))
        
        # Подготавливаем данные для каждой серии
        rc_timely_data = []
        rc_delayed_data = []
        client_timely_data = []
        client_delayed_data = []
        
        # Заполняем данные по всем датам, используя null для отсутствующих значений
        for date in all_dates:
            # Ищем данные для РЦ
            rc_record = next((item for item in chart_data if item['date'] == date and item['delivery_type'] == 'РЦ'), None)
            if rc_record:
                rc_timely_data.append(rc_record['timely_count'])
                rc_delayed_data.append(rc_record['delayed_count'])
            else:
                rc_timely_data.append(None)
                rc_delayed_data.append(None)
            
            # Ищем данные для Доставка клиенту
            client_record = next((item for item in chart_data if item['date'] == date and item['delivery_type'] == 'Доставка клиенту'), None)
            if client_record:
                client_timely_data.append(client_record['timely_count'])
                client_delayed_data.append(client_record['delayed_count'])
            else:
                client_timely_data.append(None)
                client_delayed_data.append(None)
        
        # Считаем количество реальных данных для Доставка клиенту
        client_timely_count = sum(1 for x in client_timely_data if x is not None and x > 0)
        client_delayed_count = sum(1 for x in client_delayed_data if x is not None and x > 0)
        
        # Определяем настройки для Доставка клиенту
        if client_timely_count <= 2:
            # Если 1-2 точки, показываем только точки без линии
            client_timely_config = {
                "connectNulls": False,
                "showSymbol": True,
                "symbolSize": 8,
                "lineStyle": {"width": 0}  # Скрываем линию
            }
        else:
            # Если 3+ точек, показываем линию
            client_timely_config = {
                "connectNulls": False,
                "showSymbol": True,
                "symbolSize": 6,
                "lineStyle": {"width": 3}
            }
            
        if client_delayed_count <= 2:
            client_delayed_config = {
                "connectNulls": False,
                "showSymbol": True,
                "symbolSize": 8,
                "lineStyle": {"width": 0}  # Скрываем линию
            }
        else:
            client_delayed_config = {
                "connectNulls": False,
                "showSymbol": True,
                "symbolSize": 6,
                "lineStyle": {"width": 3}
            }
        
        # Создаем диаграмму для своевременных заказов
        timely_chart = {
            "title": {
                "text": "Своевременность заказов клиент",
                "left": "center",
                "textStyle": {"fontSize": 14, "fontWeight": "bold", "color": "#333"}
            },
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "cross"}
            },
            "legend": {
                "data": ["РЦ", "Доставка клиенту"],
                "top": "30px"
            },
            "xAxis": {
                "type": "category",
                "data": all_dates,
                "axisLabel": {"rotate": 45, "fontSize": 10}
            },
            "yAxis": {
                "type": "value",
                "name": "Количество заказов"
            },
            "series": [
                {
                    "name": "РЦ",
                    "type": "line",
                    "data": rc_timely_data,
                    "lineStyle": {"color": "#4CAF50", "width": 3},
                    "itemStyle": {"color": "#4CAF50"},
                    "smooth": True,
                    "symbol": "circle",
                    "symbolSize": 6,
                    "showSymbol": True
                },
                {
                    "name": "Доставка клиенту",
                    "type": "line", 
                    "data": client_timely_data,
                    "lineStyle": {"color": "#2196F3", "width": 3},
                    "itemStyle": {"color": "#2196F3"},
                    "smooth": True,
                    "symbol": "circle",
                    "symbolSize": 6,
                    "showSymbol": True,
                    **client_timely_config
                }
            ]
        }
        
        # Создаем диаграмму для просроченных заказов
        delayed_chart = {
            "title": {
                "text": "Просрочено клиент",
                "left": "center", 
                "textStyle": {"fontSize": 14, "fontWeight": "bold", "color": "#333"}
            },
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "cross"}
            },
            "legend": {
                "data": ["РЦ", "Доставка клиенту"],
                "top": "30px"
            },
            "xAxis": {
                "type": "category",
                "data": all_dates,
                "axisLabel": {"rotate": 45, "fontSize": 10}
            },
            "yAxis": {
                "type": "value",
                "name": "Количество заказов"
            },
            "series": [
                {
                    "name": "РЦ",
                    "type": "line",
                    "data": rc_delayed_data,
                    "lineStyle": {"color": "#F44336", "width": 3},
                    "itemStyle": {"color": "#F44336"},
                    "smooth": True,
                    "symbol": "circle",
                    "symbolSize": 6,
                    "showSymbol": True
                },
                {
                    "name": "Доставка клиенту",
                    "type": "line",
                    "data": client_delayed_data,
                    "lineStyle": {"color": "#FF9800", "width": 3},
                    "itemStyle": {"color": "#FF9800"},
                    "smooth": True,
                    "symbol": "circle",
                    "symbolSize": 6,
                    "showSymbol": True,
                    **client_delayed_config
                }
            ]
        }
        
        return timely_chart, delayed_chart
    except Exception as e:
        logger.error(f"Error in update_timeliness_charts: {e}")
        return {}, {}

# JavaScript функции для tooltip
function_js_timely_tooltip = """
function(params) {
    var result = params[0].name + '<br/>';
    params.forEach(function(item) {
        result += item.marker + item.seriesName + ': ' + item.value + ' заказов<br/>';
    });
    return result;
}
"""

function_js_delayed_tooltip = """
function(params) {
    var result = params[0].name + '<br/>';
    params.forEach(function(item) {
        result += item.marker + item.seriesName + ': ' + item.value + ' заказов<br/>';
    });
    return result;
}
"""

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
                           style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'fontWeight': 'bold', 'color': '#1976D2'}),
                    html.Td(f"{item.get('Сумма_штрафов', 0):,.0f} руб",
                           style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'fontWeight': 'bold', 'color': '#1565C0'})
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
        logger.error(f"Error in update_fines_data: {e}")
        return {}, [], "Нет данных", "0 шт", "Нет данных", "0 руб", "0", "0 руб"

# Callback для обновления диаграмм штрафов
@callback(
    [Output('fines-pie-chart', 'option'),
     Output('fines-amount-chart', 'option')],
    [Input('fines-data', 'data')]
)
def update_fines_charts(fines_data):
    """Обновление диаграмм штрафов"""
    try:
        if not fines_data or 'category_data' not in fines_data:
            empty_pie = {"title": {"text": "Нет данных", "left": "center"}}
            empty_bar = {"title": {"text": "Нет данных", "left": "center"}}
            return empty_pie, empty_bar

        category_data = fines_data['category_data']

        pie_chart = create_fines_pie_chart(category_data)
        amount_chart = create_fines_amount_bar_chart(category_data)

        return pie_chart, amount_chart

    except Exception as e:
        logger.error(f"ERROR in update_fines_charts: {e}", exc_info=True)

        empty_pie = {"title": {"text": "Ошибка загрузки", "left": "center"}}
        empty_bar = {"title": {"text": "Ошибка загрузки", "left": "center"}}
        return empty_pie, empty_bar

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
        logger.error(f"Error in update_order_accuracy_chart: {e}")
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
    from components.charts import create_error_hours_chart

    if not error_hours:
        return create_error_hours_chart([])

    return create_error_hours_chart(error_hours)

# Callback для обновления KPI отклоненных строк
@callback(
    [Output('rejected-lines-kpi', 'children'),
     Output('rejected-lines-detail', 'children')],
    [Input('global-date-range', 'data')]
)
def update_rejected_lines_kpi(date_range):
    """Обновление KPI отклоненных строк"""
    if not date_range:
        return "0", "Нет данных"
    
    start_date = date_range['start_date']
    end_date = date_range['end_date']
    
    try:
        # Используем новую функцию get_rejected_lines_summary
        from data.queries_mssql import get_rejected_lines_summary
        rejected_stats = get_rejected_lines_summary(start_date, end_date)
        
        total_rejected = rejected_stats['total_rejected_lines']
        unique_orders = rejected_stats['unique_orders']
        unique_items = rejected_stats['unique_items']
        
        # Форматируем значения
        rejected_str = f"{total_rejected:,}"
        
        if unique_orders > 0:
            rejected_detail = f"↗ {unique_orders} заказов | {unique_items} позиций"
        else:
            rejected_detail = "Нет отклоненных строк"
        
        return rejected_str, rejected_detail
    except Exception as e:
        logger.error(f"Error in update_rejected_lines_kpi: {e}")
        return "0", "Ошибка загрузки"