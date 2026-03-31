#!/usr/bin/env python3
"""
Обновляет сырые данные в raw_.таблицах за последние 3 дня.
Запускается каждые 10 минут как часть 3-дневного пайплайна.

Основан на оригинальном скрипте выгрузки данных.
"""
import pymssql
from datetime import datetime, timedelta
import logging
import os
import sys

# === Параметры подключения к источнику ils ===
SRC_SERVER = '10.7.0.248'
SRC_PORT = 1433
SRC_DATABASE_ILS = 'ils'
SRC_DATABASE_SK = 'sk'
SRC_USER = 'manhreader'
SRC_PASSWORD = 'August2021'

# === Параметры подключения к целевой БД ===
DST_SERVER = '10.7.0.27'
DST_DATABASE = 'olap2_fixed'
DST_USER = 'sa'
DST_PASSWORD = 'Rdflhfn600'

# === Период обновления (3 дня вместо 7) ===
PERIOD_DAYS = 3

# === Логирование ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    log_file = os.path.join(LOG_DIR, f"reload_3days_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# === СПИСОК ЗАРЕЗЕРВИРОВАННЫХ СЛОВ В SQL SERVER ===
RESERVED_KEYWORDS = {
    'user', 'out', 'order', 'group', 'table', 'key', 'primary', 'foreign',
    'join', 'inner', 'outer', 'left', 'right', 'full', 'cross', 'on',
    'where', 'having', 'select', 'insert', 'update', 'delete', 'drop',
    'create', 'alter', 'view', 'procedure', 'function', 'trigger',
    'index', 'column', 'schema', 'database', 'server', 'login', 'role'
}

def escape_column_name(column_name):
    """
    Экранирует имя колонки квадратными скобками, если это зарезервированное слово.
    """
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
    """
    Определяет поле с датой для фильтрации данных.
    """
    if table_name == 'ORDER_HEADER':
        return 'ORDER_DATE'
    elif table_name == 'RECEIPT_HEADER':
        return 'RECEIPT_DATE'
    elif table_name == 'SHIPMENT_HEADER':
        return 'DATE_TIME_STAMP'  # ✅ ИСПРАВЛЕНО: было PLANNED_SHIP_DATE
    elif table_name in ['eks_peremer_ZX_KPP', 'Shtraf_Edit']:
        return 'date_time_stamp'
    else:
        return 'DATE_TIME_STAMP'

def get_target_table_name(table_name):
    """
    Возвращает имя целевой таблицы в схеме raw_.
    """
    if table_name == 'labor_management_detail_view':
        return 'labor_management'
    return table_name

def get_source_database(table_name):
    """
    Определяет, из какой БД читать данные.
    """
    if table_name in ['eks_peremer_ZX_KPP', 'Shtraf_Edit']:
        return 'sk'
    return 'ils'

