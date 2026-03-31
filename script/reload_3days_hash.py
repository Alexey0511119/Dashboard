#!/usr/bin/env python3
"""
Обновляет ТОЛЬКО изменённые данные в raw_.таблицах.
Запускается каждые 10 минут как часть 3-дневного пайплайна.

Использует хэширование для определения изменений.
Выгружает данные за 3 дня, но обновляет только те, где хэш отличается.
"""
import pymssql
from datetime import datetime, timedelta
import logging
import os
import sys
import hashlib

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

# Период выгрузки (3 дня)
PERIOD_DAYS = 3

# Логирование
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    log_file = os.path.join(LOG_DIR, f"reload_3days_hash_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# === СПИСОК ЗАРЕЗЕРВИРОВАННЫХ СЛОВ ===
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
    """Возвращает первичный ключ для таблицы"""
    primary_keys = {
        'ORDER_DETAIL': 'ORDER_ID',
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
        'labor_management': 'USER_NAME',
        'UPLOAD_RECEIPT_CONTAINER': 'CONTAINER_ID',
        'eks_peremer_ZX_KPP': 'id',
        'Shtraf_Edit': 'id'
    }
    return primary_keys.get(table_name)

def get_date_field(table_name):
    """Возвращает поле даты для таблицы"""
    if table_name == 'ORDER_HEADER':
        return 'ORDER_DATE'
    elif table_name == 'RECEIPT_HEADER':
        return 'RECEIPT_DATE'
    elif table_name == 'SHIPMENT_HEADER':
        return 'PLANNED_SHIP_DATE'
    elif table_name in ['eks_peremer_ZX_KPP', 'Shtraf_Edit']:
        return 'date_time_stamp'
    else:
        return 'DATE_TIME_STAMP'

def get_target_table_name(table_name):
    """Возвращает имя целевой таблицы"""
    if table_name == 'labor_management_detail_view':
        return 'labor_management'
    return table_name

def get_source_database(table_name):
    """Определяет БД источника"""
    if table_name in ['eks_peremer_ZX_KPP', 'Shtraf_Edit']:
        return 'sk'
    return 'ils'

def compute_row_hash(row, columns, pk_column):
    """
    Вычисляет хэш строки от всех полей кроме первичного ключа и даты.
    """
    # Исключаем PK и поля даты из хэша
    exclude_columns = {pk_column, 'DATE_TIME_STAMP', 'date_time_stamp', 
                       'CREATION_DATE_TIME_STAMP', 'ORDER_DATE', 'RECEIPT_DATE',
                       'PLANNED_SHIP_DATE'}
    
    hash_data = []
    for col, val in zip(columns, row):
        if col not in exclude_columns:
            hash_data.append(str(val) if val is not None else '')
    
    hash_string = '|'.join(hash_data)
    return hashlib.md5(hash_string.encode('utf-8')).hexdigest()

def init_hash_table(table_name, target_table, pk_column, pk_type, logger):
    """
    Создаёт таблицу для хранения хэшей, если не существует.
    """
    conn = get_dst_connection()
    cursor = conn.cursor()
    
    try:
        # Создаём таблицу хэшей
        hash_table = f"raw_.{target_table}_hash"
        
        cursor.execute(f"""
            IF NOT EXISTS (SELECT * FROM sys.tables 
                          WHERE name = '{target_table}_hash' AND schema_id = SCHEMA_ID('raw_'))
            BEGIN
                CREATE TABLE {hash_table} (
                    {escape_column_name(pk_column)} {pk_type} NOT NULL PRIMARY KEY,
                    row_hash VARBINARY(8000) NOT NULL,
                    last_updated DATETIME DEFAULT GETDATE()
                )
            END
        """)
        conn.commit()
        logger.info(f"✅ Таблица хэшей {hash_table} создана/проверена")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось создать таблицу хэшей: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_pk_type(source_db, table_name, pk_column, logger):
    """
    Получает тип данных первичного ключа из источника.
    """
    try:
        src = get_src_connection(source_db)
        cursor = src.cursor()
        
        cursor.execute("""
            SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = %s AND COLUMN_NAME = %s
        """, (table_name, pk_column))
        
        row = cursor.fetchone()
        src.close()
        
        if row:
            data_type = row[0]
            max_length = row[1]
            precision = row[2]
            scale = row[3]
            
            if data_type == 'nvarchar' and max_length:
                return f"NVARCHAR({max_length})"
            elif data_type == 'varchar' and max_length:
                return f"VARCHAR({max_length})"
            elif data_type == 'decimal' and precision:
                return f"DECIMAL({precision},{scale or 0})"
            elif data_type == 'numeric' and precision:
                return f"NUMERIC({precision},{scale or 0})"
            elif data_type == 'int':
                return 'INT'
            elif data_type == 'bigint':
                return 'BIGINT'
            elif data_type == 'uniqueidentifier':
                return 'UNIQUEIDENTIFIER'
            elif data_type == 'datetime':
                return 'DATETIME'
            else:
                return data_type
        else:
            return 'NVARCHAR(100)'  # По умолчанию
    except Exception as e:
        logger.warning(f"⚠️ Не удалось получить тип PK: {e}")
        return 'NVARCHAR(100)'

def get_existing_hashes(target_table, pk_column, ids, logger):
    """
    Получает хэши существующих записей.
    """
    conn = get_dst_connection()
    cursor = conn.cursor()
    
    try:
        hash_table = f"raw_.{target_table}_hash"
        
        # Получаем хэши пакетами
        batch_size = 10000
        hashes = {}
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            placeholders = ",".join(["%s"] * len(batch_ids))
            
            cursor.execute(f"""
                SELECT {escape_column_name(pk_column)}, row_hash
                FROM {hash_table}
                WHERE {escape_column_name(pk_column)} IN ({placeholders})
            """, batch_ids)
            
            hashes.update({row[0]: row[1].hex() for row in cursor.fetchall()})
        
        return hashes
    except Exception as e:
        logger.warning(f"⚠️ Ошибка получения хэшей: {e}")
        return {}
    finally:
        conn.close()

def update_hashes(target_table, pk_column, rows_to_update, rows_to_insert, columns, logger):
    """
    Обновляет/вставляет хэши в таблицу хэшей.
    """
    conn = get_dst_connection()
    cursor = conn.cursor()
    
    try:
        hash_table = f"raw_.{target_table}_hash"
        pk_index = columns.index(pk_column)
        
        # Обновляем существующие
        if rows_to_update:
            placeholders = ",".join(["%s"] * len(rows_to_update))
            update_ids = [row[pk_index] for row in rows_to_update]
            
            cursor.execute(f"""
                UPDATE {hash_table}
                SET row_hash = %s, last_updated = GETDATE()
                WHERE {escape_column_name(pk_column)} IN ({placeholders})
            """, [compute_row_hash(row, columns, pk_column) for row in rows_to_update] + update_ids)
            
            conn.commit()
        
        # Вставляем новые
        if rows_to_insert:
            for row in rows_to_insert:
                row_hash = compute_row_hash(row, columns, pk_column)
                cursor.execute(f"""
                    INSERT INTO {hash_table} ({escape_column_name(pk_column)}, row_hash)
                    VALUES (%s, %s)
                """, (row[pk_index], row_hash))
            conn.commit()
        
        logger.info(f"✅ Хэши обновлены: {len(rows_to_update)} обновлено, {len(rows_to_insert)} вставлено")
    except Exception as e:
        logger.error(f"❌ Ошибка обновления хэшей: {e}")
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

# === СПИСОК ТАБЛИЦ ===
FACTS = [
    'ORDER_DETAIL', 'ORDER_HEADER',
    'RECEIPT_DETAIL', 'RECEIPT_HEADER',
    'SHIPMENT_DETAIL', 'SHIPMENT_HEADER',
    'TRANSACTION_HISTORY', 'WORK_INSTRUCTION_VIEW2',
    'DOWNLOAD_ORDER_DETAIL', 'DOWNLOAD_ORDER_HEADER',
    'DOWNLOAD_RECEIPT_DETAIL', 'DOWNLOAD_RECEIPT_HEADER',
    'UPLOAD_ORDER_DETAIL', 'UPLOAD_ORDER_HEADER',
    'UPLOAD_RECEIPT_DETAIL', 'UPLOAD_RECEIPT_HEADER',
    'CYCLE_COUNT_REQUEST', 'labor_management_detail_view',
    'UPLOAD_RECEIPT_CONTAINER', 'eks_peremer_ZX_KPP', 'Shtraf_Edit'
]

def reload_table_hash(table_name, period_days, logger, table_num, total_tables):
    """
    Обновляет таблицу только с изменёнными данными (через хэши).
    """
    source_db = get_source_database(table_name)
    target_table = get_target_table_name(table_name)
    date_field = get_date_field(table_name)
    pk_column = get_primary_key(table_name)
    
    cutoff = datetime.now() - timedelta(days=period_days)
    
    logger.info("")
    logger.info(f"{'='*60}")
    logger.info(f"ТАБЛИЦА [{table_num}/{total_tables}]: {table_name}")
    logger.info(f"{'='*60}")
    logger.info(f"   📁 Источник: {source_db}, Поле даты: {date_field}")
    logger.info(f"   📅 Период: {cutoff.strftime('%Y-%m-%d %H:%M')} - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    if not pk_column:
        logger.warning(f"   ⚠️ Первичный ключ не найден, пропускаем хэширование")
        return False
    
    step_start = datetime.now()
    
    try:
        # Подключение к источнику
        logger.info(f"   🔌 Шаг 1/7: Подключение к источнику ({source_db})...")
        src = get_src_connection(source_db)
        logger.info(f"      ✅ Подключено")
        
        # Подключение к целевой БД
        logger.info(f"   🔌 Шаг 2/7: Подключение к целевой БД...")
        dst = get_dst_connection()
        logger.info(f"      ✅ Подключено")
        
        src_cursor = src.cursor()
        dst_cursor = dst.cursor()
        
        # Получаем колонки
        logger.info(f"   📋 Шаг 3/7: Получение структуры таблицы...")
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
        
        # Инициализируем таблицу хэшей
        logger.info(f"   📋 Шаг 4/7: Инициализация таблицы хэшей...")
        
        # Получаем тип первичного ключа
        pk_type = get_pk_type(source_db, from_table, pk_column, logger)
        init_hash_table(table_name, target_table, pk_column, pk_type, logger)
        
        # Читаем данные из источника
        logger.info(f"   📥 Шаг 5/7: Чтение данных из источника...")
        
        if table_name == 'labor_management_detail_view':
            from_table = 'labor_management_detail_view'
        else:
            from_table = table_name
        
        query = f"""
            SELECT {src_column_list}
            FROM {from_table}
            WHERE {date_field} >= %s
        """
        
        logger.info(f"      Выполняется запрос...")
        read_start = datetime.now()
        src_cursor.execute(query, (cutoff,))
        rows = src_cursor.fetchall()
        read_end = datetime.now()
        read_duration = (read_end - read_start).total_seconds()
        
        row_count = len(rows)
        logger.info(f"      ✅ Прочитано строк: {row_count:,} (за {read_duration:.2f} сек)")
        
        if row_count == 0:
            logger.info(f"      ℹ️ Нет данных для обновления")
            src.close()
            dst.close()
            return True
        
        # Получаем первичные ключи
        pk_index = columns.index(pk_column)
        ids = [row[pk_index] for row in rows]
        
        # Получаем существующие хэши
        logger.info(f"   🔍 Шаг 6/7: Сравнение хэшей...")
        existing_hashes = get_existing_hashes(target_table, pk_column, ids, logger)
        
        # Разделяем на обновляемые и новые
        rows_to_update = []
        rows_to_insert = []
        
        for row in rows:
            row_id = row[pk_index]
            new_hash = compute_row_hash(row, columns, pk_column)
            
            if row_id in existing_hashes:
                if existing_hashes[row_id] != new_hash:
                    rows_to_update.append(row)
            else:
                rows_to_insert.append(row)
        
        logger.info(f"      📊 Изменилось записей: {len(rows_to_update)}")
        logger.info(f"      📊 Новых записей: {len(rows_to_insert)}")
        logger.info(f"      📊 Без изменений: {row_count - len(rows_to_update) - len(rows_to_insert)}")
        
        # Обновляем/вставляем данные
        logger.info(f"   📊 Шаг 7/7: Обновление/вставка данных...")
        
        if rows_to_update:
            # UPDATE существующих
            update_start = datetime.now()
            
            batch_size = 5000
            updated_count = 0
            
            for i in range(0, len(rows_to_update), batch_size):
                batch = rows_to_update[i:i + batch_size]
                
                # UPDATE SET col1=%s, col2=%s, ... WHERE pk=%s
                update_set = ", ".join([f"{escape_column_name(col)} = %s" for col in columns if col != pk_column])
                update_sql = f"""
                    UPDATE raw_.{target_table}
                    SET {update_set}
                    WHERE {escape_column_name(pk_column)} = %s
                """
                
                for row in batch:
                    update_values = [val for col, val in zip(columns, row) if col != pk_column]
                    update_values.append(row[pk_index])
                    dst_cursor.execute(update_sql, update_values)
                
                dst.commit()
                updated_count += len(batch)
            
            update_end = datetime.now()
            update_duration = (update_end - update_start).total_seconds()
            logger.info(f"      ✅ Обновлено: {updated_count:,} строк (за {update_duration:.2f} сек)")
        
        if rows_to_insert:
            # INSERT новых
            insert_start = datetime.now()
            
            insert_placeholders = ",".join(["%s"] * len(columns))
            insert_sql = f"INSERT INTO raw_.{target_table} ({column_list}) VALUES ({insert_placeholders})"
            
            dst_cursor.executemany(insert_sql, rows_to_insert)
            dst.commit()
            
            insert_end = datetime.now()
            insert_duration = (insert_end - insert_start).total_seconds()
            logger.info(f"      ✅ Вставлено: {len(rows_to_insert):,} строк (за {insert_duration:.2f} сек)")
        
        # Обновляем хэши
        if rows_to_update or rows_to_insert:
            update_hashes(target_table, pk_column, rows_to_update, rows_to_insert, columns, logger)
        
        # Проверка
        logger.info(f"   🔍 Проверка результата...")
        escaped_date_field = escape_column_name(date_field)
        check_query = f"SELECT COUNT(*) FROM raw_.{target_table} WHERE {escaped_date_field} >= %s"
        dst_cursor.execute(check_query, (cutoff,))
        count_after = dst_cursor.fetchone()[0]
        logger.info(f"      ✅ В target за период: {count_after:,} строк")
        
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
        return False

def main():
    logger = setup_logging()
    
    logger.info("=" * 80)
    logger.info(f"🚀 WATERMARK + HASH: ОБНОВЛЕНИЕ ТОЛЬКО ИЗМЕНЁННЫХ ДАННЫХ")
    logger.info("=" * 80)
    logger.info(f"📊 Всего таблиц: {len(FACTS)}")
    logger.info(f"📁 Источники: ils, sk")
    logger.info(f"🎯 Целевая БД: {DST_DATABASE}.raw_")
    logger.info(f"📅 Период: {(datetime.now() - timedelta(days=PERIOD_DAYS)).strftime('%Y-%m-%d')} - {datetime.now().strftime('%Y-%m-%d')}")
    logger.info("=" * 80)
    
    start_time = datetime.now()
    success_count = 0
    error_count = 0
    
    for i, tbl in enumerate(FACTS, 1):
        logger.info(f"\n📌 [{i}/{len(FACTS)}] Обработка: {tbl}")
        try:
            if reload_table_hash(tbl, PERIOD_DAYS, logger, i, len(FACTS)):
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            logger.error(f"   ❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            error_count += 1
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("\n" + "=" * 80)
    logger.info("🏁 ОБНОВЛЕНИЕ ЗАВЕРШЕНО")
    logger.info("=" * 80)
    logger.info(f"✅ Успешно: {success_count} таблиц")
    logger.info(f"❌ Ошибок: {error_count} таблиц")
    logger.info(f"⏱️ Время: {duration:.2f} сек ({duration/60:.2f} мин)")
    logger.info(f"📅 Запуск: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    return error_count == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
