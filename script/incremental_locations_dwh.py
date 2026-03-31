#!/usr/bin/env python3
"""
Инкрементальная загрузка dwh.fact_location_snapshot из raw_.LOCATION
Запускается каждые 30-60 секунд
Загружает только изменённые записи (по DATE_TIME_STAMP)
"""

import pymssql
from datetime import datetime, timedelta
import logging
import os
import sys

# === Параметры подключения к целевой БД ===
DST_SERVER = '10.7.0.27'
DST_DATABASE = 'olap2_fixed'
DST_USER = 'sa'
DST_PASSWORD = 'Rdflhfn600'

# === Период инкрементальной загрузки (в секундах) ===
# Загружаем изменения за последние 5 минут (на случай пропусков)
INCREMENT_BUFFER_MINUTES = 5

# === Логирование ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    log_file = os.path.join(LOG_DIR, f"incremental_locations_dwh_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def get_last_timestamp_from_raw(logger):
    """Получить последнее время изменения из raw_.LOCATION"""
    
    conn = pymssql.connect(
        server=DST_SERVER,
        user=DST_USER,
        password=DST_PASSWORD,
        database=DST_DATABASE,
        charset='UTF-8'
    )
    
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
            logger.warning("⚠️ В raw_.LOCATION нет данных!")
            return datetime.now() - timedelta(days=30)
        
        logger.info(f"📍 Последнее изменение в raw_.LOCATION: {last_ts}")
        return last_ts
        
    finally:
        conn.close()


