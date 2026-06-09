import dash
from dash import Dash, html, dcc
from datetime import datetime, timedelta
import base64
from flask import request, Response
import logging
import openpyxl
from openpyxl.styles import Font, Border, Side, PatternFill, Alignment
import traceback
import sys
import os
from logging.handlers import RotatingFileHandler

# ============================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ С ФИЛЬТРАЦИЕЙ ОШИБОК DASH
# ============================================================================

class DashErrorFilter(logging.Filter):
    """Фильтр для игнорирования ожидаемых ошибок Dash"""
    def filter(self, record):
        msg = record.getMessage()
        
        # Игнорируем IndexError из pattern-matching callback'ов
        if 'IndexError' in msg and 'list index out of range' in msg:
            return False
        
        # Игнорируем ошибки группировки Dash
        if 'dash/_grouping.py' in record.pathname:
            return False
        
        # Игнорируем ошибки подготовки callback'ов
        if '_prepare_callback' in msg or '_prepare_grouping' in msg:
            return False
            
        return True


def setup_logging():
    """Настройка логирования с ротацией файлов и фильтрацией"""
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Форматтер для логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Фильтр для Dash ошибок
    dash_filter = DashErrorFilter()
    
    # Обработчик для основного файла (ротация при достижении 10 МБ)
    file_handler = RotatingFileHandler(
        f'{log_dir}/dashboard.log',
        maxBytes=10*1024*1024,
        backupCount=3
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(dash_filter)
    
    # Обработчик для ошибок (отдельный файл, 5 МБ)
    error_handler = RotatingFileHandler(
        f'{log_dir}/error.log',
        maxBytes=5*1024*1024,
        backupCount=2
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_handler.addFilter(dash_filter)
    
    # Консольный вывод (только WARNING и выше)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    console_handler.addFilter(dash_filter)
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    
    # Отключаем излишнее логирование от werkzeug
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    
    return root_logger


# Настраиваем логирование
logger = setup_logging()

# Импортируем остальные модули
from components.layout import create_layout
from callbacks.main_callbacks import *
from callbacks.tab_callbacks import *
from callbacks.modal_callbacks import *
from data.queries_mssql import refresh_data
from components.modals import (
    create_rejected_lines_modal,
    create_best_employees_modal  # <-- НОВЫЙ ИМПОРТ
)

logger = logging.getLogger(__name__)

# Инициализация приложения Dash
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# Маршрут для страницы печати ревизий
@app.server.route('/print-revision')
def print_revision_page():
    """Отдаёт HTML-страницу печати по ключу временного файла"""
    from flask import request, Response
    import json
    import os
    import tempfile
    
    key = request.args.get('key', '')
    
    if not key:
        return "Не указан ключ данных", 400
    
    temp_dir = os.path.join(tempfile.gettempdir(), 'dash_print')
    data_file = os.path.join(temp_dir, f'{key}.json')
    
    if not os.path.exists(data_file):
        return "Данные не найдены или устарели", 400
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cached_data = data.get('revisions', [])
        locations_map = data.get('locations', {})
    except:
        return "Ошибка чтения данных", 400
    
    html_blocks = []
    
    for idx, item_data in enumerate(cached_data):
        item_code = item_data.get('item', '')
        item_desc = item_data.get('item_desc', '')
        
        max_desc_len = 80
        if item_desc and len(item_desc) > max_desc_len:
            short_desc = item_desc[:max_desc_len - 3] + '...'
        else:
            short_desc = item_desc or 'Без описания'
        
        other_locations = locations_map.get(str(item_code), [])
        
        locations_rows = ""
        if other_locations:
            for loc in other_locations:
                lot_val = loc.get('lot', '') if loc.get('lot') else '—'
                um_val = loc.get('um', 'шт')
                locations_rows += f"""
                    <tr>
                        <td class="loc-col">{loc['location']}</td>
                        <td class="qty-col">{loc['quantity']:,.0f}</td>
                        <td class="um-col">{um_val}</td>
                        <td class="lot-col">{lot_val}</td>
                    </tr>"""
        else:
            locations_rows = '<tr><td colspan="4" class="no-data">Нет данных об остатках</td></tr>'
        
        html_blocks.append(f"""
            <div class="item-block" id="block-{idx}">
                <div class="item-header">
                    <label class="checkbox-label">
                        <input type="checkbox" class="item-checkbox" data-block="block-{idx}">
                        <span class="item-title">ТОВАР: {item_code} — {short_desc}</span>
                    </label>
                </div>
                <div class="revision-line">
                    Ревизия №{item_data.get('internal_count_num', '')} | 
                    Статус: {item_data.get('status_rus', '')} | 
                    Локация: {item_data.get('location', '—')} | 
                    Подсчитано: {item_data.get('quantity_counted', 0):.2f} | 
                    Системное: {item_data.get('system_quantity', 0):.2f} | 
                    Отклонение: {item_data.get('variance', 0):+.2f}
                </div>
                <div class="revision-line-2">
                    Выполнил: {item_data.get('counted_by_user', '—')} | 
                    Дата: {item_data.get('counted_date_time', '—')}
                </div>
                <div class="locations-header">ОСТАТКИ НА ВСЕХ ЯЧЕЙКАХ:</div>
                <table class="locations-table">
                    <thead>
                        <tr>
                            <th class="loc-col">Локация</th>
                            <th class="qty-col">Количество</th>
                            <th class="um-col">Ед. изм.</th>
                            <th class="lot-col">Партия</th>
                        </tr>
                    </thead>
                    <tbody>{locations_rows}</tbody>
                </table>
                <hr class="separator">
            </div>
        """)
    
    html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Печать ревизий</title>
    <style>
        @page {{ size: A4 landscape; margin: 8mm; }}
        body {{ font-family: Arial, sans-serif; color: #333; margin: 0; padding: 10px; font-size: 10px; }}
        .toolbar {{ position: fixed; top: 0; left: 0; right: 0; background: #f8f9fa; padding: 10px 20px; border-bottom: 2px solid #1976D2; display: flex; gap: 15px; z-index: 1000; }}
        .toolbar button {{ padding: 8px 20px; border: none; border-radius: 6px; font-size: 13px; cursor: pointer; font-weight: bold; }}
        .btn-select-all {{ background: #1976D2; color: white; }}
        .btn-deselect-all {{ background: #f5f5f5; color: #666; border: 1px solid #ddd; }}
        .btn-print {{ background: #4CAF50; color: white; margin-left: auto; }}
        .content {{ margin-top: 60px; }}
        .item-block {{ margin-bottom: 8px; page-break-inside: avoid; }}
        .checkbox-label {{ display: flex; align-items: center; gap: 8px; cursor: pointer; }}
        .item-checkbox {{ width: 16px; height: 16px; accent-color: #1976D2; }}
        .item-title {{ font-size: 13px; font-weight: bold; color: #1976D2; }}
        .revision-line, .revision-line-2 {{ font-size: 10px; color: #333; margin: 3px 0; padding-left: 24px; }}
        .locations-header {{ font-size: 10px; font-weight: bold; color: #666; margin: 6px 0 4px 0; padding-left: 24px; }}
        .locations-table {{ border-collapse: collapse; margin: 0 0 0 24px; font-size: 10px; }}
        .locations-table th {{ background: #999; color: white; padding: 5px 10px; border: 1px solid #ccc; font-size: 9px; }}
        .locations-table td {{ padding: 4px 10px; border: 1px solid #e0e0e0; }}
        .loc-col {{ text-align: left; min-width: 120px; }}
        .qty-col {{ text-align: right; min-width: 70px; }}
        .um-col {{ text-align: center; min-width: 55px; }}
        .lot-col {{ text-align: left; min-width: 120px; }}
        .no-data {{ text-align: center; color: #999; font-style: italic; padding: 8px; }}
        .separator {{ border: none; border-top: 1px dashed #ccc; margin: 10px 0; }}
        @media print {{
            .toolbar {{ display: none !important; }}
            .item-checkbox {{ display: none !important; }}
            .content {{ margin-top: 0; }}
            .revision-line, .revision-line-2, .locations-header {{ padding-left: 0; }}
            .locations-table {{ margin-left: 0; }}
            .item-block.hidden-for-print {{ display: none !important; }}
        }}
    </style>
</head>
<body>
    <div class="toolbar">
        <button class="btn-select-all" onclick="document.querySelectorAll('.item-checkbox').forEach(cb => cb.checked = true)">☑ Выделить всё</button>
        <button class="btn-deselect-all" onclick="document.querySelectorAll('.item-checkbox').forEach(cb => cb.checked = false)">☐ Снять всё</button>
        <button class="btn-print" onclick="printSelected()">🖨️ Печатать отмеченное</button>
    </div>
    <div class="content">{''.join(html_blocks)}</div>
    <script>
        function printSelected() {{
            document.querySelectorAll('.item-checkbox').forEach(function(cb) {{
                var block = document.getElementById(cb.dataset.block);
                if (block) {{
                    block.classList.toggle('hidden-for-print', !cb.checked);
                }}
            }});
            window.print();
            setTimeout(function() {{
                document.querySelectorAll('.item-block').forEach(function(b) {{ b.classList.remove('hidden-for-print'); }});
            }}, 500);
        }}
    </script>
</body>
</html>"""
    
    return Response(html_content, mimetype='text/html')

# Установка layout
app.layout = create_layout()

# Настройка HTML шаблона
try:
    with open("Рисунок1.png", "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode()
except FileNotFoundError:
    encoded_image = ""

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            .app-container {
                background: url("data:image/png;base64,''' + encoded_image + '''") no-repeat center center fixed;
                background-size: contain;
                padding: 20px;
                min-height: 100vh;
                font-family: Arial, sans-serif;
                width: 100%;
                margin: 0;
            }
            .dashboard-container { max-width: 100%; margin: 0 auto; }
            .dashboard-element {
                opacity: 0;
                transform: translateY(30px);
                animation: fadeInUp 0.8s ease forwards;
            }
            @keyframes fadeInUp { to { opacity: 1; transform: translateY(0); } }
            .header {
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
            }
            .header-left {
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: flex-start;
            }
            .header-left h1 { color: black; margin: 0; font-size: 28px; font-weight: bold; line-height: 1.2; }
            .header-left img { height: 90px; max-width: 240px; object-fit: contain; margin-top: 5px; }
            .header-right {
                background-color: #808080;
                padding: 5px 10px;
                border-radius: 6px;
                display: inline-block;
            }
            .header-right #last-update-time {
                color: #333;
                font-size: 12px;
                margin-bottom: 2px;
                text-align: right;
            }
            .custom-tab {
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
            }
            .custom-tab:hover {
                background-color: #e9ecef;
                color: #1976d2;
                transform: translateY(-2px);
            }
            .custom-tab--selected {
                background-color: white !important;
                color: #1976d2 !important;
                border-bottom: 3px solid #1976d2;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            .kpi-row {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                gap: 15px;
                margin-bottom: 25px;
                width: 100%;
            }
            .kpi-card {
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
            }
            .kpi-card:hover {
                transform: translateY(-5px) scale(1.02);
                box-shadow: 0 12px 30px rgba(0,0,0,0.15);
            }
            .main-content { display: flex; gap: 20px; min-height: 560px; }
            .left-panel, .right-panel, .full-width-panel { display: flex; flex-direction: column; }
            .table-container {
                background: white;
                padding: 0;
                border-radius: 0 0 12px 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                height: 520px;
                overflow: hidden;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
            }
            .table-view {
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
            }
            .table-view.active {
                opacity: 1;
                transform: translateX(0);
                pointer-events: all;
                transition-delay: 0.1s;
            }
            .nav-btn {
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
            }
            .nav-btn:hover {
                background: #f8f9fa;
                border-color: #1976d2;
                color: #1976d2;
                transform: scale(1.1);
                box-shadow: 0 4px 12px rgba(25, 118, 210, 0.2);
            }
            .chart-card {
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .chart-card:hover {
                transform: translateY(-5px) scale(1.02);
                box-shadow: 0 12px 30px rgba(0,0,0,0.15);
            }
            .chart-card-no-padding {
                background: white;
                padding: 0;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                display: flex;
                flex-direction: column;
            }
            .analytics-kpi-row {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 25px;
            }
            .analytics-kpi-card {
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
            }
            .analytics-content-row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                height: 650px;
            }
            .analytics-chart-card {
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .modal-hidden {
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
            }
            .modal-visible {
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
            }
            .modal-content {
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
            }
            .modal-content-visible {
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
            }
            .employee-link {
                color: #1976d2;
                text-decoration: none;
                cursor: pointer;
                font-weight: bold;
                transition: all 0.3s ease;
                padding: 2px 6px;
                border-radius: 4px;
            }
            .employee-link:hover {
                color: #0d47a1;
                text-decoration: underline;
                background-color: rgba(25, 118, 210, 0.1);
                box-shadow: 0 2px 8px rgba(25, 118, 210, 0.2);
            }
            .good-performance { color: #4CAF50 !important; font-weight: bold; }
            .medium-performance { color: #FF9800 !important; font-weight: bold; }
            .poor-performance { color: #F44336 !important; font-weight: bold; }
            /* Стиль для кнопки "Лучшие сотрудники" при наведении */
            #open-best-employees-modal:hover {
                background: #1976d2 !important;
                color: white !important;
                transform: translateY(-1px) !important;
                box-shadow: 0 4px 8px rgba(25, 118, 210, 0.2) !important;
            }
            #open-best-employees-modal:active {
                transform: translateY(0) !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
        
        <!-- ✅ КЛИЕНТСКИЙ ТАЙМЕР ПРОСТОЯ (СТАБИЛЬНАЯ ВЕРСИЯ) -->
        <script>
        (function() {
            setInterval(() => {
                const now = Date.now();
                document.querySelectorAll('.idle-timer').forEach(cell => {
                    if (cell.getAttribute('data-on-shift') !== 'true') {
                        cell.textContent = '0 мин 00 сек';
                        return;
                    }
                    const renderTime = parseInt(cell.getAttribute('data-render-time')) || now;
                    const base = parseInt(cell.getAttribute('data-start-sec')) || 0;
                    const elapsed = Math.max(0, Math.floor((now - renderTime) / 1000));
                    const total = base + elapsed;
                    const m = Math.floor(total / 60);
                    const s = total % 60;
                    cell.textContent = `${m} мин ${s.toString().padStart(2, '0')} сек`;
                });
            }, 1000);
        })();
        </script>
    </body>
</html>
'''


# ============================================================================
# ГЛОБАЛЬНАЯ ОБРАБОТКА ОШИБОК (ТОЛЬКО ДЛЯ НЕОЖИДАННЫХ)
# ============================================================================

@app.server.errorhandler(Exception)
def handle_global_exception(e):
    """Перехват необработанных исключений"""
    
    # Игнорируем IndexError - это норма для Dash pattern-matching
    if isinstance(e, IndexError):
        return {"status": "ok"}, 200
    
    # Игнорируем 405 Method Not Allowed
    if hasattr(e, 'code') and e.code == 405:
        return {"error": "Method not allowed"}, 405
    
    # Логируем только реальные ошибки
    logger.error(f"Unhandled exception: {e}")
    logger.error(traceback.format_exc())
    return {"error": "Internal server error"}, 500


def safe_run():
    """Безопасный запуск сервера с автоперезапуском"""
    import time
    import signal
    
    should_restart = True
    
    def signal_handler(sig, frame):
        nonlocal should_restart
        logger.info("Received shutdown signal")
        should_restart = False
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    max_restarts = 10
    restart_count = 0
    restart_delay = 5
    
    while should_restart and restart_count < max_restarts:
        try:
            logger.info(f"Starting Dash server (attempt {restart_count + 1}/{max_restarts})")
            app.run(debug=False, host='0.0.0.0', port=8050, threaded=True)
            break
            
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
            break
            
        except Exception as e:
            restart_count += 1
            logger.error(f"Server crashed: {e}")
            
            if restart_count < max_restarts:
                wait_time = restart_delay * restart_count
                logger.info(f"Restarting in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.critical("Max restart attempts reached. Exiting.")
                sys.exit(1)


# Клиентский колбэк для печати — открывает окно при обновлении URL
app.clientside_callback(
    """
    function(url) {
        if (url && url !== '') {
            window.open(url, '_blank', 'width=1200,height=800');
        }
        return '';
    }
    """,
    Output("print-revision-trigger", "children"),
    Input("print-revision-url-store", "data")
)

if __name__ == '__main__':
    safe_run()