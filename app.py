import dash
from dash import Dash, html, dcc
from datetime import datetime, timedelta
import base64
from components.layout import create_layout
from callbacks.main_callbacks import *
from callbacks.tab_callbacks import *
from callbacks.modal_callbacks import *
from data.queries_mssql import refresh_data
# Добавим импорт для нового модального окна
from components.modals import create_rejected_lines_modal

# Инициализация приложения Dash
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# Установка layout
app.layout = create_layout()

# Настройка HTML шаблона
try:
    with open("Рисунок1.png", "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode()
except FileNotFoundError:
    encoded_image = ""

app.index_string = f'''
<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        {{%favicon%}}
        {{%css%}}
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            .app-container {{
                background: url("data:image/png;base64,{encoded_image}") no-repeat center center fixed;
                background-size: contain;
                padding: 20px;
                min-height: 100vh;
                font-family: Arial, sans-serif;
                width: 100%;
                margin: 0;
            }}
            .dashboard-container {{
                max-width: 100%;
                margin: 0 auto;
            }}
            .dashboard-element {{
                opacity: 0;
                transform: translateY(30px);
                animation: fadeInUp 0.8s ease forwards;
            }}
            @keyframes fadeInUp {{
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}
            /* ОБНОВЛЕННЫЙ СТИЛЬ ДЛЯ ШАПКИ */
            .header {{
                background-color: #808080;
                padding: 15px 25px;
                margin-bottom: 25px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                border-radius: 12px 12px 0 0;
                min-height: 80px;
                width: 100%;
            }}
            .header-left {{
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: flex-start;
            }}
            .header-left h1 {{
                color: black;
                margin: 0;
                font-size: 28px;
                font-weight: bold;
                line-height: 1.2;
            }}
            .header-left img {{
                height: 90px;
                max-width: 240px;
                object-fit: contain;
                margin-top: 5px;
            }}
            .header-right {{
                background-color: #808080;
                padding: 5px 10px;
                border-radius: 6px;
                display: inline-block;
            }}
            .header-right #last-update-time {{
                color: #333;
                font-size: 12px;
                margin-bottom: 2px;
                text-align: right;
            }}
            .custom-tab {{
                background-color: #f8f9fa;
                color: #666;
                border: 1px solid #dee2e6;
                border-bottom: none;
                padding: 15px 30px;
                font-size: 18px;
                font-weight: bold;
                border-radius: 12px 12px 0 0;
                margin-right: 5px;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            .custom-tab:hover {{
                background-color: #e9ecef;
                color: #1976d2;
                transform: translateY(-2px);
            }}
            .custom-tab--selected {{
                background-color: white !important;
                color: #1976d2 !important;
                border-bottom: 3px solid #1976d2;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
            /* ИСПРАВЛЕННЫЙ СТИЛЬ ДЛЯ КАРТОЧЕК - Теперь полностью адаптивный */
            .kpi-row {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                gap: 15px;
                margin-bottom: 25px;
                width: 100%;
            }}
            .kpi-card {{
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                text-align: center;
                width: 100%;
                min-height: 180px;
            }}
            .kpi-card:hover {{
                transform: translateY(-5px) scale(1.02);
                box-shadow: 0 12px 30px rgba(0,0,0,0.15);
            }}
            .main-content {{
                display: flex;
                gap: 20px;
                min-height: 560px;
            }}
            .left-panel, .right-panel, .full-width-panel {{
                display: flex;
                flex-direction: column;
            }}
            .table-container {{
                background: white;
                padding: 0;
                border-radius: 0 0 12px 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                height: 520px;
                overflow: hidden;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
            }}
            .table-view {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                overflow-y: auto;
                opacity: 0;
                transform: translateX(50px);
                transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
                pointer-events: none;
            }}
            .table-view.active {{
                opacity: 1;
                transform: translateX(0);
                pointer-events: all;
                transition-delay: 0.1s;
            }}
            .nav-btn {{
                padding: 8px 16px;
                border: 1px solid #ddd;
                background: white;
                color: #666;
                cursor: pointer;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .nav-btn:hover {{
                background: #f8f9fa;
                border-color: #1976d2;
                color: #1976d2;
                transform: scale(1.1);
                box-shadow: 0 4px 12px rgba(25, 118, 210, 0.2);
            }}
            .chart-card {{
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            .chart-card:hover {{
                transform: translateY(-5px) scale(1.02);
                box-shadow: 0 12px 30px rgba(0,0,0,0.15);
            }}
            .analytics-kpi-row {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 25px;
            }}
            .analytics-kpi-card {{
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                text-align: center;
            }}
            .analytics-content-row {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                height: 650px;
            }}
            .analytics-chart-card {{
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            .operations-stats-table {{
                max-height: 300px;
                overflow-y: auto;
                border: 1px solid #eee;
                border-radius: 8px;
            }}
            .operations-stats-table table {{
                width: 100%;
                border-collapse: collapse;
            }}
            .operations-stats-table th {{
                background: #f8f9fa;
                padding: 10px;
                text-align: left;
                font-size: 12px;
                color: #666;
                border-bottom: 1px solid #eee;
                position: sticky;
                top: 0;
            }}
            .operations-stats-table td {{
                padding: 8px 10px;
                font-size: 12px;
                border-bottom: 1px solid #f0f0f0;
            }}
            /* НОВЫЕ СТИЛИ ДЛЯ АНИМАЦИЙ В МОДАЛЬНЫХ ОКНАХ */
            .modal-hidden {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: -1;
                opacity: 0;
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            .modal-visible {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.8);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 1000;
                opacity: 1;
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            .modal-content {{
                background: white;
                border-radius: 20px;
                width: 95%;
                height: 95%;
                max-width: 95vw;
                max-height: 95vh;
                overflow: hidden;
                transform: scale(0.7) translateY(50px);
                opacity: 0;
                box-shadow: 0 25px 80px rgba(0,0,0,0.4);
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            .modal-content-visible {{
                background: white;
                border-radius: 20px;
                width: 95%;
                height: 95%;
                max-width: 95vw;
                max-height: 95vh;
                overflow: hidden;
                transform: scale(1) translateY(0);
                opacity: 1;
                box-shadow: 0 25px 80px rgba(0,0,0,0.4);
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            /* Стили для интерактивных элементов в модальных окнах */
            .analytics-kpi-card:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                border: 1px solid rgba(25, 118, 210, 0.2);
            }}
            
            .analytics-chart-card {{
                border: 2px solid transparent;
                transition: all 0.3s ease;
            }}
            .analytics-chart-card:hover {{
                border-color: #e3f2fd;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
            }}
            
            /* Docker-like hover effects */
            .docker-hover-effect {{
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                border-radius: 10px;
                overflow: hidden;
            }}
            .docker-hover-effect:hover {{
                transform: translateY(-4px);
                box-shadow: 
                    0 15px 30px rgba(0, 0, 0, 0.1),
                    0 5px 15px rgba(0, 0, 0, 0.05),
                    inset 0 1px 0 rgba(255, 255, 255, 0.6);
                border-color: rgba(0, 150, 255, 0.3);
            }}
            
            /* Стили для кнопок сброса в модальных окнах */
            .reset-btn {{
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }}
            .reset-btn:hover {{
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                transform: scale(1.05);
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            }}
            .reset-btn:active {{
                transform: scale(0.95);
            }}
            
            /* Эффект свечения при наведении на кнопки */
            .glow-on-hover {{
                transition: all 0.3s ease;
            }}
            .glow-on-hover:hover {{
                box-shadow: 0 0 15px rgba(33, 150, 243, 0.3);
            }}
            
            /* Эффект для элементов таблицы */
            .table-row-hover {{
                transition: all 0.2s ease;
            }}
            .table-row-hover:hover {{
                background-color: rgba(25, 118, 210, 0.05);
                transform: scale(1.002);
                box-shadow: inset 0 0 0 1px rgba(25, 118, 210, 0.1);
            }}
            
            /* Эффекты для заголовков диаграмм */
            .chart-header {{
                transition: all 0.3s ease;
                position: relative;
            }}
            .chart-header:hover {{
                color: #1976d2;
                transform: translateX(5px);
            }}
            .chart-header::after {{
                content: '';
                position: absolute;
                bottom: -5px;
                left: 0;
                width: 0;
                height: 2px;
                background: linear-gradient(90deg, #1976d2, #21c1d6);
                transition: width 0.3s ease;
            }}
            .chart-header:hover::after {{
                width: 100%;
            }}
            
            .fines-employee-link {{
                color: #B71C1C;
                text-decoration: none;
                cursor: pointer;
                font-weight: bold;
                transition: all 0.3s ease;
                padding: 2px 6px;
                border-radius: 4px;
            }}
            .fines-employee-link:hover {{
                color: #F44336;
                text-decoration: underline;
                background-color: rgba(244, 67, 54, 0.1);
                box-shadow: 0 2px 8px rgba(244, 67, 54, 0.2);
            }}
            .employee-link {{
                color: #1976d2;
                text-decoration: none;
                cursor: pointer;
                font-weight: bold;
                transition: all 0.3s ease;
                padding: 2px 6px;
                border-radius: 4px;
            }}
            .employee-link:hover {{
                color: #0d47a1;
                text-decoration: underline;
                background-color: rgba(25, 118, 210, 0.1);
                box-shadow: 0 2px 8px rgba(25, 118, 210, 0.2);
            }}
            /* ИСПРАВЛЕННЫЕ стили для отображения календаря поверх элементов */
            .DateRangePicker {{
                position: relative;
                z-index: 9999 !important;
            }}
            .DateRangePickerInput, .DateInput {{
                z-index: 9999;
                position: relative;
            }}
            .DateRangePicker_picker {{
                z-index: 10000 !important;
                position: fixed !important;
                top: 120px !important;
                left: auto !important;
                right: 20px !important;
            }}
            .CalendarMonth {{
                background: white;
            }}
            .DayPicker {{
                background: white;
            }}
            /* Убедимся, что календарь всегда поверх всего */
            .DateRangePickerInput__withBorder {{
                border-radius: 4px;
                border: 1px solid #ddd;
            }}
            /* Для мобильных устройств */
            @media (max-width: 768px) {{
                .DateRangePicker_picker {{
                    position: fixed !important;
                    top: 50% !important;
                    left: 50% !important;
                    transform: translate(-50%, -50%) !important;
                    right: auto !important;
                }}
                .kpi-row {{
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                }}
                .main-content {{
                    flex-direction: column;
                }}
                .left-panel, .right-panel {{
                    width: 100% !important;
                }}
                .analytics-kpi-row {{
                    grid-template-columns: repeat(2, 1fr);
                }}
            }}
            @media (max-width: 480px) {{
                .kpi-row {{
                    grid-template-columns: 1fr;
                }}
                .analytics-kpi-row {{
                    grid-template-columns: 1fr;
                }}
                .header {{
                    flex-direction: column;
                    text-align: center;
                    gap: 15px;
                }}
                .header-right {{
                    width: 100%;
                    text-align: center;
                }}
            }}
            /* Цветовая индикация для таблиц */
            .good-performance {{
                color: #4CAF50 !important;
                font-weight: bold;
            }}
            .medium-performance {{
                color: #FF9800 !important;
                font-weight: bold;
            }}
            .poor-performance {{
                color: #F44336 !important;
                font-weight: bold;
            }}
            /* Стили для скроллбара в ряду карточек */
            .kpi-row::-webkit-scrollbar {{
                height: 6px;
            }}
            .kpi-row::-webkit-scrollbar-track {{
                background: #f1f1f1;
                border-radius: 3px;
            }}
            .kpi-row::-webkit-scrollbar-thumb {{
                background: #888;
                border-radius: 3px;
            }}
            .kpi-row::-webkit-scrollbar-thumb:hover {{
                background: #555;
            }}
        </style>
    </head>
    <body>
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>
'''

if __name__ == "__main__":
    default_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    default_end = datetime.now().strftime('%Y-%m-%d')
    
    refresh_data(default_start, default_end)
    
    app.run_server(debug=True, host="0.0.0.0", port=8055)