def get_last_timestamp_from_dwh(logger):
    """Получить последнее время изменения из dwh.fact_location_snapshot"""
    
    conn = pymssql.connect(
        server=DST_SERVER,
        user=DST_USER,
        password=DST_PASSWORD,
        database=DST_DATABASE,
        charset='UTF-8'
    )
    
    try:
        cursor = conn.cursor()
        
        # Проверяем, есть ли поле last_modified
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'dwh' 
              AND TABLE_NAME = 'fact_location_snapshot'
              AND COLUMN_NAME = 'last_modified'
        """)
        
        has_last_modified = cursor.fetchone() is not None
        
        if has_last_modified:
            # Используем last_modified
            cursor.execute("""
                SELECT MAX(last_modified) 
                FROM dwh.fact_location_snapshot 
                WHERE last_modified IS NOT NULL
            """)
        else:
            # Используем DATE_TIME_STAMP из raw таблицы через JOIN
            cursor.execute("""
                SELECT MAX(r.DATE_TIME_STAMP) 
                FROM dwh.fact_location_snapshot d
                JOIN raw_.LOCATION r ON d.location = r.LOCATION
                WHERE r.DATE_TIME_STAMP IS NOT NULL
            """)
        
        result = cursor.fetchone()
        last_ts = result[0] if result and result[0] else None
        
        if last_ts is None:
            logger.info("📍 В dwh.fact_location_snapshot нет данных, загружаем всё")
            return None
        
        logger.info(f"📍 Последнее изменение в dwh.fact_location_snapshot: {last_ts}")
        return last_ts
        
    finally:
        conn.close()


def get_changed_locations_from_raw(last_timestamp, logger):
    """Получить изменённые ячейки из raw_.LOCATION"""
    
    # Добавляем буфер на случай задержек
    buffer_timestamp = last_timestamp - timedelta(minutes=INCREMENT_BUFFER_MINUTES) if last_timestamp else None
    
    conn = pymssql.connect(
        server=DST_SERVER,
        user=DST_USER,
        password=DST_PASSWORD,
        database=DST_DATABASE,
        charset='UTF-8'
    )
    
    try:
        cursor = conn.cursor()
        
        if buffer_timestamp:
            query = """
            SELECT
                LOCATION,
                LOCATION_TYPE,
                ALLOCATION_ZONE,
                WORK_ZONE,
                LOCATING_ZONE,
                LOCATION_STS,
                LOCATION_CLASS,
                DATE_TIME_STAMP
            FROM raw_.LOCATION
            WHERE
                DATE_TIME_STAMP > %s
                AND LOCATION_STS IS NOT NULL
                AND LOCATION_STS != 'Frozen'
                AND (LOCATION_CLASS = 'Inventory' OR LOCATION_CLASS IS NULL)
                AND LOCATION_TYPE NOT IN ('Брак/бой DMG', 'Напольная', 'Улица KC', 'Ячейки KSP')
            ORDER BY DATE_TIME_STAMP
            """
            
            logger.info(f"📤 Запрос изменений с {buffer_timestamp}")
            cursor.execute(query, (buffer_timestamp,))
        else:
            # Первая загрузка - все данные
            query = """
            SELECT
                LOCATION,
                LOCATION_TYPE,
                ALLOCATION_ZONE,
                WORK_ZONE,
                LOCATING_ZONE,
                LOCATION_STS,
                LOCATION_CLASS,
                DATE_TIME_STAMP
            FROM raw_.LOCATION
            WHERE
                LOCATION_STS IS NOT NULL
                AND LOCATION_STS != 'Frozen'
                AND (LOCATION_CLASS = 'Inventory' OR LOCATION_CLASS IS NULL)
                AND LOCATION_TYPE NOT IN ('Брак/бой DMG', 'Напольная', 'Улица KC', 'Ячейки KSP')
            ORDER BY DATE_TIME_STAMP
            """
            
            logger.info("📤 Первая загрузка - все данные")
            cursor.execute(query)
        
        rows = []
        for row in cursor.fetchall():
            # Определить статус по логике эталона
            location_sts = row[5]
            if location_sts == 'Empty':
                status = 'Empty'
            elif location_sts in ('Picking', 'Storage'):
                status = 'Occupied'
            else:
                status = 'Available'
            
            rows.append({
                'LOCATION': row[0],
                'LOCATION_TYPE': row[1],
                'ALLOCATION_ZONE': row[2],
                'WORK_ZONE': row[3],
                'LOCATING_ZONE': row[4],
                'LOCATION_STS': row[5],
                'LOCATION_CLASS': row[6],
                'DATE_TIME_STAMP': row[7],
                'STATUS': status
            })
        
        logger.info(f"✅ Найдено изменений: {len(rows)}")
        return rows
        
    finally:
        conn.close()


def update_dwh_location_snapshot(changes, logger, full_load=False):
    """Обновить dwh.fact_location_snapshot изменениями (UPSERT)"""
    
    if not changes:
        logger.info("ℹ️ Нет изменений для загрузки")
        return 0, 0
    
    conn = pymssql.connect(
        server=DST_SERVER,
        user=DST_USER,
        password=DST_PASSWORD,
        database=DST_DATABASE,
        charset='UTF-8'
    )
    
    try:
        cursor = conn.cursor()
        
        # Проверяем, есть ли поле last_modified
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'dwh' 
              AND TABLE_NAME = 'fact_location_snapshot'
              AND COLUMN_NAME = 'last_modified'
        """)
        
        has_last_modified = cursor.fetchone() is not None
        
        inserted = 0
        updated = 0
        
        for row in changes:
            # Проверяем, есть ли запись
            cursor.execute("""
                SELECT COUNT(*) 
                FROM dwh.fact_location_snapshot 
                WHERE location = %s
            """, (row['LOCATION'],))
            
            exists = cursor.fetchone()[0]
            
            if exists > 0:
                # Обновить существующую запись
                if has_last_modified:
                    update_query = """
                        UPDATE dwh.fact_location_snapshot
                        SET 
                            status = %s,
                            location_type = %s,
                            allocation_zone = %s,
                            work_zone = %s,
                            locating_zone = %s,
                            last_modified = %s,
                            date_key = CAST(GETDATE() AS DATE)
                        WHERE location = %s
                    """
                    
                    cursor.execute(update_query, (
                        row['STATUS'],
                        row['LOCATION_TYPE'],
                        row['ALLOCATION_ZONE'],
                        row['WORK_ZONE'],
                        row['LOCATING_ZONE'],
                        row['DATE_TIME_STAMP'],
                        row['LOCATION']
                    ))
                else:
                    update_query = """
                        UPDATE dwh.fact_location_snapshot
                        SET 
                            status = %s,
                            location_type = %s,
                            allocation_zone = %s,
                            work_zone = %s,
                            locating_zone = %s,
                            date_key = CAST(GETDATE() AS DATE)
                        WHERE location = %s
                    """
                    
                    cursor.execute(update_query, (
                        row['STATUS'],
                        row['LOCATION_TYPE'],
                        row['ALLOCATION_ZONE'],
                        row['WORK_ZONE'],
                        row['LOCATING_ZONE'],
                        row['LOCATION']
                    ))
                
                updated += 1
                
            else:
                # Вставить новую запись
                if has_last_modified:
                    insert_query = """
                        INSERT INTO dwh.fact_location_snapshot 
                        (date_key, location, status, location_type, locating_zone, 
                         allocation_zone, work_zone, source_system, last_modified)
                        VALUES 
                        (%s, %s, %s, %s, %s, %s, %s, 'WMS', %s)
                    """
                    
                    cursor.execute(insert_query, (
                        datetime.now().date(),
                        row['LOCATION'],
                        row['STATUS'],
                        row['LOCATION_TYPE'],
                        row['LOCATING_ZONE'],
                        row['ALLOCATION_ZONE'],
                        row['WORK_ZONE'],
                        row['DATE_TIME_STAMP']
                    ))
                else:
                    insert_query = """
                        INSERT INTO dwh.fact_location_snapshot 
                        (date_key, location, status, location_type, locating_zone, 
                         allocation_zone, work_zone, source_system)
                        VALUES 
                        (%s, %s, %s, %s, %s, %s, %s, 'WMS')
                    """
                    
                    cursor.execute(insert_query, (
                        datetime.now().date(),
                        row['LOCATION'],
                        row['STATUS'],
                        row['LOCATION_TYPE'],
                        row['LOCATING_ZONE'],
                        row['ALLOCATION_ZONE'],
                        row['WORK_ZONE']
                    ))
                
                inserted += 1
        
        conn.commit()
        
        logger.info(f"✅ Загружено: {inserted} новых, {updated} обновлённых")
        return inserted, updated
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Ошибка при обновлении: {e}")
        raise
        
    finally:
        conn.close()


def run_incremental_load():
    """Основная функция загрузки"""
    
    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("🚀 Начало инкрементальной загрузки LOCATION (DWH)")
    logger.info("=" * 60)
    
    try:
        # 1. Получить последнее время изменения из DWH
        last_timestamp_dwh = get_last_timestamp_from_dwh(logger)
        
        # 2. Получить последнее время изменения из raw
        last_timestamp_raw = get_last_timestamp_from_raw(logger)
        
        # 3. Получить изменённые ячейки из raw_.LOCATION
        changes = get_changed_locations_from_raw(last_timestamp_dwh, logger)
        
        # 4. Обновить dwh.fact_location_snapshot
        inserted, updated = update_dwh_location_snapshot(changes, logger, full_load=(last_timestamp_dwh is None))
        
        logger.info("=" * 60)
        logger.info(f"✅ Загрузка завершена: {inserted + updated} записей")
        logger.info("=" * 60)
        
        return inserted + updated
        
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return 0


if __name__ == '__main__':
    total = run_incremental_load()
    sys.exit(0 if total > 0 else 1)
