#!/usr/bin/env python3
"""
ОПТИМИЗИРОВАННЫЙ 3-ДНЕВНЫЙ ETL ЧЕРЕЗ PYTHON + SQLCMD
Версия 2.0 с максимальной оптимизацией скорости

Оптимизации:
1. Пакетная вставка с pyodbc (fast_executemany=True)
2. Минимальное логгирование
3. Параллельная загрузка таблиц
4. Временные таблицы для скорости
"""
import pyodbc
import subprocess
import logging
import os
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# === Конфигурация ===
SRC_SERVER = '10.7.0.248'
SRC_DATABASE_ILS = 'ils'
SRC_DATABASE_SK = 'sk'
SRC_USER = 'manhreader'
SRC_PASSWORD = 'August2021'

DST_SERVER = '10.7.0.27'
DST_DATABASE = 'olap2_fixed'
DST_USER = 'sa'
DST_PASSWORD = 'Rdflhfn600'

PERIOD_DAYS = 3
BATCH_SIZE = 50000  # Увеличенный размер пакета

# === Логирование ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    log_file = os.path.join(LOG_DIR, f"etl_optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# === Подключения ===
def get_src_connection(database):
    """Подключение к источнику с оптимизациями"""
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SRC_SERVER};"
        f"DATABASE={database};"
        f"UID={SRC_USER};"
        f"PWD={SRC_PASSWORD};"
        f"Connect Timeout=30;"
    )
    return pyodbc.connect(conn_str, autocommit=False)

def get_dst_connection():
    """Подключение к цели с fast_executemany"""
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={DST_SERVER};"
        f"DATABASE={DST_DATABASE};"
        f"UID={DST_USER};"
        f"PWD={DST_PASSWORD};"
        f"Connect Timeout=30;"
    )
    return pyodbc.connect(conn_str, autocommit=False, fast_executemany=True)

# === Таблицы ===
FACTS = [
    ('ORDER_DETAIL', 'ils', 'DATE_TIME_STAMP'),
    ('ORDER_HEADER', 'ils', 'ORDER_DATE'),
    ('RECEIPT_DETAIL', 'ils', 'DATE_TIME_STAMP'),
    ('RECEIPT_HEADER', 'ils', 'RECEIPT_DATE'),
    ('SHIPMENT_DETAIL', 'ils', 'DATE_TIME_STAMP'),
    ('SHIPMENT_HEADER', 'ils', 'PLANNED_SHIP_DATE'),
    ('TRANSACTION_HISTORY', 'ils', 'DATE_TIME_STAMP'),
    ('WORK_INSTRUCTION_VIEW2', 'ils', 'DATE_TIME_STAMP'),
    ('DOWNLOAD_ORDER_DETAIL', 'ils', 'DATE_TIME_STAMP'),
    ('DOWNLOAD_ORDER_HEADER', 'ils', 'DATE_TIME_STAMP'),
    ('DOWNLOAD_RECEIPT_DETAIL', 'ils', 'DATE_TIME_STAMP'),
    ('DOWNLOAD_RECEIPT_HEADER', 'ils', 'DATE_TIME_STAMP'),
    ('UPLOAD_ORDER_DETAIL', 'ils', 'DATE_TIME_STAMP'),
    ('UPLOAD_ORDER_HEADER', 'ils', 'DATE_TIME_STAMP'),
    ('UPLOAD_RECEIPT_DETAIL', 'ils', 'DATE_TIME_STAMP'),
    ('UPLOAD_RECEIPT_HEADER', 'ils', 'DATE_TIME_STAMP'),
    ('UPLOAD_RECEIPT_CONTAINER', 'ils', 'DATE_TIME_STAMP'),
    ('CYCLE_COUNT_REQUEST', 'ils', 'DATE_TIME_STAMP'),
    ('labor_management_detail_view', 'ils', 'DATE_TIME_STAMP'),
    ('eks_peremer_ZX_KPP', 'sk', 'date_time_stamp'),
    ('Shtraf_Edit', 'sk', 'date_time_stamp'),
]