def reload_table(table_name, period_days, logger):
    """
    Перезаписывает данные за последние period_days дней.
    С улучшенной проверкой целостности данных.
    """
    source_db = get_source_database(table_name)
    target_table = get_target_table_name(table_name)
    date_field = get_date_field(table_name)

    cutoff = datetime.now() - timedelta(days=period_days)

    logger.info(f"🔄 Перезапись {table_name} -> raw_.{target_table} за последние {period_days} дн.")
    logger.info(f"   📁 Источник: {source_db}, поле даты: {date_field}")
    logger.info(f"   📅 Дата отсечки: {cutoff.strftime('%Y-%m-%d')}")

    # Подключение к источнику (разные БД)
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
        # === 1. Получаем колонки из целевой таблицы ===
        dst_cursor = dst.cursor()
        dst_cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'raw_' AND TABLE_NAME = %s
            AND COLUMN_NAME NOT IN ('ROW_ID', 'row_hash')
            ORDER BY ORDINAL_POSITION
        """, (target_table,))

        columns = [row[0] for row in dst_cursor.fetchall()]
        if not columns:
            logger.warning(f"   ❌ Колонки не найдены в raw_.{target_table}")
            return False  # Возвращаем False — это ошибка!

        # Экранируем имена колонок, если нужно
        escaped_columns = [escape_column_name(col) for col in columns]
        column_list = ", ".join(escaped_columns)
        src_column_list = ", ".join(escaped_columns)

        logger.info(f"   📋 Колонок для выгрузки: {len(columns)}")

        # === 2. Читаем данные из источника ===
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

        # === 3. Удаляем старые данные за период ===
        escaped_date_field = escape_column_name(date_field)
        delete_query = f"""
            DELETE FROM raw_.{target_table}
            WHERE {escaped_date_field} >= %s
        """
        dst_cursor.execute(delete_query, (cutoff,))
        deleted = dst_cursor.rowcount
        logger.info(f"   🗑️ Удалено из target: {deleted} строк")

        # === 4. Вставляем новые данные ===
        if rows:
            placeholders = ",".join(["%s"] * len(columns))
            insert_sql = f"INSERT INTO raw_.{target_table} ({column_list}) VALUES ({placeholders})"

            # ОПТИМИЗАЦИЯ: Вставляем пакетами по 10000 строк (вместо 1000)
            # Баланс между скоростью и потреблением памяти
            batch_size = 10000
            inserted = 0
            error_count = 0

            insert_start = datetime.now()
            logger.info(f"   📊 Вставка {row_count:,} строк (пакеты по {batch_size:,})...")

            for i in range(0, row_count, batch_size):
                batch = rows[i:i + batch_size]
                try:
                    dst_cursor.executemany(insert_sql, batch)
                    inserted += len(batch)
                except Exception as batch_error:
                    # Проверяем, это дубликат или другая ошибка
                    error_str = str(batch_error)
                    if 'PRIMARY KEY' in error_str or 'duplicate' in error_str.lower():
                        # Это дубликат — пробуем вставить по одной строке с пропуском дублей
                        logger.warning(f"   ⚠ Обнаружен дубликат, вставляем по одной строке...")
                        for single_row in batch:
                            try:
                                dst_cursor.execute(insert_sql, single_row)
                                inserted += 1
                            except Exception as row_error:
                                if 'PRIMARY KEY' in str(row_error) or 'duplicate' in str(row_error).lower():
                                    # Пропускаем дубликат
                                    continue
                                else:
                                    # Другая ошибка — логируем
                                    logger.warning(f"      ⚠ Ошибка строки: {row_error}")
                                    error_count += 1
                    else:
                        # Другая ошибка — пропускаем весь пакет
                        logger.warning(f"   ⚠ Ошибка пакета [{i//batch_size + 1}]: {batch_error}")
                        error_count += len(batch)
                        continue

            # ОДИН коммит после всех пакетов — значительное ускорение!
            dst.commit()
            
            insert_end = datetime.now()
            insert_duration = (insert_end - insert_start).total_seconds()
            rows_per_sec = inserted / insert_duration if insert_duration > 0 else 0

            logger.info(f"   ✅ Вставлено: {inserted:,} строк за {insert_duration:.2f} сек ({rows_per_sec:,.0f} строк/сек)")
            if error_count > 0:
                logger.warning(f"   ⚠ Пропущено из-за ошибок: {error_count:,} строк")

            # === ПРОВЕРКА ЦЕЛОСТНОСТИ ===
            # Если вставлено меньше 90% от ожидаемого — это ошибка!
            if inserted < row_count * 0.9:
                logger.error(f"   ❌ КРИТИЧЕСКАЯ ОШИБКА: Вставлено только {inserted} из {row_count} строк ({inserted*100//row_count}%)!")
                logger.error(f"   ❌ Данные могут быть неполными. Требуется вмешательство!")
                return False
        else:
            dst.commit()
            logger.info(f"   ℹ️ Нет данных для вставки")

        # === Финальная проверка результата ===
        check_query = f"SELECT COUNT(*) FROM raw_.{target_table} WHERE {escaped_date_field} >= %s"
        dst_cursor.execute(check_query, (cutoff,))
        count_after = dst_cursor.fetchone()[0]
        logger.info(f"   🔍 Проверка: в target за период {count_after} строк")

        # Если данных должно быть много, но их мало — предупреждаем
        if table_name in ['WORK_INSTRUCTION_VIEW2', 'TRANSACTION_HISTORY'] and count_after < 100:
            logger.warning(f"   ⚠️ Подозрительно мало данных ({count_after}) для важной таблицы!")

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
    logger.info(f"🚀 ПЕРЕЗАПИСЬ ДАННЫХ ЗА ПОСЛЕДНИЕ {PERIOD_DAYS} ДНЯ")
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

    # Итоги
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
