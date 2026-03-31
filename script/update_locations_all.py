#!/usr/bin/env python3
"""
Обновление данных о ячейках (LOCATION)
1. Загрузка из ILS в raw_.LOCATION (инкрементально)
2. Обновление dwh.fact_location_snapshot из raw_.LOCATION
Запускается в cron каждые 1 минуту
"""

import pymssql
from datetime import datetime, timedelta
import logging
import os
import sys

# === Параметры подключения ===
ILS_SERVER = '10.7.0.248'
ILS_PORT = 1433
ILS_DATABASE = 'ils'
ILS_USER = 'manhreader'
ILS_PASSWORD = 'August2021'

ANALYTICS_SERVER = '10.7.0.27'
ANALYTICS_DATABASE = 'olap2_fixed'
ANALYTICS_USER = 'sa'
ANALYTICS_PASSWORD = 'Rdflhfn600'

# === Буфер времени (минут) ===
BUFFER_MINUTES = 5

# === Логирование ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    log_file = os.path.join(LOG_DIR, f"update_locations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def get_analytics_connection():
    """Подключение к аналитической базе"""
    return pymssql.connect(
        server=ANALYTICS_SERVER,
        user=ANALYTICS_USER,
        password=ANALYTICS_PASSWORD,
        database=ANALYTICS_DATABASE,
        charset='UTF-8'
    )


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


def get_last_timestamp_raw(logger):
    """Получить последнее время изменения из raw_.LOCATION"""
    conn = get_analytics_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MAX(DATE_TIME_STAMP) 
            FROM raw_.LOCATION 
            WHERE DATE_TIME_STAMP IS NOT NULL
        """)
        result = cursor.fetchone()
        last_ts = result[0] if result and result[0] else None
        
        if last_ts is None:
            logger.info("📍 В raw_.LOCATION нет данных, загружаем за 30 дней")
            return datetime.now() - timedelta(days=30)
        
        logger.info(f"📍 Последнее изменение в raw_.LOCATION: {last_ts}")
        return last_ts
    finally:
        conn.close()


def load_changes_from_ils(last_timestamp, logger):
    """Загрузить изменения из ILS"""
    buffer_timestamp = last_timestamp - timedelta(minutes=BUFFER_MINUTES)
    buffer_str = buffer_timestamp.strftime('%Y-%m-%d %H:%M:%S')
    
    conn = get_ils_connection()
    try:
        cursor = conn.cursor()
        
        query = f"""
        SELECT
            LOCATION, WAREHOUSE, LOCATION_STS, LOCATION_TYPE, LOCATION_CLASS,
            LOCATING_ZONE, ALLOCATION_ZONE, WORK_ZONE, LOCATION_TEMPLATE,
            MULTI_ITEM, PICKING_SEQ, TEMPLATE_FIELD1, TEMPLATE_FIELD2,
            TEMPLATE_FIELD3, TEMPLATE_FIELD4, TEMPLATE_FIELD5,
            QTY_UM_LIST, DATE_TIME_STAMP, LAST_CYCLE_COUNT_DATE
        FROM dbo.LOCATION WITH (NOLOCK)
        WHERE
            DATE_TIME_STAMP > '{buffer_str}'
            AND LOCATION_STS IS NOT NULL
            AND LOCATION_STS != 'Frozen'
            AND (LOCATION_CLASS = 'Inventory' OR LOCATION_CLASS IS NULL)
            AND LOCATION_TYPE NOT IN ('Брак/бой DMG', 'Напольная', 'Улица KC', 'Ячейки KSP')
        ORDER BY DATE_TIME_STAMP
        """
        
        logger.info(f"📤 Запрос изменений из ILS с {buffer_timestamp}")
        cursor.execute(query)
        
        rows = []
        for row in cursor.fetchall():
            rows.append({
                'LOCATION': row[0], 'WAREHOUSE': row[1], 'LOCATION_STS': row[2],
                'LOCATION_TYPE': row[3], 'LOCATION_CLASS': row[4],
                'LOCATING_ZONE': row[5], 'ALLOCATION_ZONE': row[6], 'WORK_ZONE': row[7],
                'LOCATION_TEMPLATE': row[8], 'MULTI_ITEM': row[9], 'PICKING_SEQ': row[10],
                'TEMPLATE_FIELD1': row[11], 'TEMPLATE_FIELD2': row[12],
                'TEMPLATE_FIELD3': row[13], 'TEMPLATE_FIELD4': row[14],
                'TEMPLATE_FIELD5': row[15], 'QTY_UM_LIST': row[16],
                'DATE_TIME_STAMP': row[17], 'LAST_CYCLE_COUNT_DATE': row[18]
            })
        
        logger.info(f"✅ Найдено изменений из ILS: {len(rows)}")
        return rows
    finally:
        conn.close()


def update_raw_locations(changes, logger):
    """Обновить raw_.LOCATION (UPSERT)"""
    if not changes:
        logger.info("ℹ️ Нет изменений для raw_.LOCATION")
        return 0, 0
    
    conn = get_analytics_connection()
    try:
        cursor = conn.cursor()
        inserted = 0
        updated = 0
        
        for row in changes:
            cursor.execute("SELECT COUNT(*) FROM raw_.LOCATION WHERE LOCATION = %s", (row['LOCATION'],))
            exists = cursor.fetchone()[0]
            
            if exists > 0:
                cursor.execute("""
                    UPDATE raw_.LOCATION SET
                        WAREHOUSE=%s, LOCATION_STS=%s, LOCATION_TYPE=%s, LOCATION_CLASS=%s,
                        LOCATING_ZONE=%s, ALLOCATION_ZONE=%s, WORK_ZONE=%s, LOCATION_TEMPLATE=%s,
                        MULTI_ITEM=%s, PICKING_SEQ=%s, TEMPLATE_FIELD1=%s, TEMPLATE_FIELD2=%s,
                        TEMPLATE_FIELD3=%s, TEMPLATE_FIELD4=%s, TEMPLATE_FIELD5=%s,
                        QTY_UM_LIST=%s, DATE_TIME_STAMP=%s, LAST_CYCLE_COUNT_DATE=%s
                    WHERE LOCATION=%s
                """, (
                    row['WAREHOUSE'], row['LOCATION_STS'], row['LOCATION_TYPE'], row['LOCATION_CLASS'],
                    row['LOCATING_ZONE'], row['ALLOCATION_ZONE'], row['WORK_ZONE'], row['LOCATION_TEMPLATE'],
                    row['MULTI_ITEM'], row['PICKING_SEQ'], row['TEMPLATE_FIELD1'], row['TEMPLATE_FIELD2'],
                    row['TEMPLATE_FIELD3'], row['TEMPLATE_FIELD4'], row['TEMPLATE_FIELD5'],
                    row['QTY_UM_LIST'], row['DATE_TIME_STAMP'], row['LAST_CYCLE_COUNT_DATE'],
                    row['LOCATION']
                ))
                updated += 1
            else:
                cursor.execute("""
                    INSERT INTO raw_.LOCATION (LOCATION, WAREHOUSE, LOCATION_STS, LOCATION_TYPE, LOCATION_CLASS,
                        LOCATING_ZONE, ALLOCATION_ZONE, WORK_ZONE, LOCATION_TEMPLATE, MULTI_ITEM, PICKING_SEQ,
                        TEMPLATE_FIELD1, TEMPLATE_FIELD2, TEMPLATE_FIELD3, TEMPLATE_FIELD4, TEMPLATE_FIELD5,
                        QTY_UM_LIST, DATE_TIME_STAMP, LAST_CYCLE_COUNT_DATE)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    row['LOCATION'], row['WAREHOUSE'], row['LOCATION_STS'], row['LOCATION_TYPE'], row['LOCATION_CLASS'],
                    row['LOCATING_ZONE'], row['ALLOCATION_ZONE'], row['WORK_ZONE'], row['LOCATION_TEMPLATE'],
                    row['MULTI_ITEM'], row['PICKING_SEQ'], row['TEMPLATE_FIELD1'], row['TEMPLATE_FIELD2'],
                    row['TEMPLATE_FIELD3'], row['TEMPLATE_FIELD4'], row['TEMPLATE_FIELD5'],
                    row['QTY_UM_LIST'], row['DATE_TIME_STAMP'], row['LAST_CYCLE_COUNT_DATE']
                ))
                inserted += 1
        
        conn.commit()
        logger.info(f"✅ raw_.LOCATION: {inserted} новых, {updated} обновлённых")
        return inserted, updated
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Ошибка обновления raw_.LOCATION: {e}")
        raise
    finally:
        conn.close()


