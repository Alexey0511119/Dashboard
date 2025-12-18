from dash import html, dcc
import dash_echarts

def create_timeliness_tab():
    """Создание вкладки 'Своевременность' с диаграммами проблемных часов"""
    return html.Div([
        html.Div([
            html.Div([
                html.Div("Приходов принято в срок", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="timely-arrivals-kpi", style={'color': '#4CAF50', 'fontSize': '36px', 'fontWeight': 'bold', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div("↗ за последнюю неделю", style={'color': '#4CAF50', 'fontSize': '14px', 'textAlign': 'center'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.2s'}),
            html.Div([
                html.Div("Собрано заказов в срок", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="timely-orders-kpi", style={'color': '#2196F3', 'fontSize': '36px', 'fontWeight': 'bold', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div("↗ за последнюю неделю", style={'color': '#2196F3', 'fontSize': '14px', 'textAlign': 'center'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.3s'}),
            html.Div([
                html.Div("Просроченных приходов", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="delayed-arrivals-kpi", style={'color': '#F44336', 'fontSize': '36px', 'fontWeight': 'bold', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div("↘ с предыдущего периода", style={'color': '#F44336', 'fontSize': '14px', 'textAlign': 'center'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.4s'}),
            html.Div([
                html.Div("Просроченных заказов", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="delayed-orders-kpi", style={'color': '#FF9800', 'fontSize': '36px', 'fontWeight': 'bold', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div("↘ с предыдущего периода", style={'color': '#FF9800', 'fontSize': '14px', 'textAlign': 'center'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.5s'})
        ], className="kpi-row"),
        
        html.Div([
            # Левая панель: таблица заказов (уменьшаем высоту)
            html.Div([
                html.Div([
                    html.H3("Таблица заказов", 
                           style={'color': '#333', 'margin': '0', 'fontSize': '20px', 'flex': '1', 'fontWeight': 'bold', 'padding': '20px'}),
                ], style={
                    'background': 'white', 
                    'padding': '0', 
                    'borderRadius': '12px 12px 0 0', 
                    'margin': '0'
                }),
                html.Div([
                    html.Table([
                        html.Thead(html.Tr([
                            html.Th('ID заказа', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                            html.Th('Тип', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                            html.Th('Статус', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                            html.Th('Дата создания', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                            html.Th('До просрочки', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'})
                        ])),
                        html.Tbody(id='orders-table-body')
                    ], style={'width': '100%', 'borderCollapse': 'collapse'})
                ], className="table-container", style={
                    'height': '680px',  # Уменьшаем высоту для выравнивания
                    'overflowY': 'auto', 
                    'borderRadius': '0 0 12px 12px'
                })
            ], className="left-panel dashboard-element", style={
                'animationDelay': '0.6s', 
                'width': '50%',
                'height': '540px'  # Высота таблицы + заголовок
            }),
            
            # Правая панель: два ряда диаграмм
            html.Div([
                # Первый ряд: диаграммы своевременности (2 в ряд)
                html.Div([
                    # Диаграмма 1: Своевременность заказов Клиент
                    html.Div([
                        html.H3("Своевременность заказов Клиент", 
                               style={'color': '#333', 'marginBottom': '10px', 'fontSize': '16px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                        dash_echarts.DashECharts(
                            id='timely-client-chart',
                            option={},
                            style={'height': '220px', 'width': '100%'}
                        )
                    ], className='chart-card dashboard-element', style={
                        'animationDelay': '0.7s', 
                        'height': '260px',  # Уменьшаем высоту
                        'width': '48%',
                        'display': 'inline-block',
                        'marginRight': '4%',
                        'verticalAlign': 'top'
                    }),
                    
                    # Диаграмма 2: Просроченные заказы Клиент
                    html.Div([
                        html.H3("Просроченные заказы Клиент", 
                               style={'color': '#333', 'marginBottom': '10px', 'fontSize': '16px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                        dash_echarts.DashECharts(
                            id='delayed-client-chart',
                            option={},
                            style={'height': '220px', 'width': '100%'}
                        )
                    ], className='chart-card dashboard-element', style={
                        'animationDelay': '0.8s', 
                        'height': '260px',  # Уменьшаем высоту
                        'width': '48%',
                        'display': 'inline-block',
                        'verticalAlign': 'top'
                    })
                ], style={'marginBottom': '20px', 'width': '100%'}),
                
                # Второй ряд: диаграммы проблемных часов (2 в ряд)
                html.Div([
                    # Диаграмма 3: Топ-5 проблемных часов
                    html.Div([
                        html.H3("Топ-5 проблемных часов", 
                               style={'color': '#333', 'marginBottom': '10px', 'fontSize': '16px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                        dash_echarts.DashECharts(
                            id='problematic-hours-chart',
                            option={},
                            style={'height': '220px', 'width': '100%'}
                        )
                    ], className='chart-card dashboard-element', style={
                        'animationDelay': '0.9s', 
                        'height': '260px',  # Уменьшаем высоту
                        'width': '48%',
                        'display': 'inline-block',
                        'marginRight': '4%',
                        'verticalAlign': 'top'
                    }),
                    
                    # Диаграмма 4: Топ-5 часов с ошибками
                    html.Div([
                        html.H3("Топ-5 часов с ошибками", 
                               style={'color': '#333', 'marginBottom': '10px', 'fontSize': '16px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                        dash_echarts.DashECharts(
                            id='error-hours-chart',
                            option={},
                            style={'height': '220px', 'width': '100%'}
                        )
                    ], className='chart-card dashboard-element', style={
                        'animationDelay': '1.0s', 
                        'height': '260px',  # Уменьшаем высоту
                        'width': '48%',
                        'display': 'inline-block',
                        'verticalAlign': 'top'
                    })
                ], style={'width': '100%'})
            ], className="right-panel dashboard-element", style={
                'animationDelay': '0.7s', 
                'width': '50%', 
                'height': '740px',  # Выравниваем с таблицей
                'padding': '10px'
            })
        ], className="main-content", style={'display': 'flex', 'gap': '20px', 'minHeight': '800px'})
    ], style={'padding': '10px'})