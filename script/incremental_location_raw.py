#!/usr/bin/env python3
"""
Инкрементальная загрузка LOCATION из ILS в raw_.LOCATION
Запускается каждые 30-60 секунд
Загружает только изменённые записи (по DATE_TIME_STAMP)
"""

import pymssql
from datetime import datetime, timedelta
import logging
import os
import sys

# === Параметры подключения к источнику ILS ===
SRC_SERVER = '10.7.0.248'
SRC_PORT = 1433
SRC_DATABASE = 'ils'
SRC_USER = 'manhreader'
SRC_PASSWORD = 'August2021'

# === Параметры подключения к целевой БД ===
DST_SERVER = '10.7.0.27'
DST_DATABASE = 'olap2_fixed'
DST_USER = 'sa'
DST_PASSWORD = 'Rdflhfn600'

# === Период инкрементальной загрузки ===
# Загружаем изменения за последние 5 минут (на случай задержек)
INCREMENT_BUFFER_MINUTES = 5

# === Логирование ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    log_file = os.path.join(LOG_DIR, f"incremental_location_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def get_last_timestamp(logger):
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
            # Если нет данных, возвращаем дату 30 дней назад
            logger.info("📍 В raw_.LOCATION нет данных, загружаем за 30 дней")
            return datetime.now() - timedelta(days=30)
        
        logger.info(f"📍 Последнее изменение в raw_.LOCATION: {last_ts}")
        return last_ts
        
    finally:
        conn.close()


def get_changed_locations(last_timestamp, logger):
    """Получить изменённые ячейки из основной базы ILS"""
    
    # Добавляем буфер на случай задержек
    buffer_timestamp = last_timestamp - timedelta(minutes=INCREMENT_BUFFER_MINUTES)
    
    # Форматируем дату для SQL
    buffer_str = buffer_timestamp.strftime('%Y-%m-%d %H:%M:%S')
    
    conn = pymssql.connect(
        server=SRC_SERVER,
        port=SRC_PORT,
        user=SRC_USER,
        password=SRC_PASSWORD,
        database=SRC_DATABASE,
        tds_version='7.0'
    )
    
    try:
        cursor = conn.cursor()
        
        # Загружаем все поля из LOCATION
        query = f"""
        SELECT
            LOCATION,
            WAREHOUSE,
            LOCATION_STS,
            LOCATION_TYPE,
            LOCATION_CLASS,
            LOCATING_ZONE,
            ALLOCATION_ZONE,
            WORK_ZONE,
            LOCATION_TEMPLATE,
            MULTI_ITEM,
            PICKING_SEQ,
            TEMPLATE_FIELD1,
            TEMPLATE_FIELD2,
            TEMPLATE_FIELD3,
            TEMPLATE_FIELD4,
            TEMPLATE_FIELD5,
            QTY_UM_LIST,
            DATE_TIME_STAMP,
            LAST_CYCLE_COUNT_DATE
        FROM dbo.LOCATION WITH (NOLOCK)
        WHERE
            DATE_TIME_STAMP > '{buffer_str}'
            AND LOCATION_STS IS NOT NULL
            AND LOCATION_STS != 'Frozen'
            AND (LOCATION_CLASS = 'Inventory' OR LOCATION_CLASS IS NULL)
            AND LOCATION_TYPE NOT IN ('Брак/бой DMG', 'Напольная', 'Улица KC', 'Ячейки KSP')
        ORDER BY DATE_TIME_STAMP
        """
        
        logger.info(f"📤 Запрос изменений с {buffer_timestamp}")
        cursor.execute(query)
        
        rows = []
        for row in cursor.fetchall():
            rows.append({
                'LOCATION': row[0],
                'WAREHOUSE': row[1],
                'LOCATION_STS': row[2],
                'LOCATION_TYPE': row[3],
                'LOCATION_CLASS': row[4],
                'LOCATING_ZONE': row[5],
                'ALLOCATION_ZONE': row[6],
                'WORK_ZONE': row[7],
                'LOCATION_TEMPLATE': row[8],
                'MULTI_ITEM': row[9],
                'PICKING_SEQ': row[10],
                'TEMPLATE_FIELD1': row[11],
                'TEMPLATE_FIELD2': row[12],
                'TEMPLATE_FIELD3': row[13],
                'TEMPLATE_FIELD4': row[14],
                'TEMPLATE_FIELD5': row[15],
                'QTY_UM_LIST': row[16],
                'DATE_TIME_STAMP': row[17],
                'LAST_CYCLE_COUNT_DATE': row[18]
            })
        
        logger.info(f"✅ Найдено изменений: {len(rows)}")
        return rows
        
    finally:
        conn.close()


