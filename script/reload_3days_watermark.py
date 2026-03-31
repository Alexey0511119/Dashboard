#!/usr/bin/env python3
"""
Обновляет сырые данные в raw_.таблицах за последние 10 минут (Watermark).
Запускается каждые 10 минут как часть 3-дневного пайплайна.

В отличие от полной выгрузки, этот скрипт выгружает ТОЛЬКО изменённые данные
с последнего запуска, что ускоряет работу в 5-10 раз.
"""
import pymssql
from datetime import datetime, timedelta
import logging
import os
import sys
import time

# === Конфигурация ===
SRC_SERVER = '10.7.0.248'
SRC_PORT = 1433
SRC_DATABASE_ILS = 'ils'
SRC_DATABASE_SK = 'sk'
SRC_USER = 'manhreader'
SRC_PASSWORD = 'August2021'

DST_SERVER = '10.7.0.27'
DST_DATABASE = 'olap2_fixed'
DST_USER = 'sa'
DST_PASSWORD = 'Rdflhfn600'

# Логирование
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    log_file = os.path.join(LOG_DIR, f"reload_3days_watermark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# === СПИСОК ТАБЛИЦ ===
FACTS = [
    # Существующие таблицы из ils (16 шт)
    'ORDER_DETAIL',
    'ORDER_HEADER',
    'RECEIPT_DETAIL',
    'RECEIPT_HEADER',
    'SHIPMENT_DETAIL',
    'SHIPMENT_HEADER',
    'TRANSACTION_HISTORY',
    'WORK_INSTRUCTION_VIEW2',
    'DOWNLOAD_ORDER_DETAIL',
    'DOWNLOAD_ORDER_HEADER',
    'DOWNLOAD_RECEIPT_DETAIL',
    'DOWNLOAD_RECEIPT_HEADER',
    'UPLOAD_ORDER_DETAIL',
    'UPLOAD_ORDER_HEADER',
    'UPLOAD_RECEIPT_DETAIL',
    'UPLOAD_RECEIPT_HEADER',
    # НОВЫЕ таблицы из ils (3 шт)
    'CYCLE_COUNT_REQUEST',
    'labor_management_detail_view',
    'UPLOAD_RECEIPT_CONTAINER',
    # НОВЫЕ таблицы из sk (2 шт)
    'eks_peremer_ZX_KPP',
    'Shtraf_Edit'
]

# === ПОЛЯ ДАТЫ ДЛЯ КАЖДОЙ ТАБЛИЦЫ ===
def get_date_field(table_name):
    """
    Возвращает поле даты и условие WHERE для таблицы.
    Для CYCLE_COUNT_REQUEST — 3 поля через OR.
    """
    if table_name == 'CYCLE_COUNT_REQUEST':
        # 3 поля даты через OR
        return {
            'fields': ['CREATE_DATE_TIME', 'CLOSED_DATE_TIME', 'COUNTED_DATE_TIME'],
            'where': """
                WHERE CREATE_DATE_TIME >= %(last_run)s
                   OR CLOSED_DATE_TIME >= %(last_run)s
                   OR COUNTED_DATE_TIME >= %(last_run)s
            """,
            'date_field': 'CREATE_DATE_TIME'  # Основное поле для индекса
        }
    elif table_name in ['eks_peremer_ZX_KPP', 'Shtraf_Edit']:
        # Нижний регистр (таблицы из sk)
        return {
            'fields': ['date_time_stamp'],
            'where': "WHERE date_time_stamp >= %(last_run)s",
            'date_field': 'date_time_stamp'
        }
    elif table_name == 'labor_management_detail_view':
        # View с нижним регистром
        return {
            'fields': ['date_time_stamp'],
            'where': "WHERE date_time_stamp >= %(last_run)s",
            'date_field': 'date_time_stamp'
        }
    else:
        # Стандартное поле DATE_TIME_STAMP
        return {
            'fields': ['DATE_TIME_STAMP'],
            'where': "WHERE DATE_TIME_STAMP >= %(last_run)s",
            'date_field': 'DATE_TIME_STAMP'
        }

def get_target_table_name(table_name):
    """Возвращает имя целевой таблицы в схеме raw_"""
    if table_name == 'labor_management_detail_view':
        return 'labor_management'
    return table_name

def get_source_database(table_name):
    """Определяет, из какой БД читать данные"""
    if table_name in ['eks_peremer_ZX_KPP', 'Shtraf_Edit']:
        return 'sk'
    return 'ils'

# === WATERMARK ФУНКЦИИ ===
def init_watermark_table(logger):
    """Создаёт схему etl и таблицу watermark, если не существует"""
    conn = get_dst_connection()
    cursor = conn.cursor()
    
    try:
        # Сначала создаём схему etl, если не существует
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'etl')
            BEGIN
                EXEC('CREATE SCHEMA etl')
            END
        """)
        conn.commit()
        logger.info("✅ Схема etl создана")
        
        # Теперь создаём таблицу watermark
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables 
                          WHERE name = 'watermark' AND schema_id = SCHEMA_ID('etl'))
            BEGIN
                CREATE TABLE etl.watermark (
                    table_name NVARCHAR(100) PRIMARY KEY,
                    last_run_time DATETIME NOT NULL,
                    last_success_time DATETIME NULL,
                    rows_processed INT NULL,
                    created_date DATETIME DEFAULT GETDATE(),
                    modified_date DATETIME DEFAULT GETDATE()
                )
                
                -- Инициализируем все таблицы (3 дня назад)
                INSERT INTO etl.watermark (table_name, last_run_time)
                VALUES 
                    ('ORDER_DETAIL', DATEADD(DAY, -3, GETDATE())),
                    ('ORDER_HEADER', DATEADD(DAY, -3, GETDATE())),
                    ('RECEIPT_DETAIL', DATEADD(DAY, -3, GETDATE())),
                    ('RECEIPT_HEADER', DATEADD(DAY, -3, GETDATE())),
                    ('SHIPMENT_DETAIL', DATEADD(DAY, -3, GETDATE())),
                    ('SHIPMENT_HEADER', DATEADD(DAY, -3, GETDATE())),
                    ('TRANSACTION_HISTORY', DATEADD(DAY, -3, GETDATE())),
                    ('WORK_INSTRUCTION_VIEW2', DATEADD(DAY, -3, GETDATE())),
                    ('DOWNLOAD_ORDER_DETAIL', DATEADD(DAY, -3, GETDATE())),
                    ('DOWNLOAD_ORDER_HEADER', DATEADD(DAY, -3, GETDATE())),
                    ('DOWNLOAD_RECEIPT_DETAIL', DATEADD(DAY, -3, GETDATE())),
                    ('DOWNLOAD_RECEIPT_HEADER', DATEADD(DAY, -3, GETDATE())),
                    ('UPLOAD_ORDER_DETAIL', DATEADD(DAY, -3, GETDATE())),
                    ('UPLOAD_ORDER_HEADER', DATEADD(DAY, -3, GETDATE())),
                    ('UPLOAD_RECEIPT_DETAIL', DATEADD(DAY, -3, GETDATE())),
                    ('UPLOAD_RECEIPT_HEADER', DATEADD(DAY, -3, GETDATE())),
                    ('CYCLE_COUNT_REQUEST', DATEADD(DAY, -3, GETDATE())),
                    ('labor_management', DATEADD(DAY, -3, GETDATE())),
                    ('UPLOAD_RECEIPT_CONTAINER', DATEADD(DAY, -3, GETDATE())),
                    ('eks_peremer_ZX_KPP', DATEADD(DAY, -3, GETDATE())),
                    ('Shtraf_Edit', DATEADD(DAY, -3, GETDATE()))
            END
        """)
        conn.commit()
        logger.info("✅ Таблица etl.watermark создана/проверена")
    except Exception as e:
        logger.error(f"❌ Ошибка создания watermark: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_watermark(table_name, logger):
    """Получает время последнего успешного запуска"""
    conn = get_dst_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT last_run_time 
            FROM etl.watermark 
            WHERE table_name = %s
        """, (table_name,))
        
        row = cursor.fetchone()
        if row:
            return row[0]
        else:
            # Если записи нет — возвращаем 3 дня назад
            return datetime.now() - timedelta(days=3)
    finally:
        conn.close()

def set_watermark(table_name, rows_processed, logger, success=True):
    """Обновляет время последнего запуска"""
    conn = get_dst_connection()
    cursor = conn.cursor()
    
    try:
        if success:
            cursor.execute("""
                MERGE etl.watermark AS target
                USING (SELECT %s AS table_name) AS source
                ON (target.table_name = source.table_name)
                WHEN MATCHED THEN
                    UPDATE SET 
                        last_run_time = GETDATE(),
                        last_success_time = GETDATE(),
                        rows_processed = %s,
                        modified_date = GETDATE()
                WHEN NOT MATCHED THEN
                    INSERT (table_name, last_run_time, last_success_time, rows_processed)
                    VALUES (%s, GETDATE(), GETDATE(), %s);
            """, (table_name, rows_processed, table_name, rows_processed))
        else:
            cursor.execute("""
                UPDATE etl.watermark 
                SET last_run_time = GETDATE(),
                    modified_date = GETDATE()
                WHERE table_name = %s
            """, (table_name,))
        
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Ошибка обновления watermark: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_dst_connection():
    """Подключение к целевой БД"""
    return pymssql.connect(
        server=DST_SERVER,
        user=DST_USER,
        password=DST_PASSWORD,
        database=DST_DATABASE,
        charset='UTF-8'
    )

def get_src_connection(database):
    """Подключение к источнику"""
    return pymssql.connect(
        server=SRC_SERVER,
        port=SRC_PORT,
        user=SRC_USER,
        password=SRC_PASSWORD,
        database=database,
        tds_version='7.0'
    )

# === ЗАРЕЗЕРВИРОВАННЫЕ СЛОВА ===
RESERVED_KEYWORDS = {
    'user', 'out', 'order', 'group', 'table', 'key', 'primary', 'foreign',
    'join', 'inner', 'outer', 'left', 'right', 'full', 'cross', 'on',
    'where', 'having', 'select', 'insert', 'update', 'delete', 'drop',
    'create', 'alter', 'view', 'procedure', 'function', 'trigger',
    'index', 'column', 'schema', 'database', 'server', 'login', 'role'
}

def escape_column_name(column_name):
    """Экранирует зарезервированные слова"""
    if column_name.lower() in RESERVED_KEYWORDS:
        return f"[{column_name}]"
    return column_name

def get_primary_key(table_name):
    """Возвращает имя первичного ключа для таблицы"""
    # Словарь первичных ключей для основных таблиц
    primary_keys = {
        'ORDER_DETAIL': 'ORDER_ID',  # Может быть составной ключ
        'ORDER_HEADER': 'ORDER_ID',
        'RECEIPT_DETAIL': 'RECEIPT_ID',
        'RECEIPT_HEADER': 'RECEIPT_ID',
        'SHIPMENT_DETAIL': 'SHIPMENT_ID',
        'SHIPMENT_HEADER': 'SHIPMENT_ID',
        'TRANSACTION_HISTORY': 'TRANSACTION_ID',
        'WORK_INSTRUCTION_VIEW2': 'INTERNAL_NUM',
        'DOWNLOAD_ORDER_DETAIL': 'ORDER_ID',
        'DOWNLOAD_ORDER_HEADER': 'ORDER_ID',
        'DOWNLOAD_RECEIPT_DETAIL': 'RECEIPT_ID',
        'DOWNLOAD_RECEIPT_HEADER': 'RECEIPT_ID',
        'UPLOAD_ORDER_DETAIL': 'ORDER_ID',
        'UPLOAD_ORDER_HEADER': 'ORDER_ID',
        'UPLOAD_RECEIPT_DETAIL': 'RECEIPT_ID',
        'UPLOAD_RECEIPT_HEADER': 'RECEIPT_ID',
        'CYCLE_COUNT_REQUEST': 'REQUEST_ID',
        'labor_management': 'USER_NAME',  # View, может не иметь PK
        'UPLOAD_RECEIPT_CONTAINER': 'CONTAINER_ID',
        'eks_peremer_ZX_KPP': 'id',  # Предположительно
        'Shtraf_Edit': 'id'  # Предположительно
    }
    return primary_keys.get(table_name)

# === ОСНОВНАЯ ФУНКЦИЯ ОБНОВЛЕНИЯ ===
def reload_table_watermark(table_name, logger):
    """
    Обновляет таблицу только с изменениями с последнего запуска (Watermark).
    """
    source_db = get_source_database(table_name)
    target_table = get_target_table_name(table_name)
    date_info = get_date_field(table_name)
    date_field = date_info['date_field']
    where_clause = date_info['where']
    
    # Получаем watermark
    last_run = get_watermark(table_name, logger)
    
    logger.info("")
    logger.info(f"{'='*60}")
    logger.info(f"ТАБЛИЦА: {table_name} → raw_.{target_table}")
    logger.info(f"{'='*60}")
    logger.info(f"   📁 Источник: {source_db}")
    logger.info(f"   📅 Поле даты: {date_field}")
    logger.info(f"   ⏰ Last run: {last_run.strftime('%Y-%m-%d %H:%M:%S')}")
    
    step_start = datetime.now()
    
    try:
        # Подключение к источнику
        logger.info(f"   🔌 Шаг 1/6: Подключение к источнику ({source_db})...")
        src = get_src_connection(source_db)
        logger.info(f"      ✅ Подключено")
        
        # Подключение к целевой БД
        logger.info(f"   🔌 Шаг 2/6: Подключение к целевой БД...")
        dst = get_dst_connection()
        logger.info(f"      ✅ Подключено")
        
        src_cursor = src.cursor()
        dst_cursor = dst.cursor()
        
        # Получаем колонки
        logger.info(f"   📋 Шаг 3/6: Получение структуры таблицы...")
        dst_cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'raw_' AND TABLE_NAME = %s
            AND COLUMN_NAME NOT IN ('ROW_ID', 'row_hash')
            ORDER BY ORDINAL_POSITION
        """, (target_table,))
        
        columns = [row[0] for row in dst_cursor.fetchall()]
        if not columns:
            logger.warning(f"   ⚠️ Колонки не найдены в raw_.{target_table}")
            return True
        
        escaped_columns = [escape_column_name(col) for col in columns]
        column_list = ", ".join(escaped_columns)
        src_column_list = ", ".join(escaped_columns)
        logger.info(f"      ✅ Найдено колонок: {len(columns)}")
        
        # Читаем данные из источника (только изменения!)
        logger.info(f"   📥 Шаг 4/6: Чтение изменений с {last_run.strftime('%Y-%m-%d %H:%M:%S')}...")
        
        if table_name == 'labor_management_detail_view':
            from_table = 'labor_management_detail_view'
        else:
            from_table = table_name
        
        query = f"""
            SELECT {src_column_list}
            FROM {from_table}
            {where_clause}
        """
        
        logger.info(f"      Выполняется запрос...")
        read_start = datetime.now()
        src_cursor.execute(query, {'last_run': last_run})
        rows = src_cursor.fetchall()
        read_end = datetime.now()
        read_duration = (read_end - read_start).total_seconds()
        
        row_count = len(rows)
        logger.info(f"      ✅ Прочитано строк: {row_count:,} (за {read_duration:.2f} сек)")
        
        # Если нет изменений — пропускаем
        if row_count == 0:
            logger.info(f"      ℹ️ Нет изменений с последнего запуска")
            set_watermark(table_name, 0, logger, success=True)
            src.close()
            dst.close()
            return True
        
        # Определяем первичный ключ для таблицы
        pk_column = get_primary_key(table_name)
        
        # Удаляем существующие записи (по PK)
        if pk_column:
            logger.info(f"      🗑️ Шаг 5/6: Удаление существующих записей...")
            delete_start = datetime.now()
            
            # Получаем ID записей для удаления
            delete_ids = [row[columns.index(pk_column)] for row in rows if pk_column in columns]
            
            if delete_ids:
                # Удаляем пакетами по 10000
                batch_size = 10000
                deleted_count = 0
                
                for i in range(0, len(delete_ids), batch_size):
                    batch_ids = delete_ids[i:i + batch_size]
                    placeholders = ",".join(["%s"] * len(batch_ids))
                    delete_query = f"""
                        DELETE FROM raw_.{target_table}
                        WHERE {escape_column_name(pk_column)} IN ({placeholders})
                    """
                    dst_cursor.execute(delete_query, batch_ids)
                    deleted_count += dst_cursor.rowcount
                    dst.commit()
                
                delete_end = datetime.now()
                delete_duration = (delete_end - delete_start).total_seconds()
                logger.info(f"         ✅ Удалено записей: {deleted_count:,} (за {delete_duration:.2f} сек)")
            else:
                logger.info(f"         ℹ️ Нет записей для удаления")
                dst.commit()
        else:
            logger.info(f"      ℹ️ Первичный ключ не найден, удаление пропускается")
        # Отключаем некластеризованные индексы (для больших таблиц)
        indexes_disabled = False
        if row_count > 10000:
            try:
                logger.info(f"      ⚙️ Шаг 6/6: Отключение некластеризованных индексов...")
                dst_cursor.execute("""
                    SELECT name FROM sys.indexes 
                    WHERE object_id = OBJECT_ID(%s) 
                    AND type_desc = 'NONCLUSTERED'
                    AND is_primary_key = 0
                """, (target_table,))
                
                indexes_to_disable = [row[0] for row in dst_cursor.fetchall()]
                
                if indexes_to_disable:
                    for idx_name in indexes_to_disable:
                        dst_cursor.execute(f"ALTER INDEX {idx_name} ON raw_.{target_table} DISABLE")
                    dst.commit()
                    indexes_disabled = True
                    logger.info(f"      ✅ Отключено индексов: {len(indexes_to_disable)}")
                else:
                    logger.info(f"      ℹ️ Некластеризованные индексы не найдены")
            except Exception as idx_error:
                logger.warning(f"      ⚠️ Не удалось отключить индексы: {idx_error}")
        
        # Вставляем/обновляем данные (MERGE)
        logger.info(f"   📊 Шаг 6/6: Вставка/обновление {row_count:,} строк...")
        
        placeholders = ",".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO raw_.{target_table} ({column_list}) VALUES ({placeholders})"
        
        insert_start = datetime.now()
        
        # Вставляем все данные за один вызов
        dst_cursor.executemany(insert_sql, rows)
        dst.commit()
        
        insert_end = datetime.now()
        insert_duration = (insert_end - insert_start).total_seconds()
        rows_per_sec = row_count / insert_duration if insert_duration > 0 else 0
        
        logger.info(f"      ✅ Вставлено: {row_count:,} строк за {insert_duration:.2f} сек ({rows_per_sec:,.0f} строк/сек)")
        
        # Включаем индексы обратно
        if indexes_disabled:
            try:
                logger.info(f"      ⚙️ Включение некластеризованных индексов...")
                dst_cursor.execute("""
                    SELECT name FROM sys.indexes 
                    WHERE object_id = OBJECT_ID(%s) 
                    AND type_desc = 'NONCLUSTERED'
                    AND is_primary_key = 0
                    AND is_disabled = 1
                """, (target_table,))
                
                indexes_to_enable = [row[0] for row in dst_cursor.fetchall()]
                
                if indexes_to_enable:
                    for idx_name in indexes_to_enable:
                        dst_cursor.execute(f"ALTER INDEX {idx_name} ON raw_.{target_table} REBUILD")
                    dst.commit()
                    logger.info(f"      ✅ Включено индексов: {len(indexes_to_enable)}")
            except Exception as idx_error:
                logger.error(f"      ❌ Ошибка включения индексов: {idx_error}")
        
        # Обновляем watermark
        set_watermark(table_name, row_count, logger, success=True)
        
        # Итоги
        step_end = datetime.now()
        step_duration = (step_end - step_start).total_seconds()
        logger.info(f"")
        logger.info(f"   ⏱️ ОБЩЕЕ ВРЕМЯ: {step_duration:.2f} сек ({step_duration/60:.2f} мин)")
        logger.info(f"{'='*60}")
        
        src.close()
        dst.close()
        
        return True
        
    except Exception as e:
        logger.error(f"   ❌ ОШИБКА: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Обновляем watermark с ошибкой
        set_watermark(table_name, 0, logger, success=False)
        
        return False

def main():
    logger = setup_logging()
    
    logger.info("=" * 80)
    logger.info("🚀 WATERMARK: ОБНОВЛЕНИЕ ДАННЫХ (ТОЛЬКО ИЗМЕНЕНИЯ)")
    logger.info("=" * 80)
    logger.info(f"📊 Всего таблиц: {len(FACTS)}")
    logger.info(f"📁 Источники: ils (19 таблиц), sk (2 таблицы)")
    logger.info(f"🎯 Целевая БД: {DST_DATABASE}.raw_")
    logger.info(f"📅 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    # Инициализируем таблицу watermark
    init_watermark_table(logger)
    
    start_time = datetime.now()
    success_count = 0
    error_count = 0
    total_rows = 0
    
    for i, tbl in enumerate(FACTS, 1):
        logger.info(f"\n📌 [{i}/{len(FACTS)}] Обработка: {tbl}")
        try:
            if reload_table_watermark(tbl, logger):
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            logger.error(f"   ❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            error_count += 1
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("\n" + "=" * 80)
    logger.info("🏁 WATERMARK ОБНОВЛЕНИЕ ЗАВЕРШЕНО")
    logger.info("=" * 80)
    logger.info(f"✅ Успешно: {success_count} таблиц")
    logger.info(f"❌ Ошибок: {error_count} таблиц")
    logger.info(f"⏱️ Общее время: {duration:.2f} сек ({duration/60:.2f} мин)")
    logger.info(f"📅 Время запуска: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📅 Время завершения: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    return error_count == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
