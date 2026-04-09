from dash import html, dcc

# Стили для карточек
CARD_CONTAINER_STYLE = {
    'display': 'flex',
    'flexDirection': 'column',
    'height': '180px',
    'padding': '20px',
    'boxSizing': 'border-box'
}

CARD_TITLE_STYLE = {
    'color': '#666666',
    'fontSize': '14px',
    'fontWeight': 'normal',
    'textAlign': 'center',
    'height': '40px',
    'display': 'flex',
    'alignItems': 'center',
    'justifyContent': 'center',
    'marginBottom': '0'
}

CARD_BUTTON_ROW_STYLE = {
    'height': '35px',
    'display': 'flex',
    'alignItems': 'center',
    'justifyContent': 'center',
    'marginBottom': '0'
}

CARD_BUTTON_STYLE = {
    'background': 'transparent',
    'border': '1px solid #666666',
    'fontSize': '13px',
    'cursor': 'pointer',
    'color': '#666666',
    'padding': '6px 12px',
    'borderRadius': '20px',
    'transition': 'all 0.2s ease',
    'fontWeight': 'normal',
    'whiteSpace': 'nowrap'
}

CARD_VALUE_STYLE = {
    'color': '#666666',
    'fontSize': '36px',
    'fontWeight': 'normal',
    'textAlign': 'center',
    'height': '50px',
    'display': 'flex',
    'alignItems': 'center',
    'justifyContent': 'center',
    'marginBottom': '0'
}

CARD_DETAIL_STYLE = {
    'color': '#666666',
    'fontSize': '12px',
    'textAlign': 'center',
    'lineHeight': '1.4',
    'height': '35px',
    'display': 'flex',
    'flexDirection': 'column',
    'justifyContent': 'center'
}

CARD_EMPTY_DETAIL_STYLE = {
    'height': '35px'
}

def create_timeliness_tab():
    """Создание вкладки 'Своевременность' (диаграммы перенесены в модальные окна)"""
    return html.Div([
        # KPI карточки
        html.Div([
            # Карточка 1: Приходов принято в срок (без кнопки)
            html.Div([
                html.Div("Приходов принято в срок", style=CARD_TITLE_STYLE),
                html.Div("", style=CARD_BUTTON_ROW_STYLE),
                html.Div(id="timely-arrivals-kpi", style={**CARD_VALUE_STYLE, 'color': '#4CAF50'}),
                html.Div("", style=CARD_EMPTY_DETAIL_STYLE)
            ], className='kpi-card dashboard-element docker-hover-effect', style={'animationDelay': '0.2s', **CARD_CONTAINER_STYLE}),

            # Карточка 2: Собрано заказов в срок (с кнопкой)
            html.Div([
                html.Div("Собрано заказов в срок", style=CARD_TITLE_STYLE),
                html.Div([
                    html.Button(
                        "📋 Подробнее",
                        id="open-timely-orders-modal",
                        className="glow-on-hover",
                        style=CARD_BUTTON_STYLE
                    )
                ], style=CARD_BUTTON_ROW_STYLE),
                html.Div(id="timely-orders-kpi", style={**CARD_VALUE_STYLE, 'color': '#2196F3'}),
                html.Div("", style=CARD_EMPTY_DETAIL_STYLE)
            ], className='kpi-card dashboard-element docker-hover-effect', style={'animationDelay': '0.3s', **CARD_CONTAINER_STYLE}),

            # Карточка 3: Просроченных приходов (без кнопки)
            html.Div([
                html.Div("Просроченных приходов", style=CARD_TITLE_STYLE),
                html.Div("", style=CARD_BUTTON_ROW_STYLE),
                html.Div(id="delayed-arrivals-kpi", style={**CARD_VALUE_STYLE, 'color': '#F44336'}),
                html.Div("", style=CARD_EMPTY_DETAIL_STYLE)
            ], className='kpi-card dashboard-element docker-hover-effect', style={'animationDelay': '0.4s', **CARD_CONTAINER_STYLE}),

            # Карточка 4: Просроченных заказов (с кнопкой)
            html.Div([
                html.Div("Просроченных заказов", style=CARD_TITLE_STYLE),
                html.Div([
                    html.Button(
                        "📋 Подробнее",
                        id="open-delayed-orders-modal",
                        className="glow-on-hover",
                        style=CARD_BUTTON_STYLE
                    )
                ], style=CARD_BUTTON_ROW_STYLE),
                html.Div(id="delayed-orders-kpi", style={**CARD_VALUE_STYLE, 'color': '#FF9800'}),
                html.Div("", style=CARD_EMPTY_DETAIL_STYLE)
            ], className='kpi-card dashboard-element docker-hover-effect', style={'animationDelay': '0.5s', **CARD_CONTAINER_STYLE})
        ], className="kpi-row"),

        # Основной контент: Таблица на всю ширину
        html.Div([
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
                        'overflowX': 'auto',
                        'overflowY': 'auto',
                        'width': '100%',
                        'height': '100%'
                    })
                ], className="table-container", style={
                    'height': '680px',
                    'borderRadius': '0 0 12px 12px'
                })
            ], className="dashboard-element", style={
                'animationDelay': '0.6s',
                'width': '100%',
                'height': '740px',
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
            })
        ], className="main-content", style={'display': 'flex', 'gap': '20px', 'minHeight': '800px'})
    ], style={'padding': '10px'})
