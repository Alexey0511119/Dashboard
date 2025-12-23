from dash import html, dcc
import dash_echarts

def create_analytics_modal():
    """Создание модального окна аналитики"""
    return html.Div([
        html.Div([
            html.Div([
                html.H3("Аналитика производительности", 
                       style={'margin': '0', 'color': '#333', 'flex': '1', 'fontSize': '28px'}),
                html.Button(
                    "✕", 
                    id="close-analytics-modal",
                    style={
                        'background': '#f0f0f0',
                        'border': 'none',
                        'fontSize': '32px',
                        'cursor': 'pointer',
                        'color': '#666',
                        'width': '50px',
                        'height': '50px',
                        'borderRadius': '50%',
                        'display': 'flex',
                        'alignItems': 'center',
                        'justifyContent': 'center',
                        'transition': 'all 0.2s ease'
                    }
                )
            ], style={
                'display': 'flex',
                'justifyContent': 'space-between',
                'alignItems': 'center',
                'padding': '30px',
                'borderBottom': '2px solid #eee',
                'background': 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)'
            }),
            html.Div([
                html.Div(id="analytics-employee-name", 
                        style={'fontSize': '24px', 'fontWeight': 'bold', 'marginBottom': '20px', 'color': '#1976d2', 'textAlign': 'center'}),
                html.Div([
                    html.Div([
                        html.Div("Всего операций", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="total-operations-kpi", style={'color': '#1976d2', 'fontSize': '28px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card'),
                    html.Div([
                        html.Div("Заработок в час", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="earnings-per-hour-kpi", style={'color': '#2e7d32', 'fontSize': '28px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card'),
                    html.Div([
                        html.Div("Операций в час", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="ops-per-hour-kpi", style={'color': '#ed6c02', 'fontSize': '28px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card'),
                    html.Div([
                        html.Div("Время работы", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="work-time-kpi", style={'color': '#9c27b0', 'fontSize': '28px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card'),
                    html.Div([
                        html.Div("Общий заработок", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="total-earnings-kpi-modal", style={'color': '#9c27b0', 'fontSize': '28px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card')
                ], className="analytics-kpi-row", style={'gridTemplateColumns': '1fr 1fr 1fr 1fr 1fr'}),
                
                # ПЕРВЫЙ РЯД: Распределение операций по типам (на всю ширину)
                html.Div([
                    html.Div([
                        html.H4("Распределение операций по типам", 
                               style={'color': '#333', 'marginBottom': '15px', 'fontSize': '18px', 'fontWeight': 'bold'}),
                        dash_echarts.DashECharts(
                            id="operations-type-chart",
                            option={},
                            style={'height': '350px', 'width': '100%'},
                            click_data=None
                        )
                    ], className='analytics-chart-card', style={'height': '400px', 'width': '100%'})
                ], style={'marginBottom': '20px'}),
                
                # ВТОРОЙ РЯД: Периоды простоя (слева) + Распределение времени работы (справа)
                html.Div([
                    # ЛЕВАЯ ЧАСТЬ: Периоды простоя (кликабельная)
                    html.Div([
                        html.H4("Периоды простоя", 
                               style={'color': '#333', 'marginBottom': '15px', 'fontSize': '18px', 'fontWeight': 'bold'}),
                        dash_echarts.DashECharts(
                            id="idle-intervals-chart",
                            option={},
                            style={'height': '350px', 'width': '100%'}
                        )
                    ], className='analytics-chart-card', style={'height': '400px', 'width': '48%', 'cursor': 'pointer'}),
                    
                    # ПРАВАЯ ЧАСТЬ: Распределение времени работы
                    html.Div([
                        html.H4("Распределение времени работы", 
                               style={'color': '#333', 'marginBottom': '15px', 'fontSize': '18px', 'fontWeight': 'bold'}),
                        dash_echarts.DashECharts(
                            id="time-distribution-chart",
                            option={},
                            style={'height': '350px', 'width': '100%'}
                        )
                    ], className='analytics-chart-card', style={'height': '400px', 'width': '48%'})
                ], style={'display': 'flex', 'justifyContent': 'space-between'})
                
                # БЛОК "Ключевые метрики качества" УДАЛЕН
            ], style={'padding': '25px', 'height': 'calc(100% - 100px)', 'overflowY': 'auto'})
        ], id="analytics-modal-content", className="modal-content")
    ], id="analytics-modal", className="modal-hidden")

def create_fines_modal():
    """Создание модального окна штрафов"""
    return html.Div([
        html.Div([
            html.Div([
                html.H3("Детализация штрафов", 
                       style={'margin': '0', 'color': '#333', 'flex': '1', 'fontSize': '28px'}),
                html.Button(
                    "✕", 
                    id="close-fines-modal",
                    style={
                        'background': '#f0f0f0',
                        'border': 'none',
                        'fontSize': '32px',
                        'cursor': 'pointer',
                        'color': '#666',
                        'width': '50px',
                        'height': '50px',
                        'borderRadius': '50%',
                        'display': 'flex',
                        'alignItems': 'center',
                        'justifyContent': 'center',
                        'transition': 'all 0.2s ease'
                    }
                )
            ], style={
                'display': 'flex',
                'justifyContent': 'space-between',
                'alignItems': 'center',
                'padding': '30px',
                'borderBottom': '2px solid #eee',
                'background': 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)'
            }),
            html.Div([
                html.Div(id="fines-employee-name", 
                        style={'fontSize': '24px', 'fontWeight': 'bold', 'marginBottom': '20px', 'color': '#B71C1C', 'textAlign': 'center'}),
                html.Div([
                    html.Div([
                        html.Div("Количество штрафов", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="fines-count-kpi-modal", style={'color': '#B71C1C', 'fontSize': '28px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card'),
                    html.Div([
                        html.Div("Общая сумма", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="fines-total-kpi", style={'color': '#D32F2F', 'fontSize': '28px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card'),
                    html.Div([
                        html.Div("Средний штраф", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="fines-avg-kpi", style={'color': '#F44336', 'fontSize': '28px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card'),
                    html.Div([
                        html.Div("Дата последнего", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="fines-last-date", style={'color': '#666', 'fontSize': '24px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card')
                ], className="analytics-kpi-row", style={'marginBottom': '25px'}),
                dash_echarts.DashECharts(
                    id="fines-employee-chart",
                    option={},
                    style={'height': '500px', 'width': '100%'}
                )
            ], style={'padding': '25px', 'height': 'calc(100% - 100px)', 'overflowY': 'auto'})
        ], id="fines-modal-content", className="modal-content")
    ], id="fines-modal", className="modal-hidden")

def create_idle_detail_modal():
    """Создание модального окна детализации простоев"""
    return html.Div([
        html.Div([
            html.Div([
                html.H3("Детализация простоев сотрудника", 
                       style={'margin': '0', 'color': '#333', 'flex': '1', 'fontSize': '28px'}),
                html.Button(
                    "✕", 
                    id="close-idle-detail-modal",
                    style={
                        'background': '#f0f0f0',
                        'border': 'none',
                        'fontSize': '32px',
                        'cursor': 'pointer',
                        'color': '#666',
                        'width': '50px',
                        'height': '50px',
                        'borderRadius': '50%',
                        'display': 'flex',
                        'alignItems': 'center',
                        'justifyContent': 'center',
                        'transition': 'all 0.2s ease'
                    }
                )
            ], style={
                'display': 'flex',
                'justifyContent': 'space-between',
                'alignItems': 'center',
                'padding': '30px',
                'borderBottom': '2px solid #eee',
                'background': 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)'
            }),
            html.Div([
                html.Div(id="idle-detail-employee-name", 
                        style={'fontSize': '24px', 'fontWeight': 'bold', 'marginBottom': '20px', 'color': '#F44336', 'textAlign': 'center'}),
                html.Div(id="idle-detail-interval", 
                        style={'fontSize': '18px', 'marginBottom': '20px', 'color': '#666', 'textAlign': 'center'}),
                
                # Фильтр выбора дня
                html.Div([
                    html.Label("Выберите день для детализации:", 
                             style={'marginRight': '10px', 'fontSize': '14px', 'color': '#333'}),
                    dcc.DatePickerSingle(
                        id='idle-detail-day-picker',
                        date=None,
                        display_format='DD.MM.YYYY',
                        style={'display': 'inline-block'}
                    )
                ], style={'marginBottom': '20px', 'padding': '15px', 'background': '#f8f9fa', 'borderRadius': '8px'}),
                
                # Timeline диаграмма
                html.Div([
                    html.H4("Распределение времени в течение дня", 
                           style={'color': '#333', 'marginBottom': '15px', 'fontSize': '18px', 'fontWeight': 'bold'}),
                    dash_echarts.DashECharts(
                        id="idle-timeline-chart",
                        option={},
                        style={'height': 'px700', 'width': '100%'}
                    )
                ], className='analytics-chart-card', style={'height': '550px'}),
                
                # Информация о тестовых данных
                html.Div([
                    html.P("⚠️ Это демонстрационные данные. Реальные данные о временных интервалах простоев появятся в ближайшее время.",
                          style={'color': '#666', 'fontSize': '14px', 'textAlign': 'center', 'padding': '15px',
                                'background': '#fff3cd', 'borderRadius': '8px', 'border': '1px solid #ffeaa7'})
                ], style={'marginTop': '20px'})
            ], style={'padding': '25px', 'height': 'calc(100% - 100px)', 'overflowY': 'auto'})
        ], id="idle-detail-modal-content", className="modal-content")
    ], id="idle-detail-modal", className="modal-hidden")

def create_storage_cells_modal():
    """Создание модального окна для детальной аналитики ячеек хранения с фильтрами"""
    return html.Div([
        html.Div([
            html.Div([
                html.H3("Детальная аналитика ячеек хранения", 
                       style={'margin': '0', 'color': '#333', 'flex': '1', 'fontSize': '28px'}),
                html.Button(
                    "✕", 
                    id="close-storage-modal",
                    n_clicks=0,
                    style={
                        'background': '#f0f0f0',
                        'border': 'none',
                        'fontSize': '32px',
                        'cursor': 'pointer',
                        'color': '#666',
                        'width': '50px',
                        'height': '50px',
                        'borderRadius': '50%',
                        'display': 'flex',
                        'alignItems': 'center',
                        'justifyContent': 'center',
                        'transition': 'all 0.2s ease'
                    }
                )
            ], style={
                'display': 'flex',
                'justifyContent': 'space-between',
                'alignItems': 'center',
                'padding': '30px',
                'borderBottom': '2px solid #eee',
                'background': 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)'
            }),
            html.Div([
                # Секция с KPI
                html.Div([
                    html.Div([
                        html.Div("Всего ячеек", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="storage-total-cells", style={'color': '#1976d2', 'fontSize': '28px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card'),
                    html.Div([
                        html.Div("Занято ячеек", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="storage-occupied-cells", style={'color': '#0D47A1', 'fontSize': '28px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card'),
                    html.Div([
                        html.Div("Свободно ячеек", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="storage-free-cells", style={'color': '#2196F3', 'fontSize': '28px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card'),
                    html.Div([
                        html.Div("% занятости", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="storage-occupied-percent", style={'color': '#1565C0', 'fontSize': '28px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card')
                ], className="analytics-kpi-row", style={'marginBottom': '20px', 'gridTemplateColumns': '1fr 1fr 1fr 1fr'}),
                
                # Секция с фильтрами
                html.Div([
                    html.H4("Фильтры", style={'color': '#333', 'marginBottom': '15px', 'fontSize': '18px', 'fontWeight': 'bold'}),
                    html.Div([
                        # Тип хранения
                        html.Div([
                            html.Label("Тип хранения:", style={'display': 'block', 'marginBottom': '5px', 'fontSize': '12px', 'color': '#666'}),
                            dcc.Dropdown(
                                id='filter-storage-type',
                                options=[{'label': 'Все', 'value': 'Все'}],
                                value='Все',
                                clearable=False,
                                style={'fontSize': '12px'}
                            )
                        ], style={'flex': '1', 'marginRight': '10px'}),
                        
                        # Зона размещения
                        html.Div([
                            html.Label("Зона размещения:", style={'display': 'block', 'marginBottom': '5px', 'fontSize': '12px', 'color': '#666'}),
                            dcc.Dropdown(
                                id='filter-locating-zone',
                                options=[{'label': 'Все', 'value': 'Все'}],
                                value='Все',
                                clearable=False,
                                style={'fontSize': '12px'}
                            )
                        ], style={'flex': '1', 'marginRight': '10px'}),
                        
                        # Зона резервирования
                        html.Div([
                            html.Label("Зона резервирования:", style={'display': 'block', 'marginBottom': '5px', 'fontSize': '12px', 'color': '#666'}),
                            dcc.Dropdown(
                                id='filter-allocation-zone',
                                options=[{'label': 'Все', 'value': 'Все'}],
                                value='Все',
                                clearable=False,
                                style={'fontSize': '12px'}
                            )
                        ], style={'flex': '1', 'marginRight': '10px'}),
                        
                        # Тип МХ
                        html.Div([
                            html.Label("Тип МХ:", style={'display': 'block', 'marginBottom': '5px', 'fontSize': '12px', 'color': '#666'}),
                            dcc.Dropdown(
                                id='filter-location-type',
                                options=[{'label': 'Все', 'value': 'Все'}],
                                value='Все',
                                clearable=False,
                                style={'fontSize': '12px'}
                            )
                        ], style={'flex': '1', 'marginRight': '10px'}),
                        
                        # Рабочая зона
                        html.Div([
                            html.Label("Рабочая зона:", style={'display': 'block', 'marginBottom': '5px', 'fontSize': '12px', 'color': '#666'}),
                            dcc.Dropdown(
                                id='filter-work-zone',
                                options=[{'label': 'Все', 'value': 'Все'}],
                                value='Все',
                                clearable=False,
                                style={'fontSize': '12px'}
                            )
                        ], style={'flex': '1'})
                    ], style={'display': 'flex', 'gap': '10px', 'marginBottom': '20px'})
                ], style={'marginBottom': '20px', 'padding': '15px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px'}),
                
                # Секция с диаграммами
                html.Div([
                    # ПЕРВЫЙ РЯД: Две круговые диаграммы
                    html.Div([
                        # Диаграмма 1: Доля пустых ячеек
                        html.Div([
                            html.H4("Доля пустых ячеек", 
                                   style={'color': '#333', 'marginBottom': '15px', 'fontSize': '16px', 'fontWeight': 'bold'}),
                            dash_echarts.DashECharts(
                                id="storage-empty-chart",
                                option={},
                                style={'height': '300px', 'width': '100%'}
                            )
                        ], className='analytics-chart-card', style={'height': '400px', 'width': '48%'}),
                        
                        # Диаграмма 2: Доли типов ячеек
                        html.Div([
                            html.H4("Доли типов ячеек", 
                                   style={'color': '#333', 'marginBottom': '15px', 'fontSize': '16px', 'fontWeight': 'bold'}),
                            dash_echarts.DashECharts(
                                id="storage-types-pie-chart",
                                option={},
                                style={'height': '300px', 'width': '100%'}
                            )
                        ], className='analytics-chart-card', style={'height': '400px', 'width': '48%'})
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '20px'}),
                    
                    # ВТОРОЙ РЯД: Столбчатая диаграмма
                    html.Div([
                        html.H4("Количество типов ячеек", 
                               style={'color': '#333', 'marginBottom': '15px', 'fontSize': '16px', 'fontWeight': 'bold'}),
                        dash_echarts.DashECharts(
                            id="storage-types-bar-chart",
                            option={},
                            style={'height': '350px', 'width': '100%'}
                        )
                    ], className='analytics-chart-card', style={'height': '400px', 'width': '100%'})
                ]),
                
                # Информация о фильтрах
                html.Div([
                    html.P("ℹ️ Фильтры взаимосвязаны: выбор значения в одном фильтре ограничивает доступные значения в других",
                          style={'color': '#666', 'fontSize': '12px', 'textAlign': 'center', 'padding': '10px',
                                'background': '#e3f2fd', 'borderRadius': '6px', 'border': '1px solid #bbdefb'})
                ], style={'marginTop': '20px'})
                
            ], style={'padding': '25px', 'height': 'calc(100% - 100px)', 'overflowY': 'auto'})
        ], id="storage-modal-content", className="modal-content")
    ], id="storage-cells-modal", className="modal-hidden")

def create_rejected_lines_modal():
    """Создание модального окна с таблицей отклоненных строк"""
    return html.Div([
        html.Div([
            html.Div([
                html.H3("Детализация отклоненных строк в заказах", 
                       style={'margin': '0', 'color': '#333', 'flex': '1', 'fontSize': '28px'}),
                html.Button(
                    "✕", 
                    id="close-rejected-lines-modal",
                    style={
                        'background': '#f0f0f0',
                        'border': 'none',
                        'fontSize': '32px',
                        'cursor': 'pointer',
                        'color': '#666',
                        'width': '50px',
                        'height': '50px',
                        'borderRadius': '50%',
                        'display': 'flex',
                        'alignItems': 'center',
                        'justifyContent': 'center',
                        'transition': 'all 0.2s ease'
                    }
                )
            ], style={
                'display': 'flex',
                'justifyContent': 'space-between',
                'alignItems': 'center',
                'padding': '30px',
                'borderBottom': '2px solid #eee',
                'background': 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)'
            }),
            html.Div([
                # KPI карточки
                html.Div([
                    html.Div([
                        html.Div("Всего отклоненных строк", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="total-rejected-lines-kpi", style={'color': '#9C27B0', 'fontSize': '28px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card'),
                    html.Div([
                        html.Div("Уникальных заказов", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="unique-orders-kpi", style={'color': '#673AB7', 'fontSize': '28px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card'),
                    html.Div([
                        html.Div("Уникальных товаров", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="unique-items-kpi", style={'color': '#3F51B5', 'fontSize': '28px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card'),
                    html.Div([
                        html.Div("Последнее отклонение", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'textAlign': 'center'}),
                        html.Div(id="last-rejection-date", style={'color': '#666', 'fontSize': '20px', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ], className='analytics-kpi-card')
                ], className="analytics-kpi-row", style={'marginBottom': '20px', 'gridTemplateColumns': '1fr 1fr 1fr 1fr'}),
                
                # Таблица отклоненных строк
                html.Div([
                    html.H4("Таблица отклоненных строк", 
                           style={'color': '#333', 'marginBottom': '15px', 'fontSize': '18px', 'fontWeight': 'bold'}),
                    html.Div([
                        html.Table([
                            html.Thead(html.Tr([
                                html.Th("SHIPMENT_ID", style={'padding': '12px', 'textAlign': 'left', 'fontSize': '12px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                html.Th("ITEM", style={'padding': '12px', 'textAlign': 'left', 'fontSize': '12px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                html.Th("ITEM_DESC", style={'padding': '12px', 'textAlign': 'left', 'fontSize': '12px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                html.Th("REQUESTED_QTY", style={'padding': '12px', 'textAlign': 'left', 'fontSize': '12px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                html.Th("QUANTITY_UM", style={'padding': '12px', 'textAlign': 'left', 'fontSize': '12px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                html.Th("PICK_LOC", style={'padding': '12px', 'textAlign': 'left', 'fontSize': '12px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                html.Th("PICK_ZONE", style={'padding': '12px', 'textAlign': 'left', 'fontSize': '12px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                html.Th("DATE_TIME_STAMP", style={'padding': '12px', 'textAlign': 'left', 'fontSize': '12px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'})
                            ])),
                            html.Tbody(id="rejected-lines-table-body")
                        ], style={'width': '100%', 'borderCollapse': 'collapse'})
                    ], style={'maxHeight': '500px', 'overflowY': 'auto', 'border': '1px solid #eee', 'borderRadius': '8px'})
                ], style={'marginTop': '20px'})
                
            ], style={'padding': '25px', 'height': 'calc(100% - 100px)', 'overflowY': 'auto'})
        ], id="rejected-lines-modal-content", className="modal-content")
    ], id="rejected-lines-modal", className="modal-hidden")