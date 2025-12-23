import json
from datetime import datetime, timedelta
from data.clickhouse_client import execute_query_cached

# Получение списка сотрудников из БД
def get_employees():
    query = """
    SELECT DISTINCT fio 
    FROM dm.dim_employees 
    WHERE fio IS NOT NULL AND fio != ''
    ORDER BY fio
    """
    result = execute_query_cached(query)
    return [row[0] for row in result] if result else []

# Получение списка типов операций
def get_operation_types():
    query = """
    SELECT DISTINCT WORK_TYPE 
    FROM dwh.operations_enriched 
    WHERE WORK_TYPE IS NOT NULL AND WORK_TYPE != ''
    ORDER BY WORK_TYPE
    """
    result = execute_query_cached(query)
    return [row[0] for row in result] if result else []

# Получение списка категорий штрафов
def get_fine_categories():
    query = """
    SELECT DISTINCT fine_category 
    FROM dm.fact_fines 
    WHERE fine_category IS NOT NULL AND fine_category != ''
    ORDER BY fine_category
    """
    result = execute_query_cached(query)
    return [row[0] for row in result] if result else []

# Получение данных для карточки "Собрано заказов вовремя"
def get_orders_timely(start_date, end_date):
    query = """
    SELECT 
        COUNT(DISTINCT CASE WHEN timeliness_status IN ('вовремя', 'Вовремя') THEN SHIPMENT_ID END) as timely_count,
        COUNT(DISTINCT CASE WHEN timeliness_status IN ('просрочено', 'Просрочено') THEN SHIPMENT_ID END) as delayed_count,
        COUNT(DISTINCT SHIPMENT_ID) as total_count
    FROM dwh.orders_enriched 
    WHERE date BETWEEN %(start_date)s AND %(end_date)s
        AND ORDER_TYPE = 'Клиент'
    """
    result = execute_query_cached(query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    if result and len(result[0]) >= 3:
        timely = int(float(result[0][0])) if result[0][0] else 0
        delayed = int(float(result[0][1])) if result[0][1] else 0
        total = int(float(result[0][2])) if result[0][2] else 0
        if total > 0:
            percentage = (timely / total) * 100
        else:
            percentage = 0
        return timely, delayed, total, round(percentage, 1)
    else:
        return 0, 0, 0, 0

# Получение данных для карточки "Среднее время операции"
def get_avg_operation_time(start_date, end_date):
    query = """
    SELECT 
        CASE 
            WHEN COUNT(*) > 0 THEN SUM(duration_sec) / COUNT(*) / 60.0
            ELSE 0 
        END as avg_time_minutes
    FROM dwh.operations_enriched 
    WHERE date BETWEEN %(start_date)s AND %(end_date)s
        AND duration_sec > 0
    """
    result = execute_query_cached(query, {
        'start_date': start_date,
        'end_date': end_date
    })
    return float(result[0][0]) if result and result[0][0] else 0.0

# Получение данных для карточки "Общий заработок"
def get_total_earnings(start_date, end_date):
    """Получение общего заработка всех сотрудников (обычные операции + приемка)"""
    
    # 1. Заработок от обычных операций
    query_regular = """
    SELECT 
        COALESCE(SUM(price_per_op), 0) as total_regular_earnings
    FROM dwh.operations_enriched 
    WHERE date BETWEEN %(start_date)s AND %(end_date)s
        AND price_per_op > 0
    """
    
    regular_result = execute_query_cached(query_regular, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    regular_earnings = 0.0
    if regular_result and regular_result[0]:
        regular_earnings = float(regular_result[0][0]) if regular_result[0][0] else 0.0
    
    # 2. Заработок от операций приемки
    query_reception = """
    SELECT 
        COUNT(*) as total_reception_count
    FROM dm.fact_transaction_events 
    WHERE DATE(event_time) BETWEEN %(start_date)s AND %(end_date)s
        AND event_time IS NOT NULL
        AND smena IN ('1', '2')
    """
    
    reception_result = execute_query_cached(query_reception, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    reception_earnings = 0.0
    if reception_result and reception_result[0]:
        reception_count = int(float(reception_result[0][0])) if reception_result[0][0] else 0
        reception_earnings = reception_count * 18.70
    
    # 3. Общий заработок
    total_earnings = regular_earnings + reception_earnings
    
    print(f"Общий заработок: обычные={regular_earnings:.2f}, приемка={reception_earnings:.2f}, всего={total_earnings:.2f}")
    
    return total_earnings

def get_storage_cells_stats():
    """
    Получение статистики по ячейкам хранения с учетом LOCATION_STS
    и всех фильтров из Power Query
    """
    query = """
    SELECT 
        COUNT(DISTINCT LOCATION) as total_cells,
        SUM(CASE WHEN LOCATION_STS IN ('Storage', 'Picking') THEN 1 ELSE 0 END) as occupied_cells,
        SUM(CASE WHEN LOCATION_STS = 'Empty' THEN 1 ELSE 0 END) as free_cells
    FROM olap.raw_location 
    WHERE LOCATION IS NOT NULL 
        AND LOCATION != ''
        AND LOCATION_STS IS NOT NULL
        AND LOCATION_STS != 'Frozen'  -- Исключаем замороженные
        AND LOCATION_TYPE IS NOT NULL
        AND LOCATION_TYPE NOT IN ('Брак/бой DMG', 'Напольная', 'Улица KC', 'Ячейки KSP')  -- Исключаем типы
        AND (LOCATION_CLASS = 'Inventory' OR LOCATION_CLASS IS NULL)  -- Фильтр по классу или NULL
    """
    
    result = execute_query_cached(query)
    
    if result and result[0]:
        total_cells = int(float(result[0][0])) if result[0][0] else 0
        occupied_cells = int(float(result[0][1])) if result[0][1] else 0
        free_cells = int(float(result[0][2])) if result[0][2] else 0
        
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
    query = """
    WITH 
    all_orders AS (
        SELECT DISTINCT SHIPMENT_ID
        FROM dwh.orders_enriched 
        WHERE date BETWEEN %(start_date)s AND %(end_date)s
            AND ORDER_TYPE = 'Клиент'
    ),
    error_orders AS (
        SELECT DISTINCT o.SHIPMENT_ID
        FROM dwh.orders_enriched o
        INNER JOIN olap.raw_shtraf_edit s ON o.SHIPMENT_ID = s.reference_id
        WHERE o.date BETWEEN %(start_date)s AND %(end_date)s
            AND o.ORDER_TYPE = 'Клиент'
            AND s.name = 'Штраф по претензии'
            AND DATE(s.date_time_stamp) BETWEEN %(start_date)s AND %(end_date)s
    )
    SELECT 
        COUNT(DISTINCT a.SHIPMENT_ID) as total_orders,
        COUNT(DISTINCT e.SHIPMENT_ID) as error_orders,
        CASE 
            WHEN COUNT(DISTINCT a.SHIPMENT_ID) > 0 
            THEN (COUNT(DISTINCT a.SHIPMENT_ID) - COUNT(DISTINCT e.SHIPMENT_ID)) * 100.0 / COUNT(DISTINCT a.SHIPMENT_ID)
            ELSE 100.0
        END as accuracy_percentage
    FROM all_orders a
    LEFT JOIN error_orders e ON a.SHIPMENT_ID = e.SHIPMENT_ID
    """
    
    result = execute_query_cached(query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    if result and result[0]:
        total_orders = int(float(result[0][0])) if result[0][0] else 0
        error_orders = int(float(result[0][1])) if result[0][1] else 0
        accuracy = float(result[0][2]) if result[0][2] else 100.0
        
        orders_without_errors = total_orders - error_orders
        return accuracy, orders_without_errors, total_orders, error_orders
    else:
        return 100.0, 0, 0, 0

# Получение средней производительности сотрудников
def get_avg_productivity(start_date, end_date):
    query = """
    WITH employee_stats AS (
        SELECT 
            fio,
            COUNT(*) as total_ops,
            MIN(START_DATE_TIME) as first_op,
            MAX(END_DATE_TIME) as last_op,
            CASE 
                WHEN TIMESTAMPDIFF(MINUTE, MIN(START_DATE_TIME), MAX(END_DATE_TIME)) > 0 
                THEN COUNT(*) * 60.0 / TIMESTAMPDIFF(MINUTE, MIN(START_DATE_TIME), MAX(END_DATE_TIME))
                ELSE 0 
            END as ops_per_hour
        FROM dwh.operations_enriched 
        WHERE date BETWEEN %(start_date)s AND %(end_date)s
            AND fio IS NOT NULL
            AND START_DATE_TIME IS NOT NULL
            AND END_DATE_TIME IS NOT NULL
        GROUP BY fio
        HAVING COUNT(*) > 5
    )
    SELECT 
        CASE 
            WHEN COUNT(*) > 0 THEN AVG(ops_per_hour)
            ELSE 0 
        END as avg_ops_per_hour,
        COUNT(DISTINCT fio) as active_employees
    FROM employee_stats
    WHERE ops_per_hour > 0
    """
    
    result = execute_query_cached(query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    if result and result[0]:
        avg_ops = round(float(result[0][0]), 1) if result[0][0] else 0
        active_emp = int(float(result[0][1])) if result[0][1] else 0
        return avg_ops, active_emp
    else:
        return 0, 0

# Получение данных для таблицы производительности сотрудников
def get_performance_data(start_date, end_date):
    """Получение данных производительности сотрудников с учетом операций приемки"""
    
    # 1. Получаем обычные операции
    query_regular = """
    SELECT 
        fio as employee,
        COUNT(*) as total_regular_ops,
        CASE 
            WHEN COUNT(*) > 0 THEN SUM(duration_sec) / COUNT(*) / 60.0
            ELSE 0 
        END as avg_time_per_op,
        COALESCE(SUM(price_per_op), 0) as regular_earnings,
        MIN(START_DATE_TIME) as first_op_time,
        MAX(END_DATE_TIME) as last_op_time
    FROM dwh.operations_enriched 
    WHERE date BETWEEN %(start_date)s AND %(end_date)s
        AND fio IS NOT NULL
        AND START_DATE_TIME IS NOT NULL
        AND END_DATE_TIME IS NOT NULL
    GROUP BY fio
    HAVING COUNT(*) > 0
    """
    
    regular_result = execute_query_cached(query_regular, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    # 2. Получаем операции приемки
    reception_operations = get_reception_operations_period(start_date, end_date)
    
    # 3. Объединяем данные
    performance_data = []
    employees_processed = set()
    
    # Обрабатываем обычные операции
    if regular_result:
        for row in regular_result:
            try:
                employee = row[0] if row[0] else ''
                if not employee:
                    continue
                    
                employees_processed.add(employee)
                
                total_regular_ops = int(float(row[1])) if row[1] else 0
                avg_time = float(row[2]) if row[2] else 0.0
                regular_earnings = float(row[3]) if row[3] else 0.0
                first_op = str(row[4]) if row[4] else ''
                last_op = str(row[5]) if row[5] else ''
                
                # Получаем данные по приемке для этого сотрудника
                reception_data = reception_operations.get(employee, {
                    'reception_count': 0,
                    'earnings': 0.0,
                    'first_reception_time': '',
                    'last_reception_time': ''
                })
                
                total_ops = total_regular_ops + reception_data['reception_count']
                total_earnings = regular_earnings + reception_data['earnings']
                
                # Определяем общее время работы (из обычных операций или приемки)
                work_start_time = first_op
                work_end_time = last_op
                
                # Если есть приемка и у нее более раннее/позднее время
                if reception_data['first_reception_time']:
                    if not work_start_time or reception_data['first_reception_time'] < work_start_time:
                        work_start_time = reception_data['first_reception_time']
                if reception_data['last_reception_time']:
                    if not work_end_time or reception_data['last_reception_time'] > work_end_time:
                        work_end_time = reception_data['last_reception_time']
                
                # Рассчитываем время работы и операции в час
                work_duration = '--:--'
                ops_per_hour = 0
                
                if work_start_time and work_end_time:
                    try:
                        first_dt = datetime.strptime(work_start_time[:19], '%Y-%m-%d %H:%M:%S') if ' ' in work_start_time else datetime.strptime(work_start_time[:19], '%Y-%m-%dT%H:%M:%S')
                        last_dt = datetime.strptime(work_end_time[:19], '%Y-%m-%d %H:%M:%S') if ' ' in work_end_time else datetime.strptime(work_end_time[:19], '%Y-%m-%dT%H:%M:%S')
                        
                        work_minutes = (last_dt - first_dt).total_seconds() / 60
                        if work_minutes > 0:
                            hours = int(work_minutes // 60)
                            minutes = int(work_minutes % 60)
                            work_duration = f"{hours}ч {minutes}м"
                            
                            # Операций в час (все операции)
                            ops_per_hour = round(total_ops * 60 / work_minutes, 1)
                    except Exception as e:
                        print(f"Ошибка расчета времени для {employee}: {e}")
                
                # Время первой операции
                first_op_time = '--:--'
                if work_start_time:
                    try:
                        if ' ' in work_start_time:
                            time_part = work_start_time.split(' ')[1]
                            first_op_time = time_part[:5]
                        elif 'T' in work_start_time:
                            time_part = work_start_time.split('T')[1]
                            first_op_time = time_part[:5]
                        else:
                            first_op_time = work_start_time[:5]
                    except:
                        first_op_time = '--:--'
                
                performance_data.append({
                    'Сотрудник': employee,
                    'Общее_кол_операций': total_ops,
                    'Ср_время_на_операцию': round(avg_time, 1) if avg_time else 0.0,
                    'Заработок': round(total_earnings, 2),
                    'Операций_в_час': ops_per_hour,
                    'Время_работы': work_duration,
                    'Время_первой_операции': first_op_time,
                    'Обычные_операции': total_regular_ops,
                    'Приемка': reception_data['reception_count']
                })
            except Exception as e:
                print(f"Error processing regular operation row: {e}")
                continue
    
    # 4. Добавляем сотрудников, у которых есть только приемка (нет обычных операций)
    for employee, reception_data in reception_operations.items():
        if employee not in employees_processed:
            try:
                total_ops = reception_data['reception_count']
                total_earnings = reception_data['earnings']
                work_start_time = reception_data['first_reception_time']
                work_end_time = reception_data['last_reception_time']
                
                # Рассчитываем время работы
                work_duration = '--:--'
                ops_per_hour = 0
                
                if work_start_time and work_end_time:
                    try:
                        first_dt = datetime.strptime(work_start_time[:19], '%Y-%m-%d %H:%M:%S') if ' ' in work_start_time else datetime.strptime(work_start_time[:19], '%Y-%m-%dT%H:%M:%S')
                        last_dt = datetime.strptime(work_end_time[:19], '%Y-%m-%d %H:%M:%S') if ' ' in work_end_time else datetime.strptime(work_end_time[:19], '%Y-%m-%dT%H:%M:%S')
                        
                        work_minutes = (last_dt - first_dt).total_seconds() / 60
                        if work_minutes > 0:
                            hours = int(work_minutes // 60)
                            minutes = int(work_minutes % 60)
                            work_duration = f"{hours}ч {minutes}м"
                            
                            # Операций в час
                            ops_per_hour = round(total_ops * 60 / work_minutes, 1)
                    except Exception as e:
                        print(f"Ошибка расчета времени для {employee} (только приемка): {e}")
                
                # Время первой операции
                first_op_time = '--:--'
                if work_start_time:
                    try:
                        if ' ' in work_start_time:
                            time_part = work_start_time.split(' ')[1]
                            first_op_time = time_part[:5]
                        elif 'T' in work_start_time:
                            time_part = work_start_time.split('T')[1]
                            first_op_time = time_part[:5]
                        else:
                            first_op_time = work_start_time[:5]
                    except:
                        first_op_time = '--:--'
                
                performance_data.append({
                    'Сотрудник': employee,
                    'Общее_кол_операций': total_ops,
                    'Ср_время_на_операцию': 0.0,  # Нет данных для приемки
                    'Заработок': round(total_earnings, 2),
                    'Операций_в_час': ops_per_hour,
                    'Время_работы': work_duration,
                    'Время_первой_операции': first_op_time,
                    'Обычные_операции': 0,
                    'Приемка': reception_data['reception_count']
                })
            except Exception as e:
                print(f"Error processing reception-only row for {employee}: {e}")
                continue
    
    # 5. Сортируем по заработку (основной критерий теперь)
    performance_data.sort(key=lambda x: x['Заработок'], reverse=True)
    
    return performance_data

# Получение данных о простоях сотрудника
def get_employee_idle_data(employee_name, start_date, end_date):
    query = """
    SELECT 
        SUM(total_work_duration_sec) / 60.0 as total_work_minutes,
        SUM(total_idle_duration_sec) / 60.0 as total_idle_minutes,
        SUM(idle_count_5_10) as idle_5_10_count,
        SUM(idle_count_10_30) as idle_10_30_count,
        SUM(idle_count_30_60) as idle_30_60_count,
        SUM(idle_count_60plus) as idle_60plus_count
    FROM dm.fact_employee_activity 
    WHERE fio = %(employee_name)s
        AND date_key BETWEEN %(start_date)s AND %(end_date)s
    """
    
    result = execute_query_cached(query, {
        'employee_name': employee_name,
        'start_date': start_date,
        'end_date': end_date
    })
    
    if result and result[0]:
        row = result[0]
        return {
            'total_work_minutes': float(row[0]) if row[0] else 0.0,
            'total_idle_minutes': float(row[1]) if row[1] else 0.0,
            'idle_counts': {
                '5-10 мин': int(float(row[2])) if row[2] else 0,
                '10-30 мин': int(float(row[3])) if row[3] else 0,
                '30-60 мин': int(float(row[4])) if row[4] else 0,
                '>1 часа': int(float(row[5])) if row[5] else 0
            }
        }
    else:
        return {
            'total_work_minutes': 0.0,
            'total_idle_minutes': 0.0,
            'idle_counts': {
                '5-10 мин': 0,
                '10-30 мин': 0,
                '30-60 мин': 0,
                '>1 часа': 0
            }
        }

# Получение данных для топ-5 проблемных часов
def get_problematic_hours(start_date, end_date):
    query = """
    SELECT 
        EXTRACT(HOUR FROM START_DATE_TIME) as hour,
        COUNT(*) as total_orders,
        SUM(CASE WHEN timeliness_status IN ('просрочено', 'Просрочено') THEN 1 ELSE 0 END) as delayed_orders,
        CASE 
            WHEN COUNT(*) > 0 
            THEN ROUND(SUM(CASE WHEN timeliness_status IN ('просрочено', 'Просрочено') THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
            ELSE 0 
        END as delay_percentage
    FROM dwh.orders_enriched 
    WHERE date BETWEEN %(start_date)s AND %(end_date)s
        AND ORDER_TYPE = 'Клиент'
        AND START_DATE_TIME IS NOT NULL
    GROUP BY EXTRACT(HOUR FROM START_DATE_TIME)
    HAVING COUNT(*) >= 5
    ORDER BY delay_percentage DESC
    LIMIT 5
    """
    
    result = execute_query_cached(query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    hours_data = []
    if result:
        for row in result:
            try:
                hour = int(float(row[0])) if row[0] else 0
                total = int(float(row[1])) if row[1] else 0
                delayed = int(float(row[2])) if row[2] else 0
                percentage = float(row[3]) if row[3] else 0
                
                hours_data.append({
                    'hour': hour,
                    'total_orders': total,
                    'delayed_orders': delayed,
                    'delay_percentage': percentage
                })
            except:
                continue
    
    return hours_data

# Получение данных для топ-5 часов с наибольшим процентом ошибок
def get_error_hours_top_data(start_date, end_date):
    """Получение данных для топ-5 часов с наибольшим процентом ошибок"""
    
    print(f"DEBUG [get_error_hours_top_data]: Начало обработки периода {start_date} - {end_date}")
    
    # 1. Проверяем, есть ли вообще заказы с ошибками
    check_errors_query = """
    SELECT 
        COUNT(*) as total_errors,
        MIN(DATE(parseDateTimeBestEffortOrNull(date_time_stamp))) as first_date,
        MAX(DATE(parseDateTimeBestEffortOrNull(date_time_stamp))) as last_date
    FROM olap.raw_shtraf_edit 
    WHERE DATE(parseDateTimeBestEffortOrNull(date_time_stamp)) BETWEEN %(start_date)s AND %(end_date)s
        AND date_time_stamp IS NOT NULL
        AND date_time_stamp != ''
        AND reference_id IS NOT NULL
    """
    
    check_result = execute_query_cached(check_errors_query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    print(f"DEBUG: Всего ошибок в raw_shtraf_edit: {check_result[0][0] if check_result else 0}")
    
    # Основной запрос с простой и понятной логикой
    query = """
    WITH error_hours_base AS (
        -- Шаг 1: Получаем часы с ошибками и считаем ошибки
        SELECT 
            toHour(parseDateTimeBestEffortOrNull(s.date_time_stamp)) as hour_with_error,
            s.reference_id,
            s.name as error_type
        FROM olap.raw_shtraf_edit s
        WHERE DATE(parseDateTimeBestEffortOrNull(s.date_time_stamp)) BETWEEN %(start_date)s AND %(end_date)s
            AND s.date_time_stamp IS NOT NULL
            AND s.date_time_stamp != ''
            AND s.reference_id IS NOT NULL
            AND s.reference_id != ''
    ),
    aggregated_errors AS (
        -- Шаг 2: Агрегируем ошибки по часам
        SELECT 
            hour_with_error,
            COUNT(DISTINCT reference_id) as error_orders_count,
            arrayStringConcat(arrayDistinct(groupArray(error_type)), ', ') as error_types
        FROM error_hours_base
        WHERE hour_with_error IS NOT NULL
        GROUP BY hour_with_error
    ),
    total_orders_by_hour AS (
        -- Шаг 3: Получаем общее количество заказов по часам
        SELECT 
            toHour(START_DATE_TIME) as hour,
            COUNT(DISTINCT SHIPMENT_ID) as total_orders_in_hour
        FROM dwh.orders_enriched 
        WHERE date BETWEEN %(start_date)s AND %(end_date)s
            AND ORDER_TYPE = 'Клиент'
            AND START_DATE_TIME IS NOT NULL
        GROUP BY toHour(START_DATE_TIME)
    )
    -- Шаг 4: Объединяем ошибки с общими заказами
    SELECT 
        t.hour,
        COALESCE(e.error_orders_count, 0) as error_orders_count,
        COALESCE(t.total_orders_in_hour, 0) as total_orders_in_hour,
        CASE 
            WHEN COALESCE(t.total_orders_in_hour, 0) > 0 
            THEN ROUND(COALESCE(e.error_orders_count, 0) * 100.0 / t.total_orders_in_hour, 1)
            ELSE 0 
        END as error_percentage,
        COALESCE(e.error_types, '') as error_types
    FROM total_orders_by_hour t
    LEFT JOIN aggregated_errors e ON t.hour = e.hour_with_error
    WHERE COALESCE(e.error_orders_count, 0) > 0
        AND COALESCE(t.total_orders_in_hour, 0) > 0
    ORDER BY error_percentage DESC
    LIMIT 5
    """
    
    print(f"DEBUG: Выполняем основной запрос для периода {start_date} - {end_date}")
    
    result = execute_query_cached(query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    error_hours_data = []
    if result:
        print(f"DEBUG: Основной запрос вернул {len(result)} записей")
        for i, row in enumerate(result):
            try:
                hour = int(float(row[0])) if row[0] else 0
                error_count = int(float(row[1])) if row[1] else 0
                total_orders = int(float(row[2])) if row[2] else 0
                error_percentage = float(row[3]) if row[3] else 0
                error_types = row[4] if row[4] else ''
                
                error_hours_data.append({
                    'hour': hour,
                    'error_orders_count': error_count,
                    'total_orders_in_hour': total_orders,
                    'error_percentage': error_percentage,
                    'error_types': error_types
                })
                print(f"DEBUG: Запись {i+1}: Час {hour}: {error_count} ошибок из {total_orders} заказов ({error_percentage}%)")
            except Exception as e:
                print(f"ERROR processing row {row}: {e}")
                continue
    
    # Упрощаем логику демо-данных: только если ВООБЩЕ нет ошибок
    if not error_hours_data and check_result and check_result[0][0] == 0:
        print(f"DEBUG: ВНИМАНИЕ: Вообще нет ошибок за период {start_date} - {end_date}")
        print(f"DEBUG: Показываем сообщение 'Нет данных' вместо демо-данных")
        return []
    
    print(f"DEBUG: Итоговые данные: {len(error_hours_data)} записей")
    return error_hours_data

# Получение данных для сравнения смен (УПРОЩЕННЫЙ ЗАПРОС)
def get_shift_comparison(start_date, end_date):
    query = """
    WITH operations_data AS (
        SELECT 
            fio,
            COUNT(*) as operations_count,
            MIN(START_DATE_TIME) as first_op_time,
            MAX(END_DATE_TIME) as last_op_time,
            SUM(duration_sec) / 60.0 as total_work_minutes,
            CASE 
                WHEN COUNT(*) > 0 THEN AVG(duration_sec) / 60.0
                ELSE 0 
            END as avg_time_per_op
        FROM dwh.operations_enriched 
        WHERE date BETWEEN %(start_date)s AND %(end_date)s
            AND fio IS NOT NULL
            AND START_DATE_TIME IS NOT NULL
            AND END_DATE_TIME IS NOT NULL
        GROUP BY fio
        HAVING COUNT(*) > 5
    ),
    timeliness_data AS (
        SELECT 
            fio,
            COUNT(DISTINCT SHIPMENT_ID) as total_orders,
            SUM(CASE WHEN timeliness_status IN ('вовремя', 'Вовремя') THEN 1 ELSE 0 END) as timely_orders
        FROM dwh.orders_enriched 
        WHERE date BETWEEN %(start_date)s AND %(end_date)s
            AND fio IS NOT NULL
            AND ORDER_TYPE = 'Клиент'
        GROUP BY fio
    ),
    fines_data AS (
        SELECT 
            fio,
            COUNT(*) as fines_count,
            COALESCE(SUM(fine_amount), 0) as fines_amount
        FROM dm.fact_fines 
        WHERE date_key BETWEEN %(start_date)s AND %(end_date)s
            AND fio IS NOT NULL
        GROUP BY fio
    )
    SELECT 
        o.fio as employee,
        o.operations_count,
        -- Время работы в часах:минутах
        CASE 
            WHEN o.first_op_time IS NOT NULL AND o.last_op_time IS NOT NULL 
            THEN CONCAT(
                FLOOR(TIMESTAMPDIFF(MINUTE, o.first_op_time, o.last_op_time) / 60), 
                'ч ', 
                MOD(TIMESTAMPDIFF(MINUTE, o.first_op_time, o.last_op_time), 60), 
                'м'
            )
            ELSE '--:--'
        END as work_duration,
        -- Операций в час
        CASE 
            WHEN o.first_op_time IS NOT NULL AND o.last_op_time IS NOT NULL 
                AND TIMESTAMPDIFF(MINUTE, o.first_op_time, o.last_op_time) > 0
            THEN ROUND(o.operations_count * 60.0 / TIMESTAMPDIFF(MINUTE, o.first_op_time, o.last_op_time), 1)
            ELSE 0
        END as ops_per_hour,
        -- % занятости
        CASE 
            WHEN o.first_op_time IS NOT NULL AND o.last_op_time IS NOT NULL 
                AND TIMESTAMPDIFF(MINUTE, o.first_op_time, o.last_op_time) > 0
            THEN ROUND(o.total_work_minutes * 100.0 / TIMESTAMPDIFF(MINUTE, o.first_op_time, o.last_op_time), 1)
            ELSE 0
        END as busy_percent,
        -- % своевременности
        CASE 
            WHEN COALESCE(t.total_orders, 0) > 0 
            THEN ROUND(COALESCE(t.timely_orders, 0) * 100.0 / t.total_orders, 1)
            ELSE 100.0
        END as timely_percent,
        -- Штрафы
        COALESCE(f.fines_count, 0) as fines_count,
        COALESCE(f.fines_amount, 0) as fines_amount
    FROM operations_data o
    LEFT JOIN timeliness_data t ON o.fio = t.fio
    LEFT JOIN fines_data f ON o.fio = f.fio
    ORDER BY ops_per_hour DESC
    """
    
    result = execute_query_cached(query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    comparison_data = []
    if result:
        for row in result:
            try:
                comparison_data.append({
                    'Сотрудник': row[0],
                    'Операций': int(float(row[1])) if row[1] else 0,
                    'Время_работы': row[2] if row[2] else '--:--',
                    'Операций_в_час': float(row[3]) if row[3] else 0.0,
                    'Занятость_процент': float(row[4]) if row[4] else 0.0,
                    'Вовремя_процент': float(row[5]) if row[5] else 100.0,
                    'Штрафы_кол': int(float(row[6])) if row[6] else 0,
                    'Штрафы_сумма': float(row[7]) if row[7] else 0.0
                })
            except Exception as e:
                print(f"Error processing shift comparison row: {e}")
                continue
    
    return comparison_data

def get_error_hours_data(start_date, end_date):
    """
    Получение данных о часах с ошибками в заказах
    Возвращает топ-5 часов с наибольшим количеством ошибок
    """
    query = """
    SELECT 
        EXTRACT(HOUR FROM s.date_time_stamp) as error_hour,
        COUNT(DISTINCT o.SHIPMENT_ID) as error_orders_count
    FROM dwh.orders_enriched o
    INNER JOIN olap.raw_shtraf_edit s ON o.SHIPMENT_ID = s.reference_id
    WHERE o.date BETWEEN %(start_date)s AND %(end_date)s
        AND o.ORDER_TYPE = 'Клиент'
        AND s.name = 'Штраф по претензии'
        AND DATE(s.date_time_stamp) BETWEEN %(start_date)s AND %(end_date)s
        AND s.date_time_stamp IS NOT NULL
    GROUP BY EXTRACT(HOUR FROM s.date_time_stamp)
    HAVING COUNT(DISTINCT o.SHIPMENT_ID) >= 2
    ORDER BY error_orders_count DESC
    LIMIT 5
    """
    
    result = execute_query_cached(query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    error_hours_data = []
    if result:
        for row in result:
            hour = int(float(row[0])) if row[0] else 0
            error_count = int(float(row[1])) if row[1] else 0
            
            # Получаем общее количество заказов за этот час
            total_query = """
            SELECT COUNT(DISTINCT SHIPMENT_ID)
            FROM dwh.orders_enriched 
            WHERE date BETWEEN %(start_date)s AND %(end_date)s
                AND ORDER_TYPE = 'Клиент'
                AND START_DATE_TIME IS NOT NULL
                AND EXTRACT(HOUR FROM START_DATE_TIME) = %(hour)s
            """
            
            total_result = execute_query_cached(total_query, {
                'start_date': start_date,
                'end_date': end_date,
                'hour': hour
            })
            
            total_orders = int(float(total_result[0][0])) if total_result and total_result[0][0] else 0
            error_percentage = 0
            if total_orders > 0:
                error_percentage = round((error_count / total_orders) * 100, 1)
            
            error_hours_data.append({
                'hour': hour,
                'error_orders_count': error_count,
                'total_orders_in_hour': total_orders,
                'error_percentage': error_percentage
            })
    
    return error_hours_data

# Получение данных для детальной аналитики сотрудника
def get_employee_analytics(employee_name, start_date, end_date):
    try:
        # Основные метрики производительности
        query_regular = """
        SELECT 
            COUNT(*) as total_regular_operations,
            SUM(duration_sec) / 60.0 as total_work_minutes,
            MIN(START_DATE_TIME) as first_op_time,
            MAX(END_DATE_TIME) as last_op_time,
            COALESCE(SUM(price_per_op), 0) as regular_earnings
        FROM dwh.operations_enriched 
        WHERE fio = %(employee_name)s
            AND date BETWEEN %(start_date)s AND %(end_date)s
        """
        
        regular_result = execute_query_cached(query_regular, {
            'employee_name': employee_name,
            'start_date': start_date,
            'end_date': end_date
        })
        
        # Получаем операции приемки
        reception_query = """
        SELECT 
            COUNT(*) as reception_count,
            MIN(event_time) as first_reception_time,
            MAX(event_time) as last_reception_time
        FROM dm.fact_transaction_events 
        WHERE fio = %(employee_name)s
            AND DATE(event_time) BETWEEN %(start_date)s AND %(end_date)s
            AND event_time IS NOT NULL
            AND smena IN ('1', '2')
        """
        
        reception_result = execute_query_cached(reception_query, {
            'employee_name': employee_name,
            'start_date': start_date,
            'end_date': end_date
        })
        
        # Расчет заработка от приемки
        reception_earnings = 0.0
        reception_count = 0
        first_reception_time = ''
        last_reception_time = ''
        
        if reception_result and reception_result[0]:
            reception_count = int(float(reception_result[0][0])) if reception_result[0][0] else 0
            first_reception_time = reception_result[0][1] if reception_result[0][1] else ''
            last_reception_time = reception_result[0][2] if reception_result[0][2] else ''
            reception_earnings = reception_count * 18.70
        
        if not regular_result or not regular_result[0]:
            # Если нет обычных операций, но есть приемка
            if reception_count > 0:
                total_ops = reception_count
                total_earnings = reception_earnings
                work_start_time = first_reception_time
                work_end_time = last_reception_time
                regular_earnings = 0.0
                total_work_minutes = 0.0
            else:
                return None
        else:
            row = regular_result[0]
            total_regular_ops = int(float(row[0])) if row[0] else 0
            total_work_minutes = float(row[1]) if row[1] else 0.0
            first_regular_time = str(row[2]) if row[2] else ''
            last_regular_time = str(row[3]) if row[3] else ''
            regular_earnings = float(row[4]) if row[4] else 0.0
            
            total_ops = total_regular_ops + reception_count
            total_earnings = regular_earnings + reception_earnings
            
            # Определяем общее время работы
            work_start_time = first_regular_time
            work_end_time = last_regular_time
            
            if first_reception_time:
                if not work_start_time or first_reception_time < work_start_time:
                    work_start_time = first_reception_time
            if last_reception_time:
                if not work_end_time or last_reception_time > work_end_time:
                    work_end_time = last_reception_time
        
        # Получаем данные о простоях
        idle_data = get_employee_idle_data(employee_name, start_date, end_date)
        
        # Статистика по типам операций (обновленная - добавляем приемку)
        ops_query = """
        SELECT 
            WORK_TYPE as operation_type,
            COUNT(*) as operation_count,
            CASE 
                WHEN COUNT(*) > 0 THEN AVG(duration_sec) / 60.0
                ELSE 0 
            END as avg_time_minutes,
            SUM(duration_sec) / 60.0 as total_time_minutes
        FROM dwh.operations_enriched 
        WHERE fio = %(employee_name)s
            AND date BETWEEN %(start_date)s AND %(end_date)s
        GROUP BY WORK_TYPE
        ORDER BY operation_count DESC
        LIMIT 10
        """
        
        ops_result = execute_query_cached(ops_query, {
            'employee_name': employee_name,
            'start_date': start_date,
            'end_date': end_date
        })
        
        operations_stats = []
        if ops_result:
            for op_row in ops_result:
                operations_stats.append({
                    'type': op_row[0],
                    'count': int(float(op_row[1])) if op_row[1] else 0,
                    'avg_time': round(float(op_row[2]), 1) if op_row[2] else 0.0,
                    'total_time': round(float(op_row[3]), 1) if op_row[3] else 0.0
                })
        
        # Добавляем операцию "приемка" в статистику
        if reception_count > 0:
            operations_stats.append({
                'type': 'Приемка',
                'count': reception_count,
                'avg_time': 0.0,  # Нет данных по времени для приемки
                'total_time': 0.0
            })
        
        # Завершенные заказы
        orders_completed_query = """
        SELECT COUNT(DISTINCT SHIPMENT_ID) 
        FROM dwh.orders_enriched 
        WHERE fio = %(employee_name)s
            AND date BETWEEN %(start_date)s AND %(end_date)s
        """
        
        orders_completed_result = execute_query_cached(orders_completed_query, {
            'employee_name': employee_name,
            'start_date': start_date,
            'end_date': end_date
        })
        
        orders_completed = 0
        if orders_completed_result and orders_completed_result[0]:
            orders_completed = int(float(orders_completed_result[0][0])) if orders_completed_result[0][0] else 0
        
        # Своевременность
        timeliness_query = """
        SELECT 
            COUNT(DISTINCT SHIPMENT_ID) as total_orders,
            SUM(CASE WHEN timeliness_status IN ('вовремя', 'Вовремя') THEN 1 ELSE 0 END) as timely_orders
        FROM dwh.orders_enriched 
        WHERE fio = %(employee_name)s
            AND date BETWEEN %(start_date)s AND %(end_date)s
            AND ORDER_TYPE = 'Клиент'
        """
        
        timeliness_result = execute_query_cached(timeliness_query, {
            'employee_name': employee_name,
            'start_date': start_date,
            'end_date': end_date
        })
        
        timely_percentage = 100.0
        if timeliness_result and timeliness_result[0]:
            total_orders = int(float(timeliness_result[0][0])) if timeliness_result[0][0] else 0
            timely_orders = int(float(timeliness_result[0][1])) if timeliness_result[0][1] else 0
            if total_orders > 0:
                timely_percentage = round(timely_orders * 100.0 / total_orders, 1)
        
        # Штрафы
        fines_query = """
        SELECT 
            COUNT(*) as fines_count,
            COALESCE(SUM(fine_amount), 0) as fines_amount
        FROM dm.fact_fines 
        WHERE fio = %(employee_name)s
            AND date_key BETWEEN %(start_date)s AND %(end_date)s
        """
        
        fines_result = execute_query_cached(fines_query, {
            'employee_name': employee_name,
            'start_date': start_date,
            'end_date': end_date
        })
        
        fines_count = 0
        fines_amount = 0.0
        if fines_result and fines_result[0]:
            fines_count = int(float(fines_result[0][0])) if fines_result[0][0] else 0
            fines_amount = float(fines_result[0][1]) if fines_result[0][1] else 0.0
        
        # Расчет времени работы
        work_duration = '0ч 0м'
        if work_start_time and work_end_time:
            try:
                first_dt = datetime.strptime(work_start_time[:19], '%Y-%m-%d %H:%M:%S') if ' ' in work_start_time else datetime.strptime(work_start_time[:19], '%Y-%m-%dT%H:%M:%S')
                last_dt = datetime.strptime(work_end_time[:19], '%Y-%m-%d %H:%M:%S') if ' ' in work_end_time else datetime.strptime(work_end_time[:19], '%Y-%m-%dT%H:%M:%S')
                work_minutes = (last_dt - first_dt).total_seconds() / 60
                hours = int(work_minutes // 60)
                minutes = int(work_minutes % 60)
                work_duration = f"{hours}ч {minutes}м"
            except:
                work_duration = '--:--'
        
        # Расчет операций в час
        ops_per_hour = 0
        if total_work_minutes > 0:
            ops_per_hour = round(total_ops * 60 / total_work_minutes, 1)
        
        return {
            'total_operations': total_ops,
            'total_work_minutes': round(total_work_minutes, 0),
            'work_duration': work_duration,
            'ops_per_hour': ops_per_hour,
            'orders_completed': orders_completed,
            'timely_percentage': timely_percentage,
            'fines_count': fines_count,
            'fines_amount': fines_amount,
            'operations_stats': operations_stats,
            'idle_data': idle_data,
            'total_earnings': round(total_earnings, 2),
            'regular_earnings': round(regular_earnings, 2),
            'reception_earnings': round(reception_earnings, 2),
            'regular_operations': total_ops - reception_count,
            'reception_operations': reception_count
        }
        
    except Exception as e:
        print(f"Error in get_employee_analytics: {e}")
        return None

# Получение деталей операций по сотруднику
def get_employee_operations_detail(employee_name, start_date, end_date):
    query = """
    SELECT 
        WORK_TYPE as operation_type,
        COUNT(*) as operation_count
    FROM dwh.operations_enriched 
    WHERE fio = %(employee_name)s
        AND date BETWEEN %(start_date)s AND %(end_date)s
    GROUP BY WORK_TYPE
    ORDER BY operation_count DESC
    """
    
    result = execute_query_cached(query, {
        'employee_name': employee_name,
        'start_date': start_date,
        'end_date': end_date
    })
    
    operations_detail = {}
    if result:
        for row in result:
            operations_detail[row[0]] = int(float(row[1])) if row[1] else 0
    
    return operations_detail

# Получение данных для своевременности приходов
def get_arrival_timeliness(start_date, end_date):
    query = """
    SELECT 
        status,
        COUNT(DISTINCT receipt_id) as count
    FROM dm.fact_receipts_status 
    WHERE date_key BETWEEN %(start_date)s AND %(end_date)s
    GROUP BY status
    """
    
    result = execute_query_cached(query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    timely_arrivals = 0
    delayed_arrivals = 0
    
    if result:
        for row in result:
            status_str = str(row[0]).lower() if row[0] else ''
            count_val = int(float(row[1])) if row[1] else 0
            
            if 'вовремя' in status_str:
                timely_arrivals = count_val
            elif 'просрочено' in status_str:
                delayed_arrivals = count_val
    
    return timely_arrivals, delayed_arrivals

# Получение данных для своевременности заказов (для карточек)
def get_order_timeliness(start_date, end_date):
    query = """
    SELECT 
        timeliness_status,
        COUNT(DISTINCT SHIPMENT_ID) as count
    FROM dwh.orders_enriched 
    WHERE date BETWEEN %(start_date)s AND %(end_date)s
        AND ORDER_TYPE = 'Клиент'
    GROUP BY timeliness_status
    """
    
    result = execute_query_cached(query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    timely_orders = 0
    delayed_orders = 0
    
    if result:
        for row in result:
            status_str = str(row[0]).lower() if row[0] else ''
            count_val = int(float(row[1])) if row[1] else 0
            
            if 'вовремя' in status_str:
                timely_orders = count_val
            elif 'просрочено' in status_str:
                delayed_orders = count_val
    
    return timely_orders, delayed_orders

# Получение данных для диаграммы "Точность заказов" по периодам
def get_order_accuracy_chart_data(start_date, end_date):
    """Получение данных для диаграммы точности заказов с группировкой по периодам"""
    
    # Рассчитываем количество дней в периоде
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    delta_days = (end_dt - start_dt).days + 1
    
    # Определяем группировку в зависимости от периода
    if delta_days <= 7:
        # До 7 дней - группировка по дням
        date_expr = "toDate(date) as period"
        order_expr = "period"
    elif delta_days <= 30:
        # До 30 дней - группировка по неделям
        date_expr = "toStartOfWeek(date) as period"
        order_expr = "period"
    else:
        # Более 30 дней - группировка по месяцам
        date_expr = "toStartOfMonth(date) as period"
        order_expr = "period"
    
    query = f"""
    WITH 
    all_orders AS (
        SELECT 
            {date_expr},
            SHIPMENT_ID
        FROM dwh.orders_enriched 
        WHERE date BETWEEN %(start_date)s AND %(end_date)s
            AND ORDER_TYPE = 'Клиент'
    ),
    error_orders AS (
        SELECT 
            {date_expr},
            o.SHIPMENT_ID
        FROM dwh.orders_enriched o
        INNER JOIN olap.raw_shtraf_edit s ON o.SHIPMENT_ID = s.reference_id
        WHERE o.date BETWEEN %(start_date)s AND %(end_date)s
            AND o.ORDER_TYPE = 'Клиент'
            AND s.name = 'Штраф по претензии'
            AND DATE(s.date_time_stamp) BETWEEN %(start_date)s AND %(end_date)s
    )
    SELECT 
        a.period,
        COUNT(DISTINCT a.SHIPMENT_ID) as total_orders,
        COUNT(DISTINCT e.SHIPMENT_ID) as error_orders
    FROM all_orders a
    LEFT JOIN error_orders e ON a.SHIPMENT_ID = e.SHIPMENT_ID AND a.period = e.period
    GROUP BY a.period
    ORDER BY {order_expr}
    """
    
    result = execute_query_cached(query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    chart_data = []
    if result:
        for row in result:
            try:
                period_str = str(row[0])[:10] if row[0] else ''
                total_orders = int(float(row[1])) if row[1] else 0
                error_orders = int(float(row[2])) if row[2] else 0
                
                if total_orders > 0:
                    accuracy = ((total_orders - error_orders) / total_orders) * 100
                else:
                    accuracy = 100
                
                chart_data.append({
                    'period': period_str,
                    'total_orders': total_orders,
                    'error_orders': error_orders,
                    'correct_orders': total_orders - error_orders,
                    'accuracy': round(accuracy, 1)
                })
            except Exception:
                continue
    
    return chart_data

# Получение данных для диаграмм своевременности (ИСПРАВЛЕННЫЙ ЗАПРОС)
def get_timeliness_chart_data(start_date, end_date, timeliness_type='timely'):
    """Получение данных для диаграмм своевременности с правильной группировкой"""
    
    # Рассчитываем количество дней в периоде
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    delta_days = (end_dt - start_dt).days + 1
    
    # Определяем группировку в зависимости от периода
    if delta_days <= 7:
        # До 7 дней - группировка по дням
        date_expr = "toDate(date) as period"
        order_expr = "period"
    elif delta_days <= 30:
        # До 30 дней - группировка по неделям
        date_expr = "toStartOfWeek(date) as period"
        order_expr = "period"
    else:
        # Более 30 дней - группировка по месяцам
        date_expr = "toStartOfMonth(date) as period"
        order_expr = "period"
    
    # Определяем условие фильтрации по статусу
    status_condition = ""
    if timeliness_type == 'timely':
        status_condition = "timeliness_status IN ('вовремя', 'Вовремя')"
    else:  # 'delayed'
        status_condition = "timeliness_status IN ('просрочено', 'Просрочено')"
    
    query = f"""
    SELECT 
        {date_expr},
        ROUTING_CODE,
        COUNT(DISTINCT SHIPMENT_ID) as order_count
    FROM dwh.orders_enriched 
    WHERE date BETWEEN %(start_date)s AND %(end_date)s
        AND ORDER_TYPE = 'Клиент'
        AND {status_condition}
        AND ROUTING_CODE IS NOT NULL
    GROUP BY period, ROUTING_CODE
    ORDER BY {order_expr}
    """
    
    result = execute_query_cached(query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    # Подготавливаем структуру данных
    periods_set = set()
    data_dict = {}
    
    if result:
        for row in result:
            try:
                period_str = str(row[0])[:10] if row[0] else ''
                routing_code = row[1] if row[1] else ''
                order_count = int(float(row[2])) if row[2] else 0
                
                periods_set.add(period_str)
                
                if period_str not in data_dict:
                    data_dict[period_str] = {
                        'Доставка_клиенту_с_РЦ': 0,
                        'РЦ': 0
                    }
                
                # Приводим routing_code к стандартному виду для группировки
                routing_lower = routing_code.lower() if routing_code else ''
                
                if 'доставка клиенту' in routing_lower and 'рц' in routing_lower:
                    data_dict[period_str]['Доставка_клиенту_с_РЦ'] += order_count
                elif routing_lower == 'рц':
                    data_dict[period_str]['РЦ'] += order_count
                else:
                    # Если другой тип, добавляем в "РЦ" или создаем отдельную категорию
                    data_dict[period_str]['РЦ'] += order_count
                    
            except Exception as e:
                print(f"Error processing timeliness data: {e}")
                continue
    
    # Преобразуем в список с отсортированными периодами
    chart_data = []
    sorted_periods = sorted(list(periods_set))
    
    for period in sorted_periods:
        if period in data_dict:
            chart_data.append({
                'period': period,
                'Доставка_клиенту_с_РЦ': data_dict[period]['Доставка_клиенту_с_РЦ'],
                'РЦ': data_dict[period]['РЦ']
            })
        else:
            chart_data.append({
                'period': period,
                'Доставка_клиенту_с_РЦ': 0,
                'РЦ': 0
            })
    
    return chart_data

# Получение данных по штрафам
def get_fines_data(start_date, end_date):
    summary_query = """
    SELECT 
        fio,
        COUNT(*) as fines_count,
        COALESCE(SUM(fine_amount), 0) as total_amount,
        CASE 
            WHEN COUNT(*) > 0 THEN COALESCE(SUM(fine_amount), 0) / COUNT(*)
            ELSE 0 
        END as avg_amount
    FROM dm.fact_fines 
    WHERE date_key BETWEEN %(start_date)s AND %(end_date)s
        AND fio IS NOT NULL
    GROUP BY fio
    ORDER BY fines_count DESC
    """
    
    summary_result = execute_query_cached(summary_query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    summary_data = []
    if summary_result:
        for row in summary_result:
            summary_data.append({
                'Сотрудник': row[0],
                'Количество_штрафов': int(float(row[1])) if row[1] else 0,
                'Сумма_штрафов': float(row[2]) if row[2] else 0.0,
                'Средний_штраф': float(row[3]) if row[3] else 0.0,
                'Штрафы': []
            })
    
    category_query = """
    SELECT 
        fine_category,
        COUNT(*) as category_count,
        COALESCE(SUM(fine_amount), 0) as category_total,
        CASE 
            WHEN COUNT(*) > 0 THEN COALESCE(SUM(fine_amount), 0) / COUNT(*)
            ELSE 0 
        END as category_avg
    FROM dm.fact_fines 
    WHERE date_key BETWEEN %(start_date)s AND %(end_date)s
        AND fine_category IS NOT NULL
    GROUP BY fine_category
    """
    
    category_result = execute_query_cached(category_query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    category_data = {}
    if category_result:
        for row in category_result:
            category_data[row[0]] = {
                'count': int(float(row[1])) if row[1] else 0,
                'total_amount': float(row[2]) if row[2] else 0.0,
                'average_amount': float(row[3]) if row[3] else 0.0
            }
    
    kpi_query = """
    SELECT 
        COUNT(*) as total_fines,
        COALESCE(SUM(fine_amount), 0) as total_amount,
        CASE 
            WHEN COUNT(*) > 0 THEN COALESCE(SUM(fine_amount), 0) / COUNT(*)
            ELSE 0 
        END as avg_fine_amount
    FROM dm.fact_fines 
    WHERE date_key BETWEEN %(start_date)s AND %(end_date)s
    """
    
    kpi_result = execute_query_cached(kpi_query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    kpi_data = {
        'total_fines': 0,
        'total_amount': 0.0,
        'avg_fine_amount': 0.0,
        'max_fines_employee': 'Нет данных',
        'max_fines_count': 0,
        'max_amount_employee': 'Нет данных',
        'max_amount': 0.0
    }
    
    if kpi_result and kpi_result[0]:
        kpi_data['total_fines'] = int(float(kpi_result[0][0])) if kpi_result[0][0] else 0
        kpi_data['total_amount'] = float(kpi_result[0][1]) if kpi_result[0][1] else 0.0
        kpi_data['avg_fine_amount'] = float(kpi_result[0][2]) if kpi_result[0][2] else 0.0
    
    if summary_data:
        max_fines = max(summary_data, key=lambda x: x['Количество_штрафов'])
        kpi_data['max_fines_employee'] = max_fines['Сотрудник']
        kpi_data['max_fines_count'] = max_fines['Количество_штрафов']
        
        max_amount = max(summary_data, key=lambda x: x['Сумма_штрафов'])
        kpi_data['max_amount_employee'] = max_amount['Сотрудник']
        kpi_data['max_amount'] = max_amount['Сумма_штрафов']
    
    return {
        'summary_data': summary_data,
        'category_data': category_data,
        'kpi_data': kpi_data
    }

# Получение деталей штрафов для сотрудника
def get_employee_fines_details(employee_name, start_date, end_date):
    query = """
    SELECT 
        fine_category,
        fine_amount,
        date_key
    FROM dm.fact_fines 
    WHERE fio = %(employee_name)s
        AND date_key BETWEEN %(start_date)s AND %(end_date)s
    ORDER BY date_key DESC
    """
    
    result = execute_query_cached(query, {
        'employee_name': employee_name,
        'start_date': start_date,
        'end_date': end_date
    })
    
    fines = []
    if result:
        for row in result:
            fines.append({
                'category': row[0],
                'amount': float(row[1]) if row[1] else 0.0,
                'date': row[2]
            })
    
    return fines

# Получение данных для таблицы заказов
def get_orders_table(start_date, end_date):
    query = """
    SELECT 
        SHIPMENT_ID as order_id,
        ORDER_TYPE as order_type,
        CASE 
            WHEN timeliness_status IN ('вовремя', 'Вовремя') THEN 'Выполнено'
            WHEN timeliness_status IN ('просрочено', 'Просрочено') THEN 'Просрочено'
            ELSE 'В процессе'
        END as status,
        date as create_date
    FROM dwh.orders_enriched 
    WHERE date BETWEEN %(start_date)s AND %(end_date)s
    ORDER BY date DESC
    LIMIT 50
    """
    
    result = execute_query_cached(query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    orders = []
    if result:
        for row in result:
            status = row[2] if row[2] else 'В процессе'
            order_id = row[0] if row[0] else ''
            order_type = row[1] if row[1] else 'Не указан'
            
            create_date = 'Нет даты'
            if row[3]:
                try:
                    if isinstance(row[3], str):
                        create_date = row[3][:10]
                    else:
                        create_date = str(row[3])[:10]
                except:
                    create_date = 'Нет даты'
            
            orders.append({
                'id': order_id,
                'type': order_type,
                'status': status,
                'create_date': create_date
            })
    
    return orders

# УПРОЩЕННАЯ ФУНКЦИЯ ДЛЯ ОПРЕДЕЛЕНИЯ АКТИВНОЙ СМЕНЫ
def get_todays_shift_employees():
    """Определение сотрудников сегодняшней смены на основе поля smena из olap.raw_user_cadr_edit"""
    today = datetime.now().date()
    
    # 1. Определяем, какая смена должна работать сегодня
    # Базовый день: 11.12.2025 - первая смена
    base_date = datetime(2025, 12, 11).date()
    days_diff = (today - base_date).days
    cycle_position = days_diff % 4  # 0-3
    
    # Определяем номер смены на сегодня (значения как строки '1' или '2')
    if cycle_position == 0 or cycle_position == 1:
        # 0,1 - первая смена (как 11-12 декабря)
        today_shift = '1'
        print(f"Сегодня {today}: работает ПЕРВАЯ смена (smena='1')")
    else:
        # 2,3 - вторая смена (как 13-14 декабря)
        today_shift = '2'
        print(f"Сегодня {today}: работает ВТОРАЯ смена (smena='2')")
    
    # 2. Получаем всех сотрудников сегодняшней смены из таблицы olap.raw_user_cadr_edit
    # Исключаем уволенных сотрудников (deleted = 'False') и бригаду "Управление"
    # Также исключаем должности управления
    query = """
    SELECT DISTINCT fio, brigada, smena, deleted, position
    FROM olap.raw_user_cadr_edit 
    WHERE smena = %(today_shift)s
        AND fio IS NOT NULL 
        AND fio != ''
        AND brigada IS NOT NULL
        AND brigada != ''
        AND position IS NOT NULL
        AND position != ''
        AND (deleted IS NULL OR deleted = 'False')  -- Исключаем уволенных
        AND brigada != 'Управление'  -- Исключаем бригаду Управление
        AND position NOT IN (
            'Архивариус', 'Главный энергетик', 'Дворник', 
            'Заместитель начальника смены', 'Заместитель руководителя', 
            'Заместитель руководителя ОП', 'Инженер входного контроля', 
            'Инженер по восстановлению бракованной продукции', 'Менеджер по авто', 
            'Менеджер по жд и авиа', 'Механик', 'Механик водитель', 
            'Начальник смены', 'Оператор', 'Ревизор', 'Руководитель ОП', 
            'Руководитель ОУГ', 'Руководитель ЭММ', 'Системный администратор', 
            'Специалист отдела качества', 'Специалист по претензиям', 
            'Старший менеджер по авто', 'Экспедитор', 'Электрик'
        )  -- Исключаем должности управления
    ORDER BY fio
    """
    
    result = execute_query_cached(query, {'today_shift': today_shift})
    
    if result:
        shift_employees = []
        position_info = {}  # Теперь собираем статистику по должностям
        
        for row in result:
            fio = row[0] if row[0] else ''
            brigada = row[1] if row[1] else 'Не указана'
            smena = row[2] if row[2] else today_shift
            deleted = row[3] if row[3] else 'False'
            position = row[4] if row[4] else 'Не указана'
            
            # Дополнительная проверка на уволенных и бригаду Управление
            if deleted == 'True' or brigada == 'Управление':
                print(f"Пропускаем сотрудника: {fio} - бригада: {brigada}, deleted: {deleted}")
                continue
                
            # Дополнительная проверка на должности управления
            excluded_positions = [
                'Архивариус', 'Главный энергетик', 'Дворник', 
                'Заместитель начальника смены', 'Заместитель руководителя', 
                'Заместитель руководителя ОП', 'Инженер входного контроля', 
                'Инженер по восстановлению бракованной продукции', 'Менеджер по авто', 
                'Менеджер по жд и авиа', 'Механик', 'Механик водитель', 
                'Начальник смены', 'Оператор', 'Ревизор', 'Руководитель ОП', 
                'Руководитель ОУГ', 'Руководитель ЭММ', 'Системный администратор', 
                'Специалист отдела качества', 'Специалист по претензиям', 
                'Старший менеджер по авто', 'Экспедитор', 'Электрик'
            ]
            
            if position in excluded_positions:
                print(f"Пропускаем сотрудника {fio} - исключенная должность: {position}")
                continue
                
            if fio:
                shift_employees.append({
                    'fio': fio,
                    'brigada': brigada,
                    'smena': smena,
                    'position': position,
                    'deleted': deleted
                })
                
                # Собираем информацию по ДОЛЖНОСТЯМ (вместо бригад)
                if position not in position_info:
                    position_info[position] = {
                        'total': 0,
                        'employees': []
                    }
                position_info[position]['total'] += 1
                position_info[position]['employees'].append(fio)
        
        print(f"Найдено сотрудников смены {today_shift}: {len(shift_employees)}")
        print(f"Статистика по должностям: {position_info}")
        return shift_employees, position_info  # Возвращаем position_info вместо brigade_info
    else:
        print(f"Не найдено сотрудников для смены {today_shift}")
        return [], {}

def get_reception_operations(today, employees_list):
    """Получение операций приемки за сегодняшний день для списка сотрудников"""
    if not employees_list:
        return {}
    
    # Формируем список для SQL запроса
    employees_fio_list = [emp['fio'] for emp in employees_list]
    employees_list_str = "','".join(employees_fio_list)
    
    # Получаем минимальное время операции для каждого сотрудника
    query = f"""
    SELECT 
        fio,
        MIN(event_time) as first_reception_time,
        COUNT(*) as reception_count
    FROM dm.fact_transaction_events 
    WHERE DATE(event_time) = %(today)s
        AND fio IN ('{employees_list_str}')
        AND fio IS NOT NULL
        AND event_time IS NOT NULL
        AND smena IN ('1', '2')
    GROUP BY fio
    """
    
    result = execute_query_cached(query, {'today': today})
    
    reception_operations = {}
    if result:
        for row in result:
            fio = row[0] if row[0] else ''
            if fio:
                first_reception_time = row[1] if row[1] else ''
                reception_count = int(float(row[2])) if row[2] else 0
                reception_operations[fio] = {
                    'first_reception_time': first_reception_time,
                    'reception_count': reception_count,
                    'source': 'приемка'
                }
    
    print(f"Найдено операций приемки: {len(reception_operations)}")
    return reception_operations

def get_reception_operations_period(start_date, end_date, employees_list=None):
    """Получение операций приемки за период для списка сотрудников"""
    if employees_list and not employees_list:
        return {}
    
    base_query = """
    SELECT 
        fio,
        COUNT(*) as reception_count,
        MIN(event_time) as first_reception_time,
        MAX(event_time) as last_reception_time
    FROM dm.fact_transaction_events 
    WHERE DATE(event_time) BETWEEN %(start_date)s AND %(end_date)s
        AND fio IS NOT NULL
        AND event_time IS NOT NULL
        AND smena IN ('1', '2')
    """
    
    if employees_list:
        employees_list_str = "','".join(employees_list)
        query = base_query + f" AND fio IN ('{employees_list_str}')"
    else:
        query = base_query
    
    query += " GROUP BY fio"
    
    result = execute_query_cached(query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    reception_operations = {}
    if result:
        for row in result:
            fio = row[0] if row[0] else ''
            if fio:
                reception_count = int(float(row[1])) if row[1] else 0
                first_time = row[2] if row[2] else ''
                last_time = row[3] if row[3] else ''
                
                # Расчет заработка: 18.70 руб за операцию
                earnings = reception_count * 18.70
                
                reception_operations[fio] = {
                    'reception_count': reception_count,
                    'earnings': earnings,
                    'first_reception_time': first_time,
                    'last_reception_time': last_time,
                    'source': 'приемка'
                }
    
    print(f"Найдено операций приемки за период: {len(reception_operations)}")
    return reception_operations



def get_employees_on_shift():
    """Получение списка сотрудников на смене за текущий день с учетом операций приемки"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Получаем сотрудников сегодняшней смены и информацию о ДОЛЖНОСТЯХ
    shift_employees, position_info = get_todays_shift_employees()  # Меняем на position_info
    
    if not shift_employees:
        print("Сегодня смена отдыхает или нет данных о сотрудниках")
        return [], {}
    
    print(f"Всего сотрудников в сегодняшней смене: {len(shift_employees)}")
    
    # 1. Получаем обычные операции за сегодня для этих сотрудников
    employees_fio_list = [emp['fio'] for emp in shift_employees]
    employees_list_str = "','".join(employees_fio_list)
    
    query_today_operations = f"""
    SELECT 
        fio,
        MIN(START_DATE_TIME) as first_operation_time,
        COUNT(*) as operations_count
    FROM dwh.operations_enriched 
    WHERE date = %(today)s
        AND fio IN ('{employees_list_str}')
        AND fio IS NOT NULL
        AND START_DATE_TIME IS NOT NULL
    GROUP BY fio
    """
    
    today_operations_result = execute_query_cached(query_today_operations, {'today': today})
    
    # Создаем словарь обычных операций за сегодня
    today_operations = {}
    if today_operations_result:
        for row in today_operations_result:
            fio = row[0] if row[0] else ''
            if fio:
                first_op_time = row[1] if row[1] else ''
                operations_count = int(float(row[2])) if row[2] else 0
                today_operations[fio] = {
                    'first_op_time': first_op_time,
                    'operations_count': operations_count,
                    'source': 'обычные'
                }
    
    # 2. Получаем операции приемки за сегодня
    reception_operations = get_reception_operations(today, shift_employees)
    
    # 3. Получаем информацию о сотрудниках из olap.raw_user_cadr_edit (исключаем уволенных и управление)
    query_employees_info = f"""
    SELECT 
        fio,
        COALESCE(position, 'Не указана') as position,
        COALESCE(brigada, 'Не указана') as brigade,
        COALESCE(smena, 'Не указана') as smena
    FROM olap.raw_user_cadr_edit 
    WHERE fio IN ('{employees_list_str}')
        AND fio IS NOT NULL 
        AND fio != ''
        AND (deleted IS NULL OR deleted = 'False')  -- Исключаем уволенных
        AND brigada != 'Управление'  -- Исключаем бригаду Управление
        AND position NOT IN (
            'Архивариус', 'Главный энергетик', 'Дворник', 
            'Заместитель начальника смены', 'Заместитель руководителя', 
            'Заместитель руководителя ОП', 'Инженер входного контроля', 
            'Инженер по восстановлению бракованной продукции', 'Менеджер по авто', 
            'Менеджер по жд и авиа', 'Механик', 'Механик водитель', 
            'Начальник смены', 'Оператор', 'Ревизор', 'Руководитель ОП', 
            'Руководитель ОУГ', 'Руководитель ЭММ', 'Системный администратор', 
            'Специалист отдела качества', 'Специалист по претензиям', 
            'Старший менеджер по авто', 'Экспедитор', 'Электрик'
        )  -- Исключаем должности управления
    ORDER BY fio
    """
    
    employees_info_result = execute_query_cached(query_employees_info)
    
    # Создаем словарь информации о сотрудниках
    employees_info = {}
    if employees_info_result:
        for row in employees_info_result:
            fio = row[0] if row[0] else ''
            if fio:
                employees_info[fio] = {
                    'position': row[1] if row[1] else 'Не указана',
                    'brigade': row[2] if row[2] else 'Не указана',
                    'smena': row[3] if row[3] else 'Не указана'
                }
    
    # 4. Формируем результат и статистику по ДОЛЖНОСТЯМ
    employees = []
    position_stats = {}  # Теперь статистика по должностям
    on_work_count = 0
    not_come_count = 0
    
    # Инициализируем статистику по должностям (исключаем "Не указана")
    for position in position_info.keys():
        if position != 'Не указана':
            position_stats[position] = {
                'total': position_info[position]['total'],
                'on_work': 0,
                'not_come': 0,
                'employees': []
            }
    
    for employee in shift_employees:
        fio = employee['fio']
        position = employee['position']  # Используем position из shift_employees
        brigada = employee['brigada']
        
        # Пропускаем бригаду Управление (уже отфильтровано)
        if brigada == 'Управление':
            print(f"Пропускаем сотрудника {fio} - бригада Управление")
            continue
        
        # Дополнительная проверка: если сотрудник не найден в employees_info, пропускаем
        if fio not in employees_info:
            print(f"Сотрудник {fio} не найден в employees_info, возможно исключенная должность. Пропускаем.")
            continue
        
        # Получаем информацию о сотруднике
        position_info_data = employees_info[fio]['position']
        brigade = employees_info[fio]['brigade']
        smena = employees_info[fio]['smena']
        
        # Проверяем, не является ли должность исключенной
        excluded_positions = [
            'Архивариус', 'Главный энергетик', 'Дворник', 
            'Заместитель начальника смены', 'Заместитель руководителя', 
            'Заместитель руководителя ОП', 'Инженер входного контроля', 
            'Инженер по восстановлению бракованной продукции', 'Менеджер по авто', 
            'Менеджер по жд и авиа', 'Механик', 'Механик водитель', 
            'Начальник смены', 'Оператор', 'Ревизор', 'Руководитель ОП', 
            'Руководитель ОУГ', 'Руководитель ЭММ', 'Системный администратор', 
            'Специалист отдела качества', 'Специалист по претензиям', 
            'Старший менеджер по авто', 'Экспедитор', 'Электрик'
        ]
        
        if position_info_data in excluded_positions:
            print(f"Пропускаем сотрудника {fio} - исключенная должность: {position_info_data}")
            continue
        
        # Определяем статус и данные операций
        status = 'Не вышел'
        first_op_data = ''
        operations_count = 0
        operation_type = ''
        
        # Проверяем обычные операции
        if fio in today_operations:
            status = 'На работе'
            first_op_data = today_operations[fio]['first_op_time']
            operations_count = today_operations[fio]['operations_count']
            operation_type = today_operations[fio]['source']
        
        # Проверяем операции приемки (имеет приоритет, если не было обычных операций)
        if fio in reception_operations and status == 'Не вышел':
            status = 'На работе'
            first_op_data = reception_operations[fio]['first_reception_time']
            operations_count = reception_operations[fio]['reception_count']
            operation_type = reception_operations[fio]['source']
        
        # Форматируем время первой операции
        first_op_time = '--:--'
        if first_op_data:
            try:
                if isinstance(first_op_data, str) and first_op_data.strip():
                    # Пробуем разные форматы
                    if ' ' in first_op_data:
                        time_part = first_op_data.split(' ')[1]
                        first_op_time = time_part[:5]
                    elif 'T' in first_op_data:
                        time_part = first_op_data.split('T')[1]
                        first_op_time = time_part[:5]
                    elif ':' in first_op_data:
                        # Если это уже время в формате HH:MM:SS
                        first_op_time = first_op_data[:5]
                    else:
                        # Пробуем парсить как timestamp
                        dt = datetime.strptime(first_op_data[:19], '%Y-%m-%d %H:%M:%S')
                        first_op_time = dt.strftime('%H:%M')
            except Exception as e:
                print(f"Ошибка форматирования времени для {fio}: {e}")
                first_op_time = '--:--'
        
        # Добавляем информацию об источнике операции
        if operation_type == 'приемка':
            operations_info = f"{operations_count} (приемка)"
        else:
            operations_info = str(operations_count)
        
        # Обновляем счетчики
        if status == 'На работе':
            on_work_count += 1
            if position in position_stats:
                position_stats[position]['on_work'] += 1
        else:
            not_come_count += 1
            if position in position_stats:
                position_stats[position]['not_come'] += 1
        
        # Добавляем сотрудника в статистику должности
        if position in position_stats:
            position_stats[position]['employees'].append({
                'fio': fio,
                'status': status,
                'first_op_time': first_op_time
            })
        
        employees.append({
            'ФИО': fio,
            'Должность': position,
            'Бригада': brigade,
            'Смена': smena,
            'Время_первой_операции': first_op_time,
            'Статус': status,
            'Операций сегодня': '0',
            'Тип операций': ''
        })
    
    # 5. Формируем строку статистики по ДОЛЖНОСТЯМ (исключаем пустые и "Не указана")
    position_stats_text = []
    for position, stats in position_stats.items():
        if position != 'Не указана' and position and stats['total'] > 0:
            position_stats_text.append(f"{position}: {stats['on_work']}/{stats['total']}")
    
    position_stats_str = " | ".join(position_stats_text) if position_stats_text else "Нет данных по должностям"
    
    print(f"Итог: На работе: {on_work_count}, Не вышли: {not_come_count}")
    print(f"Статистика по должностям: {position_stats_str}")
    
    # Сортируем: сначала сотрудники на работе, потом не вышедшие
    employees.sort(key=lambda x: (0 if x['Статус'] == 'На работе' else 1, x['ФИО']))
    
    return employees, position_stats_str  # Возвращаем position_stats_str вместо brigade_stats_str



def get_positions_list():
    """Получение списка уникальных должностей из olap.raw_user_cadr_edit"""
    query = """
    SELECT DISTINCT position 
    FROM olap.raw_user_cadr_edit 
    WHERE position IS NOT NULL 
        AND position != ''
        AND (deleted IS NULL OR deleted = 'False')  -- Исключаем уволенных
        AND brigada != 'Управление'  -- Исключаем бригаду Управление
        AND position NOT IN (
            'Архивариус', 'Главный энергетик', 'Дворник', 
            'Заместитель начальника смены', 'Заместитель руководителя', 
            'Заместитель руководителя ОП', 'Инженер входного контроля', 
            'Инженер по восстановлению бракованной продукции', 'Менеджер по авто', 
            'Менеджер по жд и авиа', 'Механик', 'Механик водитель', 
            'Начальник смены', 'Оператор', 'Ревизор', 'Руководитель ОП', 
            'Руководитель ОУГ', 'Руководитель ЭММ', 'Системный администратор', 
            'Специалист отдела качества', 'Специалист по претензиям', 
            'Старший менеджер по авто', 'Экспедитор', 'Электрик'
        )  -- Исключаем должности управления
    ORDER BY position
    """
    
    result = execute_query_cached(query)
    return [row[0] for row in result] if result else []

def get_brigades_list():
    """Получение списка уникальных бригад из olap.raw_user_cadr_edit"""
    query = """
    SELECT DISTINCT brigada 
    FROM olap.raw_user_cadr_edit 
    WHERE brigada IS NOT NULL 
        AND brigada != ''
        AND (deleted IS NULL OR deleted = 'False')  -- Исключаем уволенных
        AND brigada != 'Управление'  -- Исключаем бригаду Управление
    ORDER BY brigada
    """
    
    result = execute_query_cached(query)
    return [row[0] for row in result] if result else []

def get_brigades_list():
    """Получение списка уникальных бригад из olap.users"""
    query = """
    SELECT DISTINCT brigada 
    FROM olap.users 
    WHERE brigada IS NOT NULL 
        AND brigada != ''
    ORDER BY brigada
    """
    
    result = execute_query_cached(query)
    return [row[0] for row in result] if result else []

# Глобальные переменные для хранения данных (оставляем для обратной совместимости)
employees = get_employees()
operation_types = get_operation_types()
fine_categories = get_fine_categories()

performance_data_cache = []
employee_analytics_cache = {}
employee_operations_detail_cache = {}
shift_comparison_cache = []
problematic_hours_cache = []

def refresh_data(start_date, end_date):
    """Обновление всех данных"""
    global performance_data_cache, employee_analytics_cache, employee_operations_detail_cache
    global shift_comparison_cache, problematic_hours_cache
    
    performance_data_cache = get_performance_data(start_date, end_date)
    shift_comparison_cache = get_shift_comparison(start_date, end_date)
    problematic_hours_cache = get_problematic_hours(start_date, end_date)
    employee_analytics_cache = {}
    employee_operations_detail_cache = {}

def get_all_storage_data():
    """
    Получение ВСЕХ данных по ячейкам хранения со всеми преобразованиями
    Возвращает полный набор данных для фильтров и диаграмм
    """
    query = """
    SELECT 
        -- Основные поля
        LOCATION as location_id,
        LOCATION_STS as status,
        LOCATION_TYPE as location_type,
        LOCATING_ZONE as locating_zone,
        ALLOCATION_ZONE as allocation_zone,
        WORK_ZONE as work_zone,
        -- Преобразование Тип хранения (как в Power Query)
        CASE 
            WHEN LOCATION_TYPE = 'Бокс большой' THEN 'Боксы для неликвидов'
            WHEN LOCATING_ZONE = 'ZX_Gofra_BIG' THEN 'Ячейки для гофротрубы'
            WHEN LOCATING_ZONE = 'ZX_Gofra' THEN 'Ячейки для гофротрубы'
            WHEN LOCATING_ZONE = 'ZX_ST_E' THEN 'Ячейки для неликвидов'
            WHEN WORK_ZONE = 'NG_WK' THEN 'Ячейки негабарита КНС'
            WHEN LOCATING_ZONE = 'ZX_Kanal' THEN 'Ячейки негабарита КНС'
            WHEN LOCATING_ZONE = 'ZX_Long < 2' THEN 'Ячейки негабарита ЭЛО'
            WHEN LOCATING_ZONE = 'ZX_Volumetric' THEN 'Ячейки негабарита ЭЛО'
            WHEN LOCATING_ZONE = 'ZX_Schit_etagniy' THEN 'Ячейки негабарита ЭЛО'
            WHEN WORK_ZONE = 'ZX_WK1' THEN 'Ячейки отбора'
            WHEN ALLOCATION_ZONE = 'ZX_подборщик 20-30' THEN 'Ячейки отбора'
            WHEN WORK_ZONE = 'ZX_WK_K' THEN 'Ячейки отбора КПП'
            WHEN WORK_ZONE = 'ZX_WK2' THEN 'Паллетное хранение'
            WHEN LEFT(WORK_ZONE, 2) = 'ME' THEN 'Мезонин'
            WHEN LOCATION_TYPE = 'Ячейки KP' THEN 'Ячейки отмотки КПП'
            ELSE 'Остальное'
        END as storage_type
    FROM olap.raw_location 
    WHERE LOCATION IS NOT NULL 
        AND LOCATION != ''
        AND LOCATION_STS IS NOT NULL
        AND LOCATION_STS != 'Frozen'
        AND LOCATION_TYPE IS NOT NULL
        AND LOCATION_TYPE NOT IN ('Брак/бой DMG', 'Напольная', 'Улица KC', 'Ячейки KSP')
        AND (LOCATION_CLASS = 'Inventory' OR LOCATION_CLASS IS NULL)
    """
    
    result = execute_query_cached(query)
    
    if not result:
        return {
            'all_data': [],
            'filter_options': {
                'storage_type': [],
                'locating_zone': [],
                'allocation_zone': [],
                'location_type': [],
                'work_zone': []
            }
        }
    
    # Обработка данных
    all_data = []
    filter_sets = {
        'storage_type': set(),
        'locating_zone': set(),
        'allocation_zone': set(),
        'location_type': set(),
        'work_zone': set()
    }
    
    for row in result:
        try:
            location_id = row[0] if row[0] else ''
            status = row[1] if row[1] else ''
            location_type = row[2] if row[2] else ''
            locating_zone = row[3] if row[3] else ''
            allocation_zone = row[4] if row[4] else ''
            work_zone = row[5] if row[5] else ''
            storage_type = row[6] if row[6] else 'Остальное'
            
            # Проверяем что статус правильный
            if status not in ['Empty', 'Storage', 'Picking']:
                continue
            
            data_item = {
                'location_id': location_id,
                'status': status,
                'location_type': location_type,
                'locating_zone': locating_zone,
                'allocation_zone': allocation_zone,
                'work_zone': work_zone,
                'storage_type': storage_type,
                'is_empty': 1 if status == 'Empty' else 0,
                'is_occupied': 1 if status in ['Storage', 'Picking'] else 0
            }
            
            all_data.append(data_item)
            
            # Добавляем значения в фильтры
            if storage_type and storage_type != '':
                filter_sets['storage_type'].add(storage_type)
            if locating_zone and locating_zone != '':
                filter_sets['locating_zone'].add(locating_zone)
            if allocation_zone and allocation_zone != '':
                filter_sets['allocation_zone'].add(allocation_zone)
            if location_type and location_type != '':
                filter_sets['location_type'].add(location_type)
            if work_zone and work_zone != '':
                filter_sets['work_zone'].add(work_zone)
                
        except Exception as e:
            print(f"Error processing storage data row: {e}")
            continue
    
    # Преобразуем множества в отсортированные списки
    filter_options = {}
    for key, value_set in filter_sets.items():
        filter_options[key] = sorted(list(value_set))
    
    return {
        'all_data': all_data,
        'filter_options': filter_options
    }

def filter_storage_data(all_data, filters):
    """
    Фильтрация данных по выбранным фильтрам
    и определение доступных значений для других фильтров
    
    Parameters:
    -----------
    all_data : list
        Все данные полученные из get_all_storage_data()
    filters : dict
        Текущие активные фильтры
    
    Returns:
    --------
    dict:
        - filtered_data: отфильтрованные данные
        - available_filters: доступные значения для каждого фильтра
        - summary: статистика для KPI
        - chart_data: данные для диаграмм
    """
    # Сначала фильтруем данные
    filtered_data = all_data.copy()
    
    # Применяем фильтры
    for filter_key, filter_value in filters.items():
        if filter_value and filter_value != 'Все':
            filtered_data = [
                item for item in filtered_data 
                if item.get(filter_key) == filter_value
            ]
    
    # Определяем доступные значения для каждого фильтра
    available_filters = {
        'storage_type': set(),
        'locating_zone': set(),
        'allocation_zone': set(),
        'location_type': set(),
        'work_zone': set()
    }
    
    for item in filtered_data:
        if item['storage_type'] and item['storage_type'] != '':
            available_filters['storage_type'].add(item['storage_type'])
        if item['locating_zone'] and item['locating_zone'] != '':
            available_filters['locating_zone'].add(item['locating_zone'])
        if item['allocation_zone'] and item['allocation_zone'] != '':
            available_filters['allocation_zone'].add(item['allocation_zone'])
        if item['location_type'] and item['location_type'] != '':
            available_filters['location_type'].add(item['location_type'])
        if item['work_zone'] and item['work_zone'] != '':
            available_filters['work_zone'].add(item['work_zone'])
    
    # Преобразуем в списки и сортируем
    for key in available_filters:
        available_filters[key] = sorted(list(available_filters[key]))
    
    # Рассчитываем статистику для KPI
    total = len(filtered_data)
    empty = sum(1 for item in filtered_data if item['status'] == 'Empty')
    occupied = sum(1 for item in filtered_data if item['status'] in ['Storage', 'Picking'])
    
    # Данные для диаграммы "Доли типов ячеек" (по location_type)
    location_type_stats = {}
    for item in filtered_data:
        loc_type = item['location_type']
        if loc_type not in location_type_stats:
            location_type_stats[loc_type] = {
                'total': 0,
                'empty': 0,
                'occupied': 0
            }
        location_type_stats[loc_type]['total'] += 1
        if item['status'] == 'Empty':
            location_type_stats[loc_type]['empty'] += 1
        else:
            location_type_stats[loc_type]['occupied'] += 1
    
    # Преобразуем в список и сортируем
    chart_data_by_type = []
    for loc_type, stats in location_type_stats.items():
        chart_data_by_type.append({
            'location_type': loc_type,
            'total': stats['total'],
            'empty': stats['empty'],
            'occupied': stats['occupied']
        })
    
    chart_data_by_type.sort(key=lambda x: x['total'], reverse=True)
    
    return {
        'filtered_data': filtered_data,
        'available_filters': available_filters,
        'summary': {
            'total': total,
            'empty': empty,
            'occupied': occupied
        },
        'chart_data': {
            'by_location_type': chart_data_by_type[:100]  # Топ-15 типов
        }
    }

# Получение данных по ревизиям по событию
def get_revision_stats(start_date=None, end_date=None):
    """
    Получение статистики по ревизиям по событию
    В таблице нет поля date, поэтому используем все записи
    """
    print(f"[DEBUG] get_revision_stats вызвана")
    
    # Тестовый запрос: посмотреть все данные в таблице
    query_test = """
    SELECT 
        WORK_TYPE,
        INSTRUCTION_TYPE,
        CONDITION,
        COUNT(*) as count
    FROM olap.raw_work_instruction_view2 
    GROUP BY WORK_TYPE, INSTRUCTION_TYPE, CONDITION
    ORDER BY count DESC
    """
    
    try:
        # Сначала выполняем тестовый запрос
        test_result = execute_query_cached(query_test)
        
        print(f"[DEBUG] Всего найдено {len(test_result)} комбинаций данных:")
        for row in test_result:
            work_type = row[0] if row[0] else ''
            instr_type = row[1] if row[1] else ''
            condition = row[2] if row[2] else ''
            count = int(float(row[3])) if row[3] else 0
            
            print(f"[DEBUG] WORK_TYPE='{work_type}', INSTRUCTION_TYPE='{instr_type}', CONDITION='{condition}': {count} шт.")
        
        # Основные запросы (БЕЗ ФИЛЬТРА ПО DATE - его нет в таблице!)
        
        # 1. Открытые ревизии (Detail + Open)
        query_open = """
        SELECT 
            COUNT(*) as open_revisions
        FROM olap.raw_work_instruction_view2 
        WHERE WORK_TYPE = 'Ревизия по событию'
            AND INSTRUCTION_TYPE = 'Detail'
            AND CONDITION = 'Open'
        """
        
        # 2. Ревизии на согласовании (Header + In Process)
        query_in_process = """
        SELECT 
            COUNT(*) as in_process_revisions
        FROM olap.raw_work_instruction_view2 
        WHERE WORK_TYPE = 'Ревизия по событию'
            AND INSTRUCTION_TYPE = 'Header'
            AND CONDITION = 'In Process'
        """
        
        # Выполняем запросы
        open_result = execute_query_cached(query_open)
        in_process_result = execute_query_cached(query_in_process)
        
        # Извлекаем значения
        open_revisions = 0
        in_process_revisions = 0
        
        if open_result and open_result[0] and open_result[0][0]:
            open_revisions = int(float(open_result[0][0]))
        
        if in_process_result and in_process_result[0] and in_process_result[0][0]:
            in_process_revisions = int(float(in_process_result[0][0]))
        
        # Общее количество (сумма открытых и на согласовании)
        total_revisions = open_revisions + in_process_revisions
        
        print(f"[DEBUG] Статистика по ревизиям:")
        print(f"[DEBUG] - WORK_TYPE='Ревизия по событию', INSTRUCTION_TYPE='Detail', CONDITION='Open': {open_revisions} шт.")
        print(f"[DEBUG] - WORK_TYPE='Ревизия по событию', INSTRUCTION_TYPE='Header', CONDITION='In Process': {in_process_revisions} шт.")
        print(f"[DEBUG] - Всего ревизий: {total_revisions}")
        
        return {
            'total_revisions': total_revisions,
            'open_revisions': open_revisions,
            'in_process_revisions': in_process_revisions
        }
        
    except Exception as e:
        print(f"[ERROR] Ошибка в get_revision_stats: {e}")
        import traceback
        traceback.print_exc()
        return {
            'total_revisions': 0,
            'open_revisions': 0,
            'in_process_revisions': 0
        }
    
def get_placement_errors():
    """
    Получение количества ошибок при размещении
    
    Логика:
    1. Фильтруем записи: WORK_TYPE = 'Размещение KC', 
                        INSTRUCTION_TYPE = 'Detail', 
                        CONDITION = 'Closed'
    2. Присоединяем таблицу raw_item для получения ITEM_CATEGORY9
    3. Фильтруем по 2025 году из DATE_TIME_STAMP
    4. Определяем статус "Верно"/"Ошибка" по правилам:
       - Если ITEM_CATEGORY9 = "A" или "B" И LOCATING_ZONE = "KC_ST_A" или "KC_ST_B" → "Верно"
       - Если ITEM_CATEGORY9 = "C" И LOCATING_ZONE = "KC_ST_C" → "Верно"
       - В остальных случаях → "Ошибка"
    5. Считаем количество ошибок и верных размещений
    """
    query = """
    WITH placement_data AS (
        SELECT 
            w.COMPLETED_BY_USER,
            w.ITEM,
            w.LOCATING_ZONE,
            i.ITEM_CATEGORY9,
            w.DATE_TIME_STAMP
        FROM olap.raw_work_instruction_view2 w
        LEFT JOIN olap.raw_item i ON w.ITEM = i.ITEM
        WHERE w.WORK_TYPE = 'Размещение KC'
            AND w.INSTRUCTION_TYPE = 'Detail'
            AND w.CONDITION = 'Closed'
            AND w.DATE_TIME_STAMP IS NOT NULL
            AND w.DATE_TIME_STAMP != ''
            AND toYear(parseDateTimeBestEffortOrNull(w.DATE_TIME_STAMP)) = 2025
    ),
    categorized_data AS (
        SELECT 
            COMPLETED_BY_USER,
            ITEM,
            LOCATING_ZONE,
            ITEM_CATEGORY9,
            DATE_TIME_STAMP,
            CASE 
                WHEN (ITEM_CATEGORY9 IN ('A', 'B') AND LOCATING_ZONE IN ('KC_ST_A', 'KC_ST_B')) 
                     OR (ITEM_CATEGORY9 = 'C' AND LOCATING_ZONE = 'KC_ST_C')
                THEN 'Верно'
                ELSE 'Ошибка'
            END as placement_status
        FROM placement_data
        WHERE ITEM_CATEGORY9 IS NOT NULL
            AND ITEM_CATEGORY9 != ''
            AND LOCATING_ZONE IS NOT NULL
            AND LOCATING_ZONE != ''
    )
    SELECT 
        placement_status,
        COUNT(*) as count,
        COUNT(DISTINCT COMPLETED_BY_USER) as unique_users,
        COUNT(DISTINCT ITEM) as unique_items
    FROM categorized_data
    GROUP BY placement_status
    """
    
    try:
        result = execute_query_cached(query)
        
        print(f"[DEBUG] get_placement_errors результат: {result}")
        
        # Извлекаем значения
        correct_count = 0
        error_count = 0
        unique_users = 0
        unique_items = 0
        
        if result:
            for row in result:
                status = row[0] if row[0] else ''
                count = int(float(row[1])) if row[1] else 0
                users = int(float(row[2])) if row[2] else 0
                items = int(float(row[3])) if row[3] else 0
                
                if status == 'Верно':
                    correct_count = count
                elif status == 'Ошибка':
                    error_count = count
                
                # Берем максимум из уникальных пользователей/предметов
                unique_users = max(unique_users, users)
                unique_items = max(unique_items, items)
        
        total_count = correct_count + error_count
        
        # Рассчитываем процент ошибок
        error_percentage = 0
        if total_count > 0:
            error_percentage = round((error_count / total_count) * 100, 1)
        
        print(f"[DEBUG] Итог: Верно={correct_count}, Ошибок={error_count}, Всего={total_count}, % ошибок={error_percentage}%")
        
        return {
            'correct_count': correct_count,
            'error_count': error_count,
            'total_count': total_count,
            'error_percentage': error_percentage,
            'unique_users': unique_users,
            'unique_items': unique_items
        }
        
    except Exception as e:
        print(f"[ERROR] Ошибка в get_placement_errors: {e}")
        import traceback
        traceback.print_exc()
        return {
            'correct_count': 0,
            'error_count': 0,
            'total_count': 0,
            'error_percentage': 0,
            'unique_users': 0,
            'unique_items': 0
        }
    
# Получение количества отклоненных строк в заказах
def get_rejected_lines_count(start_date, end_date):
    """Получение количества отклоненных строк в заказах по полю DATE_TIME_STAMP"""
    query = """
    SELECT 
        COUNT(*) as rejected_lines_count
    FROM dwh.cube_shipment_detail 
    WHERE DATE(DATE_TIME_STAMP) BETWEEN %(start_date)s AND %(end_date)s
        AND DATE_TIME_STAMP IS NOT NULL
    """
    
    result = execute_query_cached(query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    rejected_count = 0
    if result and result[0] and result[0][0]:
        rejected_count = int(float(result[0][0]))
    
    print(f"[DEBUG] Отклоненных строк за период {start_date} - {end_date}: {rejected_count}")
    return rejected_count

# Получение детальной информации по отклоненным строкам
def get_rejected_lines_details(start_date, end_date):
    """Получение детальной информации по отклоненным строкам"""
    query = """
    SELECT 
        SHIPMENT_ID,
        ITEM,
        ITEM_DESC,
        REQUESTED_QTY,
        QUANTITY_UM,
        PICK_LOC,
        PICK_ZONE,
        DATE_TIME_STAMP
    FROM dwh.cube_shipment_detail 
    WHERE DATE(DATE_TIME_STAMP) BETWEEN %(start_date)s AND %(end_date)s
        AND DATE_TIME_STAMP IS NOT NULL
    ORDER BY DATE_TIME_STAMP DESC
    LIMIT 1000
    """
    
    result = execute_query_cached(query, {
        'start_date': start_date,
        'end_date': end_date
    })
    
    rejected_lines = []
    if result:
        for row in result:
            try:
                # Преобразуем дату в строку для корректного отображения
                date_str = ""
                if row[7]:  # DATE_TIME_STAMP
                    if isinstance(row[7], str):
                        date_str = row[7]
                    else:
                        date_str = str(row[7])
                
                rejected_lines.append({
                    'SHIPMENT_ID': row[0] if row[0] else '',
                    'ITEM': row[1] if row[1] else '',
                    'ITEM_DESC': row[2] if row[2] else '',
                    'REQUESTED_QTY': float(row[3]) if row[3] else 0.0,
                    'QUANTITY_UM': row[4] if row[4] else '',
                    'PICK_LOC': row[5] if row[5] else '',
                    'PICK_ZONE': row[6] if row[6] else '',
                    'DATE_TIME_STAMP': date_str
                })
            except Exception as e:
                print(f"Ошибка обработки строки отклоненного заказа: {e}")
                continue
    
    print(f"[DEBUG] Детали отклоненных строк: {len(rejected_lines)} записей")
    return rejected_lines    