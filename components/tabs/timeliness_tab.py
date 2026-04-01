from dash import html, dcc
import dash_echarts

def create_timeliness_tab():
    """Создание вкладки 'Своевременность' с диаграммами проблемных часов"""
    return html.Div([
        html.Div([
            html.Div([
                html.Div("Приходов принято в срок", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="timely-arrivals-kpi", style={'color': '#4CAF50', 'fontSize': '36px', 'fontWeight': 'bold', 'marginBottom': '8px', 'textAlign': 'center'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.2s'}),
            html.Div([
                html.Div("Собрано заказов в срок", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="timely-orders-kpi", style={'color': '#2196F3', 'fontSize': '36px', 'fontWeight': 'bold', 'marginBottom': '8px', 'textAlign': 'center'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.3s'}),
            html.Div([
                html.Div("Просроченных приходов", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="delayed-arrivals-kpi", style={'color': '#F44336', 'fontSize': '36px', 'fontWeight': 'bold', 'marginBottom': '8px', 'textAlign': 'center'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.4s'}),
            html.Div([
                html.Div("Просроченных заказов", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="delayed-orders-kpi", style={'color': '#FF9800', 'fontSize': '36px', 'fontWeight': 'bold', 'marginBottom': '8px', 'textAlign': 'center'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.5s'})
        ], className="kpi-row"),
        
        html.Div([
            # Левая панель: таблица заказов (уменьшаем высоту)
            html.Div([
                html.Div([
                    html.H3("Список прихода",
                           style={'color': '#333', 'margin': '0', 'fontSize': '20px', 'flex': '1', 'fontWeight': 'bold', 'padding': '20px'}),
                    html.Button(
                        "⛶ Развернуть",
                        id="expand-receipt-table-btn",
                        n_clicks=0,
                        style={
                            'padding': '8px 16px',
                            'backgroundColor': '#f8f9fa',
                            'border': '1px solid #ddd',
                            'borderRadius': '6px',
                            'cursor': 'pointer',
                            'fontSize': '13px',
                            'color': '#666',
                            'transition': 'all 0.2s ease',
                            'marginRight': '20px'
                        }
                    )
                ], style={
                    'background': 'white',
                    'padding': '0',
                    'borderRadius': '12px 12px 0 0',
                    'margin': '0',
                    'display': 'flex',
                    'alignItems': 'center',
                    'justifyContent': 'space-between'
                }),
                html.Div([
                    html.Div([
                        html.Table([
                            html.Thead(html.Tr([
                                html.Th('Номер в WMS', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                html.Th('Номер Веста', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                html.Th('Поставщик', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                html.Th('Тип прихода', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                html.Th('Дата создания', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                html.Th('Строк', style={'color': '#666', 'padding': '12px', 'textAlign': 'center', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                html.Th('Время выполнения', style={'color': '#666', 'padding': '12px', 'textAlign': 'center', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                html.Th('Просрочится через', style={'color': '#666', 'padding': '12px', 'textAlign': 'center', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                html.Th('Статус', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'})
                            ])),
                            html.Tbody(id='receipt-list-table-body')
                        ], style={'width': '100%', 'borderCollapse': 'collapse', 'minWidth': '1200px'})
                    ], style={
                        'overflowX': 'auto',  # Горизонтальный скроллинг
                        'overflowY': 'auto',  # Вертикальный скроллинг
                        'width': '100%',
                        'height': '100%'
                    })
                ], className="table-container", style={
                    'height': '680px',
                    'borderRadius': '0 0 12px 12px'
                })
            ], className="left-panel dashboard-element", style={
                'animationDelay': '0.6s',
                'width': '50%',
                'height': '540px',  # Высота таблицы + заголовок
                'position': 'relative',
                'zIndex': '100'
            }),
            
            # Развернутая таблица (скрыта по умолчанию)
            html.Div([
                html.Div([
                    html.Div([
                        html.H3("Список прихода - развернутый вид",
                               style={'color': '#333', 'margin': '0', 'fontSize': '20px', 'flex': '1', 'fontWeight': 'bold', 'padding': '20px'}),
                        html.Button(
                            "⛶ Свернуть",
                            id="collapse-receipt-table-btn",
                            n_clicks=0,
                            style={
                                'padding': '8px 16px',
                                'backgroundColor': '#f8f9fa',
                                'border': '1px solid #ddd',
                                'borderRadius': '6px',
                                'cursor': 'pointer',
                                'fontSize': '13px',
                                'color': '#666',
                                'transition': 'all 0.2s ease',
                                'marginRight': '20px'
                            }
                        )
                    ], style={
                        'background': 'white',
                        'padding': '0',
                        'borderRadius': '12px 12px 0 0',
                        'margin': '0',
                        'display': 'flex',
                        'alignItems': 'center',
                        'justifyContent': 'space-between'
                    }),
                    html.Div([
                        html.Div([
                            html.Table([
                                html.Thead(html.Tr([
                                    html.Th('Номер в WMS', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                    html.Th('Номер Веста', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                    html.Th('Поставщик', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                    html.Th('Тип прихода', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                    html.Th('Дата создания', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                    html.Th('Строк', style={'color': '#666', 'padding': '12px', 'textAlign': 'center', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                    html.Th('Время выполнения', style={'color': '#666', 'padding': '12px', 'textAlign': 'center', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                    html.Th('Просрочится через', style={'color': '#666', 'padding': '12px', 'textAlign': 'center', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'}),
                                    html.Th('Статус', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa', 'whiteSpace': 'nowrap'})
                                ])),
                                html.Tbody(id='receipt-list-table-body-expanded')
                            ], style={'width': '100%', 'borderCollapse': 'collapse', 'minWidth': '1200px'})
                        ], style={
                            'overflowX': 'auto',
                            'overflowY': 'auto',
                            'width': '100%',
                            'height': '100%'
                        })
                    ], style={
                        'height': 'calc(100vh - 200px)',
                        'borderRadius': '0 0 12px 12px'
                    })
                ], style={
                    'position': 'fixed',
                    'top': '50%',
                    'left': '50%',
                    'transform': 'translate(-50%, -50%)',
                    'width': '95%',
                    'height': '90vh',
                    'backgroundColor': 'white',
                    'borderRadius': '12px',
                    'boxShadow': '0 10px 50px rgba(0,0,0,0.3)',
                    'zIndex': '9999'
                })
            ], id='expanded-receipt-table-container', style={
                'display': 'none'
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