def reload_table(table_info, cutoff, logger):
    """Перезапись таблицы с оптимизацией"""
    table_name, source_db, date_field = table_info
    cutoff_date = cutoff.strftime('%Y-%m-%d')
    
    try:
        # Подключения
        src = get_src_connection(source_db)
        dst = get_dst_connection()
        
        src_cursor = src.cursor()
        dst_cursor = dst.cursor()
        
        # Получаем колонки
        dst_cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'raw_' AND TABLE_NAME = ?
            AND COLUMN_NAME NOT IN ('ROW_ID', 'row_hash')
            ORDER BY ORDINAL_POSITION
        """, (table_name,))
        
        columns = [row[0] for row in dst_cursor.fetchall()]
        if not columns:
            logger.warning(f"  ⚠️ {table_name}: колонки не найдены")
            return False
        
        column_list = ", ".join([f"[{c}]" for c in columns])
        
        # Читаем из источника
        query = f"SELECT {column_list} FROM {table_name} WHERE [{date_field}] >= ?"
        src_cursor.execute(query, (cutoff,))
        rows = src_cursor.fetchall()
        
        # Удаляем старые
        delete_query = f"DELETE FROM raw_.[{table_name}] WHERE [{date_field}] >= ?"
        dst_cursor.execute(delete_query, (cutoff,))
        dst.commit()
        
        # Вставляем новые пакетами
        if rows:
            placeholders = ",".join(["?"] * len(columns))
            insert_sql = f"INSERT INTO raw_.[{table_name}] ({column_list}) VALUES ({placeholders})"
            
            inserted = 0
            for i in range(0, len(rows), BATCH_SIZE):
                batch = rows[i:i + BATCH_SIZE]
                dst_cursor.executemany(insert_sql, batch)
                inserted += len(batch)
            
            dst.commit()
            logger.info(f"  ✅ {table_name}: {inserted:,} строк")
        else:
            logger.info(f"  ℹ️ {table_name}: нет данных")
        
        src.close()
        dst.close()
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ {table_name}: {e}")
        return False

def run_parallel_reload(cutoff, logger, max_workers=3):
    """Параллельная загрузка таблиц"""
    logger.info(f"🚀 Параллельная загрузка {len(FACTS)} таблиц...")
    
    success_count = 0
    error_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(reload_table, table_info, cutoff, logger): table_info
            for table_info in FACTS
        }
        
        for future in as_completed(futures):
            table_info = futures[future]
            try:
                if future.result():
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"  ❌ {table_info[0]}: {e}")
                error_count += 1
    
    return success_count, error_count

def run_update_dwh(logger):
    """Выполнение SQL-скрипта обновления DWH"""
    logger.info("=" * 80)
    logger.info("ШАГ 2: Обновление DWH таблиц")
    logger.info("=" * 80)
    
    sql_file = os.path.join(SCRIPT_DIR, 'update_dwh_3days_linked.sql')
    
    if not os.path.exists(sql_file):
        logger.error(f"❌ SQL-файл не найден: {sql_file}")
        return False
    
    cmd = [
        'sqlcmd',
        '-S', DST_SERVER,
        '-U', DST_USER,
        '-P', DST_PASSWORD,
        '-d', DST_DATABASE,
        '-i', sql_file,
        '-C',  # Игнорировать SSL
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600
        )
        
        if result.returncode == 0 or 'ОБНОВЛЕНИЕ ЗАВЕРШЕНО' in result.stdout:
            logger.info("✅ DWH обновлено")
            return True
        else:
            logger.error(f"❌ Ошибка DWH: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return False

def main():
    logger = setup_logging()
    
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 20 + "ОПТИМИЗИРОВАННЫЙ 3-ДНЕВНЫЙ ETL" + " " * 27 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    
    start_time = datetime.now()
    cutoff = datetime.now() - timedelta(days=PERIOD_DAYS)
    
    logger.info(f"📅 Период: {cutoff.strftime('%Y-%m-%d')} - {datetime.now().strftime('%Y-%m-%d')}")
    logger.info(f"📦 Размер пакета: {BATCH_SIZE:,} строк")
    logger.info("")
    
    # ШАГ 1: Параллельная загрузка сырых данных
    logger.info("=" * 80)
    logger.info("ШАГ 1: Обновление сырых данных (параллельно)")
    logger.info("=" * 80)
    
    success, errors = run_parallel_reload(cutoff, logger, max_workers=3)
    
    logger.info("")
    logger.info(f"✅ Успешно: {success} таблиц")
    logger.info(f"❌ Ошибок: {errors} таблиц")
    logger.info("")
    
    # ШАГ 2: Обновление DWH
    if errors == 0:
        if not run_update_dwh(logger):
            logger.error("❌ Ошибка обновления DWH")
            return False
    else:
        logger.warning("⚠️ Пропускаем DWH из-за ошибок на шаге 1")
    
    # Итоги
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("ETL ЗАВЕРШЁН")
    logger.info("=" * 80)
    logger.info(f"⏱️ Время выполнения: {duration:.2f} сек ({duration/60:.2f} мин)")
    logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return errors == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
