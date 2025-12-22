from dash import html, dcc
import dash_echarts
from components.tables import create_shift_employees_table

def create_general_tab():
    """Создание вкладки 'Общая сводка' (без диаграммы Точность заказов)"""
    return html.Div([
        # KPI карточки
        html.Div([
            # НОВАЯ КАРТОЧКА: Кол-во ревизий по событию (заменяет "Собрано заказов вовремя")
            html.Div([
                html.Div([
                    html.Span("Кол-во ревизий по событию", 
                             style={'verticalAlign': 'middle'}),
                    html.Button(
                        "ℹ️",
                        id="open-revision-info",
                        title="Подробная информация",
                        style={
                            'background': 'transparent',
                            'border': 'none',
                            'fontSize': '12px',
                            'cursor': 'pointer',
                            'color': '#2e7d32',
                            'marginLeft': '6px',
                            'padding': '1px 4px',
                            'borderRadius': '3px',
                            'transition': 'all 0.2s ease',
                            'verticalAlign': 'middle'
                        }
                    )
                ], style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="total-revisions-kpi", style={'color': '#2e7d32', 'fontSize': '36px', 'fontWeight': 'bold', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div([
                    html.Div([
                        html.Span("📋 Открыто: ", style={'fontWeight': 'bold'}),
                        html.Span(id="open-revisions-kpi", style={'color': '#ff9800'})
                    ], style={'marginBottom': '4px'}),
                    html.Div([
                        html.Span("⏳ На согласовании: ", style={'fontWeight': 'bold'}),
                        html.Span(id="in-process-revisions-kpi", style={'color': '#2196f3'})
                    ], style={})
                ], style={'color': '#666', 'fontSize': '12px', 'textAlign': 'center', 'lineHeight': '1.4'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.2s'}),
            
            # Существующие карточки (остаются без изменений)
            html.Div([
                html.Div("Ср. время операции", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="avg-operation-time-kpi", style={'color': '#1976d2', 'fontSize': '36px', 'fontWeight': 'bold', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="avg-productivity-kpi", style={'color': '#1976d2', 'fontSize': '14px', 'textAlign': 'center'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.3s'}),
            html.Div([
                html.Div("Точность заказов", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="order-accuracy-kpi", style={'color': '#ed6c02', 'fontSize': '36px', 'fontWeight': 'bold', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="order-accuracy-detail", style={'color': '#ed6c02', 'fontSize': '14px', 'textAlign': 'center'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.4s'}),
            html.Div([
                html.Div([
                    html.Span("Ячейки хранения своб/зан", 
                             style={'verticalAlign': 'middle'}),
                    html.Button(
                        "📊",
                        id="open-storage-modal",
                        title="Подробная аналитика",
                        style={
                            'background': 'transparent',
                            'border': 'none',
                            'fontSize': '16px',
                            'cursor': 'pointer',
                            'color': '#9c27b0',
                            'marginLeft': '8px',
                            'padding': '2px 6px',
                            'borderRadius': '4px',
                            'transition': 'all 0.2s ease',
                            'verticalAlign': 'middle'
                        }
                    )
                ], style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="storage-cells-kpi", style={'color': '#9c27b0', 'fontSize': '36px', 'fontWeight': 'bold', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="storage-cells-detail", style={'color': '#9c27b0', 'fontSize': '14px', 'textAlign': 'center'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.5s'})
        ], className="kpi-row"),
        
        # Основной контент: Левая панель (таблица) + Правая панель (статистика)
        html.Div([
            # ЛЕВАЯ ПАНЕЛЬ: Только таблица сотрудников на смене
            html.Div([
                html.Div([
                    html.H3("Сотрудники на смене", 
                           style={'color': '#333', 'margin': '0', 'fontSize': '20px', 'flex': '1', 'fontWeight': 'bold'})
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
                    create_shift_employees_table()
                ], className="table-container", style={'height': '520px', 'overflowY': 'auto', 'borderRadius': '0 0 12px 12px'})
            ], className="left-panel dashboard-element", style={'animationDelay': '0.6s', 'width': '60%'}),
            
            # ПРАВАЯ ПАНЕЛЬ: Контейнер статистики смены (ВМЕСТО диаграммы)
            html.Div([
                html.Div([
                    html.Div([
                        html.H3("Статистика смены", style={'color': '#333', 'marginBottom': '15px', 'fontSize': '18px', 'fontWeight': 'bold'}),
                        # Контейнер для статистики (заполняется через callback)
                        html.Div(id='shift-stats-info', style={'height': '520px', 'overflowY': 'auto'})
                    ], className='chart-card dashboard-element', style={'animationDelay': '0.7s', 'height': '600px'})
                ], className="charts-row", style={'height': '620px'})
            ], className="right-panel dashboard-element", style={'animationDelay': '0.7s', 'width': '40%'})
        ], className="main-content", style={'display': 'flex', 'gap': '20px'})
    ], style={'padding': '10px'})