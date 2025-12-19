import base64
from dash import html, dcc
from datetime import datetime, timedelta
import dash_echarts
from components.modals import create_analytics_modal, create_fines_modal, create_idle_detail_modal, create_storage_cells_modal
from components.tabs.general_tab import create_general_tab
from components.tabs.productivity_tab import create_productivity_tab
from components.tabs.timeliness_tab import create_timeliness_tab
from components.tabs.fines_tab import create_fines_tab
from components.tabs.shift_tab import create_shift_tab

def create_layout():
    """Создание основного layout приложения"""
    
    # ОТЛАДОЧНАЯ ИНФОРМАЦИЯ
    print("=== LAYOUT DEBUG ===")
    print("Проверка наличия функций:")
    print("- create_analytics_modal:", "create_analytics_modal" in globals())
    print("- create_fines_modal:", "create_fines_modal" in globals())
    print("- create_idle_detail_modal:", "create_idle_detail_modal" in globals())
    
    # Загрузка фонового изображения
    try:
        with open("Рисунок1.png", "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        encoded_image = ""
    
    # Загрузка логотипа
    logo_url = ""
    try:
        with open("logo.png", "rb") as logo_file:
            encoded_logo = base64.b64encode(logo_file.read()).decode()
            logo_url = f"data:image/png;base64,{encoded_logo}"
    except FileNotFoundError:
        logo_url = ""
    
    return html.Div([
        # Модальные окна
        create_analytics_modal(),
        create_fines_modal(),
        create_idle_detail_modal(),  # ДОБАВЛЕНО НОВОЕ ОКНО
        create_storage_cells_modal(),
        
        # Store компоненты для хранения состояния
        dcc.Store(id='selected-employee', data=''),
        dcc.Store(id='current-table-view', data='all'),
        dcc.Store(id='selected-analytics-employee', data=''),
        dcc.Store(id='timeliness-period', data='week'),
        dcc.Store(id='timeliness-data', data={}),
        dcc.Store(id='fines-data', data={}),
        dcc.Store(id='fines-period', data='week'),
        dcc.Store(id='selected-fines-employee', data=''),
        dcc.Store(id='shift-comparison-data', data={}),
        dcc.Store(id='global-date-range', data={
            'start_date': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            'end_date': datetime.now().strftime('%Y-%m-%d')
        }),
        dcc.Store(id='orders-table-data', data=[]),
        dcc.Store(id='performance-data-cache', data=[]),
        dcc.Store(id='shift-comparison-cache', data=[]),
        dcc.Store(id='problematic-hours-cache', data=[]),
        dcc.Store(id='error-hours-cache', data=[]),
        dcc.Store(id='shift-employees-cache', data=[]),
        
        # НОВЫЕ Store компоненты
        dcc.Store(id='selected-idle-interval', data=''),  # Для хранения выбранного интервала простоя
        dcc.Store(id='idle-detail-day', data=''),  # Для хранения выбранного дня
        
        # Основной контент с вкладками
        html.Div([
            # Шапка с названием дашборда - НОВАЯ СТРУКТУРА
            html.Div([
                # ЛЕВАЯ ЧАСТЬ: Название дашборда (вверху) + логотип (внизу)
                html.Div([
                    # Название дашборда
                    html.H1("РЦ Новосибирск", 
                           style={
                               'color': 'black', 
                               'margin': '0', 
                               'marginTop': '30px',
                               'fontSize': '28px', 
                               'fontWeight': 'bold',
                               'lineHeight': '1.2'
                           }),
                    
                    # Логотип под названием
                    html.Img(
                        src=logo_url,
                        style={
                            'height': '90px',
                            'maxWidth': '240px',
                            'objectFit': 'contain',
                            'marginTop': '-10px'
                        }
                    ) if logo_url else html.Div()
                ], style={
                    'display': 'flex',
                    'flexDirection': 'column',
                    'justifyContent': 'center',
                    'alignItems': 'flex-start'
                }),
                
                # ПРАВАЯ ЧАСТЬ: Дата и фильтр
                html.Div([
                    html.Div(id="last-update-time", 
                            style={
                                'color': '#333', 
                                'fontSize': '12px', 
                                'marginBottom': '2px',
                                'textAlign': 'right'
                            }),
                    dcc.DatePickerRange(
                        id='global-date-range-picker',
                        start_date=datetime.now() - timedelta(days=7),
                        end_date=datetime.now(),
                        display_format='DD.MM.YYYY',
                        style={
                            'fontSize': '12px',
                            'position': 'relative',
                            'zIndex': '9999'
                        }
                    )
                ], style={
                    'padding': '5px 10px',
                    'backgroundColor': '#808080',  # Серый цвет как у панели
                    'borderRadius': '6px',
                    'display': 'inline-block'
                })
            ], className="header dashboard-element", style={
                'animationDelay': '0.1s', 
                'padding': '15px 25px',
                'position': 'relative',
                'backgroundColor': '#808080',  # Серый цвет
                'display': 'flex',
                'justifyContent': 'space-between',  # Растягиваем по всей ширине
                'alignItems': 'center',  # Выравниваем по центру вертикально
                'borderRadius': '12px 12px 0 0',
                'minHeight': '80px',  # Оставляем стандартную высоту
                'width': '100%'  # Занимает всю ширину
            }),
            
            # Вкладки (обновленный список с новой вкладкой Производительность)
            dcc.Tabs(id="main-tabs", value='general', children=[
                dcc.Tab(
                    label='Общая сводка',
                    value='general',
                    className='custom-tab',
                    selected_className='custom-tab--selected',
                    children=[create_general_tab()]
                ),
                dcc.Tab(
                    label='Производительность',
                    value='productivity',
                    className='custom-tab',
                    selected_className='custom-tab--selected',
                    children=[create_productivity_tab()]
                ),
                dcc.Tab(
                    label='Своевременность',
                    value='timeliness',
                    className='custom-tab',
                    selected_className='custom-tab--selected',
                    children=[create_timeliness_tab()]
                ),
                dcc.Tab(
                    label='Штрафы',
                    value='fines',
                    className='custom-tab',
                    selected_className='custom-tab--selected',
                    children=[create_fines_tab()]
                ),
                dcc.Tab(
                    label='Сравнение смен',
                    value='shift-comparison',
                    className='custom-tab',
                    selected_className='custom-tab--selected',
                    children=[create_shift_tab()]
                )
            ], style={'marginBottom': '20px'})
        ], className="dashboard-container", id="dashboard-content")
    ], className="app-container")