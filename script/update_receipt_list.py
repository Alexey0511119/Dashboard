#!/usr/bin/env python3
"""
Обновление данных списка приходов
Прямой запрос к ILS.dbo.RECEIPT_HEADER → dwh.receipt_list
Запускается каждые 5 минут
Полная перезапись таблицы (TRUNCATE + INSERT)
"""

import pymssql
from datetime import datetime, timedelta
import os
import sys

# === Параметры подключения к источнику ILS ===
ILS_SERVER = '10.7.0.248'
ILS_PORT = 1433
ILS_DATABASE = 'ils'
ILS_USER = 'manhreader'
ILS_PASSWORD = 'August2021'

# === Параметры подключения к целевой БД ===
ANALYTICS_SERVER = '10.7.0.27'
ANALYTICS_DATABASE = 'olap2_fixed'
ANALYTICS_USER = 'sa'
ANALYTICS_PASSWORD = 'Rdflhfn600'


def get_ils_connection():
    """Подключение к ILS"""
    return pymssql.connect(
        server=ILS_SERVER,
        port=ILS_PORT,
        user=ILS_USER,
        password=ILS_PASSWORD,
        database=ILS_DATABASE,
        tds_version='7.0'
    )


def get_analytics_connection():
    """Подключение к аналитической базе"""
    return pymssql.connect(
        server=ANALYTICS_SERVER,
        user=ANALYTICS_USER,
        password=ANALYTICS_PASSWORD,
        database=ANALYTICS_DATABASE,
        charset='UTF-8'
    )


def fetch_receipt_list_from_ils(log):
    """Загрузить список приходов из ILS"""

    conn = get_ils_connection()
    try:
        cursor = conn.cursor()

        # Запрос с фильтрами по статусам (как в ТЗ)
        query = """
        SELECT
            RECEIPT_ID,
            ERP_ORDER_NUM,
            SOURCE_NAME,
            RECEIPT_TYPE,
            CREATION_DATE_TIME_STAMP,
            TOTAL_LINES,
            TRAILING_STS,
            LEADING_STS
        FROM dbo.RECEIPT_HEADER WITH (NOLOCK)
        WHERE 
            -- Ожидает приема: TRAILING_STS = 100 AND LEADING_STS = 100
            (TRAILING_STS = 100 AND LEADING_STS = 100)
            -- Размещается: TRAILING_STS = 300
            OR (TRAILING_STS = 300)
            -- Принимается: TRAILING_STS IN (100, 200) AND LEADING_STS != 100
            OR (TRAILING_STS IN (100, 200) AND LEADING_STS NOT IN (100))
        ORDER BY CREATION_DATE_TIME_STAMP DESC
        """

        log(f"📤 Запрос к ILS.dbo.RECEIPT_HEADER...")
        cursor.execute(query)

        rows = []
        for row in cursor.fetchall():
            rows.append({
                'RECEIPT_ID': row[0] if row[0] else '',
                'ERP_ORDER_NUM': row[1] if row[1] else '',
                'SOURCE_NAME': row[2] if row[2] else '',
                'RECEIPT_TYPE': row[3] if row[3] else '',
                'CREATION_DATE_TIME_STAMP': row[4] if row[4] else None,
                'TOTAL_LINES': row[5] if row[5] else 0,
                'TRAILING_STS': row[6] if row[6] else 0,
                'LEADING_STS': row[7] if row[7] else 0
            })

        log(f"✅ Найдено приходов: {len(rows)}")
        return rows

    finally:
        conn.close()


