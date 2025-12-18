from dash import html, dcc
import dash_echarts

def create_fines_tab():
    """Создание вкладки 'Штрафы'"""
    return html.Div([
        html.Div([
            html.Div([
                html.Div("Сотрудник с наиб. кол-вом штрафов", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="max-fines-employee-kpi", style={'color': '#B71C1C', 'fontSize': '20px', 'fontWeight': 'bold', 'marginBottom': '5px', 'textAlign': 'center'}),
                html.Div(id="max-fines-count-kpi", style={'color': '#B71C1C', 'fontSize': '16px', 'textAlign': 'center'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.2s'}),
            html.Div([
                html.Div("Сотрудник с наиб. суммой штрафов", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="max-amount-employee-kpi", style={'color': '#D32F2F', 'fontSize': '20px', 'fontWeight': 'bold', 'marginBottom': '5px', 'textAlign': 'center'}),
                html.Div(id="max-amount-kpi", style={'color': '#D32F2F', 'fontSize': '16px', 'textAlign': 'center'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.3s'}),
            html.Div([
                html.Div("Количество штрафов за период", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="total-fines-kpi", style={'color': '#F44336', 'fontSize': '36px', 'fontWeight': 'bold', 'marginBottom': '5px', 'textAlign': 'center'}),
                html.Div("за выбранный период", style={'color': '#F44336', 'fontSize': '14px', 'textAlign': 'center'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.4s'}),
            html.Div([
                html.Div("Средняя сумма штрафа", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="avg-fine-amount-kpi", style={'color': '#E57373', 'fontSize': '36px', 'fontWeight': 'bold', 'marginBottom': '5px', 'textAlign': 'center'}),
                html.Div("за выбранный период", style={'color': '#E57373', 'fontSize': '14px', 'textAlign': 'center'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.5s'})
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
                ], className="table-container", style={'height': '500px', 'overflowY': 'auto', 'borderRadius': '0 0 12px 12px'})
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