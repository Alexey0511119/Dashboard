#!/usr/bin/env python3
"""
ОЧЕНЬ БЫСТРОЕ обновление данных через BULK INSERT.
Использует временные CSV файлы и BULK INSERT для максимальной скорости.
"""
import pymssql
from datetime import datetime, timedelta
import logging
import os
import sys
import tempfile
import csv
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

PERIOD_DAYS = 3

# Логирование
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Временная папка для CSV
TEMP_DIR = os.path.join(SCRIPT_DIR, 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

def setup_logging():
    log_file = os.path.join(LOG_DIR, f"bulk_insert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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
    if column_name.lower() in RESERVED_KEYWORDS:
        return f"[{column_name}]"
    return column_name

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

def get_date_field(table_name):
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
    if table_name == 'labor_management_detail_view':
        return 'labor_management'
    return table_name

def get_source_database(table_name):
    if table_name in ['eks_peremer_ZX_KPP', 'Shtraf_Edit']:
        return 'sk'
    return 'ils'

def save_to_csv(rows, columns, table_name):
    """
    Сохраняет данные в CSV файл для BULK INSERT.
    """
    csv_file = os.path.join(TEMP_DIR, f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in rows:
            # Преобразуем None в пустые строки, datetime в строки
            cleaned_row = []
            for val in row:
                if val is None:
                    cleaned_row.append('')
                elif isinstance(val, datetime):
                    cleaned_row.append(val.strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    cleaned_row.append(str(val))
            writer.writerow(cleaned_row)
    
    return csv_file

def bulk_insert_table(csv_file, target_table, columns, logger):
    """
    Выполняет вставку большими пакетами.
    """
    # Открываем отдельное подключение без транзакции
    conn = pymssql.connect(
        server=DST_SERVER,
        user=DST_USER,
        password=DST_PASSWORD,
        database=DST_DATABASE,
        charset='UTF-8',
        as_dict=False,
        autocommit=True  # Авто-коммит!
    )
    cursor = conn.cursor()
    
    try:
        # Читаем CSV
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        row_count = len(rows)
        column_list = ", ".join([escape_column_name(col) for col in columns])
        placeholders = ",".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO raw_.{target_table} ({column_list}) VALUES ({placeholders})"
        
        # Вставляем пакетами по 10000
        batch_size = 10000
        inserted = 0
        
        for i in range(0, row_count, batch_size):
            batch = rows[i:i + batch_size]
            
            # Преобразуем строки в кортежи
            batch_tuples = []
            for row in batch:
                tuple_row = []
                for val in row:
                    if val == '':
                        tuple_row.append(None)
                    else:
                        tuple_row.append(val)
                batch_tuples.append(tuple(tuple_row))
            
            cursor.executemany(insert_sql, batch_tuples)
            inserted += len(batch)
        
        return inserted
        
    except Exception as e:
        logger.error(f"      ❌ Ошибка вставки: {e}")
        raise
    finally:
        conn.close()

def reload_table_bulk(table_name, period_days, logger, table_num, total_tables):
    """
    Обновляет таблицу через BULK INSERT.
    """
    source_db = get_source_database(table_name)
    target_table = get_target_table_name(table_name)
    date_field = get_date_field(table_name)
    
    cutoff = datetime.now() - timedelta(days=period_days)
    
    logger.info("")
    logger.info(f"{'='*60}")
    logger.info(f"ТАБЛИЦА [{table_num}/{total_tables}]: {table_name}")
    logger.info(f"{'='*60}")
    logger.info(f"   📁 Источник: {source_db}, Поле даты: {date_field}")
    
    step_start = datetime.now()
    
    try:
        # Подключение к источнику
        logger.info(f"   🔌 Шаг 1/6: Подключение к источнику ({source_db})...")
        if source_db == 'sk':
            src = pymssql.connect(
                server=SRC_SERVER,
                port=SRC_PORT,
                user=SRC_USER,
                password=SRC_PASSWORD,
                database=SRC_DATABASE_SK,
                tds_version='7.0'
            )
        else:
            src = pymssql.connect(
                server=SRC_SERVER,
                port=SRC_PORT,
                user=SRC_USER,
                password=SRC_PASSWORD,
                database=SRC_DATABASE_ILS,
                tds_version='7.0'
            )
        logger.info(f"      ✅ Подключено")
        
        # Подключение к целевой БД
        logger.info(f"   🔌 Шаг 2/6: Подключение к целевой БД...")
        dst = pymssql.connect(
            server=DST_SERVER,
            user=DST_USER,
            password=DST_PASSWORD,
            database=DST_DATABASE,
            charset='UTF-8'
        )
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
            logger.warning(f"   ⚠️ Колонки не найдены")
            return True
        
        logger.info(f"      ✅ Найдено колонок: {len(columns)}")
        
        # Читаем данные из источника
        logger.info(f"   📥 Шаг 4/6: Чтение данных из источника...")
        
        if table_name == 'labor_management_detail_view':
            from_table = 'labor_management_detail_view'
        else:
            from_table = table_name
        
        query = f"""
            SELECT {", ".join(columns)}
            FROM {from_table}
            WHERE {date_field} >= %s
        """
        
        read_start = datetime.now()
        src_cursor.execute(query, (cutoff,))
        rows = src_cursor.fetchall()
        read_end = datetime.now()
        
        row_count = len(rows)
        logger.info(f"      ✅ Прочитано: {row_count:,} строк (за {(read_end-read_start).total_seconds():.2f} сек)")
        
        if row_count == 0:
            logger.info(f"      ℹ️ Нет данных")
            src.close()
            dst.close()
            return True
        
        # Удаляем старые данные
        logger.info(f"   🗑️ Шаг 5/6: Удаление старых данных...")
        
        escaped_date_field = escape_column_name(date_field)
        delete_start = datetime.now()
        dst_cursor.execute(f"DELETE FROM raw_.{target_table} WHERE {escaped_date_field} >= %s", (cutoff,))
        deleted = dst_cursor.rowcount
        dst.commit()
        delete_end = datetime.now()
        
        logger.info(f"      🗑️ Удалено: {deleted:,} строк (за {(delete_end-delete_start).total_seconds():.2f} сек)")
        
        # BULK INSERT
        logger.info(f"   📊 Шаг 6/6: BULK INSERT...")
        
        # Сохраняем в CSV
        csv_start = datetime.now()
        csv_file = save_to_csv(rows, columns, target_table)
        csv_end = datetime.now()
        logger.info(f"      📁 CSV создан: {os.path.getsize(csv_file) / 1024 / 1024:.2f} MB (за {(csv_end-csv_start).total_seconds():.2f} сек)")
        
        # BULK INSERT
        bulk_start = datetime.now()
        inserted = bulk_insert_table(csv_file, target_table, columns, logger)
        bulk_end = datetime.now()
        
        # Удаляем CSV
        try:
            os.remove(csv_file)
        except:
            pass
        
        logger.info(f"      ✅ BULK INSERT: {inserted:,} строк за {(bulk_end-bulk_start).total_seconds():.2f} сек")
        
        # Проверка
        logger.info(f"   🔍 Проверка...")
        dst_cursor.execute(f"SELECT COUNT(*) FROM raw_.{target_table} WHERE {escaped_date_field} >= %s", (cutoff,))
        count_after = dst_cursor.fetchone()[0]
        logger.info(f"      ✅ В target: {count_after:,} строк")
        
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
    finally:
        pass

def main():
    logger = setup_logging()
    
    logger.info("=" * 80)
    logger.info(f"🚀 BULK INSERT: ОЧЕНЬ БЫСТРОЕ ОБНОВЛЕНИЕ ЗА {PERIOD_DAYS} ДНЯ")
    logger.info("=" * 80)
    logger.info(f"📊 Всего таблиц: {len(FACTS)}")
    logger.info(f"🎯 Целевая БД: {DST_DATABASE}.raw_")
    logger.info("=" * 80)
    
    start_time = datetime.now()
    success_count = 0
    error_count = 0
    
    for i, tbl in enumerate(FACTS, 1):
        logger.info(f"\n📌 [{i}/{len(FACTS)}] Обработка: {tbl}")
        try:
            if reload_table_bulk(tbl, PERIOD_DAYS, logger, i, len(FACTS)):
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            logger.error(f"   ❌ ОШИБКА: {e}")
            error_count += 1
    
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info("\n" + "=" * 80)
    logger.info("🏁 ЗАВЕРШЕНО")
    logger.info("=" * 80)
    logger.info(f"✅ Успешно: {success_count}/{len(FACTS)}")
    logger.info(f"❌ Ошибок: {error_count}")
    logger.info(f"⏱️ Общее время: {duration:.2f} сек ({duration/60:.2f} мин)")
    logger.info("=" * 80)
    
    return error_count == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
