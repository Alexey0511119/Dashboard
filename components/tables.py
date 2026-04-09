import dash
from dash import html, dcc
import pandas as pd
import json
from data.queries_mssql import get_employees_on_shift, get_positions_list, get_brigades_list
from data.queries_mssql import get_employees_on_shift_new, get_positions_list_new, get_brigades_list_new

def create_performance_table(df, title="", is_best=False, is_worst=False):
    """Создание HTML таблицы производительности с колонкой заработка"""
    if len(df) == 0:
        return html.Table([
            html.Thead(html.Tr([
                html.Th('Сотрудник', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                html.Th('Операции', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                html.Th('Время', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                html.Th('Заработок', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                html.Th('Оп/час', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'})
            ])),
            html.Tbody([
                html.Tr([
                    html.Td("Нет данных", colSpan=5, style={'textAlign': 'center', 'padding': '20px', 'color': '#666'})
                ])
            ])
        ], style={'width': '100%', 'borderCollapse': 'collapse'})

    rows = []
    for idx, row in df.iterrows():
        # Определяем цвет для времени на операцию
        time_color = '#d32f2f' if row.get('Ср_время_на_операцию', 0) > 2.5 else '#2e7d32'

        # Определяем цвет для операций в час
        ops_per_hour = row.get('Операций_в_час', 0)
        if ops_per_hour >= 15:
            ops_color = 'good-performance'
        elif ops_per_hour >= 10:
            ops_color = 'medium-performance'
        else:
            ops_color = 'poor-performance'

        # Определяем цвет для заработка (чем больше, тем зеленее)
        earnings = row.get('Заработок', 0)
        earnings_color = '#2e7d32'  # зеленый по умолчанию

        if earnings < 1000:
            earnings_color = '#d32f2f'  # красный для низкого заработка
        elif earnings < 3000:
            earnings_color = '#ed6c02'  # оранжевый для среднего

        # Используем индекс строки как идентификатор (как в других таблицах)
        rows.append(
            html.Tr([
                html.Td(
                    html.A(
                        row.get('Сотрудник', 'Неизвестно'),
                        href='#',
                        id={'type': 'employee', 'index': idx},
                        className='employee-link'
                    ),
                    style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'transition': 'all 0.3s ease'}
                ),
                html.Td(str(int(row.get('Общее_кол_операций', 0))),
                       style={'color': '#333', 'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'fontWeight': 'bold', 'transition': 'all 0.3s ease'}),
                html.Td(f"{row.get('Ср_время_на_операцию', 0):.1f} мин",
                       style={'color': time_color, 'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'fontWeight': 'bold', 'transition': 'all 0.3s ease'}),
                html.Td(f"{earnings:,.2f} ₽",
                       style={'color': earnings_color, 'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'fontWeight': 'bold', 'transition': 'all 0.3s ease'}),
                html.Td(f"{ops_per_hour:.1f}",
                       style={'padding': '12px', 'borderBottom': '1px solid #eee', 'fontSize': '14px', 'fontWeight': 'bold', 'transition': 'all 0.3s ease', 'className': ops_color})
            ])
        )

    return html.Table([
        html.Thead(html.Tr([
            html.Th('Сотрудник', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
            html.Th('Операции', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
            html.Th('Время', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
            html.Th('Заработок', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
            html.Th('Оп/час', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'})
        ])),
        html.Tbody(rows)
    ], style={'width': '100%', 'borderCollapse': 'collapse'})
    
    

def create_shift_employees_table():
    """Создание таблицы 'Сотрудники на смене' - ТОЛЬКО СЕГОДНЯШНЯЯ СМЕНА
    Использует новое view dm.v_employees_shift_daily
    Сортировка по клику на заголовки: Статус, Время первой операции
    """

    # Получаем данные из нового view
    employees, position_stats = get_employees_on_shift_new()
    positions = get_positions_list_new()
    brigades = get_brigades_list_new()

    # Создаем фильтры
    position_filter = dcc.Dropdown(
        id='position-filter',
        options=[{'label': 'Все должности', 'value': 'all'}] + [{'label': pos, 'value': pos} for pos in positions],
        value='all',
        clearable=False,
        style={'width': '100%', 'marginBottom': '10px'}
    )

    # Фильтр по участку (переименовано с бригады)
    brigade_filter = dcc.Dropdown(
        id='brigade-filter',
        options=[{'label': 'Все участки', 'value': 'all'}] + [{'label': brig, 'value': brig} for brig in brigades],
        value='all',
        clearable=False,
        style={'width': '100%', 'marginBottom': '10px'}
    )

    # Стили для кликабельных заголовков
    sortable_header_style = {
        'color': '#666',
        'padding': '12px',
        'textAlign': 'left',
        'fontSize': '14px',
        'borderBottom': '2px solid #eee',
        'background': '#f8f9fa',
        'cursor': 'pointer',
        'userSelect': 'none',
        'transition': 'all 0.2s ease'
    }

    # Стили для иконки сортировки
    sort_icon_style = {
        'marginLeft': '5px',
        'fontSize': '12px',
        'opacity': '0.5'
    }

    return html.Div([
        html.Div([
            html.Div([
                html.Label("Фильтр по должности:", style={'fontSize': '12px', 'color': '#666', 'marginBottom': '5px'}),
                position_filter
            ], style={'flex': '1', 'marginRight': '10px'}),
            html.Div([
                html.Label("Фильтр по участку:", style={'fontSize': '12px', 'color': '#666', 'marginBottom': '5px'}),
                brigade_filter
            ], style={'flex': '1'})
        ], style={'display': 'flex', 'padding': '15px', 'background': '#f8f9fa', 'borderRadius': '8px', 'marginBottom': '15px'}),

        # УДАЛЕН блок info_panel с статистикой (перемещен в правую панель)

        html.Table([
            html.Thead(html.Tr([
                html.Th('ФИО сотрудника', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                html.Th('Должность', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                html.Th('Участок', style={'color': '#666', 'padding': '12px', 'textAlign': 'left', 'fontSize': '14px', 'borderBottom': '2px solid #eee', 'background': '#f8f9fa'}),
                html.Th(
                    html.Div([
                        html.Span('Статус', style={'marginRight': '5px'}),
                        html.Span('⇅', id='sort-status-icon', style=sort_icon_style)
                    ], style={'display': 'flex', 'alignItems': 'center'}),
                    id='sort-status-header',
                    style=sortable_header_style,
                    n_clicks=0
                ),
                html.Th(
                    html.Div([
                        html.Span('Время первой операции', style={'marginRight': '5px'}),
                        html.Span('⇅', id='sort-time-icon', style=sort_icon_style)
                    ], style={'display': 'flex', 'alignItems': 'center'}),
                    id='sort-time-header',
                    style={**sortable_header_style, 'textAlign': 'center'},
                    n_clicks=0
                ),
                html.Th(
                    html.Div([
                        html.Span('Время посл. операции', style={'marginRight': '5px'}),
                        html.Span('⇅', id='sort-last-time-icon', style=sort_icon_style)
                    ], style={'display': 'flex', 'alignItems': 'center'}),
                    id='sort-last-time-header',
                    style={**sortable_header_style, 'textAlign': 'center'},
                    n_clicks=0
                ),
            ])),
            html.Tbody(id='shift-employees-table-body')
        ], style={'width': '100%', 'borderCollapse': 'collapse'})
    ])