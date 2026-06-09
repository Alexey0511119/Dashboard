import json
import logging
from datetime import datetime, timedelta
from data.mssql_client import execute_query_cached, mssql_client
from functools import lru_cache

logger = logging.getLogger(__name__)

# Глобальные переменные для кэширования данных
PERFORMANCE_DATA_CACHE = []
EMPLOYEE_ANALYTICS_CACHE = {}
EMPLOYEE_OPERATIONS_DETAIL_CACHE = {}
SHIFT_COMPARISON_CACHE = []
PROBLEMATIC_HOURS_CACHE = []
ERROR_HOURS_CACHE = []

# Получение списка сотрудников из БД
def get_employees():
    query = """
    SELECT DISTINCT fio 
    FROM dm.v_employee_analytics 
    WHERE fio IS NOT NULL AND fio != ''
    ORDER BY fio
    """
    result = execute_query_cached(query)
    return [row[0] for row in result] if result else []

# Получение списка типов операций
def get_operation_types():
    query = """
    SELECT DISTINCT 'WMS операции' as WORK_TYPE
    FROM dm.v_employee_analytics 
    WHERE wms_operations > 0
    UNION
    SELECT DISTINCT 'Приемка' as WORK_TYPE
    FROM dm.v_reception_operations
    """
    result = execute_query_cached(query)
    return [row[0] for row in result] if result else []

# Получение списка категорий штрафов
def get_fine_categories():
    query = """
    SELECT DISTINCT fine_category 
    FROM dm.v_penalty_summary 
    WHERE fine_category IS NOT NULL AND fine_category != ''
    ORDER BY fine_category
    """
    result = execute_query_cached(query)
    return [row[0] for row in result] if result else []

# Получение данных для карточки "Собрано заказов вовремя"
def get_orders_timely(start_date, end_date):
    """Получение своевременности заказов из dm.v_order_timeliness_by_delivery"""
    query = """
    SELECT 
        SUM(CASE WHEN timeliness_status = 'Вовремя' THEN count ELSE 0 END) as timely_count,
        SUM(CASE WHEN timeliness_status = 'Просрочено' THEN count ELSE 0 END) as delayed_count,
        SUM(count) as total_count,
        CAST(SUM(CASE WHEN timeliness_status = 'Вовремя' THEN count ELSE 0 END) * 100.0 / 
             NULLIF(SUM(count), 0) as decimal(10,1)) as percentage
    FROM dm.v_order_timeliness_by_delivery 
    WHERE date_key BETWEEN ? AND ?
    """
    result = execute_query_cached(query, (start_date, end_date))
    
    if result and result[0]:
        timely = int(result[0][0]) if result[0][0] else 0
        delayed = int(result[0][1]) if result[0][1] else 0
        total = int(result[0][2]) if result[0][2] else 0
        percentage = float(result[0][3]) if result[0][3] else 0
        
        return timely, delayed, total, round(percentage, 1)
    else:
        return 0, 0, 0, 0

# Получение данных для карточки "Среднее время операции"
def get_orders_timeliness_by_delivery(start_date, end_date):
    """Получение своевременности заказов по типам доставки для диаграмм"""
    query = """
    SELECT 
        date_key,
        delivery_type,
        SUM(CASE WHEN timeliness_status = 'Вовремя' THEN count ELSE 0 END) as timely_count,
        SUM(CASE WHEN timeliness_status = 'Просрочено' THEN count ELSE 0 END) as delayed_count,
        SUM(count) as total_count
    FROM dm.v_order_timeliness_by_delivery 
    WHERE date_key BETWEEN ? AND ?
    GROUP BY date_key, delivery_type
    ORDER BY date_key, delivery_type
    """
    result = execute_query_cached(query, (start_date, end_date))
    
    chart_data = []
    if result:
        for row in result:
            try:
                date_key = row[0] if row[0] else ''
                delivery_type = row[1] if row[1] else ''
                timely_count = int(row[2]) if row[2] else 0
                delayed_count = int(row[3]) if row[3] else 0
                total_count = int(row[4]) if row[4] else 0
                
                chart_data.append({
                    'date': date_key,
                    'delivery_type': delivery_type,
                    'timely_count': timely_count,
                    'delayed_count': delayed_count,
                    'total_count': total_count
                })
            except Exception as e:
                logger.error("Error processing order timeliness row: %s", e)
                continue
    
    return chart_data

def get_avg_operation_time(start_date, end_date):
    """Получение среднего времени операции"""
    query = """
    SELECT 
        CASE 
            WHEN COUNT(*) > 0 THEN AVG(CAST(total_minutes as float)) / COUNT(*)
            ELSE 0 
        END as avg_time_minutes
    FROM dm.v_earnings_daily 
    WHERE date_key BETWEEN ? AND ?
        AND total_operations > 0
        AND total_minutes > 0
    """
    result = execute_query_cached(query, (start_date, end_date))
    return float(result[0][0]) if result and result[0][0] else 0.0

# Получение данных для карточки "Общий заработок"
def get_total_earnings(start_date, end_date):
    query = """
    SELECT 
        COALESCE(SUM(total_earnings), 0) as total_earnings
    FROM dm.v_earnings_daily 
    WHERE date_key BETWEEN ? AND ?
    """
    
    result = execute_query_cached(query, (start_date, end_date))
    
    if result and result[0]:
        return float(result[0][0]) if result[0][0] else 0.0
    else:
        return 0.0

def get_storage_cells_stats():
    """Получение статистики по ячейкам хранения используя v_storage_current_status
    БЕЗ КЭШИРОВАНИЯ - для реального времени
    """
    # Агрегируем данные из v_storage_current_status
    query = """
    SELECT
        SUM(total_cells) as total_cells,
        SUM(occupied_cells) as occupied_cells,
        SUM(free_cells) as free_cells,
        AVG(occupancy_pct) as avg_occupancy
    FROM dm.v_storage_current_status
    """

    # Используем прямой запрос без кэша
    result = mssql_client.execute(query)

    if result and result[0]:
        total_cells = int(result[0][0]) if result[0][0] else 0
        occupied_cells = int(result[0][1]) if result[0][1] else 0
        free_cells = int(result[0][2]) if result[0][2] else 0
        avg_occupancy = float(result[0][3]) if result[0][3] else 0.0

        # Рассчитываем проценты
        occupied_percent = 0
        free_percent = 0
        if total_cells > 0:
            occupied_percent = round((occupied_cells / total_cells) * 100, 1)
            free_percent = round((free_cells / total_cells) * 100, 1)

        return {
            'total_cells': total_cells,
            'occupied_cells': occupied_cells,
            'free_cells': free_cells,
            'occupied_percent': occupied_percent,
            'free_percent': free_percent
        }
    else:
        return {
            'total_cells': 0,
            'occupied_cells': 0,
            'free_cells': 0,
            'occupied_percent': 0,
            'free_percent': 0
        }

# Получение данных для карточки "Точность заказов"
def get_order_accuracy(start_date, end_date):
    """Получение данных по точности заказов из dm.v_order_accuracy_daily"""
    try:
        # Основной запрос для получения статистики по точности заказов
        query = """
        SELECT 
            SUM(total_assembled) as total_orders,
            SUM(correct_count) as correct_orders,
            SUM(error_count) as error_orders,
            AVG(accuracy_pct) as avg_accuracy
        FROM dm.v_order_accuracy_daily
        WHERE date BETWEEN ? AND ?
        """
        
        result = execute_query_cached(query, (start_date, end_date))
        
        if result and len(result) > 0:
            row = result[0]
            
            # Обрабатываем данные с проверкой на None
            total_orders = row[0] if row[0] is not None else 0
            correct_orders = row[1] if row[1] is not None else 0
            error_orders = row[2] if row[2] is not None else 0
            avg_accuracy = float(row[3]) if row[3] is not None else 0.0
            
            # Рассчитываем фактический процент точности
            accuracy = (correct_orders / total_orders * 100) if total_orders > 0 else 100.0
            
            return accuracy, correct_orders, total_orders, error_orders
        else:
            # Если нет данных за указанный период, возвращаем значения по умолчанию
            return 100.0, 0, 0, 0
            
    except Exception as e:
        logger.error("Ошибка в get_order_accuracy: %s", e)
        
        # Возвращаем значения по умолчанию в случае ошибки
        return 100.0, 0, 0, 0

# Получение данных по отклоненным строкам для карточки
def get_rejected_lines_summary(start_date=None, end_date=None):
    """Получение данных по отклоненным строкам для карточки из dm.v_rejected_lines_summary
    БЕЗ КЭШИРОВАНИЯ - для реального времени
    start_date и end_date не используются (VIEW содержит все данные)
    """
    try:
        # Основной запрос для получения статистики по отклоненным строкам
        # VIEW содержит все данные - фильтра по датам нет
        query = """
        SELECT
            total_rejected_lines,
            unique_orders,
            unique_items,
            last_rejection_date
        FROM dm.v_rejected_lines_summary
        """

        # Используем прямой запрос без кэша
        result = mssql_client.execute(query)

        if result and len(result) > 0:
            row = result[0]

            # Обрабатываем данные с проверкой на None
            total_rejected_lines = row[0] if row[0] is not None else 0
            unique_orders = row[1] if row[1] is not None else 0
            unique_items = row[2] if row[2] is not None else 0
            last_rejection_date = row[3] if row[3] is not None else None

            return {
                'total_rejected_lines': total_rejected_lines,
                'unique_orders': unique_orders,
                'unique_items': unique_items,
                'last_rejection_date': last_rejection_date
            }
        else:
            # Если нет данных, возвращаем пустые значения
            return {
                'total_rejected_lines': 0,
                'unique_orders': 0,
                'unique_items': 0,
                'last_rejection_date': None
            }

    except Exception as e:
        logger.error("Ошибка в get_rejected_lines_summary: %s", e)

        # Возвращаем значения по умолчанию в случае ошибки
        return {
            'total_rejected_lines': 0,
            'unique_orders': 0,
            'unique_items': 0,
            'last_rejection_date': None
        }

# Получение детальных данных по отклоненным строкам для модального окна
def get_rejected_lines_detail(start_date=None, end_date=None, limit=100):
    """Получение детальных данных по отклоненным строкам для модального окна из dm.v_rejected_lines_detail"""
    try:
        query = """
        SELECT TOP {limit}
        SHIPMENT_ID,
        ORDER_TYPE,
        ITEM,
        ITEM_DESC,
        REQUESTED_QTY,
        QUANTITY_UM,
        PICK_LOC,
        PICK_ZONE,
        DATE_TIME_STAMP,
        REJECTION_NOTE,
        STATUS  -- <-- ДОБАВЛЕНО ПОЛЕ STATUS
        FROM dm.v_rejected_lines_detail
        ORDER BY
        CASE WHEN ORDER_TYPE = N'Клиент' THEN 0 ELSE 1 END,
        SHIPMENT_ID,
        ITEM_DESC
        """.format(limit=limit)
        
        result = mssql_client.execute(query)
        detail_data = []
        if result:
            for row in result:
                detail_data.append({
                    'shipment_id': row[0] if row[0] is not None else '',
                    'order_type': row[1] if row[1] is not None else '',
                    'item': row[2] if row[2] is not None else '',
                    'item_desc': row[3] if row[3] is not None else '',
                    'requested_qty': row[4] if row[4] is not None else 0,
                    'quantity_um': row[5] if row[5] is not None else '',
                    'pick_loc': row[6] if row[6] is not None else '',
                    'pick_zone': row[7] if row[7] is not None else '',
                    'date_time_stamp': row[8] if row[8] is not None else None,
                    'rejection_note': row[9] if row[9] is not None else '',
                    'status': row[10] if row[10] is not None else ''  # <-- ДОБАВЛЕНО В СЛОВАРЬ
                })
        return detail_data
    except Exception as e:
        logger.error("Ошибка в get_rejected_lines_detail: %s", e)
        return []

