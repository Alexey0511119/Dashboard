from dash import html, dcc
import dash_echarts

def create_productivity_tab():
    """Создание вкладки 'Производительность'"""
    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.H3("Производительность сотрудников", 
                           style={'color': '#333', 'margin': '0', 'fontSize': '20px', 'flex': '1', 'fontWeight': 'bold'}),
                    html.Div([
                        html.Button(
                            "←",
                            id="prev-table",
                            className="nav-btn",
                            style={'marginRight': '10px'}
                        ),
                        html.Div(id="table-title", 
                                style={
                                    'fontSize': '16px', 
                                    'fontWeight': 'bold', 
                                    'color': '#1976d2',
                                    'minWidth': '120px',
                                    'textAlign': 'center'
                                }),
                        html.Button(
                            "→",
                            id="next-table",
                            className="nav-btn",
                            style={'marginLeft': '10px'}
                        )
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style={
                    'display': 'flex', 
                    'justifyContent': 'space-between', 
                    'alignItems': 'center',
                    'background': 'white', 
                    'padding': '20px', 
                    'borderRadius': '12px 12px 0 0', 
                    'margin': '0'
                }),
                html.Div([
                    html.Div(id="table-all-employees", className="table-view active"),
                    html.Div(id="table-top-best", className="table-view"),
                    html.Div(id="table-top-worst", className="table-view")
                ], className="table-container", id="productivity-table-container", style={'height': '700px'})
            ], className="full-width-panel dashboard-element", style={'animationDelay': '0.6s', 'width': '100%'})
        ], className="main-content", style={'display': 'flex', 'gap': '20px', 'minHeight': '800px'})
    ], style={'padding': '10px'})