def calculate_status_and_times(row):
    """Вычислить статус, время выполнения и просрочку"""
    
    trailing_sts = row.get('TRAILING_STS', 0)
    leading_sts = row.get('LEADING_STS', 0)
    creation_date = row.get('CREATION_DATE_TIME_STAMP')
    
    # Определяем статус
    if trailing_sts == 100 and leading_sts == 100:
        status = 'Ожидает приема'
    elif trailing_sts == 300:
        status = 'Размещается'
    elif trailing_sts in (100, 200) and leading_sts not in (100,):
        status = 'Принимается'
    else:
        status = 'Прочее'
    
    # Вычисляем время выполнения и просрочку
    if creation_date:
        now = datetime.now()
        creation_dt = creation_date if isinstance(creation_date, datetime) else datetime.strptime(str(creation_date), '%Y-%m-%d %H:%M:%S.%f')
        
        # Время выполнения (от создания до текущего времени)
        execution_delta = now - creation_dt
        execution_hours = int(execution_delta.total_seconds() // 3600)
        execution_minutes = int((execution_delta.total_seconds() % 3600) // 60)
        execution_time = f"{execution_hours}ч {execution_minutes}м"
        
        # Просрочится через (24 часа от создания)
        hours_since_creation = execution_delta.total_seconds() / 3600
        
        if hours_since_creation >= 24:
            overdue_in = 'Просрочено'
        else:
            remaining_hours = 24 - hours_since_creation
            remaining_h = int(remaining_hours)
            remaining_m = int((remaining_hours - remaining_h) * 60)
            overdue_in = f"{remaining_h}ч {remaining_m}м"
    else:
        execution_time = ''
        overdue_in = ''
    
    return status, execution_time, overdue_in


def update_dwh_receipt_list(rows, log):
    """Обновить dwh.receipt_list (ПОЛНАЯ ПЕРЕЗАПИСЬ)"""

    conn = get_analytics_connection()
    try:
        cursor = conn.cursor()

        # 1. Очистка таблицы (TRUNCATE)
        log("🗑️ Очистка dwh.receipt_list...")
        cursor.execute("TRUNCATE TABLE dwh.receipt_list")
        log("   ✅ Таблица очищена")

        # 2. Вставка данных
        if rows:
            log(f"➕ Вставка {len(rows)} записей...")

            insert_query = """
                INSERT INTO dwh.receipt_list
                (RECEIPT_ID, ERP_ORDER_NUM, SOURCE_NAME, RECEIPT_TYPE, 
                 CREATION_DATE_TIME_STAMP, TOTAL_LINES, TRAILING_STS, LEADING_STS,
                 STATUS, EXECUTION_TIME, OVERDUE_IN)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # Вставляем пакетами по 100 строк
            batch_size = 100
            inserted_count = 0

            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(rows) + batch_size - 1) // batch_size

                # Вычисляем статус и время для каждой строки
                batch_data = []
                for row in batch:
                    status, execution_time, overdue_in = calculate_status_and_times(row)
                    batch_data.append((
                        row['RECEIPT_ID'],
                        row['ERP_ORDER_NUM'],
                        row['SOURCE_NAME'],
                        row['RECEIPT_TYPE'],
                        row['CREATION_DATE_TIME_STAMP'],
                        row['TOTAL_LINES'],
                        row['TRAILING_STS'],
                        row['LEADING_STS'],
                        status,
                        execution_time,
                        overdue_in
                    ))

                cursor.executemany(insert_query, batch_data)
                conn.commit()

                inserted_count += len(batch)
                log(f"   Пакет {batch_num}/{total_batches}: {len(batch)} записей")

            log(f"✅ Вставлено записей: {inserted_count}")
        else:
            log("ℹ️ Нет данных для вставки")

        return True

    except Exception as e:
        conn.rollback()
        log(f"❌ Ошибка при обновлении: {e}")
        raise
    finally:
        conn.close()


def verify_data(log):
    """Проверить данные после загрузки"""

    conn = get_analytics_connection()
    try:
        cursor = conn.cursor()

        # Проверить количество записей
        cursor.execute("SELECT COUNT(*) FROM dwh.receipt_list")
        count = cursor.fetchone()[0]
        log(f"📊 В таблице: {count:,} записей")

        # Проверить последние данные
        cursor.execute("""
            SELECT TOP 1 RECEIPT_ID, CREATION_DATE_TIME_STAMP, STATUS
            FROM dwh.receipt_list
            ORDER BY CREATION_DATE_TIME_STAMP DESC
        """)
        row = cursor.fetchone()
        if row:
            log(f"📍 Последняя запись: {row[0]} ({row[1]}) - {row[2]}")

        # Проверка по статусам
        cursor.execute("""
            SELECT STATUS, COUNT(*) as cnt
            FROM dwh.receipt_list
            GROUP BY STATUS
            ORDER BY cnt DESC
        """)
        status_counts = cursor.fetchall()
        if status_counts:
            log("📊 Распределение по статусам:")
            for status_row in status_counts:
                log(f"   {status_row[0]}: {status_row[1]}")

        return True

    except Exception as e:
        log(f"❌ Ошибка проверки: {e}")
        return False
    finally:
        conn.close()


def run_update():
    """Основная функция обновления"""

    # Простое логирование в stdout
    def log(message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{timestamp} - INFO - {message}")

    log("=" * 70)
    log("🚀 Обновление списка приходов (receipt_list)")
    log("=" * 70)
    log(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)

    try:
        # 1. Загрузить данные из ILS
        rows = fetch_receipt_list_from_ils(log)

        # 2. Обновить dwh.receipt_list
        update_dwh_receipt_list(rows, log)

        # 3. Проверить данные
        verify_data(log)

        log("=" * 70)
        log("✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО")
        log("=" * 70)

        return True

    except Exception as e:
        log(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_update()
    sys.exit(0 if success else 1)