# Получение данных списка приходов
def get_receipt_list_data():
    """Получение данных списка приходов из dwh.receipt_list (БЕЗ КЭШИРОВАНИЯ)"""
    query = """
    SELECT
        RECEIPT_ID as receipt_id,
        ERP_ORDER_NUM as erp_order_num,
        SOURCE_NAME as source_name,
        RECEIPT_TYPE as receipt_type,
        CREATION_DATE_TIME_STAMP as creation_date,
        TOTAL_LINES as total_lines,
        STATUS as status,
        EXECUTION_TIME as execution_time,
        OVERDUE_IN as overdue_in
    FROM dwh.receipt_list
    ORDER BY creation_date DESC
    """

    # ПРЯМОЙ ЗАПРОС БЕЗ КЭША - всегда актуальные данные
    result = mssql_client.execute(query)

    receipt_list = []
    if result:
        for row in result:
            receipt_list.append({
                'receipt_id': row[0] if row[0] else '',
                'erp_order_num': row[1] if row[1] else '',
                'source_name': row[2] if row[2] else '',
                'receipt_type': row[3] if row[3] else '',
                'creation_date': row[4] if row[4] else '',
                'total_lines': row[5] if row[5] else 0,
                'status': row[6] if row[6] else '',
                'execution_time': row[7] if row[7] else '',
                'overdue_in': row[8] if row[8] else ''
            })

    return receipt_list

# Получение средней производительности сотрудников
def get_avg_productivity(start_date, end_date):
    query = """
    SELECT 
        AVG(CAST(total_operations as float)) as avg_ops,
        COUNT(DISTINCT fio) as active_employees
    FROM dm.v_employee_analytics 
    WHERE total_operations > 0
    """
    
    result = execute_query_cached(query)
    
    if result and result[0]:
        avg_ops = round(float(result[0][0]), 1) if result[0][0] else 0
        active_emp = int(result[0][1]) if result[0][1] else 0
        return avg_ops, active_emp
    else:
        return 0, 0

