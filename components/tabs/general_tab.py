from dash import html, dcc
import dash_echarts
from components.tables import create_shift_employees_table

# Единый стиль для всех карточек - ВСЁ ПО ВЫСОТЕ
CARD_CONTAINER_STYLE = {
    'display': 'flex',
    'flexDirection': 'column',
    'height': '180px',  # Фиксированная высота
    'padding': '20px',
    'boxSizing': 'border-box'
}

CARD_TITLE_STYLE = {
    'color': '#666666',  # Как у вкладок
    'fontSize': '14px',
    'fontWeight': 'normal',  # Тоньше
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
    'color': '#666666',  # Как у вкладок
    'fontSize': '36px',
    'fontWeight': 'normal',  # Тоньше
    'textAlign': 'center',
    'height': '50px',
    'display': 'flex',
    'alignItems': 'center',
    'justifyContent': 'center',
    'marginBottom': '0'
}

CARD_DETAIL_STYLE = {
    'color': '#666666',  # Как у вкладок
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

def create_general_tab():
    """Создание вкладки 'Общая сводка' (без диаграммы Точность заказов)"""
    return html.Div([
        # KPI карточки - ИСПРАВЛЕННЫЙ РЯД С АДАПТИВНОСТЬЮ
        html.Div([
            # Карточка 1: Кол-во ревизий по событию
            html.Div([
                # Ряд 1: Название
                html.Div("Кол-во ревизий по событию", style=CARD_TITLE_STYLE),
                # Ряд 2: Кнопка
                html.Div([
                    html.Button(
                        "📋 Подробнее",
                        id="open-revision-info",
                        className="glow-on-hover",
                        style=CARD_BUTTON_STYLE
                    )
                ], style=CARD_BUTTON_ROW_STYLE),
                # Ряд 3: Основное значение
                html.Div(id="total-revisions-kpi", style=CARD_VALUE_STYLE),
                # Ряд 4: Детали
                html.Div([
                    html.Div([
                        html.Span("📋 Открыто: ", style={'fontWeight': 'bold'}),
                        html.Span(id="open-revisions-kpi")
                    ]),
                    html.Div([
                        html.Span("⏳ На согласовании: ", style={'fontWeight': 'bold'}),
                        html.Span(id="in-process-revisions-kpi")
                    ])
                ], style=CARD_DETAIL_STYLE)
            ], className='kpi-card dashboard-element docker-hover-effect', style={'animationDelay': '0.2s', **CARD_CONTAINER_STYLE}),

            # Карточка 2: Ошибки при размещении
            html.Div([
                # Ряд 1: Название
                html.Div("Ошибки при размещении", style=CARD_TITLE_STYLE),
                # Ряд 2: Кнопка
                html.Div([
                    html.Button(
                        "📋 Подробнее",
                        id="open-placement-info",
                        className="glow-on-hover",
                        style=CARD_BUTTON_STYLE
                    )
                ], style=CARD_BUTTON_ROW_STYLE),
                # Ряд 3: Основное значение
                html.Div(id="placement-errors-kpi", style=CARD_VALUE_STYLE),
                # Ряд 4: Детали
                html.Div([
                    html.Div([
                        html.Span("✅ Верно: ", style={'fontWeight': 'bold'}),
                        html.Span(id="placement-correct-kpi")
                    ]),
                    html.Div([
                        html.Span("❌ Ошибок: ", style={'fontWeight': 'bold'}),
                        html.Span(id="placement-errors-count-kpi")
                    ])
                ], style=CARD_DETAIL_STYLE)
            ], className='kpi-card dashboard-element docker-hover-effect', style={'animationDelay': '0.3s', **CARD_CONTAINER_STYLE}),

            # Карточка 3: Точность заказов
            html.Div([
                # Ряд 1: Название
                html.Div("Точность заказов", style=CARD_TITLE_STYLE),
                # Ряд 2: Кнопка
                html.Div([
                    html.Button(
                        "📋 Подробнее",
                        id="open-order-accuracy-modal",
                        className="glow-on-hover",
                        style=CARD_BUTTON_STYLE
                    )
                ], style=CARD_BUTTON_ROW_STYLE),
                # Ряд 3: Основное значение
                html.Div(id="order-accuracy-kpi", style=CARD_VALUE_STYLE),
                # Ряд 4: Пусто (нет деталей)
                html.Div("", style=CARD_EMPTY_DETAIL_STYLE)
            ], className='kpi-card dashboard-element docker-hover-effect', style={'animationDelay': '0.4s', **CARD_CONTAINER_STYLE}),

            # Карточка 4: Ячейки хранения
            html.Div([
                # Ряд 1: Название
                html.Div("Ячейки хранения своб/зан", style=CARD_TITLE_STYLE),
                # Ряд 2: Кнопка
                html.Div([
                    html.Button(
                        "📋 Подробнее",
                        id="open-storage-modal",
                        className="glow-on-hover",
                        style=CARD_BUTTON_STYLE
                    )
                ], style=CARD_BUTTON_ROW_STYLE),
                # Ряд 3: Основное значение
                html.Div(id="storage-cells-kpi", style=CARD_VALUE_STYLE),
                # Ряд 4: Детали
                html.Div(id="storage-cells-detail", style=CARD_DETAIL_STYLE)
            ], className='kpi-card dashboard-element docker-hover-effect', style={'animationDelay': '0.5s', **CARD_CONTAINER_STYLE}),

            # Карточка 5: Отклоненные строки в заказах
            html.Div([
                # Ряд 1: Название
                html.Div("Отклоненные строки в заказах", style=CARD_TITLE_STYLE),
                # Ряд 2: Кнопка
                html.Div([
                    html.Button(
                        "📋 Подробнее",
                        id="open-rejected-lines-modal",
                        className="glow-on-hover",
                        style=CARD_BUTTON_STYLE
                    )
                ], style=CARD_BUTTON_ROW_STYLE),
                # Ряд 3: Основное значение
                html.Div(id="rejected-lines-kpi", style=CARD_VALUE_STYLE),
                # Ряд 4: Детали
                html.Div(id="rejected-lines-detail", style=CARD_DETAIL_STYLE)
            ], className='kpi-card dashboard-element docker-hover-effect', style={'animationDelay': '0.6s', **CARD_CONTAINER_STYLE})
        ], className="kpi-row"),
        
        # Основной контент: Левая панель (таблица) + Правая панель (статистика)
        html.Div([
            # ЛЕВАЯ ПАНЕЛЬ: Только таблица сотрудников на смене
            html.Div([
                html.H3("Сотрудники на смене",
                       style={'color': '#333', 'margin': '0', 'fontSize': '20px', 'fontWeight': 'bold', 'padding': '15px 20px'}),
                html.Div([
                    create_shift_employees_table()
                ], style={'flex': '1', 'overflowY': 'auto', 'padding': '0 20px 20px 20px'})
            ], className="dashboard-element docker-hover-effect", style={'animationDelay': '0.7s', 'width': '60%', 'height': '600px', 'display': 'flex', 'flexDirection': 'column', 'background': 'white', 'borderRadius': '12px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'}),
            
            # ПРАВАЯ ПАНЕЛЬ: Контейнер статистики смены
            html.Div([
                html.H3("Статистика смены",
                       className="chart-header",
                       style={'color': '#333', 'margin': '0', 'fontSize': '18px', 'fontWeight': 'bold', 'padding': '15px 20px', 'background': 'white', 'borderRadius': '12px 12px 0 0'}),
                # Контейнер для статистики (заполняется через callback)
                html.Div(id='shift-stats-info', style={'flex': '1', 'overflowY': 'auto', 'padding': '0 20px 20px 20px'})
            ], className='chart-card-no-padding dashboard-element docker-hover-effect', style={'animationDelay': '0.8s', 'width': '40%', 'height': '600px', 'display': 'flex', 'flexDirection': 'column'})
        ], className="main-content", style={'display': 'flex', 'gap': '20px'})
    ], style={'padding': '10px'})