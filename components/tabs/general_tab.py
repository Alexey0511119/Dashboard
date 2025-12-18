from dash import html, dcc
import dash_echarts
from components.tables import create_shift_employees_table

def create_general_tab():
    """Создание вкладки 'Общая сводка' (без диаграммы Точность заказов)"""
    return html.Div([
        # KPI карточки
        html.Div([
            html.Div([
                html.Div("Собрано заказов вовремя", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="orders-timely-kpi", style={'color': '#2e7d32', 'fontSize': '36px', 'fontWeight': 'bold', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="orders-percentage-kpi", style={'color': '#2e7d32', 'fontSize': '14px', 'textAlign': 'center'})
            ], className='kpi-card dashboard-element', style={'animationDelay': '0.2s'}),
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
                html.Div("Общий заработок", style={'color': '#666', 'fontSize': '16px', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="total-earnings-kpi", style={'color': '#9c27b0', 'fontSize': '36px', 'fontWeight': 'bold', 'marginBottom': '8px', 'textAlign': 'center'}),
                html.Div(id="active-employees-kpi", style={'color': '#9c27b0', 'fontSize': '14px', 'textAlign': 'center'})
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