def update_dwh_snapshot(logger):
    """Обновить dwh.fact_location_snapshot через процедуру"""
    conn = get_analytics_connection()
    try:
        cursor = conn.cursor()
        logger.info("🔄 Вызов процедуры sp_update_location_snapshot...")
        cursor.execute("EXEC dwh.sp_update_location_snapshot @buffer_minutes = %s, @debug = 0", (BUFFER_MINUTES,))
        conn.commit()
        logger.info("✅ dwh.fact_location_snapshot обновлена")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Ошибка обновления dwh.fact_location_snapshot: {e}")
        raise
    finally:
        conn.close()


def verify_data(logger):
    """Проверить данные"""
    conn = get_analytics_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM raw_.LOCATION")
        raw_count = cursor.fetchone()[0]
        logger.info(f"📊 raw_.LOCATION: {raw_count:,} записей")
        
        cursor.execute("SELECT status, COUNT(*) FROM dwh.fact_location_snapshot GROUP BY status")
        for row in cursor.fetchall():
            logger.info(f"📊 {row[0]}: {row[1]:,}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка проверки: {e}")
        return False
    finally:
        conn.close()


def run_update():
    """Основная функция"""
    logger = setup_logging()
    logger.info("=" * 70)
    logger.info("🚀 Обновление LOCATION (ILS → raw → DWH)")
    logger.info("=" * 70)
    logger.info(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Буфер: {BUFFER_MINUTES} мин")
    logger.info("=" * 70)
    
    try:
        # 1. Загрузка из ILS в raw_.LOCATION
        last_timestamp = get_last_timestamp_raw(logger)
        changes = load_changes_from_ils(last_timestamp, logger)
        update_raw_locations(changes, logger)
        
        # 2. Обновление dwh.fact_location_snapshot
        update_dwh_snapshot(logger)
        
        # 3. Проверка
        verify_data(logger)
        
        logger.info("=" * 70)
        logger.info("✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО")
        logger.info("=" * 70)
        return True
        
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_update()
    sys.exit(0 if success else 1)
