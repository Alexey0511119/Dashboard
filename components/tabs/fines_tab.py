from dash import html, dcc
import dash_echarts

# Единый стиль для карточек - выравнивание как в общей сводке
FINES_CARD_CONTAINER_STYLE = {
    'display': 'flex',
    'flexDirection': 'column',
    'height': '180px',  # Фиксированная высота как в общей сводке
    'padding': '20px',
    'boxSizing': 'border-box'
}

FINES_TITLE_STYLE = {
    'color': '#666',
    'fontSize': '14px',
    'fontWeight': 'normal',
    'textAlign': 'center',
    'height': '40px',
    'display': 'flex',
    'alignItems': 'center',
    'justifyContent': 'center',
    'marginBottom': '0'
}

FINES_VALUE_STYLE = {
    'textAlign': 'center',
    'height': '50px',
    'display': 'flex',
    'alignItems': 'center',
    'justifyContent': 'center',
    'marginBottom': '0'
}

FINES_DETAIL_STYLE = {
    'color': '#666',
    'fontSize': '12px',
    'textAlign': 'center',
    'lineHeight': '1.4',
    'height': '35px',
    'display': 'flex',
    'flexDirection': 'column',
    'justifyContent': 'center'
}

FINES_EMPTY_DETAIL_STYLE = {
    'height': '35px'
}

def create_fines_tab():
    """Создание вкладки 'Штрафы'"""
    return html.Div([
        html.Div([
            # Карточка 1: Сотрудник с наиб. кол-вом штрафов
            html.Div([
                # Ряд 1: Название
                html.Div("Сотрудник с наиб. кол-вом штрафов", style=FINES_TITLE_STYLE),
                # Ряд 2: Пусто (нет кнопки)
                html.Div("", style={'height': '35px'}),
                # Ряд 3: Основное значение
                html.Div(id="max-fines-employee-kpi", style={**FINES_VALUE_STYLE, 'color': '#1976D2', 'fontSize': '20px', 'fontWeight': 'bold'}),
                # Ряд 4: Детали
                html.Div(id="max-fines-count-kpi", style={**FINES_DETAIL_STYLE, 'color': '#1976D2', 'fontSize': '16px'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.2s', **FINES_CARD_CONTAINER_STYLE}),

            # Карточка 2: Сотрудник с наиб. суммой штрафов
            html.Div([
                # Ряд 1: Название
                html.Div("Сотрудник с наиб. суммой штрафов", style=FINES_TITLE_STYLE),
                # Ряд 2: Пусто (нет кнопки)
                html.Div("", style={'height': '35px'}),
                # Ряд 3: Основное значение
                html.Div(id="max-amount-employee-kpi", style={**FINES_VALUE_STYLE, 'color': '#1565C0', 'fontSize': '20px', 'fontWeight': 'bold'}),
                # Ряд 4: Детали
                html.Div(id="max-amount-kpi", style={**FINES_DETAIL_STYLE, 'color': '#1565C0', 'fontSize': '16px'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.3s', **FINES_CARD_CONTAINER_STYLE}),

            # Карточка 3: Количество штрафов за период
            html.Div([
                # Ряд 1: Название
                html.Div("Количество штрафов за период", style=FINES_TITLE_STYLE),
                # Ряд 2: Пусто (нет кнопки)
                html.Div("", style={'height': '35px'}),
                # Ряд 3: Основное значение
                html.Div(id="total-fines-kpi", style={**FINES_VALUE_STYLE, 'color': '#0D47A1', 'fontSize': '36px', 'fontWeight': 'bold'}),
                # Ряд 4: Детали
                html.Div("за выбранный период", style={**FINES_DETAIL_STYLE, 'color': '#0D47A1', 'fontSize': '14px'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.4s', **FINES_CARD_CONTAINER_STYLE}),

            # Карточка 4: Средняя сумма штрафа
            html.Div([
                # Ряд 1: Название
                html.Div("Средняя сумма штрафа", style=FINES_TITLE_STYLE),
                # Ряд 2: Пусто (нет кнопки)
                html.Div("", style={'height': '35px'}),
                # Ряд 3: Основное значение
                html.Div(id="avg-fine-amount-kpi", style={**FINES_VALUE_STYLE, 'color': '#1E88E5', 'fontSize': '36px', 'fontWeight': 'bold'}),
                # Ряд 4: Детали
                html.Div("за выбранный период", style={**FINES_DETAIL_STYLE, 'color': '#1E88E5', 'fontSize': '14px'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.5s', **FINES_CARD_CONTAINER_STYLE})
        ], className="kpi-row"),
        
        html.Div([
            html.Div([
                html.Div([
                    html.H3("Штрафы по сотрудникам", 
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
                            html.Th('Сотрудник', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                            html.Th('Кол-во штрафов', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                            html.Th('Сумма штрафов', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'})
                        ])),
                        html.Tbody(id='fines-table-body')
                    ], style={'width': '100%', 'borderCollapse': 'collapse'})
                ], className="table-container", style={'height': '700px', 'overflowY': 'auto', 'borderRadius': '0 0 12px 12px'})
            ], className="left-panel dashboard-element", style={'animationDelay': '0.6s', 'width': '40%'}),
            
            html.Div([
                html.Div([
                    dash_echarts.DashECharts(
                        id='fines-pie-chart',
                        option={},
                        style={'height': '300px', 'width': '100%'}
                    )
                ], className='chart-card dashboard-element', style={'animationDelay': '0.7s', 'height': '350px', 'paddingBottom': '10px'}),
                html.Div([
                    dash_echarts.DashECharts(
                        id='fines-amount-chart',
                        option={},
                        style={'height': '300px', 'width': '100%'}
                    )
                ], className='chart-card dashboard-element', style={'animationDelay': '0.8s', 'height': '350px', 'marginTop': '20px', 'paddingBottom': '10px'})
            ], className="right-panel dashboard-element", style={'animationDelay': '0.7s', 'width': '60%', 'display': 'flex', 'flexDirection': 'column'})
        ], className="main-content", style={'display': 'flex', 'gap': '20px', 'minHeight': '900px'})
    ], style={'padding': '10px'})