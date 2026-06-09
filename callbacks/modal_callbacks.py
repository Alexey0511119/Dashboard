import logging
import dash
from dash import Input, Output, State, callback, ALL, html, dcc
from utils.callback_helpers import safe_pattern_callback
import json
from data.queries_mssql import (
    get_employee_fines_details,
    get_employee_idle_intervals,
    get_employee_operations_by_type,
    get_employee_modal_detail,
    get_employee_volume_by_type,
    get_rejected_lines_summary,
    get_rejected_lines_detail,
    get_daily_pick_stats,
    get_pick_error_details,
    get_problematic_hours,
    get_error_hours_top_data,
    get_orders_timeliness_by_delivery,
    get_best_employees
)
from components.charts import (
    create_time_distribution_pie_echarts,
    create_idle_intervals_bar_echarts,
    create_employee_fines_chart,
    create_timeline_chart,
    create_problematic_hours_chart,
    create_error_hours_chart,
)

logger = logging.getLogger(__name__)

@callback(
    [Output("analytics-modal", "className"),
     Output("analytics-modal-content", "className"),
     Output("analytics-employee-name", "children"),
     Output("selected-analytics-employee", "data"),
     Output("total-operations-kpi", "children"),
     Output("earnings-per-hour-kpi", "children"),
     Output("ops-per-hour-kpi", "children"),
     Output("total-volume-kpi", "children"),
     Output("total-containers-kpi", "children"),
     Output("avg-volume-kpi", "children"),
     Output("work-time-kpi", "children"),
     Output("total-earnings-kpi-modal", "children"),
     Output("operations-type-chart", "option"),
     Output("volume-type-chart", "option"),
     Output("time-distribution-chart", "option"),
     Output("idle-intervals-chart", "option")],
    [Input("close-analytics-modal", "n_clicks"),
     Input({'type': 'employee', 'index': ALL}, 'n_clicks')],
    [State("selected-analytics-employee", "data"),
     State("global-date-range", "data"),
     State("performance-data-cache", "data")],
    prevent_initial_call=True
)
@safe_pattern_callback
def handle_analytics_modal(close_clicks, employee_clicks, selected_analytics_employee, date_range, performance_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    
    triggered = ctx.triggered[0]
    prop_id = triggered['prop_id']
    click_values = triggered['value']
    
    if 'close-analytics-modal' in prop_id:
        return ["modal-hidden", "modal-content", "", "", "", "", "", "", "", "", "", "", {}, {}, {}, {}]
    
    if 'employee' in prop_id:
        if isinstance(click_values, list):
            if not any(v is not None and v > 0 for v in click_values):
                raise dash.exceptions.PreventUpdate
        else:
            if not click_values or click_values == 0:
                raise dash.exceptions.PreventUpdate
                
        try:
            id_str = prop_id.rsplit('.', 1)[0]
            id_dict = json.loads(id_str)
            user_name = id_dict.get('index', '')
        except Exception as e:
            logger.warning(f"Не удалось распарсить prop_id '{prop_id}': {e}")
            raise dash.exceptions.PreventUpdate
            
        if not user_name:
            raise dash.exceptions.PreventUpdate
            
        logger.info(f"Открытие модального окна аналитики для: {user_name}")
        
        # 🔑 Вспомогательная функция для безопасного сокращения длинных названий операций
        def truncate_text(text, max_length=25):
            if len(text) > max_length:
                return text[:22] + "..."
            return text
        
        employee_data = None
        employee_display_name = user_name
        
        if performance_data:
            user_name_upper = str(user_name).strip().upper()
            for emp in performance_data:
                emp_user_name = str(emp.get('user_name', '')).strip().upper()
                if emp_user_name == user_name_upper:
                    employee_data = emp
                    employee_display_name = emp.get('Сотрудник', user_name)
                    break
                    
        if not employee_data:
            logger.warning(f"Сотрудник {user_name} не найден в performance_data")
            return ["modal-visible", "modal-content-visible", f"Ошибка: Сотрудник {user_name} не найден в кэше", "", "0", "0", "0", "0", "0", "0", "0", "0", {}, {}, {}, {}]
            
        if not date_range:
            raise dash.exceptions.PreventUpdate
            
        detail_data = get_employee_modal_detail(user_name, date_range['start_date'], date_range['end_date'])
        
        if not detail_data:
            analytics_data = {
                'total_operations': 0, 'total_earnings': 0.0,
                'orders_completed': 0, 'timely_percentage': 0.0, 'fines_count': 0,
                'fines_amount': 0.0, 'operations_by_type': '', 'reception_count': 0, 'daily_data': [],
                'total_volume': 0.0, 'total_containers': 0, 'avg_volume': 0.0
            }
        else:
            total_operations = sum(d['total_operations'] for d in detail_data)
            total_earnings = sum(d['total_earnings'] for d in detail_data)
            fines_count = sum(d.get('fines_count', 0) for d in detail_data)
            fines_amount = sum(d.get('fines_amount', 0) for d in detail_data)
            reception_count = sum(d.get('reception_count', 0) for d in detail_data)
            
            total_volume = sum(d.get('total_volume', 0) for d in detail_data)
            total_containers = sum(d.get('total_containers', 0) for d in detail_data)
            avg_volume = total_volume / total_containers if total_containers > 0 else 0.0
            
            analytics_data = {
                'total_operations': total_operations, 'total_earnings': total_earnings,
                'fines_count': fines_count, 'fines_amount': fines_amount,
                'operations_by_type': detail_data[0]['operations_by_type'] if detail_data else '',
                'reception_count': reception_count, 'daily_data': detail_data,
                'total_volume': total_volume, 'total_containers': total_containers, 'avg_volume': avg_volume
            }
            
        total_ops = analytics_data['total_operations']
        total_earnings = analytics_data['total_earnings']
        
        idle_data = get_employee_idle_intervals(user_name, date_range['start_date'], date_range['end_date'])
        chart_work_minutes = idle_data.get('total_work_minutes', 0)
        chart_idle_minutes = idle_data.get('total_idle_minutes', 0)
        
        work_hours = chart_work_minutes / 60.0 if chart_work_minutes > 0 else 0.0
        ops_per_hour = total_ops / work_hours if work_hours > 0 else 0.0
        earnings_per_hour = total_earnings / work_hours if work_hours > 0 else 0.0
        
        work_hours_val = chart_work_minutes // 60
        work_mins_val = chart_work_minutes % 60
        work_duration = f"{work_hours_val}ч {work_mins_val}м"
        
        operations_by_type = get_employee_operations_by_type(user_name, date_range['start_date'], date_range['end_date'])
        
        try:
            volume_by_type = get_employee_volume_by_type(user_name, date_range['start_date'], date_range['end_date'])
        except Exception as e:
            logger.warning(f"Не удалось получить объёмные данные: {e}")
            volume_by_type = []
            
        # 🔑 ПОДГОТОВКА ДАННЫХ: сокращаем текст для оси X, но сохраняем полное имя для tooltip
        x_data_ops = [truncate_text(op['operation_type']) for op in operations_by_type]
        series_data_ops = [
            {"value": op['total_operations'], "name": op['operation_type'], "itemStyle": {"color": "#0D47A1"}} 
            for op in operations_by_type
        ]

        operations_chart = {
            "title": {"text": "Штучные операции", "left": "center", "textStyle": {"fontSize": 14, "fontWeight": "bold", "color": "#333"}},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}, "formatter": "{b}<br/>{a}: {c} оп."},
            "grid": {"left": "10%", "right": "5%", "bottom": "25%", "top": "15%", "containLabel": True}, # 🔑 РЕЗЕРВИРУЕТ МЕСТО СНИЗУ
            "xAxis": {
                "type": "category", 
                "data": x_data_ops, 
                "axisLabel": {"rotate": 45, "fontSize": 11, "interval": 0, "margin": 20} # margin добавляет отступ от оси
            },
            "yAxis": {"type": "value", "name": "Кол-во", "nameTextStyle": {"color": "#666"}},
            "series": [{
                "name": "Операции", 
                "type": "bar", 
                "data": series_data_ops, 
                "itemStyle": {"borderRadius": [4, 4, 0, 0]}, 
                "label": {"show": True, "position": "top", "formatter": "{c}", "fontSize": 8}
            }]
        }
        
        # 🔑 ПОДГОТОВКА ДАННЫХ для объемных операций
        x_data_vol = [truncate_text(op['operation_type']) for op in volume_by_type]
        series_data_vol = [
            {"value": op['total_volume'], "name": op['operation_type'], "itemStyle": {"color": "#E65100"}} 
            for op in volume_by_type
        ]

        volume_chart = {
            "title": {"text": "Объемные операции (м³)", "left": "center", "textStyle": {"fontSize": 14, "fontWeight": "bold", "color": "#333"}},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}, "formatter": "{b}<br/>{a}: {c} м³"},
            "grid": {"left": "10%", "right": "5%", "bottom": "25%", "top": "15%", "containLabel": True}, # 🔑 РЕЗЕРВИРУЕТ МЕСТО СНИЗУ
            "xAxis": {
                "type": "category", 
                "data": x_data_vol, 
                "axisLabel": {"rotate": 45, "fontSize": 11, "interval": 0, "margin": 20}
            },
            "yAxis": {"type": "value", "name": "Объем (м³)", "nameTextStyle": {"color": "#666"}},
            "series": [{
                "name": "Объем", 
                "type": "bar", 
                "data": series_data_vol, 
                "itemStyle": {"borderRadius": [4, 4, 0, 0]}, 
                "label": {"show": True, "position": "top", "formatter": "{c}", "fontSize": 8}
            }]
        }
        
        time_distribution_pie = create_time_distribution_pie_echarts(chart_work_minutes, chart_idle_minutes)
        idle_intervals_bar = create_idle_intervals_bar_echarts(idle_data)
        
        return [
            "modal-visible", "modal-content-visible",
            f"Сотрудник: {employee_display_name}",
            employee_display_name,
            str(total_ops),
            f"{earnings_per_hour:.2f} ₽/час",
            f"{ops_per_hour:.1f}",
            f"{analytics_data['total_volume']:.2f} м³",
            f"{analytics_data['total_containers']:,}".replace(',', ' '),
            f"{analytics_data['avg_volume']:.2f} м³",
            work_duration,
            f"{total_earnings:,.2f} ₽",
            operations_chart,
            volume_chart,
            time_distribution_pie,
            idle_intervals_bar
        ]
        
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
def handle_idle_detail_modal(selected_data, close_clicks, employee_name):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    button_id = ctx.triggered[0]['prop_id']

    logger.info("Обработка выбора на диаграмме: %s, сотрудник: %s", button_id, employee_name)

    if 'close-idle-detail-modal' in button_id:
        return ["modal-hidden", "modal-content", "", "", ""]

    if 'idle-intervals-chart.clickData' in button_id and selected_data:
        try:
            logger.debug("Данные выбора: %s", json.dumps(selected_data, indent=2, ensure_ascii=False))

            # Получаем имя интервала из данных выбора
            interval_name = "Неизвестный интервал"

            # ECharts обычно возвращает данные в таком формате
            if isinstance(selected_data, list) and len(selected_data) > 0:
                first_item = selected_data[0]
                if 'name' in first_item:
                    interval_name = first_item['name']
                elif 'data' in first_item and 'name' in first_item['data']:
                    interval_name = first_item['data']['name']
            elif isinstance(selected_data, dict):
                if 'name' in selected_data:
                    interval_name = selected_data['name']
                elif 'data' in selected_data and 'name' in selected_data['data']:
                    interval_name = selected_data['data']['name']
                elif 'seriesName' in selected_data:
                    interval_name = selected_data['seriesName']
                elif 'value' in selected_data:
                    if isinstance(selected_data['value'], (list, tuple)) and len(selected_data['value']) > 0:
                        interval_name = str(selected_data['value'][0])
                    else:
                        interval_name = str(selected_data['value'])

            logger.info("Определен интервал: %s", interval_name)

            if employee_name:
                return [
                    "modal-visible", "modal-content-visible",
                    f"Сотрудник: {employee_name}",
                    f"Выбранный интервал: {interval_name}",
                    interval_name
                ]

        except Exception as e:
            logger.error("Ошибка при обработке выбора: %s", e, exc_info=True)
    
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
@safe_pattern_callback
def handle_fines_modal(close_clicks, fines_clicks, selected_fines_employee, fines_data, date_range):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    
    # 🛡️ ЕДИНСТВЕННОЕ ИСПРАВЛЕНИЕ: Защита от инициализации ALL
    # При загрузке страницы Dash передает список нулей или None: [0, 0, 0] или [None, None]
    # Если все значения ложные, значит это не реальный клик, а загрузка страницы.
    if isinstance(fines_clicks, list):
        if not any(fines_clicks):
            raise dash.exceptions.PreventUpdate
    else:
        if not fines_clicks:
            raise dash.exceptions.PreventUpdate

    prop_id = ctx.triggered[0]['prop_id']
    
    if 'close-fines-modal' in prop_id:
        return ["modal-hidden", "modal-content", "", "", "", "", "", {}, ""]
    
    if 'fines-employee' in prop_id:
        import json
        try:
            id_str = prop_id.rsplit('.', 1)[0]
            id_dict = json.loads(id_str)
            employee_name = id_dict.get('index', '')
        except Exception:
            raise dash.exceptions.PreventUpdate
        
        if not employee_name:
            raise dash.exceptions.PreventUpdate
        
        if date_range:
            fines_details = get_employee_fines_details(employee_name, date_range['start_date'], date_range['end_date'])
            
            summary_data = fines_data.get('summary_data', []) if fines_data else []
            employee_data = next((emp for emp in summary_data if emp.get('Сотрудник') == employee_name), None)
            
            if not employee_data:
                employee_data = {
                    'Сотрудник': employee_name,
                    'Количество_штрафов': 0,
                    'Сумма_штрафов': 0,
                    'Средний_штраф': 0
                }
            
            fines_count = employee_data.get('Количество_штрафов', 0)
            total_amount = employee_data.get('Сумма_штрафов', 0)
            avg_amount = employee_data.get('Средний_штраф', 0)
            
            last_date = "Нет данных"
            if fines_details:
                try:
                    dates = [str(f['date'])[:10] for f in fines_details if f.get('date')]
                    if dates:
                        last_date = max(dates)
                except Exception:
                    pass
            
            employee_chart = create_employee_fines_chart({
                'Сотрудник': employee_name,
                'Количество_штрафов': fines_count,
                'Сумма_штрафов': total_amount,
                'Средний_штраф': avg_amount,
                'Штрафы': fines_details
            })
            
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
    prevent_initial_call=True
)
def handle_rejected_lines_modal(open_clicks, close_clicks):
    """Открытие модального окна отклоненных строк (данные из VIEW без фильтра по датам)"""
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    
    button_id = ctx.triggered[0]['prop_id']
    
    if 'close-rejected-lines-modal' in button_id:
        return ["modal-hidden", "modal-content", "", "", "", "", []]
    
    if 'open-rejected-lines-modal' in button_id and open_clicks:
        try:
            # Получаем данные из VIEW (без фильтра по датам - VIEW содержит все данные)
            summary_stats = get_rejected_lines_summary()
            # Получаем детальные данные (без параметров дат, лимит 1000)
            rejected_lines = get_rejected_lines_detail(limit=1000)
            
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
            for line in rejected_lines:
                # Форматируем дату для отображения
                display_date = ""
                if line.get('date_time_stamp'):
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
                
                # 🔑 НОВОЕ ПОЛЕ: Получаем статус и задаем цвет
                status_val = line.get('status', '')
                status_color = '#2e7d32' if status_val == 'Отгружен' else '#c62828'
                
                table_rows.append(
                    html.Tr([
                        html.Td(line.get('shipment_id', '') or '', style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px'}),
                        html.Td(line.get('order_type', '') or '', style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px'}),
                        html.Td(line.get('item', '') or '', style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px'}),
                        html.Td(line.get('item_desc', '') or '', style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px', 'maxWidth': '200px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'}),
                        html.Td(str(line.get('requested_qty', '')) if line.get('requested_qty') else '', style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px', 'textAlign': 'right'}),
                        html.Td(line.get('quantity_um', '') or '', style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px'}),
                        html.Td(line.get('pick_loc', '') or '', style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px'}),
                        html.Td(line.get('pick_zone', '') or '', style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px'}),
                        html.Td(display_date, style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px', 'color': '#673AB7'}),
                        html.Td(line.get('rejection_note', '') or '', style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px', 'maxWidth': '250px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'}),
                        # 🔑 НОВОЕ ПОЛЕ: ЯЧЕЙКА STATUS С ЦВЕТОВОЙ ПОДСВЕТКОЙ
                        html.Td(status_val, style={'padding': '8px', 'borderBottom': '1px solid #eee', 'fontSize': '11px', 'fontWeight': 'bold', 'color': status_color})
                    ])
                )
            
            if not table_rows:
                # 🔑 ИЗМЕНЕНО: colSpan=11 (теперь столбцов 11)
                table_rows = [html.Tr([html.Td("Нет данных", colSpan=11, style={'textAlign': 'center', 'padding': '20px', 'color': '#666'})])]
            
            return [
                "modal-visible", "modal-content-visible",
                str(total_lines),
                str(unique_orders_count),
                str(unique_items_count),
                last_date or "Нет данных",
                table_rows
            ]
        except Exception as e:
            logger.error("Error in handle_rejected_lines_modal: %s", e, exc_info=True)
            return ["modal-hidden", "modal-content", "Ошибка", "0", "0", "Ошибка", []]
            
    raise dash.exceptions.PreventUpdate


# ============================================================================
# Callback: Модальное окно «Точность заказов» (часы с ошибками + проблемные часы)
# ============================================================================
@callback(
    [Output("order-accuracy-modal", "className"),
     Output("order-accuracy-modal-content", "className"),
     Output("total-picks-kpi", "children"),
     Output("claim-errors-kpi", "children"),
     Output("short-pick-errors-kpi", "children"),
     Output("error-hours-chart-modal", "option"),
     Output("problematic-hours-chart-modal", "option")],
    [Input("open-order-accuracy-modal", "n_clicks"),
     Input("close-order-accuracy-modal", "n_clicks")],
    [State("global-date-range", "data")],
    prevent_initial_call=True
)
def handle_order_accuracy_modal(open_clicks, close_clicks, date_range):
    """Открытие модального окна с анализом точности заказов по часам"""
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    button_id = ctx.triggered[0]['prop_id']

    if 'close-order-accuracy-modal' in button_id:
        return ["modal-hidden", "modal-content", "", "", "", {}, {}]

    if 'open-order-accuracy-modal' in button_id and open_clicks:
        try:
            # Получаем даты из date_range или используем значения по умолчанию
            if date_range:
                start_date = date_range.get('start_date')
                end_date = date_range.get('end_date')
            else:
                from datetime import datetime, timedelta
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            # Получаем данные для KPI
            pick_stats = get_daily_pick_stats(start_date, end_date)
            error_details = get_pick_error_details(start_date, end_date)
            
            # Форматируем значения
            total_picks_value = pick_stats.get('total_picks', 0)
            claim_errors_value = error_details.get('Штраф по претензии', 0)
            short_pick_value = error_details.get('Short Pick', 0)
            
            # Форматируем для отображения
            if total_picks_value > 0:
                total_picks = f"{total_picks_value:,}".replace(',', ' ')
            else:
                total_picks = "0"
                
            claim_errors = str(claim_errors_value)
            short_pick_errors = str(short_pick_value)
            
            # Данные для диаграмм
            error_hours = get_error_hours_top_data(start_date, end_date)
            error_chart = create_error_hours_chart(error_hours)

            problematic_hours = get_problematic_hours(start_date, end_date)
            problem_chart = create_problematic_hours_chart(problematic_hours)

            return [
                "modal-visible", 
                "modal-content-visible",
                total_picks,
                claim_errors,
                short_pick_errors,
                error_chart, 
                problem_chart
            ]

        except Exception as e:
            logger.error("Error in handle_order_accuracy_modal: %s", e, exc_info=True)
            return ["modal-hidden", "modal-content", "0", "0", "0", {}, {}]

    raise dash.exceptions.PreventUpdate


# ============================================================================
# Callback: Модальное окно «Своевременность заказов Клиент»
# ============================================================================
@callback(
    [Output("timely-orders-modal", "className"),
     Output("timely-orders-modal-content", "className"),
     Output("timely-client-chart-modal", "option")],
    [Input("open-timely-orders-modal", "n_clicks"),
     Input("close-timely-orders-modal", "n_clicks")],
    [State("global-date-range", "data")],
    prevent_initial_call=True
)
def handle_timely_orders_modal(open_clicks, close_clicks, date_range):
    """Открытие модального окна с диаграммой своевременности заказов Клиент"""
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    button_id = ctx.triggered[0]['prop_id']

    if 'close-timely-orders-modal' in button_id:
        return ["modal-hidden", "modal-content", {}]

    if 'open-timely-orders-modal' in button_id and open_clicks:
        try:
            if not date_range:
                from datetime import datetime, timedelta
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                end_date = datetime.now().strftime('%Y-%m-%d')
            else:
                start_date = date_range['start_date']
                end_date = date_range['end_date']

            chart_data = get_orders_timeliness_by_delivery(start_date, end_date)
            timely_chart = _build_timely_client_figure(chart_data, start_date, end_date)

            return [
                "modal-visible", "modal-content-visible",
                timely_chart
            ]

        except Exception as e:
            logger.error("Error in handle_timely_orders_modal: %s", e, exc_info=True)
            return ["modal-hidden", "modal-content", {}]

    raise dash.exceptions.PreventUpdate


# ============================================================================
# Callback: Модальное окно «Просроченные заказы Клиент»
# ============================================================================
@callback(
    [Output("delayed-orders-modal", "className"),
     Output("delayed-orders-modal-content", "className"),
     Output("delayed-client-chart-modal", "option")],
    [Input("open-delayed-orders-modal", "n_clicks"),
     Input("close-delayed-orders-modal", "n_clicks")],
    [State("global-date-range", "data")],
    prevent_initial_call=True
)
def handle_delayed_orders_modal(open_clicks, close_clicks, date_range):
    """Открытие модального окна с диаграммой просроченных заказов Клиент"""
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    button_id = ctx.triggered[0]['prop_id']

    if 'close-delayed-orders-modal' in button_id:
        return ["modal-hidden", "modal-content", {}]

    if 'open-delayed-orders-modal' in button_id and open_clicks:
        try:
            if not date_range:
                from datetime import datetime, timedelta
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                end_date = datetime.now().strftime('%Y-%m-%d')
            else:
                start_date = date_range['start_date']
                end_date = date_range['end_date']

            chart_data = get_orders_timeliness_by_delivery(start_date, end_date)
            delayed_chart = _build_delayed_client_figure(chart_data, start_date, end_date)

            return [
                "modal-visible", "modal-content-visible",
                delayed_chart
            ]

        except Exception as e:
            logger.error("Error in handle_delayed_orders_modal: %s", e, exc_info=True)
            return ["modal-hidden", "modal-content", {}]

    raise dash.exceptions.PreventUpdate


# ============================================================================
# Вспомогательные функции для построения диаграмм своевременности
# ============================================================================
def _build_timely_client_figure(chart_data, start_date, end_date):
    """Построение figure для своевременности заказов Клиент (копия оригинальной логики)"""
    if not chart_data:
        return {"title": {"text": "Нет данных", "left": "center"}}

    all_dates = sorted(set(item['date'] for item in chart_data))

    rc_timely_data = []
    client_timely_data = []

    for date in all_dates:
        rc_record = next((item for item in chart_data if item['date'] == date and item['delivery_type'] == 'РЦ'), None)
        if rc_record:
            rc_timely_data.append(rc_record['timely_count'])
        else:
            rc_timely_data.append(None)

        client_record = next((item for item in chart_data if item['date'] == date and item['delivery_type'] == 'Доставка клиенту'), None)
        if client_record:
            client_timely_data.append(client_record['timely_count'])
        else:
            client_timely_data.append(None)

    client_timely_count = sum(1 for x in client_timely_data if x is not None and x > 0)

    if client_timely_count <= 2:
        client_timely_config = {
            "connectNulls": False,
            "showSymbol": True,
            "symbolSize": 8,
            "lineStyle": {"width": 0}
        }
    else:
        client_timely_config = {
            "connectNulls": False,
            "showSymbol": True,
            "symbolSize": 6,
            "lineStyle": {"width": 3}
        }

    return {
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


def _build_delayed_client_figure(chart_data, start_date, end_date):
    """Построение figure для просроченных заказов Клиент (копия оригинальной логики)"""
    if not chart_data:
        return {"title": {"text": "Нет данных", "left": "center"}}

    all_dates = sorted(set(item['date'] for item in chart_data))

    rc_delayed_data = []
    client_delayed_data = []

    for date in all_dates:
        rc_record = next((item for item in chart_data if item['date'] == date and item['delivery_type'] == 'РЦ'), None)
        if rc_record:
            rc_delayed_data.append(rc_record['delayed_count'])
        else:
            rc_delayed_data.append(None)

        client_record = next((item for item in chart_data if item['date'] == date and item['delivery_type'] == 'Доставка клиенту'), None)
        if client_record:
            client_delayed_data.append(client_record['delayed_count'])
        else:
            client_delayed_data.append(None)

    client_delayed_count = sum(1 for x in client_delayed_data if x is not None and x > 0)

    if client_delayed_count <= 2:
        client_delayed_config = {
            "connectNulls": False,
            "showSymbol": True,
            "symbolSize": 8,
            "lineStyle": {"width": 0}
        }
    else:
        client_delayed_config = {
            "connectNulls": False,
            "showSymbol": True,
            "symbolSize": 6,
            "lineStyle": {"width": 3}
        }

    return {
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

# ============================================================================
# Callback: Модальное окно «Лучшие сотрудники»
# ============================================================================
@callback(
    [Output("best-employees-modal", "className"),
     Output("best-employees-modal-content", "className"),
     Output("best-employees-table-body", "children"),
     Output("best-employees-year-dropdown", "value"),
     Output("best-employees-month-dropdown", "value")],
    [Input("open-best-employees-modal", "n_clicks"),
     Input("close-best-employees-modal", "n_clicks"),
     Input("best-employees-year-dropdown", "value"),
     Input("best-employees-month-dropdown", "value")],
    [State("best-employees-year-dropdown", "value"),
     State("best-employees-month-dropdown", "value")],
    prevent_initial_call=True
)
def handle_best_employees_modal(open_clicks, close_clicks, year_dd, month_dd, current_year, current_month):
    """Обработка модального окна лучших сотрудников"""
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Закрытие модального окна
    if trigger_id == 'close-best-employees-modal':
        return [
            "modal-hidden", 
            "modal-content", 
            [],  # очищаем таблицу
            dash.no_update,
            dash.no_update
        ]

    # Открытие или изменение фильтров
    if trigger_id in ['open-best-employees-modal', 'best-employees-year-dropdown', 'best-employees-month-dropdown']:
        try:
            # Определяем год и месяц для запроса
            if trigger_id == 'open-best-employees-modal':
                # При открытии используем значения по умолчанию (предыдущий месяц)
                from datetime import datetime
                now = datetime.now()
                if now.month == 1:
                    year_to_use = now.year - 1
                    month_to_use = 12
                else:
                    year_to_use = now.year
                    month_to_use = now.month - 1
            else:
                # При изменении фильтров используем выбранные значения
                year_to_use = year_dd if year_dd else current_year
                month_to_use = month_dd if month_dd else current_month

            # Получаем данные из БД
            from data.queries_mssql import get_best_employees
            employees_data = get_best_employees(year_to_use, month_to_use)

            # Формируем строки таблицы
            table_rows = []
            if employees_data:
                for emp in employees_data:
                    table_rows.append(
                        html.Tr([
                            html.Td(
                                emp.get('full_name', ''),
                                style={
                                    'padding': '12px',
                                    'borderBottom': '1px solid #eee',
                                    'fontSize': '14px',
                                    'color': '#333'
                                }
                            ),
                            html.Td(
                                emp.get('profession', ''),
                                style={
                                    'padding': '12px',
                                    'borderBottom': '1px solid #eee',
                                    'fontSize': '14px',
                                    'color': '#666'
                                }
                            )
                        ])
                    )
            else:
                # Нет данных за выбранный период
                table_rows = [
                    html.Tr([
                        html.Td(
                            "Нет данных за выбранный период",
                            colSpan=2,
                            style={
                                'textAlign': 'center',
                                'padding': '40px',
                                'color': '#999',
                                'fontSize': '16px',
                                'fontStyle': 'italic'
                            }
                        )
                    ])
                ]

            return [
                "modal-visible", 
                "modal-content-visible",
                table_rows,
                year_to_use,
                month_to_use
            ]

        except Exception as e:
            logger.error("Error in handle_best_employees_modal: %s", e, exc_info=True)
            return [
                "modal-hidden", 
                "modal-content", 
                [html.Tr([html.Td("Произошла ошибка при загрузке данных", 
                                 colSpan=2, 
                                 style={'textAlign': 'center', 'padding': '40px', 'color': '#f44336'})])],
                dash.no_update,
                dash.no_update
            ]

    raise dash.exceptions.PreventUpdate  