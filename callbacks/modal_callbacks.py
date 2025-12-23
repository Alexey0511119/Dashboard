import dash
from dash import Input, Output, State, callback, ALL
import json
import re
from data.queries import (
    get_employee_analytics, get_employee_operations_detail,
    get_employee_fines_details
)
from components.charts import (
    create_operations_type_chart, create_time_distribution_pie_echarts,
    create_idle_intervals_bar_echarts, create_employee_fines_chart,
    create_timeline_chart
)
from dash import html

# Callback для аналитического модального окна
@callback(
    [Output("analytics-modal", "className"),
     Output("analytics-modal-content", "className"),
     Output("analytics-employee-name", "children"),
     Output("selected-analytics-employee", "data"),
     Output("total-operations-kpi", "children"),
     Output("earnings-per-hour-kpi", "children"),
     Output("ops-per-hour-kpi", "children"),
     Output("work-time-kpi", "children"),
     Output("total-earnings-kpi-modal", "children"),
     Output("operations-type-chart", "option"),
     Output("time-distribution-chart", "option"),
     Output("idle-intervals-chart", "option")],
    [Input("close-analytics-modal", "n_clicks"),
     Input({'type': 'employee', 'index': ALL}, 'n_clicks')],
    [State("selected-analytics-employee", "data"),
     State("global-date-range", "data"),
     State("performance-data-cache", "data")],
    prevent_initial_call=True
)
def handle_analytics_modal(close_clicks, employee_clicks, selected_analytics_employee, date_range, performance_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    
    button_id = ctx.triggered[0]['prop_id']
    
    if 'close-analytics-modal' in button_id:
        return ["modal-hidden", "modal-content", "", "", "", "", "", "", "", {}, {}, {}]
    
    if 'employee' in button_id:
        triggered_input = ctx.triggered[0]
        if triggered_input['value'] is None:
            raise dash.exceptions.PreventUpdate
            
        button_data = triggered_input['prop_id'].split('.')[0]
        try:
            button_json = json.loads(button_data.replace("'", '"'))
            employee_idx = button_json['index']
            
            if performance_data and 0 <= employee_idx < len(performance_data):
                employee_name = performance_data[employee_idx]['Сотрудник']
                
                if date_range:
                    analytics_data = get_employee_analytics(employee_name, 
                                                          date_range['start_date'], 
                                                          date_range['end_date'])
                    
                    if not analytics_data:
                        analytics_data = {
                            'total_operations': 0,
                            'total_work_minutes': 0,
                            'work_duration': '0ч 0м',
                            'ops_per_hour': 0,
                            'orders_completed': 0,
                            'timely_percentage': 100.0,
                            'fines_count': 0,
                            'fines_amount': 0.0,
                            'operations_stats': [],
                            'idle_data': {
                                'total_work_minutes': 0,
                                'total_idle_minutes': 0,
                                'idle_counts': {
                                    '5-10 мин': 0,
                                    '10-30 мин': 0,
                                    '30-60 мин': 0,
                                    '>1 часа': 0
                                }
                            },
                            'total_earnings': 0.0,
                            'regular_earnings': 0.0,
                            'reception_earnings': 0.0
                        }
                    
                    ops_detail = get_employee_operations_detail(employee_name,
                                                               date_range['start_date'],
                                                               date_range['end_date'])
                    
                    total_operations = analytics_data['total_operations']
                    ops_per_hour = analytics_data['ops_per_hour']
                    work_duration = analytics_data['work_duration']
                    total_earnings = analytics_data.get('total_earnings', 0.0)
                    idle_data = analytics_data.get('idle_data', {})
                    
                    # РАСЧЕТ ЗАРАБОТКА В ЧАС
                    earnings_per_hour = 0.0
                    if work_duration and work_duration != '0ч 0м':
                        hours_match = re.search(r'(\d+)ч', work_duration)
                        minutes_match = re.search(r'(\d+)м', work_duration)
                        
                        hours = int(hours_match.group(1)) if hours_match else 0
                        minutes = int(minutes_match.group(1)) if minutes_match else 0
                        
                        total_hours = hours + (minutes / 60)
                        if total_hours > 0:
                            earnings_per_hour = total_earnings / total_hours
                    
                    # Создаем диаграммы
                    operations_chart = create_operations_type_chart(employee_name, ops_detail)
                    
                    # Круговая диаграмма распределения времени
                    work_minutes = idle_data.get('total_work_minutes', 0)
                    idle_minutes = idle_data.get('total_idle_minutes', 0)
                    time_distribution_pie = create_time_distribution_pie_echarts(work_minutes, idle_minutes)
                    
                    # Столбчатая диаграмма периодов простоя
                    idle_counts = idle_data.get('idle_counts', {})
                    idle_intervals_bar = create_idle_intervals_bar_echarts(idle_counts)
                    
                    return [
                        "modal-visible", "modal-content-visible", 
                        f"Сотрудник: {employee_name}", 
                        employee_name,
                        str(total_operations),
                        f"{earnings_per_hour:.2f} ₽/час",
                        f"{ops_per_hour:.1f}",
                        work_duration,
                        f"{total_earnings:,.2f} ₽",
                        operations_chart,
                        time_distribution_pie,
                        idle_intervals_bar
                    ]
                    
        except Exception as e:
            print(f"Error in handle_analytics_modal: {e}")
            return ["modal-hidden", "modal-content", "", "", "", "", "", "", "", {}, {}, {}]
    
    raise dash.exceptions.PreventUpdate

# Callback для открытия модального окна детализации простоев
@callback(
    [Output("idle-detail-modal", "className"),
     Output("idle-detail-modal-content", "className"),
     Output("idle-detail-employee-name", "children"),
     Output("idle-detail-interval", "children"),
     Output("selected-idle-interval", "data")],
    [Input("idle-intervals-chart", "clickData"),
     Input("close-idle-detail-modal", "n_clicks")],
    [State("selected-analytics-employee", "data")],
    prevent_initial_call=True
)
def handle_idle_detail_modal(click_data, close_clicks, employee_name):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    
    button_id = ctx.triggered[0]['prop_id']
    
    print(f"\n{'='*60}")
    print(f"=== ОБРАБОТКА КЛИКА ПО ДИАГРАММЕ ===")
    print(f"Сработало: {button_id}")
    print(f"Данные клика: {click_data}")
    print(f"Имя сотрудника: {employee_name}")
    print(f"{'='*60}\n")
    
    if 'close-idle-detail-modal' in button_id:
        print(">>> Закрытие модального окна")
        return ["modal-hidden", "modal-content", "", "", ""]
    
    if 'idle-intervals-chart.clickData' in button_id and click_data:
        try:
            print(f">>> Данные клика: {json.dumps(click_data, indent=2, ensure_ascii=False)}")
            
            # Получаем имя интервала из данных клика
            interval_name = "Неизвестный интервал"
            
            # ECharts обычно возвращает данные в таком формате
            if 'name' in click_data:
                interval_name = click_data['name']
                print(f">>> Найдено имя в click_data['name']: {interval_name}")
            elif 'data' in click_data and 'name' in click_data['data']:
                interval_name = click_data['data']['name']
                print(f">>> Найдено имя в click_data['data']['name']: {interval_name}")
            elif 'seriesName' in click_data:
                interval_name = click_data['seriesName']
                print(f">>> Найдено имя в seriesName: {interval_name}")
            elif 'value' in click_data:
                if isinstance(click_data['value'], (list, tuple)) and len(click_data['value']) > 0:
                    interval_name = str(click_data['value'][0])
                else:
                    interval_name = str(click_data['value'])
                print(f">>> Найдено значение: {interval_name}")
            
            print(f">>> Определен интервал: {interval_name}")
            
            if employee_name:
                print(f">>> Открытие модального окна для {employee_name}")
                return [
                    "modal-visible", "modal-content-visible",
                    f"Сотрудник: {employee_name}",
                    f"Выбранный интервал: {interval_name}",
                    interval_name
                ]
                
        except Exception as e:
            print(f">>> ОШИБКА при обработке клика: {e}")
            import traceback
            traceback.print_exc()
    
    return ["modal-hidden", "modal-content", "", "", ""]

# Callback для обновления timeline-диаграммы
@callback(
    [Output("idle-timeline-chart", "option"),
     Output("idle-detail-day", "data")],
    [Input("idle-detail-day-picker", "date"),
     Input("selected-idle-interval", "data")],
    [State("selected-analytics-employee", "data"),
     State("idle-detail-day", "data")],
    prevent_initial_call=True
)
def update_timeline_chart(selected_date, selected_interval, employee_name, current_day):
    # Если не выбран сотрудник, возвращаем пустую диаграмму
    if not employee_name:
        empty_chart = {
            "title": {
                "text": "Выберите сотрудника",
                "left": "center",
                "textStyle": {"color": "#666"}
            },
            "xAxis": {"type": "category", "data": [], "show": False},
            "yAxis": {"type": "value", "show": False},
            "series": []
        }
        return empty_chart, current_day
    
    # Определяем выбранный день
    day_to_show = selected_date if selected_date else current_day
    
    # Если день не выбран, используем сегодня
    if not day_to_show:
        from datetime import datetime
        day_to_show = datetime.now().strftime('%Y-%m-%d')
    
    # Создаем timeline-диаграмму
    timeline_chart = create_timeline_chart(employee_name, day_to_show, selected_interval)
    
    return timeline_chart, day_to_show

# Callback для модального окна штрафов
@callback(
    [Output("fines-modal", "className"),
     Output("fines-modal-content", "className"),
     Output("fines-employee-name", "children"),
     Output("fines-count-kpi-modal", "children"),
     Output("fines-total-kpi", "children"),
     Output("fines-avg-kpi", "children"),
     Output("fines-last-date", "children"),
     Output("fines-employee-chart", "option"),
     Output("selected-fines-employee", "data")],
    [Input("close-fines-modal", "n_clicks"),
     Input({'type': 'fines-employee', 'index': ALL}, 'n_clicks')],
    [State("selected-fines-employee", "data"),
     State("fines-data", "data"),
     State("global-date-range", "data")],
    prevent_initial_call=True
)
def handle_fines_modal(close_clicks, fines_clicks, selected_fines_employee, fines_data, date_range):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    
    button_id = ctx.triggered[0]['prop_id']
    
    if 'close-fines-modal' in button_id:
        return ["modal-hidden", "modal-content", "", "", "", "", "", {}, ""]
    
    if 'fines-employee' in button_id:
        triggered_input = ctx.triggered[0]
        if triggered_input['value'] is None:
            raise dash.exceptions.PreventUpdate
            
        button_data = triggered_input['prop_id'].split('.')[0]
        try:
            button_json = json.loads(button_data.replace("'", '"'))
            employee_idx = button_json['index']
            
            summary_data = fines_data.get('summary_data', []) if fines_data else []
            sorted_summary_data = sorted(summary_data, key=lambda x: x.get('Количество_штрафов', 0), reverse=True)
            
            if 0 <= employee_idx < len(sorted_summary_data):
                employee_data = sorted_summary_data[employee_idx]
                employee_name = employee_data.get('Сотрудник', 'Неизвестно')
                
                if date_range:
                    fines_details = get_employee_fines_details(employee_name, 
                                                             date_range['start_date'], 
                                                             date_range['end_date'])
                    employee_data['Штрафы'] = fines_details
                
                fines_count = employee_data.get('Количество_штрафов', 0)
                total_amount = employee_data.get('Сумма_штрафов', 0)
                avg_amount = employee_data.get('Средний_штраф', 0)
                
                last_date = "Нет данных"
                if fines_details:
                    try:
                        dates = []
                        for fine in fines_details:
                            if fine.get('date'):
                                dates.append(fine['date'])
                        
                        if dates:
                            date_strings = []
                            for date_obj in dates:
                                if isinstance(date_obj, str):
                                    date_strings.append(date_obj)
                                else:
                                    date_strings.append(str(date_obj))
                            
                            if date_strings:
                                last_date = max(date_strings)[:10]
                    except:
                        pass
                
                employee_chart = create_employee_fines_chart(employee_data)
                
                return (
                    "modal-visible", "modal-content-visible",
                    f"Сотрудник: {employee_name}",
                    str(fines_count),
                    f"{total_amount:,.0f} руб",
                    f"{avg_amount:,.0f} руб",
                    last_date,
                    employee_chart,
                    employee_name
                )
        except Exception as e:
            print(f"Error in handle_fines_modal: {e}")
            raise dash.exceptions.PreventUpdate
    
    raise dash.exceptions.PreventUpdate

# Callback для открытия модального окна отклоненных строк
@callback(
    [Output("rejected-lines-modal", "className"),
     Output("rejected-lines-modal-content", "className"),
     Output("total-rejected-lines-kpi", "children"),
     Output("unique-orders-kpi", "children"),
     Output("unique-items-kpi", "children"),
     Output("last-rejection-date", "children"),
     Output("rejected-lines-table-body", "children")],
    [Input("open-rejected-lines-modal", "n_clicks"),
     Input("close-rejected-lines-modal", "n_clicks")],
    [State("global-date-range", "data")],
    prevent_initial_call=True
)
def handle_rejected_lines_modal(open_clicks, close_clicks, date_range):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    
    button_id = ctx.triggered[0]['prop_id']
    
    if 'close-rejected-lines-modal' in button_id:
        return ["modal-hidden", "modal-content", "", "", "", "", []]
    
    if 'open-rejected-lines-modal' in button_id and open_clicks:
        if not date_range:
            return ["modal-hidden", "modal-content", "0", "0", "0", "Нет данных", []]
        
        start_date = date_range['start_date']
        end_date = date_range['end_date']
        
        try:
            from data.queries import get_rejected_lines_details
            rejected_lines = get_rejected_lines_details(start_date, end_date)
            
            # Рассчитываем KPI
            total_lines = len(rejected_lines)
            
            unique_orders = set()
            unique_items = set()
            last_date = ""
            
            for line in rejected_lines:
                if line['SHIPMENT_ID']:
                    unique_orders.add(line['SHIPMENT_ID'])
                if line['ITEM']:
                    unique_items.add(line['ITEM'])
                
                # Находим самую позднюю дату
                if line['DATE_TIME_STAMP']:
                    if not last_date or line['DATE_TIME_STAMP'] > last_date:
                        last_date = line['DATE_TIME_STAMP']
            
            unique_orders_count = len(unique_orders)
            unique_items_count = len(unique_items)
            
            # Форматируем последнюю дату
            if last_date:
                if ' ' in last_date:
                    last_date = last_date.split(' ')[0]
                elif 'T' in last_date:
                    last_date = last_date.split('T')[0]
            
            # Создаем строки таблицы
            table_rows = []
            for line in rejected_lines[:500]:  # Ограничим 500 строками для производительности
                # Форматируем дату для отображения
                display_date = ""
                if line['DATE_TIME_STAMP']:
                    if ' ' in line['DATE_TIME_STAMP']:
                        date_part = line['DATE_TIME_STAMP'].split(' ')[0]
                        time_part = line['DATE_TIME_STAMP'].split(' ')[1][:8]
                        display_date = f"{date_part} {time_part}"
                    elif 'T' in line['DATE_TIME_STAMP']:
                        date_part = line['DATE_TIME_STAMP'].split('T')[0]
                        time_part = line['DATE_TIME_STAMP'].split('T')[1][:8]
                        display_date = f"{date_part} {time_part}"
                    else:
                        display_date = line['DATE_TIME_STAMP'][:19]
                
                table_rows.append(
                    html.Tr([
                        html.Td(line['SHIPMENT_ID'] or '', 
                               style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px'}),
                        html.Td(line['ITEM'] or '', 
                               style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px'}),
                        html.Td(line['ITEM_DESC'] or '', 
                               style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px', 'maxWidth': '200px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'}),
                        html.Td(str(line['REQUESTED_QTY']) if line['REQUESTED_QTY'] else '', 
                               style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px', 'textAlign': 'right'}),
                        html.Td(line['QUANTITY_UM'] or '', 
                               style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px'}),
                        html.Td(line['PICK_LOC'] or '', 
                               style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px'}),
                        html.Td(line['PICK_ZONE'] or '', 
                               style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px'}),
                        html.Td(display_date, 
                               style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px', 'color': '#673AB7'})
                    ])
                )
            
            return [
                "modal-visible", "modal-content-visible",
                str(total_lines),
                str(unique_orders_count),
                str(unique_items_count),
                last_date[:10] if last_date else "Нет данных",
                table_rows
            ]
            
        except Exception as e:
            print(f"Error in handle_rejected_lines_modal: {e}")
            return ["modal-hidden", "modal-content", "0", "0", "0", "Ошибка", []]
    
    raise dash.exceptions.PreventUpdate