# Получение данных для таблицы производительности сотрудников
def get_performance_data(start_date, end_date):
    """
    Получение данных производительности сотрудников из dwh.sdelka_daily.
    Должность берется из проверенного источника (dm.v_employees_shift_daily) 
    через get_employee_positions_map(), чтобы гарантировать соответствие вкладке "Сотрудники на смене".
    """
    query = """
    SELECT
        [User name],
        MAX([Описание]) AS fio,
        
        -- 1. Сумма всех операций за период
        SUM(
            ISNULL([Отбор ME],0) + ISNULL([Отбор ZX 20-30 Компл],0) + ISNULL([Отбор ZX 10-20],0) + 
            ISNULL([Отбор ZX 30-50],0) + ISNULL([Отбор ZX 30-50 компл],0) + ISNULL([Отбор ZX КПП],0) + 
            ISNULL([Отбор БРАК/БОЙ],0) + ISNULL([Отбор негабарит],0) + ISNULL([Отбор транзит],0) + 
            ISNULL([Отбор WH2 ZX 10-20],0) + ISNULL([Отбор WH2 ZX 30-50],0) + ISNULL([Отбор WH2 ME],0) + 
            ISNULL([Отбор WH2 ZX негабарит],0) + ISNULL([Перемещение на КС],0) + ISNULL([Перемещение по КС],0) + 
            ISNULL([Пополнение KSP],0) + ISNULL([Пополнение KSPPROGREV],0) + ISNULL([Пополнение ZX],0) + 
            ISNULL([Прием],0) + ISNULL([Прием WH2],0) + ISNULL([Размещение КС],0) + ISNULL([Размещение ME],0) + 
            ISNULL([Размещение NG],0) + ISNULL([Размещение ZX 10-15],0) + ISNULL([Размещение ZX 20-50],0) + 
            ISNULL([Размещение ZX КПП],0) + ISNULL([Размещение брака/боя],0) + ISNULL([Размещение транзит],0) + 
            ISNULL([Размещение WH2],0) + ISNULL([Ревизия КС],0) + ISNULL([Ревизия ME],0) + ISNULL([Ревизия NG],0) + 
            ISNULL([Ревизия ZX 10-20],0) + ISNULL([Ревизия ZX 20],0) + ISNULL([Ревизия ZX 30-50],0) + 
            ISNULL([Ревизия ZX КПП],0) + ISNULL([Ревизия по событию],0) + ISNULL([Ревизия NG WH2],0) + 
            ISNULL([Ревизия ZX 10-20 WH2],0) + ISNULL([Ревизия ZX 30-50 WH2],0) + ISNULL([Перемещение],0) + 
            ISNULL([Трансферт],0) + ISNULL([Загрузка механизмами],0) + ISNULL([Разгрузка механизмами],0) + 
            ISNULL([Позиции контролер филиал],0) + ISNULL([Позиции контролер клиент],0) + 
            ISNULL([Загрузка ручная],0) + ISNULL([Разгрузка ручная],0) + ISNULL([Сортировка товаров приемка],0) + 
            ISNULL([Сортировка товаров отгрузка],0) + ISNULL([Перемер с прихода],0) + ISNULL([Перемер ZX KPP],0) + 
            ISNULL([Отбор KSP ААБЛ],0) + ISNULL([Отбор KSP не ААБЛ],0) + ISNULL([Отбор KP],0) + 
            ISNULL([Перемещение PME],0)
        ) AS total_operations,
        
        -- 2. Заработок
        SUM(ISNULL([Цена],0)) AS total_earnings,
        
        -- 3. Суммарное рабочее время (окно присутствия) в минутах за период
        SUM(ISNULL(work_minutes, 0)) AS total_work_minutes,
        
        -- 4. Дополнительные метрики
        SUM(ISNULL([Контейнеров отгружено], 0)) AS total_containers,
        CASE 
            WHEN SUM(ISNULL([Контейнеров отгружено], 0)) > 0 
            THEN (SUM(ISNULL([Загрузка механизмами],0)) + SUM(ISNULL([Разгрузка механизмами],0)) + SUM(ISNULL([Загрузка ручная],0)) + SUM(ISNULL([Разгрузка ручная],0))) / SUM(ISNULL([Контейнеров отгружено], 0))
            ELSE 0 
        END AS avg_volume_per_container,
        SUM(ISNULL([Загрузка механизмами],0)) + SUM(ISNULL([Разгрузка механизмами],0)) + 
        SUM(ISNULL([Загрузка ручная],0)) + SUM(ISNULL([Разгрузка ручная],0)) AS total_volume

    FROM dwh.sdelka_daily
    WHERE calc_date BETWEEN ? AND ?
    GROUP BY [User name]
    HAVING (
        SUM(
            ISNULL([Отбор ME],0) + ISNULL([Отбор ZX 20-30 Компл],0) + ISNULL([Отбор ZX 10-20],0) + 
            ISNULL([Отбор ZX 30-50],0) + ISNULL([Отбор ZX 30-50 компл],0) + ISNULL([Отбор ZX КПП],0) + 
            ISNULL([Отбор БРАК/БОЙ],0) + ISNULL([Отбор негабарит],0) + ISNULL([Отбор транзит],0) + 
            ISNULL([Отбор WH2 ZX 10-20],0) + ISNULL([Отбор WH2 ZX 30-50],0) + ISNULL([Отбор WH2 ME],0) + 
            ISNULL([Отбор WH2 ZX негабарит],0) + ISNULL([Перемещение на КС],0) + ISNULL([Перемещение по КС],0) + 
            ISNULL([Пополнение KSP],0) + ISNULL([Пополнение KSPPROGREV],0) + ISNULL([Пополнение ZX],0) + 
            ISNULL([Прием],0) + ISNULL([Прием WH2],0) + ISNULL([Размещение КС],0) + ISNULL([Размещение ME],0) + 
            ISNULL([Размещение NG],0) + ISNULL([Размещение ZX 10-15],0) + ISNULL([Размещение ZX 20-50],0) + 
            ISNULL([Размещение ZX КПП],0) + ISNULL([Размещение брака/боя],0) + ISNULL([Размещение транзит],0) + 
            ISNULL([Размещение WH2],0) + ISNULL([Ревизия КС],0) + ISNULL([Ревизия ME],0) + ISNULL([Ревизия NG],0) + 
            ISNULL([Ревизия ZX 10-20],0) + ISNULL([Ревизия ZX 20],0) + ISNULL([Ревизия ZX 30-50],0) + 
            ISNULL([Ревизия ZX КПП],0) + ISNULL([Ревизия по событию],0) + ISNULL([Ревизия NG WH2],0) + 
            ISNULL([Ревизия ZX 10-20 WH2],0) + ISNULL([Ревизия ZX 30-50 WH2],0) + ISNULL([Перемещение],0) + 
            ISNULL([Трансферт],0) + ISNULL([Загрузка механизмами],0) + ISNULL([Разгрузка механизмами],0) + 
            ISNULL([Позиции контролер филиал],0) + ISNULL([Позиции контролер клиент],0) + 
            ISNULL([Загрузка ручная],0) + ISNULL([Разгрузка ручная],0) + ISNULL([Сортировка товаров приемка],0) + 
            ISNULL([Сортировка товаров отгрузка],0) + ISNULL([Перемер с прихода],0) + ISNULL([Перемер ZX KPP],0) + 
            ISNULL([Отбор KSP ААБЛ],0) + ISNULL([Отбор KSP не ААБЛ],0) + ISNULL([Отбор KP],0) + 
            ISNULL([Перемещение PME],0)
        ) > 0
    )
    ORDER BY total_earnings DESC
    """
    
    result = execute_query_cached(query, (start_date, end_date))
    
    # ✅ ПОЛУЧАЕМ АКТУАЛЬНЫЙ МАППИНГ ФИО -> ДОЛЖНОСТЬ из dm.v_employees_shift_daily
    # Эта функция уже есть в твоем коде и использует lru_cache, поэтому работает мгновенно
    pos_map = get_employee_positions_map()
    
    performance_data = []
    if result:
        for row in result:
            try:
                user_name = row[0] if row[0] else ''
                fio_raw = row[1] if row[1] else ''
                fio = fio_raw if fio_raw else user_name
                
                # ✅ НОВАЯ ЛОГИКА: Берем должность из проверенного справочника по ФИО
                fio_key = str(fio).strip().upper()
                position_raw = pos_map.get(fio_key, '')
                
                # Приводим к красивому виду (Первая буква заглавная, остальные строчные)
                position = position_raw.strip().title() if position_raw.strip() else 'Не указана'
                
                total_ops = int(row[2]) if row[2] is not None else 0
                earnings = float(row[3]) if row[3] is not None else 0.0
                
                # КЛЮЧЕВОЙ МОМЕНТ: берем суммарное рабочее время из БД
                total_work_min = float(row[4]) if row[4] is not None else 0.0
                
                total_containers = int(row[5]) if row[5] is not None else 0
                avg_volume = float(row[6]) if row[6] is not None else 0.0
                total_volume = float(row[7]) if row[7] is not None else 0.0
                
                # Расчет метрик на основе реального суммарного рабочего времени за период
                total_work_hours = total_work_min / 60.0 if total_work_min > 0 else 0.0
                
                # Операций в час = Всего операций / Часы работы
                ops_per_hour = total_ops / total_work_hours if total_work_hours > 0 else 0.0
                
                # Среднее время на операцию (в минутах) = Минуты работы / Всего операций
                avg_time_per_op = total_work_min / total_ops if total_ops > 0 else 0.0
                
                # Форматирование времени работы в строку "Xч Yм"
                work_hours_int = int(total_work_min // 60)
                work_minutes_int = int(total_work_min % 60)
                work_time_formatted = f"{work_hours_int}ч {work_minutes_int}м"
                
                performance_data.append({
                    'Сотрудник': fio,
                    'user_name': user_name,
                    'position': position, # <-- Теперь здесь гарантированно верная должность
                    'Общее_кол_операций': total_ops,
                    'Ср_время_на_операцию': round(avg_time_per_op, 1),
                    'Заработок': round(earnings, 2),
                    'Операций_в_час': round(ops_per_hour, 1),
                    'Время_работы': work_time_formatted,
                    'Объем': round(total_volume, 2),
                    'Контейнеров': total_containers,
                    'Ср_объем_контейнера': round(avg_volume, 2)
                })
            except Exception as e:
                logger.error("Error processing performance row: %s", e)
                continue
    
    return performance_data

def get_employee_modal_detail(employee_name, start_date, end_date):
    """Получение детальных данных для модального окна сотрудника из dwh.sdelka_daily"""
    query = """
    SELECT
        calc_date,
        [User name],
        -- Сумма всех операций
        ISNULL([Отбор ME],0) + ISNULL([Отбор ZX 20-30 Компл],0) + ISNULL([Отбор ZX 10-20],0) +
        ISNULL([Отбор ZX 30-50],0) + ISNULL([Отбор ZX 30-50 компл],0) + ISNULL([Отбор ZX КПП],0) +
        ISNULL([Отбор БРАК/БОЙ],0) + ISNULL([Отбор негабарит],0) + ISNULL([Отбор транзит],0) +
        ISNULL([Отбор WH2 ZX 10-20],0) + ISNULL([Отбор WH2 ZX 30-50],0) + ISNULL([Отбор WH2 ME],0) +
        ISNULL([Отбор WH2 ZX негабарит],0) + ISNULL([Перемещение на КС],0) + ISNULL([Перемещение по КС],0) +
        ISNULL([Пополнение KSP],0) + ISNULL([Пополнение KSPPROGREV],0) + ISNULL([Пополнение ZX],0) +
        ISNULL([Прием],0) + ISNULL([Прием WH2],0) + ISNULL([Размещение КС],0) + ISNULL([Размещение ME],0) +
        ISNULL([Размещение NG],0) + ISNULL([Размещение ZX 10-15],0) + ISNULL([Размещение ZX 20-50],0) +
        ISNULL([Размещение ZX КПП],0) + ISNULL([Размещение брака/боя],0) + ISNULL([Размещение транзит],0) +
        ISNULL([Размещение WH2],0) + ISNULL([Ревизия КС],0) + ISNULL([Ревизия ME],0) + ISNULL([Ревизия NG],0) +
        ISNULL([Ревизия ZX 10-20],0) + ISNULL([Ревизия ZX 20],0) + ISNULL([Ревизия ZX 30-50],0) +
        ISNULL([Ревизия ZX КПП],0) + ISNULL([Ревизия по событию],0) + ISNULL([Ревизия NG WH2],0) +
        ISNULL([Ревизия ZX 10-20 WH2],0) + ISNULL([Ревизия ZX 30-50 WH2],0) + ISNULL([Перемещение],0) +
        ISNULL([Трансферт],0) + ISNULL([Загрузка механизмами],0) + ISNULL([Разгрузка механизмами],0) +
        ISNULL([Позиции контролер филиал],0) + ISNULL([Позиции контролер клиент],0) +
        ISNULL([Загрузка ручная],0) + ISNULL([Разгрузка ручная],0) + ISNULL([Сортировка товаров приемка],0) +
        ISNULL([Сортировка товаров отгрузка],0) + ISNULL([Перемер с прихода],0) + ISNULL([Перемер ZX KPP],0) +
        ISNULL([Отбор KSP ААБЛ],0) + ISNULL([Отбор KSP не ААБЛ],0) + ISNULL([Отбор KP],0) +
        ISNULL([Перемещение PME],0) AS total_operations,
        -- Заработок
        ISNULL([Цена],0) AS total_earnings,
        -- 🔑 НОВЫЕ МЕТРИКИ: Объем и контейнеры
        ISNULL([Контейнеров отгружено], 0) AS total_containers,
        CASE
            WHEN ISNULL([Контейнеров отгружено], 0) > 0
            THEN (ISNULL([Загрузка механизмами],0) + ISNULL([Разгрузка механизмами],0) + ISNULL([Загрузка ручная],0) + ISNULL([Разгрузка ручная],0)) / ISNULL([Контейнеров отгружено], 0)
            ELSE 0
        END AS avg_volume_per_container,
        ISNULL([Загрузка механизмами],0) + ISNULL([Разгрузка механизмами],0) +
        ISNULL([Загрузка ручная],0) + ISNULL([Разгрузка ручная],0) AS total_volume,
        -- Штрафы
        ISNULL([Штрафы],0) AS fines_amount,
        -- Приемка
        ISNULL([Прием],0) + ISNULL([Прием WH2],0) AS reception_count,
        -- Все операции для JSON (начинаются с индекса 9)
        [Отбор ME], [Отбор ZX 20-30 Компл], [Отбор ZX 10-20], [Отбор ZX 30-50], [Отбор ZX 30-50 компл],
        [Отбор ZX КПП], [Отбор БРАК/БОЙ], [Отбор негабарит], [Отбор транзит],
        [Отбор WH2 ZX 10-20], [Отбор WH2 ZX 30-50], [Отбор WH2 ME], [Отбор WH2 ZX негабарит],
        [Перемещение на КС], [Перемещение по КС], [Пополнение KSP], [Пополнение KSPPROGREV], [Пополнение ZX],
        [Прием], [Прием WH2], [Размещение КС], [Размещение ME], [Размещение NG],
        [Размещение ZX 10-15], [Размещение ZX 20-50], [Размещение ZX КПП], [Размещение брака/боя],
        [Размещение транзит], [Размещение WH2], [Ревизия КС], [Ревизия ME], [Ревизия NG],
        [Ревизия ZX 10-20], [Ревизия ZX 20], [Ревизия ZX 30-50], [Ревизия ZX КПП], [Ревизия по событию],
        [Ревизия NG WH2], [Ревизия ZX 10-20 WH2], [Ревизия ZX 30-50 WH2], [Перемещение], [Трансферт],
        [Загрузка механизмами], [Разгрузка механизмами], [Позиции контролер филиал], [Позиции контролер клиент],
        [Загрузка ручная], [Разгрузка ручная], [Сортировка товаров приемка], [Сортировка товаров отгрузка],
        [Перемер с прихода], [Перемер ZX KPP], [Отбор KSP ААБЛ], [Отбор KSP не ААБЛ], [Отбор KP],
        [Перемещение PME]
    FROM dwh.sdelka_daily
    WHERE [User name] = ?
    AND calc_date BETWEEN ? AND ?
    ORDER BY calc_date DESC
    """
    employee_name_upper = str(employee_name).strip().upper()
    result = execute_query_cached(query, (employee_name_upper, start_date, end_date))
    detail_data = []
    if result:
        for row in result:
            try:
                date_key = row[0] if row[0] else ''
                fio = row[1] if row[1] else ''
                total_operations = int(row[2]) if row[2] else 0
                total_earnings = float(row[3]) if row[3] else 0.0
                
                # 🔑 НОВЫЕ МЕТРИКИ
                total_containers = int(row[4]) if row[4] else 0
                avg_volume = float(row[5]) if row[5] else 0.0
                total_volume = float(row[6]) if row[6] else 0.0
                
                fines_amount = float(row[7]) if row[7] else 0.0
                reception_count = int(row[8]) if row[8] else 0
                
                # Формируем JSON из всех операций (колонки с индекса 9)
                operations_dict = {}
                operation_names = [
                    'Отбор ME', 'Отбор ZX 20-30 Компл', 'Отбор ZX 10-20', 'Отбор ZX 30-50', 'Отбор ZX 30-50 компл',
                    'Отбор ZX КПП', 'Отбор БРАК/БОЙ', 'Отбор негабарит', 'Отбор транзит',
                    'Отбор WH2 ZX 10-20', 'Отбор WH2 ZX 30-50', 'Отбор WH2 ME', 'Отбор WH2 ZX негабарит',
                    'Перемещение на КС', 'Перемещение по КС', 'Пополнение KSP', 'Пополнение KSPPROGREV', 'Пополнение ZX',
                    'Прием', 'Прием WH2', 'Размещение КС', 'Размещение ME', 'Размещение NG',
                    'Размещение ZX 10-15', 'Размещение ZX 20-50', 'Размещение ZX КПП', 'Размещение брака/боя',
                    'Размещение транзит', 'Размещение WH2', 'Ревизия КС', 'Ревизия ME', 'Ревизия NG',
                    'Ревизия ZX 10-20', 'Ревизия ZX 20', 'Ревизия ZX 30-50', 'Ревизия ZX КПП', 'Ревизия по событию',
                    'Ревизия NG WH2', 'Ревизия ZX 10-20 WH2', 'Ревизия ZX 30-50 WH2', 'Перемещение', 'Трансферт',
                    'Загрузка механизмами', 'Разгрузка механизмами', 'Позиции контролер филиал', 'Позиции контролер клиент',
                    'Загрузка ручная', 'Разгрузка ручная', 'Сортировка товаров приемка', 'Сортировка товаров отгрузка',
                    'Перемер с прихода', 'Перемер ZX KPP', 'Отбор KSP ААБЛ', 'Отбор KSP не ААБЛ', 'Отбор KP',
                    'Перемещение PME'
                ]
                for i, op_name in enumerate(operation_names):
                    op_value = int(row[9 + i]) if row[9 + i] else 0
                    if op_value > 0:
                        operations_dict[op_name] = op_value
                operations_by_type = json.dumps(operations_dict, ensure_ascii=False) if operations_dict else ''
                
                detail_data.append({
                    'fio': fio,
                    'smena': '',
                    'date_key': str(date_key)[:10] if date_key else '',
                    'total_operations': total_operations,
                    'total_earnings': round(total_earnings, 2),
                    'total_idle_minutes': 0,
                    'orders_completed': 0,
                    'timely_percentage': 0.0,
                    'fines_count': 0,
                    'fines_amount': round(fines_amount, 2),
                    'operations_by_type': operations_by_type,
                    'reception_count': reception_count,
                    # 🔑 ДОБАВЛЕНО В СЛОВАРЬ
                    'total_containers': total_containers,
                    'avg_volume_per_container': avg_volume,
                    'total_volume': total_volume
                })
            except Exception as e:
                logger.error("Error processing employee detail row: %s", e)
                continue
    return detail_data

def get_employee_operations_by_type(employee_name, start_date, end_date):
    """Получение данных о типах операций сотрудника для диаграммы из dwh.sdelka_daily"""
    query = """
    SELECT
        [Отбор ME], [Отбор ZX 20-30 Компл], [Отбор ZX 10-20], [Отбор ZX 30-50], [Отбор ZX 30-50 компл],
        [Отбор ZX КПП], [Отбор БРАК/БОЙ], [Отбор негабарит], [Отбор транзит],
        [Отбор WH2 ZX 10-20], [Отбор WH2 ZX 30-50], [Отбор WH2 ME], [Отбор WH2 ZX негабарит],
        [Перемещение на КС], [Перемещение по КС], [Пополнение KSP], [Пополнение KSPPROGREV], [Пополнение ZX],
        [Прием], [Прием WH2], [Размещение КС], [Размещение ME], [Размещение NG],
        [Размещение ZX 10-15], [Размещение ZX 20-50], [Размещение ZX КПП], [Размещение брака/боя],
        [Размещение транзит], [Размещение WH2], [Ревизия КС], [Ревизия ME], [Ревизия NG],
        [Ревизия ZX 10-20], [Ревизия ZX 20], [Ревизия ZX 30-50], [Ревизия ZX КПП], [Ревизия по событию],
        [Ревизия NG WH2], [Ревизия ZX 10-20 WH2], [Ревизия ZX 30-50 WH2], [Перемещение], [Трансферт],
        [Загрузка механизмами], [Разгрузка механизмами], [Позиции контролер филиал], [Позиции контролер клиент],
        [Загрузка ручная], [Разгрузка ручная], [Сортировка товаров приемка], [Сортировка товаров отгрузка],
        [Перемер с прихода], [Перемер ZX KPP], [Отбор KSP ААБЛ], [Отбор KSP не ААБЛ], [Отбор KP],
        [Перемещение PME]
    FROM dwh.sdelka_daily
    WHERE [User name] = ?
    AND calc_date BETWEEN ? AND ?
    """
    # Приводим имя к верхнему регистру
    employee_name_upper = str(employee_name).strip().upper()
    result = execute_query_cached(query, (employee_name_upper, start_date, end_date))
    
    # Суммируем все операции за период
    operations_sum = {}
    operation_names = [
        'Отбор ME', 'Отбор ZX 20-30 Компл', 'Отбор ZX 10-20', 'Отбор ZX 30-50', 'Отбор ZX 30-50 компл',
        'Отбор ZX КПП', 'Отбор БРАК/БОЙ', 'Отбор негабарит', 'Отбор транзит',
        'Отбор WH2 ZX 10-20', 'Отбор WH2 ZX 30-50', 'Отбор WH2 ME', 'Отбор WH2 ZX негабарит',
        'Перемещение на КС', 'Перемещение по КС', 'Пополнение KSP', 'Пополнение KSPPROGREV', 'Пополнение ZX',
        'Прием', 'Прием WH2', 'Размещение КС', 'Размещение ME', 'Размещение NG',
        'Размещение ZX 10-15', 'Размещение ZX 20-50', 'Размещение ZX КПП', 'Размещение брака/боя',
        'Размещение транзит', 'Размещение WH2', 'Ревизия КС', 'Ревизия ME', 'Ревизия NG',
        'Ревизия ZX 10-20', 'Ревизия ZX 20', 'Ревизия ZX 30-50', 'Ревизия ZX КПП', 'Ревизия по событию',
        'Ревизия NG WH2', 'Ревизия ZX 10-20 WH2', 'Ревизия ZX 30-50 WH2', 'Перемещение', 'Трансферт',
        'Загрузка механизмами', 'Разгрузка механизмами', 'Позиции контролер филиал', 'Позиции контролер клиент',
        'Загрузка ручная', 'Разгрузка ручная', 'Сортировка товаров приемка', 'Сортировка товаров отгрузка',
        'Перемер с прихода', 'Перемер ZX KPP', 'Отбор KSP ААБЛ', 'Отбор KSP не ААБЛ', 'Отбор KP',
        'Перемещение PME'
    ]
    
    if result:
        for row in result:
            for i, op_name in enumerate(operation_names):
                op_value = int(row[i]) if row[i] else 0
                if op_name not in operations_sum:
                    operations_sum[op_name] = 0
                operations_sum[op_name] += op_value
    
    # Формируем список операций, отсортированный по количеству
    operations_data = []
    for op_name, total_ops in operations_sum.items():
        if total_ops > 0:
            operations_data.append({
                'operation_type': op_name,
                'total_operations': total_ops,
                'avg_time': 0.0,  # Не рассчитывается
                'total_earnings': 0.0  # Не рассчитывается
            })
    
    # Сортируем по убыванию количества операций
    operations_data.sort(key=lambda x: x['total_operations'], reverse=True)
    
    return operations_data

def get_employee_idle_intervals(fio, start_date, end_date):
    """Получение данных о простоях сотрудника по интервалам из dm.employee_work_idle_summary"""
    query = """
    SELECT
        idle_10_20,
        idle_20_30,
        idle_30_60,
        idle_60plus,
        total_idle_min,
        total_work_min,
        work_percentage,
        idle_percentage
    FROM dm.employee_work_idle_summary
    WHERE (LOWER(user_name) = LOWER(?) OR LOWER(fio) = LOWER(?))
    AND date_key BETWEEN ? AND ?
    """
    result = execute_query_cached(query, (fio, fio, start_date, end_date))
    
    total_idle_10_20 = 0
    total_idle_20_30 = 0
    total_idle_30_60 = 0
    total_idle_60plus = 0
    total_idle_minutes = 0
    total_work_minutes = 0
    avg_work_percentage = 0
    avg_idle_percentage = 0
    days_count = 0
    
    if result:
        for row in result:
            try:
                total_idle_10_20 += int(row[0]) if row[0] else 0
                total_idle_20_30 += int(row[1]) if row[1] else 0
                total_idle_30_60 += int(row[2]) if row[2] else 0
                total_idle_60plus += int(row[3]) if row[3] else 0
                total_idle_minutes += int(row[4]) if row[4] else 0
                total_work_minutes += int(row[5]) if row[5] else 0
                avg_work_percentage += float(row[6]) if row[6] else 0
                avg_idle_percentage += float(row[7]) if row[7] else 0
                days_count += 1
            except Exception as e:
                logger.error("Error processing idle interval row: %s", e)
                continue
                
    return {
        'idle_10_20': total_idle_10_20,
        'idle_20_30': total_idle_20_30,
        'idle_30_60': total_idle_30_60,
        'idle_60plus': total_idle_60plus,
        'total_idle_minutes': total_idle_minutes,
        'total_work_minutes': total_work_minutes,
        'work_percentage': avg_work_percentage / days_count if days_count > 0 else 0,
        'idle_percentage': avg_idle_percentage / days_count if days_count > 0 else 0,
        'days_count': days_count
    }

# Получение данных о простоях сотрудника
def get_employee_idle_data(employee_name, start_date, end_date):
    query = """
    SELECT
        COUNT(*) as idle_intervals,
        AVG(CAST(total_minutes as float)) as avg_idle_time
    FROM dm.v_employee_idle_time
    WHERE fio = ?
        AND date_key BETWEEN ? AND ?
    """

    result = execute_query_cached(query, (employee_name, start_date, end_date))

    if result and result[0]:
        idle_intervals = int(result[0][0]) if result[0][0] else 0
        avg_idle_time = float(result[0][1]) if result[0][1] else 0.0

        return {
            'total_work_minutes': 480.0,  # Упрощенно 8 часов
            'total_idle_minutes': avg_idle_time * idle_intervals,
            'idle_counts': {
                '5-10 мин': idle_intervals // 3,
                '10-30 мин': idle_intervals // 3,
                '30-60 мин': idle_intervals // 3,
                '>1 часа': idle_intervals % 3
            }
        }
    else:
        return {
            'total_work_minutes': 480.0,
            'total_idle_minutes': 0.0,
            'idle_counts': {
                '5-10 мин': 0,
                '10-30 мин': 0,
                '30-60 мин': 0,
                '>1 часа': 0
            }
        }

def get_employee_work_idle_detail(employee_name, start_date, end_date):
    """Получение детальных данных о времени работы и простоя по дням из dm.employee_work_idle_summary"""
    query = """
    SELECT
        user_name,
        fio,
        date_key,
        first_op_time,
        last_op_time,
        total_period_min,
        total_work_min,
        total_idle_min,
        work_percentage,
        idle_percentage,
        idle_10_20,
        idle_20_30,
        idle_30_60,
        idle_60plus
    FROM dm.employee_work_idle_summary
    WHERE LOWER(user_name) = LOWER(?)
        AND date_key BETWEEN ? AND ?
    ORDER BY date_key DESC
    """

    result = execute_query_cached(query, (employee_name, start_date, end_date))

    detail_data = []
    if result:
        for row in result:
            try:
                user_name = row[0] if row[0] else ''
                fio = row[1] if row[1] else ''
                date_key = row[2] if row[2] else ''
                first_op_time = row[3] if row[3] else ''
                last_op_time = row[4] if row[4] else ''
                total_period_min = int(row[5]) if row[5] else 0
                total_work_min = int(row[6]) if row[6] else 0
                total_idle_min = int(row[7]) if row[7] else 0
                work_percentage = float(row[8]) if row[8] else 0
                idle_percentage = float(row[9]) if row[9] else 0
                idle_10_20 = int(row[10]) if row[10] else 0
                idle_20_30 = int(row[11]) if row[11] else 0
                idle_30_60 = int(row[12]) if row[12] else 0
                idle_60plus = int(row[13]) if row[13] else 0

                detail_data.append({
                    'user_name': user_name,
                    'fio': fio,
                    'date_key': date_key,
                    'first_op_time': first_op_time,
                    'last_op_time': last_op_time,
                    'total_period_min': total_period_min,
                    'total_work_min': total_work_min,
                    'total_idle_min': total_idle_min,
                    'work_percentage': round(work_percentage, 2),
                    'idle_percentage': round(idle_percentage, 2),
                    'idle_10_20': idle_10_20,
                    'idle_20_30': idle_20_30,
                    'idle_30_60': idle_30_60,
                    'idle_60plus': idle_60plus
                })
            except Exception as e:
                logger.error("Error processing employee work idle detail row: %s", e)
                continue

    return detail_data

# Получение данных для топ-5 проблемных часов
def get_problematic_hours(start_date, end_date):
    """Получение данных для топ-5 проблемных часов из dm.v_hourly_delays"""
    # View уже содержит агрегированные данные, фильтрация не нужна
    query = """
    SELECT TOP 5
        hour,
        total_orders,
        delayed_orders,
        pct_delayed
    FROM dm.v_hourly_delays
    ORDER BY pct_delayed DESC
    """

    result = execute_query_cached(query)

    problematic_hours = []
    if result:
        for row in result[:5]:  # Берем только топ-5
            try:
                hour = int(row[0]) if row[0] is not None else 0
                total_orders = int(row[1]) if row[1] is not None else 0
                delayed_orders = int(row[2]) if row[2] is not None else 0
                delay_percentage = float(row[3]) if row[3] is not None else 0.0

                problematic_hours.append({
                    'hour': hour,
                    'total_orders': total_orders,
                    'delayed_orders': delayed_orders,
                    'delay_percentage': delay_percentage
                })
            except Exception as e:
                logger.error("Error processing problematic hours row: %s", e)
                continue

    return problematic_hours

# Получение данных для топ-5 часов с наибольшим процентом ошибок
def get_error_hours_top_data(start_date, end_date):
    """Получение данных для топ-5 часов с наибольшим процентом ошибок из dm.v_hourly_errors"""
    # View уже содержит агрегированные данные, фильтрация не нужна
    query = """
    SELECT TOP 5
        hour,
        total_orders,
        error_orders,
        pct_errors
    FROM dm.v_hourly_errors
    ORDER BY pct_errors DESC
    """

    result = execute_query_cached(query)

    error_hours = []
    if result:
        for row in result[:5]:  # Берем только топ-5
            try:
                hour = int(row[0]) if row[0] is not None else 0
                total_orders_in_hour = int(row[1]) if row[1] is not None else 0
                error_orders_count = int(row[2]) if row[2] is not None else 0
                error_percentage = float(row[3]) if row[3] is not None else 0.0

                error_hours.append({
                    'hour': hour,
                    'total_orders_in_hour': total_orders_in_hour,
                    'error_orders_count': error_orders_count,
                    'error_percentage': error_percentage,
                    'error_types': ''  # В этой таблице нет информации о типах ошибок
                })
            except Exception as e:
                logger.error("Error processing error hours row: %s", e)
                continue

    return error_hours

# Получение данных для сравнения смен
def get_shift_comparison(start_date, end_date):
    query = """
    SELECT 
        fio as employee,
        total_operations,
        total_earnings,
        smena,
        brigada
    FROM dm.v_employee_analytics 
    WHERE total_operations > 0
    ORDER BY total_earnings DESC
    """
    
    result = execute_query_cached(query)
    
    comparison_data = []
    if result:
        for row in result:
            try:
                employee = row[0] if row[0] else ''
                operations_count = int(row[1]) if row[1] else 0
                earnings = float(row[2]) if row[2] else 0.0
                smena = row[3] if row[3] else ''
                brigada = row[4] if row[4] else ''
                
                # Упрощенные расчеты
                work_duration = '8ч 0м'
                ops_per_hour = round(operations_count / 8.0, 1)
                busy_percent = min(100, round((operations_count / 100) * 100, 1))
                timely_percent = 95.0  # Упрощенно
                fines_count = 0
                fines_amount = 0.0
                
                comparison_data.append({
                    'Сотрудник': employee,
                    'Операций в час': ops_per_hour,
                    'Время работы': work_duration,
                    'Занятость (%)': busy_percent,
                    'Вовремя (%)': timely_percent,
                    'Штрафы': fines_count
                })
            except Exception as e:
                logger.error("Error processing comparison row: %s", e)
                continue
    
    return comparison_data

def get_fines_data(start_date, end_date):
    query = """
    SELECT 
        fio,
        COUNT(*) as fines_count,
        SUM(total_fine) as total_fine_amount,
        AVG(total_fine) as avg_fine_amount
    FROM dm.v_penalty_summary 
    WHERE date_key BETWEEN ? AND ?
    GROUP BY fio
    ORDER BY total_fine_amount DESC
    """
    
    result = execute_query_cached(query, (start_date, end_date))
    
    fines_data = []
    summary_data = []
    if result:
        for row in result:
            try:
                employee = row[0] if row[0] else ''
                fines_count = int(row[1]) if row[1] else 0
                total_amount = float(row[2]) if row[2] else 0.0
                avg_amount = float(row[3]) if row[3] else 0.0
                
                fines_data.append({
                    'Сотрудник': employee,
                    'Кол-во штрафов': fines_count,
                    'Сумма штрафов': round(total_amount, 2),
                    'Средний штраф': round(avg_amount, 2)
                })

                summary_data.append({
                    'Сотрудник': employee,
                    'Количество_штрафов': fines_count,
                    'Сумма_штрафов': round(total_amount, 2),
                    'Средний_штраф': round(avg_amount, 2)
                })
            except Exception as e:
                logger.error("Error processing fines row: %s", e)
                continue
    
    # Получаем данные по категориям штрафов
    category_query = """
    SELECT
        fine_category,
        COUNT(*) as fine_count,
        SUM(total_fine) as total_amount
    FROM dm.v_penalty_summary
    WHERE date_key BETWEEN ? AND ?
        AND fine_category IS NOT NULL
        AND fine_category != ''
    GROUP BY fine_category
    ORDER BY total_amount DESC
    """
    
    category_result = execute_query_cached(category_query, (start_date, end_date))
    
    category_data = {}
    if category_result:
        for row in category_result:
            try:
                category = row[0] if row[0] else 'Без категории'
                count = int(row[1]) if row[1] else 0
                total_amount = float(row[2]) if row[2] else 0.0
                
                category_data[category] = {
                    'count': count,
                    'total_amount': total_amount
                }
            except Exception as e:
                logger.error("Error processing category row: %s", e)
                continue

    # Получаем KPI данные
    kpi_data = get_fines_kpi_data(start_date, end_date)

    return {
        'summary_data': summary_data,
        'category_data': category_data,
        'kpi_data': {
            'max_fines_employee': kpi_data['max_count_employee'],
            'max_fines_count': kpi_data['max_count'],
            'max_amount_employee': kpi_data['max_amount_employee'],
            'max_amount': kpi_data['max_amount'],
            'total_fines': kpi_data['total_fines'],
            'avg_fine_amount': kpi_data['avg_amount']
        }
    }

# Получение данных для KPI штрафов
def get_fines_kpi_data(start_date, end_date):
    query = """
    SELECT 
        COUNT(*) as total_fines,
        SUM(total_fine) as total_amount,
        AVG(total_fine) as avg_amount
    FROM dm.v_penalty_summary 
    WHERE date_key BETWEEN ? AND ?
    """
    
    result = execute_query_cached(query, (start_date, end_date))
    
    if result and result[0]:
        total_fines = int(result[0][0]) if result[0][0] else 0
        total_amount = float(result[0][1]) if result[0][1] else 0.0
        avg_amount = float(result[0][2]) if result[0][2] else 0.0
        
        # Находим сотрудника с максимальным количеством штрафов
        max_count_query = """
        SELECT TOP 1 fio, COUNT(*) as count
        FROM dm.v_penalty_summary 
        WHERE date_key BETWEEN ? AND ?
        GROUP BY fio
        ORDER BY count DESC
        """
        max_count_result = execute_query_cached(max_count_query, (start_date, end_date))
        
        max_count_employee = ''
        max_count = 0
        if max_count_result:
            max_count_employee = max_count_result[0][0] if max_count_result[0][0] else ''
            max_count = int(max_count_result[0][1]) if max_count_result[0][1] else 0
        
        # Находим сотрудника с максимальной суммой штрафов
        max_amount_query = """
        SELECT TOP 1 fio, SUM(total_fine) as amount
        FROM dm.v_penalty_summary 
        WHERE date_key BETWEEN ? AND ?
        GROUP BY fio
        ORDER BY amount DESC
        """
        max_amount_result = execute_query_cached(max_amount_query, (start_date, end_date))
        
        max_amount_employee = ''
        max_amount = 0.0
        if max_amount_result:
            max_amount_employee = max_amount_result[0][0] if max_amount_result[0][0] else ''
            max_amount = float(max_amount_result[0][1]) if max_amount_result[0][1] else 0.0
        
        return {
            'total_fines': total_fines,
            'total_amount': round(total_amount, 2),
            'avg_amount': round(avg_amount, 2),
            'max_count_employee': max_count_employee,
            'max_count': max_count,
            'max_amount_employee': max_amount_employee,
            'max_amount': round(max_amount, 2)
        }
    else:
        return {
            'total_fines': 0,
            'total_amount': 0.0,
            'avg_amount': 0.0,
            'max_count_employee': '',
            'max_count': 0,
            'max_amount_employee': '',
            'max_amount': 0.0
        }

# Получение данных о сотрудниках на смене
def get_employees_on_shift():
    """Получение данных о сотрудниках на смене из dm.v_employees_on_shift_detailed"""
    query = """
    SELECT 
        fio,
        position,
        brigada,
        smena,
        status_on_shift,
        first_activity_time
    FROM dm.v_employees_on_shift_detailed 
    ORDER BY fio
    """
    
    result = execute_query_cached(query)
    
    employees_data = []
    if result:
        for row in result:
            try:
                fio = row[0] if row[0] else ''
                position = row[1] if row[1] else ''
                brigada = row[2] if row[2] else ''
                smena = row[3] if row[3] else ''
                status_on_shift = row[4] if row[4] else ''
                first_activity_time = row[5] if row[5] else ''
                
                # Форматируем время
                if first_activity_time and hasattr(first_activity_time, 'strftime'):
                    formatted_time = first_activity_time.strftime('%H:%M')
                elif first_activity_time:
                    # Если это строка, пытаемся извлечь время
                    time_str = str(first_activity_time)
                    if ' ' in time_str and ':' in time_str:
                        # Формат "2026-02-02 08:31:25.017"
                        time_part = time_str.split(' ')[1]  # "08:31:25.017"
                        time_parts = time_part.split(':')
                        if len(time_parts) >= 2:
                            formatted_time = f"{time_parts[0]}:{time_parts[1]}"
                        else:
                            formatted_time = time_part[:5]
                    elif ':' in time_str:
                        # Формат "08:31:25"
                        time_parts = time_str.split(':')
                        if len(time_parts) >= 2:
                            formatted_time = f"{time_parts[0]}:{time_parts[1]}"
                        else:
                            formatted_time = time_str[:5]
                    else:
                        formatted_time = time_str
                else:
                    formatted_time = ''
                
                employees_data.append({
                    'ФИО': fio,
                    'Должность': position,
                    'Бригада': brigada,
                    'Смена': smena,
                    'Статус': status_on_shift,
                    'Время_первой_операции': formatted_time
                })
            except Exception as e:
                logger.error("Error processing employee row: %s", e)
                continue

    # Возвращаем кортеж (employees_data, position_stats) для совместимости
    position_stats = {
        'Кладовщик': len(employees_data),
        'Оператор': 0,
        'Комплектовщик': 0
    }
    
    return employees_data, position_stats

def get_positions_list():
    """Получение списка уникальных должностей из dm.v_employees_on_shift_detailed"""
    query = """
    SELECT DISTINCT position 
    FROM dm.v_employees_on_shift_detailed 
    WHERE position IS NOT NULL AND position != ''
    ORDER BY position
    """
    
    result = execute_query_cached(query)
    return [row[0] for row in result] if result else []

def get_brigades_list():
    """Получение списка уникальных бригад из dm.v_employees_on_shift_detailed"""
    query = """
    SELECT DISTINCT brigada
    FROM dm.v_employees_on_shift_detailed
    WHERE brigada IS NOT NULL AND brigada != ''
    ORDER BY brigada
    """

    result = execute_query_cached(query)
    return [row[0] for row in result] if result else []


# ============================================================================
# НОВЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С dm.v_employees_shift_daily
# ============================================================================

def get_todays_shift():
    """
    Определение, какая смена работает сегодня (4-дневный цикл от 11.12.2025)
    Возвращает '1' или '2'
    """
    today = datetime.now().date()
    base_date = datetime(2025, 12, 11).date()
    days_diff = (today - base_date).days
    cycle_position = days_diff % 4
    
    if cycle_position == 0 or cycle_position == 1:
        today_shift = '1'
    else:
        today_shift = '2'

    return today_shift


def get_employees_on_shift_new():
    """
    Получение данных о сотрудниках на текущей смене из dm.v_employees_shift_daily
    + добавляет статус на основе времени первой операции

    Возвращает кортеж (employees_data, position_stats)
    """
    today_shift = get_todays_shift()
    today_date = datetime.now().strftime('%Y-%m-%d')

    # Получаем данные из нового view (оно уже фильтрует по текущему дню)
    # Теперь view возвращает всех сотрудников смены, включая тех, кто не работал
    # today_date встроен в текст запроса для уникального кэш-ключа на каждый день
    query = f"""
    SELECT
        fio,
        position,
        brigada,
        smena,
        first_operation_time,
        last_operation_time,
        total_operations,
        status_on_shift
    FROM dm.v_employees_shift_daily
    WHERE smena = ?
      AND date_key = '{today_date}'
    ORDER BY fio
    """

    # Прямой запрос без кэша — всегда актуальные данные
    result = mssql_client.execute(query, (today_shift,))

    employees_data = []
    if result:
        for row in result:
            try:
                fio = row[0] if row[0] else ''
                position = row[1] if row[1] else ''
                brigada = row[2] if row[2] else ''
                smena = row[3] if row[3] else ''
                first_operation_time = row[4] if row[4] else None
                last_operation_time = row[5] if row[5] else None
                total_operations = row[6] if row[6] else 0
                status_on_shift = row[7] if row[7] else 'Не вышел'

                # Форматируем время первой операции
                if first_operation_time:
                    if hasattr(first_operation_time, 'strftime'):
                        formatted_first_time = first_operation_time.strftime('%H:%M')
                    else:
                        time_str = str(first_operation_time)
                        if ' ' in time_str and ':' in time_str:
                            time_part = time_str.split(' ')[1]
                            time_parts = time_part.split(':')
                            formatted_first_time = f"{time_parts[0]}:{time_parts[1]}" if len(time_parts) >= 2 else time_part[:5]
                        elif ':' in time_str:
                            time_parts = time_str.split(':')
                            formatted_first_time = f"{time_parts[0]}:{time_parts[1]}" if len(time_parts) >= 2 else time_str[:5]
                        else:
                            formatted_first_time = time_str
                else:
                    formatted_first_time = '--:--'

                # Форматируем время последней операции
                if last_operation_time:
                    if hasattr(last_operation_time, 'strftime'):
                        formatted_last_time = last_operation_time.strftime('%H:%M')
                    else:
                        time_str = str(last_operation_time)
                        if ' ' in time_str and ':' in time_str:
                            time_part = time_str.split(' ')[1]
                            time_parts = time_part.split(':')
                            formatted_last_time = f"{time_parts[0]}:{time_parts[1]}" if len(time_parts) >= 2 else time_part[:5]
                        elif ':' in time_str:
                            time_parts = time_str.split(':')
                            formatted_last_time = f"{time_parts[0]}:{time_parts[1]}" if len(time_parts) >= 2 else time_str[:5]
                        else:
                            formatted_last_time = time_str
                else:
                    formatted_last_time = '--:--'

                employees_data.append({
                    'ФИО': fio,
                    'Должность': position,
                    'Бригада': brigada,
                    'Смена': smena,
                    'Статус': status_on_shift,
                    'Время_первой_операции': formatted_first_time,
                    'Время_последней_операции': formatted_last_time
                })
            except Exception as e:
                logger.error("Error processing employee row: %s", e)
                continue

    # Статистика по должностям
    position_stats = {}
    for emp in employees_data:
        pos = emp.get('Должность', 'Не указана')
        if pos not in position_stats:
            position_stats[pos] = 0
        position_stats[pos] += 1

    return employees_data, position_stats


def get_positions_list_new():
    """Получение списка уникальных должностей из dm.v_employees_shift_daily
    БЕЗ КЭША - всегда актуальные данные
    """
    today_shift = get_todays_shift()

    query = """
    SELECT DISTINCT position
    FROM dm.v_employees_shift_daily
    WHERE smena = ?
        AND position IS NOT NULL
        AND position != ''
    ORDER BY position
    """

    # Прямой запрос без кэша
    result = mssql_client.execute(query, (today_shift,))
    return [row[0] for row in result] if result else []


def get_brigades_list_new():
    """Получение списка уникальных бригад (участков) из dm.v_employees_shift_daily
    БЕЗ КЭША - всегда актуальные данные
    """
    today_shift = get_todays_shift()

    query = """
    SELECT DISTINCT brigada
    FROM dm.v_employees_shift_daily
    WHERE smena = ?
        AND brigada IS NOT NULL
        AND brigada != ''
    ORDER BY brigada
    """

    # Прямой запрос без кэша
    result = mssql_client.execute(query, (today_shift,))
    return [row[0] for row in result] if result else []


# Получение всех данных по ячейкам хранения
def get_all_storage_data():
    """Получение данных по ячейкам хранения из v_storage_current_status
    БЕЗ КЭШИРОВАНИЯ - для реального времени
    """
    query = """
    SELECT
        location_type,
        allocation_zone,
        work_zone,
        locating_zone,
        total_cells,
        occupied_cells,
        free_cells,
        occupancy_pct
    FROM dm.v_storage_current_status
    ORDER BY location_type, allocation_zone
    """

    # Используем прямой запрос без кэша
    result = mssql_client.execute(query)

    storage_data = []
    if result:
        for row in result:
            try:
                location_type = row[0] if row[0] else ''
                allocation_zone = row[1] if row[1] else ''
                work_zone = row[2] if row[2] else ''
                locating_zone = row[3] if row[3] else ''
                total_cells = int(row[4]) if row[4] else 0
                occupied_cells = int(row[5]) if row[5] else 0
                free_cells = int(row[6]) if row[6] else 0
                occupancy_pct = float(row[7]) if row[7] else 0.0

                storage_data.append({
                    'location_type': location_type,
                    'allocation_zone': allocation_zone,
                    'work_zone': work_zone,
                    'locating_zone': locating_zone,
                    'total_cells': total_cells,
                    'occupied_cells': occupied_cells,
                    'free_cells': free_cells,
                    'occupancy_pct': round(occupancy_pct, 1)
                })
            except Exception as e:
                logger.error("Error processing storage row: %s", e)
                continue

    return storage_data

# Функция для обновления данных (аналог refresh_data)
def refresh_data(start_date, end_date):
    """Обновление всех данных для дашборда"""
    global PERFORMANCE_DATA_CACHE, EMPLOYEE_ANALYTICS_CACHE, EMPLOYEE_OPERATIONS_DETAIL_CACHE
    global SHIFT_COMPARISON_CACHE, PROBLEMATIC_HOURS_CACHE, ERROR_HOURS_CACHE

    logger.info("Обновление данных за период: %s - %s", start_date, end_date)

    try:
        # Обновляем кэши
        PERFORMANCE_DATA_CACHE = get_performance_data(start_date, end_date)
        logger.info("Данные производительности обновлены: %d сотрудников", len(PERFORMANCE_DATA_CACHE))

        SHIFT_COMPARISON_CACHE = get_shift_comparison(start_date, end_date)
        logger.info("Данные сравнения смен обновлены")

        PROBLEMATIC_HOURS_CACHE = get_problematic_hours(start_date, end_date)
        logger.info("Данные проблемных часов обновлены: %d записей", len(PROBLEMATIC_HOURS_CACHE))

        ERROR_HOURS_CACHE = get_error_hours_top_data(start_date, end_date)
        logger.info("Данные часов с ошибками обновлены: %d записей", len(ERROR_HOURS_CACHE))

        # Инициализируем остальные кэши
        EMPLOYEE_ANALYTICS_CACHE = {}
        EMPLOYEE_OPERATIONS_DETAIL_CACHE = {}

        logger.info("Данные успешно обновлены")

    except Exception as e:
        logger.error("Ошибка при обновлении данных: %s", e)
        import traceback
        traceback.print_exc()

# Недостающие функции для совместимости

def get_revision_stats():
    """Получение статистики по ревизиям из dm.v_revision_by_event"""
    try:
        # Используем правильный путь к view
        query = "SELECT * FROM dm.v_revision_by_event"

        result = execute_query_cached(query)

        if result and len(result) > 0:
            row = result[0]

            # Обрабатываем данные в зависимости от формата
            if isinstance(row, dict):
                open_revisions = row.get('open_revisions') or 0
                in_process_revisions = row.get('in_process_revisions') or 0
                total_revisions = row.get('total_revisions') or 0
            else:
                # Если это кортеж, берем по индексам
                open_revisions = row[0] if len(row) > 0 and row[0] else 0
                in_process_revisions = row[1] if len(row) > 1 and row[1] else 0
                total_revisions = row[2] if len(row) > 2 and row[2] else 0

            return {
                'total_revisions': total_revisions,
                'open_revisions': open_revisions,
                'in_process_revisions': in_process_revisions
            }
        else:
            return {
                'total_revisions': 0,
                'open_revisions': 0,
                'in_process_revisions': 0
            }

    except Exception as e:
        logger.error("Ошибка в get_revision_stats: %s", e)

        # Возвращаем значения по умолчанию в случае ошибки
        return {
            'total_revisions': 0,
            'open_revisions': 0,
            'in_process_revisions': 0
        }

def get_revision_detail_data():
    """Получение детальных данных по ревизиям по событию из dm.v_revision_detail"""
    try:
        query = """
        SELECT 
            internal_count_num,
            condition,
            status_rus,
            item,
            item_desc,
            lot,
            location,
            quantity_counted,
            system_quantity,
            variance,
            counted_by_user,
            counted_date_time
        FROM dm.v_revision_detail
        ORDER BY 
            CASE WHEN condition = 'Open' THEN 0 ELSE 1 END,
            internal_count_num
        """
        
        result = execute_query_cached(query)
        
        detail_data = []
        if result:
            for row in result:
                # Форматируем дату
                counted_date = row[11]
                if counted_date:
                    if hasattr(counted_date, 'strftime'):
                        formatted_date = counted_date.strftime('%d.%m.%Y %H:%M')
                    else:
                        formatted_date = str(counted_date)[:19]
                else:
                    formatted_date = ''
                
                detail_data.append({
                    'internal_count_num': row[0] if row[0] else '',
                    'condition': row[1] if row[1] else '',
                    'status_rus': row[2] if row[2] else '',
                    'item': row[3] if row[3] else '',
                    'item_desc': row[4] if row[4] else '',
                    'lot': row[5] if row[5] else '',
                    'location': row[6] if row[6] else '',
                    'quantity_counted': float(row[7]) if row[7] else 0,
                    'system_quantity': float(row[8]) if row[8] else 0,
                    'variance': float(row[9]) if row[9] else 0,
                    'counted_by_user': row[10] if row[10] else '',
                    'counted_date_time': formatted_date
                })
        
        return detail_data
        
    except Exception as e:
        logger.error("Ошибка в get_revision_detail_data: %s", e)
        return []

def get_placement_errors(start_date=None, end_date=None):
    """Получение данных по ошибкам размещения из dm.v_placement_detail за выбранный период"""
    try:
        # Основной запрос для получения статистики по ошибкам размещения
        # Добавляем фильтрацию по датам, если они указаны
        if start_date and end_date:
            query = """
            SELECT 
                COUNT(*) as total_count,
                SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct_count,
                SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) as error_count,
                COUNT(DISTINCT fio) as unique_users,
                COUNT(DISTINCT ITEM_CATEGORY9) as unique_items
            FROM dm.v_placement_detail
            WHERE CAST(date AS DATE) BETWEEN ? AND ?
            """
            result = execute_query_cached(query, (start_date, end_date))
        else:
            query = """
            SELECT 
                COUNT(*) as total_count,
                SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct_count,
                SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) as error_count,
                COUNT(DISTINCT fio) as unique_users,
                COUNT(DISTINCT ITEM_CATEGORY9) as unique_items
            FROM dm.v_placement_detail
            """
            result = execute_query_cached(query)
        
        if result and len(result) > 0:
            row = result[0]
            
            # Обрабатываем данные в зависимости от формата
            if hasattr(row, '__getitem__'):
                total_count = row[0]
                correct_count = row[1]
                error_count = row[2]
                unique_users = row[3]
                unique_items = row[4]
            else:
                total_count = getattr(row, 'total_count', 0)
                correct_count = getattr(row, 'correct_count', 0)
                error_count = getattr(row, 'error_count', 0)
                unique_users = getattr(row, 'unique_users', 0)
                unique_items = getattr(row, 'unique_items', 0)
            
            # Рассчитываем процент ошибок
            error_percentage = 0.0
            if total_count > 0:
                error_percentage = round((error_count / total_count) * 100, 2)
            
            return {
                'total_count': total_count,
                'correct_count': correct_count,
                'error_count': error_count,
                'error_percentage': error_percentage,
                'unique_users': unique_users,
                'unique_items': unique_items
            }
        else:
            # Возвращаем пустые значения если нет данных
            return {
                'total_count': 0,
                'correct_count': 0,
                'error_count': 0,
                'error_percentage': 0.0,
                'unique_users': 0,
                'unique_items': 0
            }
            
    except Exception as e:
        logger.error("Ошибка в get_placement_errors: %s", e)
        
        # Возвращаем значения по умолчанию в случае ошибки
        return {
            'total_count': 0,
            'correct_count': 0,
            'error_count': 0,
            'error_percentage': 0.0,
            'unique_users': 0,
            'unique_items': 0
        }

def get_timeliness_chart_data(start_date, end_date, chart_type):
    """Получение данных для диаграмм своевременности"""
    query = """
    SELECT 
        date,
        total_orders,
        on_time_orders,
        total_orders - on_time_orders as delayed_orders
    FROM dm.v_order_timeliness 
    WHERE date BETWEEN ? AND ?
    ORDER BY date
    """
    
    result = execute_query_cached(query, (start_date, end_date))
    
    chart_data = []
    if result:
        for row in result:
            try:
                date = row[0] if row[0] else ''
                total_orders = int(row[1]) if row[1] else 0
                on_time_orders = int(row[2]) if row[2] else 0
                delayed_orders = int(row[3]) if row[3] else 0
                
                if chart_type == 'timely':
                    chart_data.append({
                        'date': date,
                        'value': on_time_orders
                    })
                else:  # delayed
                    chart_data.append({
                        'date': date,
                        'value': delayed_orders
                    })
            except Exception as e:
                logger.error("Error processing chart row: %s", e)
                continue
    
    return chart_data

def get_orders_table(start_date, end_date):
    """Получение таблицы заказов (упрощенная версия)"""
    # Используем данные из v_order_timeliness для создания таблицы заказов
    query = """
    SELECT 
        date,
        total_orders,
        on_time_orders,
        total_orders - on_time_orders as delayed_orders
    FROM dm.v_order_timeliness 
    WHERE date BETWEEN ? AND ?
    ORDER BY date DESC
    """
    
    result = execute_query_cached(query, (start_date, end_date))
    
    orders = []
    if result:
        for i, row in enumerate(result):
            try:
                date = row[0] if row[0] else ''
                total_orders = int(row[1]) if row[1] else 0
                on_time_orders = int(row[2]) if row[2] else 0
                delayed_orders = int(row[3]) if row[3] else 0
                
                # Создаем несколько записей для каждого дня
                for j in range(min(3, total_orders)):  # Максимум 3 заказа в день
                    order_id = f"ORD-{date.replace('-', '')}-{j+1:03d}"
                    
                    if j < on_time_orders:
                        status = 'Выполнено'
                        status_color = '#4CAF50'
                    else:
                        status = 'Просрочено'
                        status_color = '#F44336'
                    
                    orders.append({
                        'id': order_id,
                        'type': 'Клиент',
                        'status': status,
                        'create_date': date,
                        'status_color': status_color
                    })
            except Exception as e:
                logger.error("Error processing order row: %s", e)
                continue
    
    return orders

def get_arrival_timeliness(start_date, end_date):
    """Получение своевременности приходов из dm.v_receipt_timeliness"""
    try:
        query = """
        SELECT 
            status,
            SUM(count) as total_count
        FROM dm.v_receipt_timeliness
        WHERE date_key BETWEEN ? AND ?
        GROUP BY status
        """
        
        result = execute_query_cached(query, (start_date, end_date))
        
        timely_count = 0
        delayed_count = 0
        
        if result:
            for row in result:
                status = row[0] if row[0] else ''
                count = int(row[1]) if row[1] else 0
                
                if 'Сделано вовремя' in status:
                    timely_count += count
                elif 'Просрочено' in status:
                    delayed_count += count
        
        return timely_count, delayed_count
        
    except Exception as e:
        logger.error("Ошибка в get_arrival_timeliness: %s", e)
        return 0, 0

def get_order_timeliness(start_date, end_date):
    """Получение своевременности заказов"""
    return get_orders_timely(start_date, end_date)

def get_employee_analytics(employee_name, start_date, end_date):
    """Получение аналитики по сотруднику (упрощенная версия)"""
    performance_data = get_performance_data(start_date, end_date)
    
    for emp in performance_data:
        if emp['Сотрудник'] == employee_name:
            return {
                'total_operations': emp['Общее_кол_операций'],
                'total_earnings': emp['Заработок'],
                'ops_per_hour': emp['Операций_в_час'],
                'work_time': emp['Время_работы'],
                'regular_operations': emp['Обычные_операции'],
                'reception_operations': emp['Приемка']
            }
    
    return {
        'total_operations': 0,
        'total_earnings': 0.0,
        'ops_per_hour': 0.0,
        'work_time': '0ч 0м',
        'regular_operations': 0,
        'reception_operations': 0
    }

def get_employee_operations_detail(employee_name, start_date, end_date):
    """Получени�� детализации операций сотрудника (упрощенная версия)"""
    return []

def get_employee_fines_details(employee_name, start_date, end_date):
    """Получение детализации штрафов сотрудника"""
    # Запрос для получения детализированных данных штрафов для конкретного сотрудника
    query = """
    SELECT
        date_key,
        fine_category,
        total_fine,
        smena
    FROM dm.v_penalty_summary
    WHERE fio = ? AND date_key BETWEEN ? AND ?
    ORDER BY date_key DESC
    """
    
    result = execute_query_cached(query, (employee_name, start_date, end_date))
    
    fines_details = []
    if result:
        for row in result:
            try:
                date_key = row[0] if row[0] else ''
                category = row[1] if row[1] else 'Без категории'
                amount = float(row[2]) if row[2] else 0.0
                shift = row[3] if row[3] else ''
                
                fines_details.append({
                    'date': str(date_key),
                    'category': category,
                    'amount': amount,
                    'shift': shift,
                    'description': f"Штраф за {category}, смена {shift}"
                })
            except Exception as e:
                logger.error("Error processing fine detail row: %s", e)
                continue
    
    return fines_details

def filter_storage_data(storage_data, filters):
    """Фильтрация данных по ячейкам хранения"""
    if not storage_data:
        return {
            'filtered_data': [],
            'summary': {'total': 0, 'occupied': 0, 'empty': 0},
            'available_filters': {
                'storage_type': [],
                'allocation_zone': [],
                'locating_zone': [],
                'location_type': [],
                'work_zone': []
            },
            'chart_data': []
        }
    
    filtered_data = storage_data
    
    # Применяем фильтры
    if filters.get('storage_type') and filters['storage_type'] != 'Все':
        filtered_data = [d for d in filtered_data if d.get('location_type') == filters['storage_type']]
    
    if filters.get('allocation_zone') and filters['allocation_zone'] != 'Все':
        filtered_data = [d for d in filtered_data if d.get('allocation_zone') == filters['allocation_zone']]
    
    if filters.get('locating_zone') and filters['locating_zone'] != 'Все':
        filtered_data = [d for d in filtered_data if d.get('locating_zone') == filters['locating_zone']]
    
    if filters.get('location_type') and filters['location_type'] != 'Все':
        filtered_data = [d for d in filtered_data if d.get('location_type') == filters['location_type']]
    
    if filters.get('work_zone') and filters['work_zone'] != 'Все':
        filtered_data = [d for d in filtered_data if d.get('work_zone') == filters['work_zone']]
    
    # Фильтр "Только пустые ячейки"
    if filters.get('only_empty'):
        filtered_data = [d for d in filtered_data if d.get('free_cells', 0) > 0]
    
    # Считаем сумму
    total_cells = sum(d.get('total_cells', 0) for d in filtered_data)
    occupied_cells = sum(d.get('occupied_cells', 0) for d in filtered_data)
    free_cells = sum(d.get('free_cells', 0) for d in filtered_data)
    
    # Получаем уникальные значения для фильтров из ОТФИЛЬТРОВАННЫХ данных (для взаимозависимости)
    available_filters = {
        'storage_type': sorted(list(set(d.get('location_type', '') for d in filtered_data if d.get('location_type')))),
        'allocation_zone': sorted(list(set(d.get('allocation_zone', '') for d in filtered_data if d.get('allocation_zone')))),
        'locating_zone': sorted(list(set(d.get('locating_zone', '') for d in filtered_data if d.get('locating_zone')))),
        'location_type': sorted(list(set(d.get('location_type', '') for d in filtered_data if d.get('location_type')))),
        'work_zone': sorted(list(set(d.get('work_zone', '') for d in filtered_data if d.get('work_zone'))))
    }
    
    # Подготавливаем данные для диаграмм
    chart_data = []
    for d in filtered_data:
        chart_data.append({
            'name': d.get('location_type', 'Неизвестно'),
            'value': d.get('total_cells', 0),
            'occupied': d.get('occupied_cells', 0),
            'empty': d.get('free_cells', 0)
        })
    
    return {
        'filtered_data': filtered_data,
        'summary': {
            'total': total_cells,
            'occupied': occupied_cells,
            'empty': free_cells
        },
        'available_filters': available_filters,
        'chart_data': chart_data
    }


# Получение данных мониторинга нагрузки групп отбора
def get_group_load_monitor():
    """Получение данных из VIEW raw_.VW_GROUP_LOAD_MONITOR
    Возвращает: group_name, work_type, employees_count, open_tasks_count, status_color
    """
    query = """
    SELECT
        group_name,
        work_type,
        employees_count,
        open_tasks_count,
        status_color
    FROM raw_.VW_GROUP_LOAD_MONITOR
    ORDER BY group_name, work_type
    """
    
    result = execute_query_cached(query)
    
    groups_data = []
    if result:
        for row in result:
            try:
                groups_data.append({
                    'group_name': row[0] if row[0] else '',
                    'work_type': row[1] if row[1] else '',
                    'employees_count': int(row[2]) if row[2] is not None else 0,
                    'open_tasks_count': int(row[3]) if row[3] is not None else 0,
                    'status_color': row[4] if row[4] else 'GRAY'
                })
            except Exception as e:
                logger.error("Error processing group load row: %s", e)
                continue
    
    return groups_data


# ============================================================================
# Функции для модального окна "Точность заказов"
# ============================================================================

def get_daily_pick_stats(start_date=None, end_date=None):
    """
    Получение статистики отборов из vw_daily_pick_stats
    Возвращает общее количество операций отбора за период
    
    Args:
        start_date (str): Начальная дата в формате 'YYYY-MM-DD'
        end_date (str): Конечная дата в формате 'YYYY-MM-DD'
    
    Returns:
        dict: {'total_picks': int} - общее количество отборов
    """
    query = """
    SELECT 
        ISNULL(SUM([Всего операций отбора]), 0) as total_picks
    FROM dwh.vw_daily_pick_stats
    WHERE 1=1
    """
    
    params = []
    if start_date and end_date:
        query += " AND [Дата] >= ? AND [Дата] <= ?"
        params = [start_date, end_date]
    
    try:
        result = mssql_client.execute(query, params)
        if result and len(result) > 0:
            total = int(result[0][0]) if result[0][0] else 0
            return {'total_picks': total}
        return {'total_picks': 0}
    except Exception as e:
        logger.error(f"Error getting daily pick stats: {e}")
        return {'total_picks': 0}


def get_pick_error_details(start_date=None, end_date=None):
    """
    Получение детализации ошибок отбора из vw_pick_error_details
    Возвращает количество ошибок по типам: 'Штраф по претензии' и 'Short Pick'
    
    Args:
        start_date (str): Начальная дата в формате 'YYYY-MM-DD'
        end_date (str): Конечная дата в формате 'YYYY-MM-DD'
    
    Returns:
        dict: {'Штраф по претензии': int, 'Short Pick': int}
    """
    query = """
    SELECT 
        [Ошибка],
        COUNT(*) as error_count
    FROM dwh.vw_pick_error_details
    WHERE 1=1
    """
    
    params = []
    if start_date and end_date:
        query += " AND [Дата ошибки] >= ? AND [Дата ошибки] <= ?"
        params = [start_date, end_date]
    
    query += " GROUP BY [Ошибка]"
    
    try:
        result = mssql_client.execute(query, params)
        errors = {'Штраф по претензии': 0, 'Short Pick': 0}
        
        if result:
            for row in result:
                error_type = row[0]
                count = row[1]
                if error_type == 'Штраф по претензии':
                    errors['Штраф по претензии'] = count
                elif error_type == 'Short Pick':
                    errors['Short Pick'] = count
                    
        return errors
    except Exception as e:
        logger.error(f"Error getting pick error details: {e}")
        return {'Штраф по претензии': 0, 'Short Pick': 0}

# ============================================================================
# Функция для проверки возможности загрузки данных с учетом ETL
# ============================================================================

def check_data_availability():
    """
    Проверяет, можно ли загружать свежие данные
    
    Returns:
        dict: {
            'can_load': bool,
            'etl_status': dict,
            'message': str
        }
    """
    from utils.etl_status import ETLChecker
    
    etl_status = ETLChecker.get_status()
    
    return {
        'can_load': etl_status['can_load_fresh_data'],
        'etl_status': etl_status,
        'message': 'ETL is updating' if etl_status['is_updating'] else 'Data is fresh'
    }

# ============================================================================
# Функция для получения лучших сотрудников за месяц
# ============================================================================

def get_best_employees(report_year, report_month):
    """
    Получение списка лучших сотрудников за указанный месяц и год
    из olap2_fixed.dwh.best_employees_monthly
    
    Args:
        report_year (int): Год (например, 2026)
        report_month (int): Месяц числом (1-12)
    
    Returns:
        list: Список словарей с ключами 'full_name' и 'profession'
    """
    try:
        query = """
        SELECT 
            full_name,
            profession
        FROM olap2_fixed.dwh.best_employees_monthly
        WHERE report_year = ? AND report_month = ?
        ORDER BY full_name
        """
        
        # Прямой запрос без кэша - данные обновляются редко
        result = mssql_client.execute(query, (report_year, report_month))
        
        employees_data = []
        if result:
            for row in result:
                try:
                    full_name = row[0] if row[0] else ''
                    profession = row[1] if row[1] else ''
                    
                    employees_data.append({
                        'full_name': full_name,
                        'profession': profession
                    })
                except Exception as e:
                    logger.error("Error processing best employee row: %s", e)
                    continue
        
        return employees_data
        
    except Exception as e:
        logger.error("Ошибка в get_best_employees: %s", e)
        return []

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_employee_positions_map():
    """Маппинг ФИО -> Должность. Берёт данные из проверенного источника."""
    query = """
    SELECT DISTINCT fio, position 
    FROM dm.v_employees_shift_daily
    WHERE fio IS NOT NULL AND position IS NOT NULL AND TRIM(position) != ''
    """
    result = execute_query_cached(query, ttl=3600)
    
    if not result: 
        logger.warning("⚠️ Справочник должностей пуст в dm.v_employees_shift_daily")
        return {}

    pos_map = {}
    for fio, pos in result:
        # ✅ Нормализуем ключ: убираем пробелы, приводим к верхнему регистру
        key = str(fio).strip().upper()
        pos_map[key] = str(pos).strip()
        
    logger.info(f"✅ Загружено должностей: {len(pos_map)}. Примеры: {dict(list(pos_map.items())[:3])}")
    return pos_map

def get_items_locations(item_codes):
    """
    Получение остатков по всем ячейкам для списка товаров из raw_.LOCATION_INVENTORY
    
    Args:
        item_codes (list): список кодов товаров (ITEM)
    
    Returns:
        dict: {item_code: [{'location': ..., 'quantity': ..., 'um': ..., 'lot': ...}, ...]}
    """
    if not item_codes:
        return {}
    
    # Убираем дубликаты и пустые значения
    items = list(set(str(i) for i in item_codes if i))
    if not items:
        return {}
    
    # Формируем плейсхолдеры для IN (...)
    placeholders = ','.join(['?' for _ in items])
    
    query = f"""
    SELECT 
        ITEM,
        LOCATION,
        ON_HAND_QTY,
        QUANTITY_UM,
        LOT
    FROM raw_.LOCATION_INVENTORY
    WHERE ITEM IN ({placeholders})
        AND ON_HAND_QTY > 0
    ORDER BY ITEM, LOCATION
    """
    
    try:
        result = mssql_client.execute(query, items)
        
        locations_map = {}
        if result:
            for row in result:
                item = str(row[0]) if row[0] else ''
                location = row[1] if row[1] else ''
                quantity = float(row[2]) if row[2] else 0
                um = row[3] if row[3] else ''
                lot = row[4] if row[4] else ''
                
                if item not in locations_map:
                    locations_map[item] = []
                
                locations_map[item].append({
                    'location': location,
                    'quantity': quantity,
                    'um': um,
                    'lot': lot
                })
        
        return locations_map
        
    except Exception as e:
        logger.error("Ошибка в get_items_locations: %s", e)
        return {}

def get_employee_volume_by_type(employee_name, start_date, end_date):
    """Получение данных об объемных операциях сотрудника для диаграммы"""
    query = """
    SELECT
        SUM(ISNULL([Загрузка механизмами], 0)) AS [Загрузка механизмами],
        SUM(ISNULL([Разгрузка механизмами], 0)) AS [Разгрузка механизмами],
        SUM(ISNULL([Загрузка ручная], 0)) AS [Загрузка ручная],
        SUM(ISNULL([Разгрузка ручная], 0)) AS [Разгрузка ручная]
    FROM dwh.sdelka_daily
    WHERE [User name] = ?
    AND calc_date BETWEEN ? AND ?
    """
    employee_name_upper = str(employee_name).strip().upper()
    result = execute_query_cached(query, (employee_name_upper, start_date, end_date))
    
    volume_data = []
    if result and len(result) > 0:
        row = result[0]
        operations = [
            ('Загрузка механизмами', row[0]),
            ('Разгрузка механизмами', row[1]),
            ('Загрузка ручная', row[2]),
            ('Разгрузка ручная', row[3])
        ]
        for op_name, op_value in operations:
            val = float(op_value) if op_value else 0.0
            if val > 0:
                volume_data.append({
                    'operation_type': op_name,
                    'total_volume': round(val, 2)
                })
    
    # Сортируем по убыванию объема
    volume_data.sort(key=lambda x: x['total_volume'], reverse=True)
    return volume_data

def get_employee_actual_work_time(employee_name, start_date, end_date):
    """
    Расчет фактического отработанного времени как разницы между 
    временем последней и первой операции за каждый день в выбранном периоде.
    
    Используем dm.employee_work_idle_summary, так как это исторический аналог 
    dm.v_employees_shift_daily, который поддерживает фильтрацию по диапазону дат (BETWEEN).
    """
    query = """
    SELECT 
        ISNULL(SUM(DATEDIFF(minute, first_op_time, last_op_time)), 0) as total_work_minutes
    FROM dm.employee_work_idle_summary
    WHERE LOWER(user_name) = LOWER(?)
      AND date_key BETWEEN ? AND ?
    """
    try:
        # Приводим имя к верхнему регистру для корректного поиска, как в других функциях
        employee_name_upper = str(employee_name).strip().upper()
        result = execute_query_cached(query, (employee_name_upper, start_date, end_date))
        
        if result and result[0] and result[0][0] is not None:
            return int(result[0][0])
        return 0
    except Exception as e:
        logger.error("Ошибка в get_employee_actual_work_time: %s", e)
        return 0

if __name__ == "__main__":
    # Тестирование основных функций
    refresh_data('2024-01-01', '2024-12-31')
