#!/usr/bin/env python3
"""
Инкрементальное обновление raw_.TRANSACTION_HISTORY.

Только добавление НОВЫХ строк (без DELETE).
Таблица транзакций — данные только добавляются, не изменяются.

Запускается каждые 2 минуты через cron.
"""
import pymssql
from datetime import datetime, timedelta
import logging
import os
import sys

# === Параметры подключения к источнику ils ===
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

# === Размер пакета для вставки ===
BATCH_SIZE = 100000

# === Логирование ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    log_file = os.path.join(LOG_DIR, f"reload_transaction_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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
    """Экранирует зарезервированные слова квадратными скобками"""
    if column_name.lower() in RESERVED_KEYWORDS:
        return f"[{column_name}]"
    return column_name

def reload_transaction_history(logger):
    """Инкрементальное обновление raw_.TRANSACTION_HISTORY"""

    logger.info("=" * 80)
    logger.info("🔄 ИНКРЕМЕНТАЛЬНОЕ ОБНОВЛЕНИЕ raw_.TRANSACTION_HISTORY")
    logger.info("=" * 80)
    logger.info(f"📁 Источник: {SRC_SERVER}/{SRC_DATABASE}.TRANSACTION_HISTORY")
    logger.info(f"🎯 Цель:    {DST_SERVER}/{DST_DATABASE}.raw_.TRANSACTION_HISTORY")
    logger.info("=" * 80)

    t_start = datetime.now()

    # Подключение к целевой БД
    try:
        dst = pymssql.connect(
            server=DST_SERVER,
            user=DST_USER,
            password=DST_PASSWORD,
            database=DST_DATABASE,
            charset='UTF-8',
            login_timeout=30,
            timeout=300
        )
        logger.info("✅ Подключение к целевой БД (olap2_fixed) успешно")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к целевой БД: {e}")
        return False

    try:
        dst_cursor = dst.cursor()

        # === Шаг 1: Получаем max DATE_TIME_STAMP из целевой таблицы ===
        logger.info("\n📊 Определение последней записи в raw_.TRANSACTION_HISTORY...")
        dst_cursor.execute("SELECT MAX(DATE_TIME_STAMP) FROM raw_.TRANSACTION_HISTORY")
        result = dst_cursor.fetchone()
        max_date = result[0] if result and result[0] else None

        if max_date:
            cutoff = max_date
            logger.info(f"   📅 Последняя запись: {cutoff}")
        else:
            # Таблица пуста — загружаем последние 3 дня
            cutoff = datetime.now() - timedelta(days=3)
            logger.info(f"   ⚠️ Таблица пуста! Загружаем данные с {cutoff}")

        # === Шаг 2: Получаем колонки ===
        dst_cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'raw_' AND TABLE_NAME = 'TRANSACTION_HISTORY'
            AND COLUMN_NAME NOT IN ('ROW_ID', 'row_hash')
            ORDER BY ORDINAL_POSITION
        """)

        columns = [row[0] for row in dst_cursor.fetchall()]
        if not columns:
            logger.error("❌ Колонки не найдены в raw_.TRANSACTION_HISTORY")
            return False

        escaped_columns = [escape_column_name(col) for col in columns]
        column_list = ", ".join(escaped_columns)

        logger.info(f"📋 Колонок: {len(columns)}")

        # === Шаг 3: Читаем НОВЫЕ данные из источника ===
        logger.info(f"\n📥 Чтение новых данных (после {cutoff})...")
        query = f"SELECT {column_list} FROM TRANSACTION_HISTORY WHERE DATE_TIME_STAMP > %s"

        # Подключение к источнику
        try:
            src = pymssql.connect(
                server=SRC_SERVER,
                port=SRC_PORT,
                user=SRC_USER,
                password=SRC_PASSWORD,
                database=SRC_DATABASE,
                tds_version='7.0',
                login_timeout=30,
                timeout=300
            )
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к источнику: {e}")
            return False

        src_cursor = src.cursor()
        src_cursor.execute(query, (cutoff,))
        rows = src_cursor.fetchall()
        row_count = len(rows)
        src.close()

        t_read = datetime.now()
        logger.info(f"   📊 Новых строк: {row_count:,} (за {(t_read - t_start).total_seconds():.1f} сек)")

        if row_count == 0:
            logger.info("   ℹ️ Нет новых данных для добавления")
            return True

        # === Шаг 4: Вставка новых данных ===
        logger.info(f"\n📝 Вставка {row_count:,} строк (пакеты по {BATCH_SIZE:,})...")
        placeholders = ",".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO raw_.TRANSACTION_HISTORY WITH (TABLOCK) ({column_list}) VALUES ({placeholders})"

        t_insert_start = datetime.now()
        inserted = 0
        error_count = 0
        total_batches = (row_count + BATCH_SIZE - 1) // BATCH_SIZE

        for i in range(0, row_count, BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            try:
                dst_cursor.executemany(insert_sql, batch)
                inserted += len(batch)

                if batch_num % 5 == 0 or batch_num == total_batches:
                    elapsed = (datetime.now() - t_insert_start).total_seconds()
                    rows_per_sec = inserted / elapsed if elapsed > 0 else 0
                    logger.info(f"   📦 Пакет {batch_num}/{total_batches}: вставлено {inserted:,}/{row_count:,} ({rows_per_sec:,.0f} строк/сек)")
            except Exception as batch_error:
                error_str = str(batch_error)
                if 'PRIMARY KEY' in error_str or 'duplicate' in error_str.lower():
                    for single_row in batch:
                        try:
                            dst_cursor.execute(insert_sql, single_row)
                            inserted += 1
                        except Exception:
                            error_count += 1
                else:
                    logger.warning(f"   ⚠ Ошибка пакета [{batch_num}]: {batch_error}")
                    error_count += len(batch)

        dst.commit()

        t_insert_end = datetime.now()
        insert_duration = (t_insert_end - t_insert_start).total_seconds()
        rows_per_sec = inserted / insert_duration if insert_duration > 0 else 0

        logger.info(f"   ✅ Вставлено: {inserted:,} строк за {insert_duration:.1f} сек ({rows_per_sec:,.0f} строк/сек)")
        if error_count > 0:
            logger.warning(f"   ⚠ Пропущено из-за ошибок: {error_count:,} строк")

        # === Шаг 5: Финальная проверка ===
        dst_cursor.execute("SELECT COUNT(*) FROM raw_.TRANSACTION_HISTORY WHERE DATE_TIME_STAMP >= CAST(GETDATE() AS DATE)")
        today_count = dst_cursor.fetchone()[0]
        logger.info(f"\n🔍 Проверка: записей за сегодня: {today_count:,}")

        dst_cursor.execute("SELECT COUNT(*) FROM raw_.TRANSACTION_HISTORY")
        total_count = dst_cursor.fetchone()[0]
        logger.info(f"   📊 Всего записей в таблице: {total_count:,}")

        total_duration = (datetime.now() - t_start).total_seconds()
        logger.info(f"\n⏱️ Общее время выполнения: {total_duration:.1f} сек")

        logger.info("\n" + "=" * 80)
        logger.info("✅ ОБНОВЛЕНИЕ TRANSACTION_HISTORY ЗАВЕРШЕНО УСПЕШНО")
        logger.info("=" * 80)

        dst.close()
        return True

    except Exception as e:
        logger.error(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            dst.close()
        except Exception:
            pass

def main():
    logger = setup_logging()
    success = reload_transaction_history(logger)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
