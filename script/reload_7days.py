#!/usr/bin/env python3
"""
Обновляет сырые данные в raw_.таблицах за последние 7 дней.
Запускается ежедневно в 23:59 как часть 7-дневного пайплайна.
"""
import pymssql
from datetime import datetime, timedelta
import logging
import os
import sys

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

# Период обновления (7 дней)
PERIOD_DAYS = 7

# Логирование
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    log_file = os.path.join(LOG_DIR, f"reload_7days_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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
    column_name_lower = column_name.lower()
    if column_name_lower in RESERVED_KEYWORDS:
        return f"[{column_name}]"
    return column_name

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

def reload_table(table_name, period_days, logger):
    """
    Перезаписывает данные за последние period_days дней.
    """
    source_db = get_source_database(table_name)
    target_table = get_target_table_name(table_name)
    date_field = get_date_field(table_name)
    
    cutoff = datetime.now() - timedelta(days=period_days)
    
    logger.info(f"🔄 {table_name} -> raw_.{target_table} за последние {period_days} дн.")
    
    # Подключение к источнику
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
    
    # Подключение к целевой БД
    dst = pymssql.connect(
        server=DST_SERVER,
        user=DST_USER,
        password=DST_PASSWORD,
        database=DST_DATABASE,
        charset='UTF-8'
    )
    
    try:
        dst_cursor = dst.cursor()
        
        # Получаем колонки
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
        
        # Читаем данные из источника
        src_cursor = src.cursor()
        
        if table_name == 'labor_management_detail_view':
            from_table = 'labor_management_detail_view'
        else:
            from_table = table_name
        
        query = f"""
            SELECT {src_column_list}
            FROM {from_table}
            WHERE {date_field} >= %s
        """
        
        src_cursor.execute(query, (cutoff,))
        rows = src_cursor.fetchall()
        row_count = len(rows)
        logger.info(f"   📥 Найдено в источнике: {row_count} строк")
        
        # Удаляем старые данные
        escaped_date_field = escape_column_name(date_field)
        delete_query = f"""
            DELETE FROM raw_.{target_table}
            WHERE {escaped_date_field} >= %s
        """
        dst_cursor.execute(delete_query, (cutoff,))
        deleted = dst_cursor.rowcount
        logger.info(f"   🗑️ Удалено из target: {deleted} строк")
        
        # Вставляем новые данные (все сразу, без пакетов)
        if rows:
            placeholders = ",".join(["%s"] * len(columns))
            insert_sql = f"INSERT INTO raw_.{target_table} ({column_list}) VALUES ({placeholders})"
            
            insert_start = datetime.now()
            logger.info(f"      📊 Вставка {row_count:,} строк (единым вызовом)...")
            
            # Вставляем все данные за один вызов (для 150K строк - нормально)
            dst_cursor.executemany(insert_sql, rows)
            dst.commit()
            
            insert_end = datetime.now()
            insert_duration = (insert_end - insert_start).total_seconds()
            rows_per_sec = row_count / insert_duration if insert_duration > 0 else 0
            
            logger.info(f"      ✅ Вставлено: {row_count:,} строк за {insert_duration:.2f} сек ({rows_per_sec:,.0f} строк/сек)")
        else:
            dst.commit()
            logger.info(f"      ℹ️ Нет данных для вставки")
        
        # Проверка
        check_query = f"SELECT COUNT(*) FROM raw_.{target_table} WHERE {escaped_date_field} >= %s"
        dst_cursor.execute(check_query, (cutoff,))
        count_after = dst_cursor.fetchone()[0]
        logger.info(f"   🔍 Проверка: в target за период {count_after} строк")
        
        return True
        
    except Exception as e:
        logger.error(f"   ❌ ОШИБКА: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        src.close()
        dst.close()

def main():
    logger = setup_logging()
    
    logger.info("=" * 80)
    logger.info(f"🚀 ПЕРЕЗАПИСЬ ДАННЫХ ЗА ПОСЛЕДНИЕ {PERIOD_DAYS} ДНЕЙ")
    logger.info("=" * 80)
    logger.info(f"📊 Всего таблиц: {len(FACTS)}")
    logger.info(f"📁 Источники: ils ({len([f for f in FACTS if get_source_database(f) == 'ils'])} таблиц), sk ({len([f for f in FACTS if get_source_database(f) == 'sk'])} таблицы)")
    logger.info(f"🎯 Целевая БД: {DST_DATABASE}.raw_")
    logger.info(f"📅 Период: {(datetime.now() - timedelta(days=PERIOD_DAYS)).strftime('%Y-%m-%d')} - {datetime.now().strftime('%Y-%m-%d')}")
    logger.info("=" * 80)
    
    start_time = datetime.now()
    success_count = 0
    error_count = 0
    
    for i, tbl in enumerate(FACTS, 1):
        logger.info(f"\n📌 [{i}/{len(FACTS)}] Обработка таблицы: {tbl}")
        try:
            if reload_table(tbl, PERIOD_DAYS, logger):
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            logger.error(f"   ❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            error_count += 1
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("\n" + "=" * 80)
    logger.info("🏁 ПЕРЕЗАПИСЬ ЗАВЕРШЕНА")
    logger.info("=" * 80)
    logger.info(f"✅ Успешно: {success_count} таблиц")
    logger.info(f"❌ Ошибок: {error_count} таблиц")
    logger.info(f"⏱️ Время выполнения: {duration:.2f} сек ({duration/60:.2f} мин)")
    logger.info(f"📅 Дата запуска: {start_time}")
    logger.info("=" * 80)
    
    return error_count == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
