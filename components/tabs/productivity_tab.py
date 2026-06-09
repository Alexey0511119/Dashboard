from dash import html, dcc

def create_productivity_tab():
    """Создание вкладки 'Производительность' (единая таблица с сортировкой)"""
    sortable_header_style = {
        'color': '#666', 'padding': '12px', 'textAlign': 'center', 'fontSize': '14px',
        'borderBottom': '2px solid #eee', 'background': '#f8f9fa',
        'cursor': 'pointer', 'userSelect': 'none'
    }

    def make_sortable_header(title, key):
        return html.Th(
            html.Div([
                html.Span(title, style={'marginRight': '5px'}),
                html.Span('⇅', id=f'prod-sort-{key}-icon', style={'marginLeft': '5px', 'fontSize': '12px', 'opacity': '0.5'})
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'}),
            id=f'prod-sort-{key}-header',
            style=sortable_header_style
        )

    return html.Div([
        html.Div([], className="kpi-row"),
        html.Div([
            html.Div([
                # Кнопка "Лучшие сотрудники" в правом верхнем углу
                html.Div([
                    html.Button(
                        "⭐ Лучшие сотрудники",
                        id="open-best-employees-modal",
                        n_clicks=0,
                        style={
                            'padding': '10px 24px', 'background': 'white', 'border': '2px solid #1976d2',
                            'borderRadius': '8px', 'fontSize': '14px', 'color': '#1976d2', 'cursor': 'pointer',
                            'fontWeight': '500', 'transition': 'all 0.3s ease', 'boxShadow': '0 2px 4px rgba(25, 118, 210, 0.1)'
                        },
                        title="Показать лучших сотрудников за месяц"
                    )
                ], style={'display': 'flex', 'justifyContent': 'flex-end', 'marginBottom': '15px'}),
                
                # Таблица производительности
                html.Div([
                    html.Table([
                        html.Thead(html.Tr([
                            # ✅ ТЕПЕРЬ ВСЕ ЗАГОЛОВКИ СОРТИРУЕМЫЕ
                            make_sortable_header('Сотрудник', 'Сотрудник'),
                            make_sortable_header('Должность', 'Должность'),
                            make_sortable_header('Операции', 'Операции'),
                            make_sortable_header('Объем (м³)', 'Объем'),
                            make_sortable_header('Контейнеров', 'Контейнеров'),
                            make_sortable_header('Ср. объем', 'Ср_объем'),
                            make_sortable_header('Время', 'Время'),
                            make_sortable_header('Оп/час', 'Оп/час'),
                            make_sortable_header('Заработок', 'Заработок')
                        ])),
                        html.Tbody(id='productivity-table-body')
                    ], style={'width': '100%', 'borderCollapse': 'collapse'})
                ], style={
                    'overflowX': 'auto', 'overflowY': 'auto', 'width': '100%', 'height': '100%'
                })
            ], className="full-width-panel dashboard-element", style={
                'animationDelay': '0.6s', 'width': '100%', 'height': '760px',
                'background': 'white', 'borderRadius': '12px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
            })
        ], className="main-content", style={'display': 'flex', 'gap': '20px', 'minHeight': '800px'})
    ], style={'padding': '10px'})