def update_raw_locations(changes, logger):
    """Обновить raw_.LOCATION изменениями (UPSERT)"""
    
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
        
        inserted = 0
        updated = 0
        
        for row in changes:
            # Проверяем, есть ли запись
            cursor.execute("""
                SELECT COUNT(*) 
                FROM raw_.LOCATION 
                WHERE LOCATION = %s
            """, (row['LOCATION'],))
            
            exists = cursor.fetchone()[0]
            
            if exists > 0:
                # Обновить существующую запись
                update_query = """
                    UPDATE raw_.LOCATION
                    SET 
                        WAREHOUSE = %s,
                        LOCATION_STS = %s,
                        LOCATION_TYPE = %s,
                        LOCATION_CLASS = %s,
                        LOCATING_ZONE = %s,
                        ALLOCATION_ZONE = %s,
                        WORK_ZONE = %s,
                        LOCATION_TEMPLATE = %s,
                        MULTI_ITEM = %s,
                        PICKING_SEQ = %s,
                        TEMPLATE_FIELD1 = %s,
                        TEMPLATE_FIELD2 = %s,
                        TEMPLATE_FIELD3 = %s,
                        TEMPLATE_FIELD4 = %s,
                        TEMPLATE_FIELD5 = %s,
                        QTY_UM_LIST = %s,
                        DATE_TIME_STAMP = %s,
                        LAST_CYCLE_COUNT_DATE = %s
                    WHERE LOCATION = %s
                """
                
                cursor.execute(update_query, (
                    row['WAREHOUSE'],
                    row['LOCATION_STS'],
                    row['LOCATION_TYPE'],
                    row['LOCATION_CLASS'],
                    row['LOCATING_ZONE'],
                    row['ALLOCATION_ZONE'],
                    row['WORK_ZONE'],
                    row['LOCATION_TEMPLATE'],
                    row['MULTI_ITEM'],
                    row['PICKING_SEQ'],
                    row['TEMPLATE_FIELD1'],
                    row['TEMPLATE_FIELD2'],
                    row['TEMPLATE_FIELD3'],
                    row['TEMPLATE_FIELD4'],
                    row['TEMPLATE_FIELD5'],
                    row['QTY_UM_LIST'],
                    row['DATE_TIME_STAMP'],
                    row['LAST_CYCLE_COUNT_DATE'],
                    row['LOCATION']
                ))
                
                updated += 1
                
            else:
                # Вставить новую запись
                insert_query = """
                    INSERT INTO raw_.LOCATION 
                    (LOCATION, WAREHOUSE, LOCATION_STS, LOCATION_TYPE, LOCATION_CLASS,
                     LOCATING_ZONE, ALLOCATION_ZONE, WORK_ZONE, LOCATION_TEMPLATE,
                     MULTI_ITEM, PICKING_SEQ, TEMPLATE_FIELD1, TEMPLATE_FIELD2,
                     TEMPLATE_FIELD3, TEMPLATE_FIELD4, TEMPLATE_FIELD5,
                     QTY_UM_LIST, DATE_TIME_STAMP, LAST_CYCLE_COUNT_DATE)
                    VALUES 
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(insert_query, (
                    row['LOCATION'],
                    row['WAREHOUSE'],
                    row['LOCATION_STS'],
                    row['LOCATION_TYPE'],
                    row['LOCATION_CLASS'],
                    row['LOCATING_ZONE'],
                    row['ALLOCATION_ZONE'],
                    row['WORK_ZONE'],
                    row['LOCATION_TEMPLATE'],
                    row['MULTI_ITEM'],
                    row['PICKING_SEQ'],
                    row['TEMPLATE_FIELD1'],
                    row['TEMPLATE_FIELD2'],
                    row['TEMPLATE_FIELD3'],
                    row['TEMPLATE_FIELD4'],
                    row['TEMPLATE_FIELD5'],
                    row['QTY_UM_LIST'],
                    row['DATE_TIME_STAMP'],
                    row['LAST_CYCLE_COUNT_DATE']
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
    logger.info("=" * 70)
    logger.info("🚀 Начало инкрементальной загрузки LOCATION (raw)")
    logger.info("=" * 70)
    
    try:
        # 1. Получить последнее время изменения
        last_timestamp = get_last_timestamp(logger)
        
        # 2. Получить изменённые ячейки
        changes = get_changed_locations(last_timestamp, logger)
        
        # 3. Обновить raw_.LOCATION
        inserted, updated = update_raw_locations(changes, logger)
        
        logger.info("=" * 70)
        logger.info(f"✅ Загрузка завершена: {inserted + updated} записей")
        logger.info("=" * 70)
        
        return inserted + updated
        
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return 0


if __name__ == '__main__':
    total = run_incremental_load()
    sys.exit(0 if total > 0 else 1)
