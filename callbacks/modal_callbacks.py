import dash
from dash import Input, Output, State, callback, ALL
import json
import re
from data.queries_mssql import (
    get_employee_analytics, get_employee_operations_detail,
    get_employee_fines_details, get_employee_idle_data, get_all_storage_data, filter_storage_data
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
                    from data.queries_mssql import get_employee_modal_detail
                    detail_data = get_employee_modal_detail(employee_name, 
                                                           date_range['start_date'], 
                                                           date_range['end_date'])
                    
                    if not detail_data:
                        analytics_data = {
                            'total_operations': 0,
                            'total_earnings': 0.0,
                            'total_idle_minutes': 0,
                            'orders_completed': 0,
                            'timely_percentage': 0.0,
                            'fines_count': 0,
                            'fines_amount': 0.0,
                            'operations_by_type': '',
                            'reception_count': 0,
                            'daily_data': []
                        }
                    else:
                        # Агрегируем данные за период
                        total_operations = sum(d['total_operations'] for d in detail_data)
                        total_earnings = sum(d['total_earnings'] for d in detail_data)
                        total_idle_minutes = sum(d['total_idle_minutes'] for d in detail_data)
                        orders_completed = sum(d['orders_completed'] for d in detail_data)
                        fines_count = sum(d['fines_count'] for d in detail_data)
                        fines_amount = sum(d['fines_amount'] for d in detail_data)
                        reception_count = sum(d['reception_count'] for d in detail_data)
                        
                        # Средний процент своевременности
                        timely_records = [d for d in detail_data if d['timely_percentage'] > 0]
                        avg_timely = sum(d['timely_percentage'] for d in timely_records) / len(timely_records) if timely_records else 0.0
                        
                        analytics_data = {
                            'total_operations': total_operations,
                            'total_earnings': total_earnings,
                            'total_idle_minutes': total_idle_minutes,
                            'orders_completed': orders_completed,
                            'timely_percentage': avg_timely,
                            'fines_count': fines_count,
                            'fines_amount': fines_amount,
                            'operations_by_type': detail_data[0]['operations_by_type'] if detail_data else '',
                            'reception_count': reception_count,
                            'daily_data': detail_data
                        }
                    
                    ops_detail = get_employee_operations_detail(employee_name,
                                                               date_range['start_date'],
                                                               date_range['end_date'])
                    
                    total_operations = analytics_data['total_operations']
                    total_earnings = analytics_data['total_earnings']
                    total_idle_minutes = analytics_data['total_idle_minutes']
                    
                    # Упрощенный расчет операций в час (на основе 8-часового рабочего дня)
                    work_hours = 8.0
                    if total_operations > 0:
                        ops_per_hour = total_operations / work_hours
                    else:
                        ops_per_hour = 0.0
                    
                    # РАСЧЕТ ЗАРАБОТКА В ЧАС
                    earnings_per_hour = total_earnings / work_hours if work_hours > 0 else 0.0
                    
                    # Форматирование времени работы
                    work_duration = f"{int(work_hours)}ч 0м"
                    
                    # Получаем данные для диаграмм
                    from data.queries_mssql import get_employee_operations_by_type, get_employee_idle_intervals
                    
                    operations_by_type = get_employee_operations_by_type(employee_name, 
                                                                        date_range['start_date'], 
                                                                        date_range['end_date'])
                    idle_intervals = get_employee_idle_intervals(employee_name, 
                                                               date_range['start_date'], 
                                                               date_range['end_date'])
                    
                    total_operations = analytics_data['total_operations']
                    total_earnings = analytics_data['total_earnings']
                    total_idle_minutes = analytics_data['total_idle_minutes']
                    
                    # Упрощенный расчет операций в час (на основе 8-часового рабочего дня)
                    work_hours = 8.0
                    if total_operations > 0:
                        ops_per_hour = total_operations / work_hours
                    else:
                        ops_per_hour = 0.0
                    
                    # РАСЧЕТ ЗАРАБОТКА В ЧАС
                    earnings_per_hour = total_earnings / work_hours if work_hours > 0 else 0.0
                    
                    # Форматирование времени работы
                    work_duration = f"{int(work_hours)}ч 0м"
                    
                    # Создаем СТОЛБЧАТУЮ диаграмму типов операций (цвета как в ячейках хранения)
                    operations_chart = {
                        "title": {
                            "text": "Типы операций",
                            "left": "center",
                            "textStyle": {
                                "fontSize": 14,
                                "fontWeight": "bold",
                                "color": "#333"
                            }
                        },
                        "tooltip": {
                            "trigger": "axis", 
                            "axisPointer": {"type": "shadow"},
                            "formatter": "{b}<br/>{a}: {c} операций"
                        },
                        "xAxis": {
                            "type": "category",
                            "data": [op['operation_type'] for op in operations_by_type],
                            "axisLabel": {"rotate": 45, "fontSize": 10}
                        },
                        "yAxis": {
                            "type": "value", 
                            "name": "Количество операций",
                            "nameTextStyle": {"color": "#666"}
                        },
                        "series": [{
                            "name": "Операции",
                            "type": "bar",
                            "data": [
                                {
                                    "value": op['total_operations'], 
                                    "itemStyle": {"color": "#0D47A1"}
                                } for op in operations_by_type
                            ],
                            "itemStyle": {
                                "borderRadius": [4, 4, 0, 0]
                            },
                            "label": {
                                "show": True, 
                                "position": "top",
                                "formatter": "{c}",
                                "fontSize": 8
                            }
                        }]
                    }
                    
                    # Круговая диаграмма распределения времени
                    work_minutes = int(work_hours * 60)
                    idle_minutes = total_idle_minutes
                    time_distribution_pie = create_time_distribution_pie_echarts(work_minutes, idle_minutes)
                    
                    # Столбчатая диаграмма периодов простоя
                    idle_intervals_bar = create_idle_intervals_bar_echarts(idle_intervals)
                    
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
    [Input("idle-intervals-chart", "selectedData"),
     Input("close-idle-detail-modal", "n_clicks")],
    [State("selected-analytics-employee", "data")],
    prevent_initial_call=True
)
def handle_idle_detail_modal(selected_data, close_clicks, employee_name):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    
    button_id = ctx.triggered[0]['prop_id']
    
    print(f"\n{'='*60}")
    print(f"=== ОБРАБОТКА ВЫБОРА НА ДИАГРАММЕ ===")
    print(f"Сработало: {button_id}")
    print(f"Выбранные данные: {selected_data}")
    print(f"Имя сотрудника: {employee_name}")
    print(f"{'='*60}\n")
    
    if 'close-idle-detail-modal' in button_id:
        print(">>> Закрытие модального окна")
        return ["modal-hidden", "modal-content", "", "", ""]
    
    if 'idle-intervals-chart.selectedData' in button_id and selected_data:
        try:
            print(f">>> Данные выбора: {json.dumps(selected_data, indent=2, ensure_ascii=False)}")
            
            # Получаем имя интервала из данных выбора
            interval_name = "Неизвестный интервал"
            
            # ECharts обычно возвращает данные в таком формате
            if isinstance(selected_data, list) and len(selected_data) > 0:
                # Если это массив выбранных элементов
                first_item = selected_data[0]
                if 'name' in first_item:
                    interval_name = first_item['name']
                    print(f">>> Найдено имя в selected_data[0]['name']: {interval_name}")
                elif 'data' in first_item and 'name' in first_item['data']:
                    interval_name = first_item['data']['name']
                    print(f">>> Найдено имя в selected_data[0]['data']['name']: {interval_name}")
            elif isinstance(selected_data, dict):
                # Если это один объект
                if 'name' in selected_data:
                    interval_name = selected_data['name']
                    print(f">>> Найдено имя в selected_data['name']: {interval_name}")
                elif 'data' in selected_data and 'name' in selected_data['data']:
                    interval_name = selected_data['data']['name']
                    print(f">>> Найдено имя в selected_data['data']['name']: {interval_name}")
                elif 'seriesName' in selected_data:
                    interval_name = selected_data['seriesName']
                    print(f">>> Найдено имя в seriesName: {interval_name}")
                elif 'value' in selected_data:
                    if isinstance(selected_data['value'], (list, tuple)) and len(selected_data['value']) > 0:
                        interval_name = str(selected_data['value'][0])
                    else:
                        interval_name = str(selected_data['value'])
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
            print(f">>> ОШИБКА при обработке выбора: {e}")
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
            # Используем новую функцию get_rejected_lines_summary и get_rejected_lines_detail
            from data.queries_mssql import get_rejected_lines_summary, get_rejected_lines_detail
            
            # Получаем сводную статистику
            summary_stats = get_rejected_lines_summary(start_date, end_date)
            
            # Получаем детальные данные (убираем лимит, чтобы показать все записи)
            rejected_lines = get_rejected_lines_detail(start_date, end_date, limit=1000)
            
            # Используем данные из summary_stats
            total_lines = summary_stats['total_rejected_lines']
            unique_orders_count = summary_stats['unique_orders']
            unique_items_count = summary_stats['unique_items']
            last_date = summary_stats['last_rejection_date']
            
            # Форматируем последнюю дату
            if last_date:
                if hasattr(last_date, 'strftime'):
                    last_date = last_date.strftime('%Y-%m-%d')
                elif ' ' in str(last_date):
                    last_date = str(last_date).split(' ')[0]
                elif 'T' in str(last_date):
                    last_date = str(last_date).split('T')[0]
            
            # Создаем строки таблицы
            table_rows = []
            for line in rejected_lines:  # Показываем все записи без ограничений
                # Форматируем дату для отображения
                display_date = ""
                if line['date_time_stamp']:
                    if hasattr(line['date_time_stamp'], 'strftime'):
                        display_date = line['date_time_stamp'].strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(line['date_time_stamp'], str):
                        if ' ' in line['date_time_stamp']:
                            date_part = line['date_time_stamp'].split(' ')[0]
                            time_part = line['date_time_stamp'].split(' ')[1][:8]
                            display_date = f"{date_part} {time_part}"
                        elif 'T' in line['date_time_stamp']:
                            date_part = line['date_time_stamp'].split('T')[0]
                            time_part = line['date_time_stamp'].split('T')[1][:8]
                            display_date = f"{date_part} {time_part}"
                        else:
                            display_date = str(line['date_time_stamp'])[:19]
                
                table_rows.append(
                    html.Tr([
                        html.Td(line['shipment_id'] or '', 
                               style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px'}),
                        html.Td(line['item'] or '', 
                               style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px'}),
                        html.Td(line['item_desc'] or '', 
                               style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px', 'maxWidth': '200px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'}),
                        html.Td(str(line['requested_qty']) if line['requested_qty'] else '', 
                               style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px', 'textAlign': 'right'}),
                        html.Td(line['quantity_um'] or '', 
                               style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px'}),
                        html.Td(line['pick_loc'] or '', 
                               style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px'}),
                        html.Td(line['pick_zone'] or '', 
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