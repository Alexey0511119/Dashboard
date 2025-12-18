from dash import html, dcc
import dash_echarts

def create_shift_tab():
    """Создание вкладки 'Сравнение смен'"""
    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.H3("Сравнение производительности сотрудников", 
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
                            html.Th('Операций в час', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                            html.Th('Время работы', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                            html.Th('Занятость (%)', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                            html.Th('Вовремя (%)', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                            html.Th('Штрафы', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'})
                        ])),
                        html.Tbody(id='shift-comparison-table-body')
                    ], style={'width': '100%', 'borderCollapse': 'collapse'})
                ], className="table-container", style={'height': '700px', 'overflowY': 'auto', 'borderRadius': '0 0 12px 12px'})
            ], className="full-width-panel dashboard-element", style={'animationDelay': '0.6s', 'width': '100%'})
        ], className="main-content", style={'display': 'flex', 'gap': '20px', 'minHeight': '800px'})
    ], style={'padding': '10px'})