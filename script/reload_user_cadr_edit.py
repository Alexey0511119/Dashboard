#!/usr/bin/env python3
"""
Полная перезапись таблицы raw_.USER_CADR_EDIT из sk.USER_CADR_EDIT.

Запускается отдельно (не часть пайплайна).
Полностью очищает и перезаписывает все данные.
"""
import pymssql
from datetime import datetime
import logging
import os
import sys

# === Параметры подключения к источнику (sk) ===
SRC_SERVER = '10.7.0.248'
SRC_PORT = 1433
SRC_DATABASE = 'sk'
SRC_USER = 'manhreader'
SRC_PASSWORD = 'August2021'

# === Параметры подключения к целевой БД ===
DST_SERVER = '10.7.0.27'
DST_DATABASE = 'olap2_fixed'
DST_USER = 'sa'
DST_PASSWORD = 'Rdflhfn600'

# === Логирование ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    log_file = os.path.join(LOG_DIR, f"reload_user_cadr_edit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# === Колонки таблицы USER_CADR_EDIT ===
COLUMNS = [
    'tab_number', 'user_name', 'user_name2', 'fio', 'smena',
    'brigada', 'isBrigadier', 'position', 'user_def1', 'user_def2',
    'user_def3', 'user_def4', 'deleted', 'id', 'old_tab_number'
]

def reload_user_cadr_edit(logger):
    """Полная перезапись raw_.USER_CADR_EDIT из sk.USER_CADR_EDIT"""

    logger.info("=" * 80)
    logger.info("🔄 ПОЛНАЯ ПЕРЕЗАПИСЬ raw_.USER_CADR_EDIT")
    logger.info("=" * 80)
    logger.info(f"📁 Источник: {SRC_SERVER}/{SRC_DATABASE}.USER_CADR_EDIT")
    logger.info(f"🎯 Цель:    {DST_SERVER}/{DST_DATABASE}.raw_.USER_CADR_EDIT")
    logger.info("=" * 80)

    # Подключение к источнику
    try:
        src = pymssql.connect(
            server=SRC_SERVER,
            port=SRC_PORT,
            user=SRC_USER,
            password=SRC_PASSWORD,
            database=SRC_DATABASE,
            tds_version='7.0'
        )
        logger.info("✅ Подключение к источнику (sk) успешно")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к источнику: {e}")
        return False

    # Подключение к целевой БД
    try:
        dst = pymssql.connect(
            server=DST_SERVER,
            user=DST_USER,
            password=DST_PASSWORD,
            database=DST_DATABASE,
            charset='UTF-8'
        )
        logger.info("✅ Подключение к целевой БД (olap2_fixed) успешно")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к целевой БД: {e}")
        src.close()
        return False

    try:
        src_cursor = src.cursor()
        dst_cursor = dst.cursor()

        # === Шаг 1: Читаем все данные из источника ===
        logger.info("\n📥 Чтение данных из sk.USER_CADR_EDIT...")
        column_list = ", ".join(COLUMNS)
        query = f"SELECT {column_list} FROM USER_CADR_EDIT"

        src_cursor.execute(query)
        rows = src_cursor.fetchall()
        row_count = len(rows)
        logger.info(f"   📊 Прочитано строк: {row_count:,}")

        if row_count == 0:
            logger.warning("⚠️ Источник пуст — нет данных для перезаписи")
            return False

        # === Шаг 2: Полное удаление целевой таблицы ===
        logger.info("\n🗑️ Очистка raw_.USER_CADR_EDIT...")
        dst_cursor.execute("DELETE FROM raw_.USER_CADR_EDIT")
        deleted = dst_cursor.rowcount
        dst.commit()
        logger.info(f"   📤 Удалено строк: {deleted:,}")

        # === Шаг 3: Вставка всех данных ===
        logger.info(f"\n📝 Вставка {row_count:,} строк в raw_.USER_CADR_EDIT...")
        placeholders = ",".join(["%s"] * len(COLUMNS))
        insert_sql = f"INSERT INTO raw_.USER_CADR_EDIT ({column_list}) VALUES ({placeholders})"

        insert_start = datetime.now()
        batch_size = 1000
        inserted = 0
        error_count = 0

        for i in range(0, row_count, batch_size):
            batch = rows[i:i + batch_size]
            try:
                dst_cursor.executemany(insert_sql, batch)
                inserted += len(batch)
            except Exception as batch_error:
                error_str = str(batch_error)
                if 'PRIMARY KEY' in error_str or 'duplicate' in error_str.lower():
                    # Вставляем по одной строке, пропуская дубликаты
                    for single_row in batch:
                        try:
                            dst_cursor.execute(insert_sql, single_row)
                            inserted += 1
                        except Exception:
                            error_count += 1
                else:
                    logger.warning(f"   ⚠ Ошибка пакета [{i//batch_size + 1}]: {batch_error}")
                    error_count += len(batch)

        dst.commit()

        insert_end = datetime.now()
        insert_duration = (insert_end - insert_start).total_seconds()
        rows_per_sec = inserted / insert_duration if insert_duration > 0 else 0

        logger.info(f"   ✅ Вставлено: {inserted:,} строк за {insert_duration:.2f} сек ({rows_per_sec:,.0f} строк/сек)")
        if error_count > 0:
            logger.warning(f"   ⚠ Пропущено из-за ошибок: {error_count:,} строк")

        # === Шаг 4: Проверка целостности ===
        dst_cursor.execute("SELECT COUNT(*) FROM raw_.USER_CADR_EDIT")
        count_after = dst_cursor.fetchone()[0]
        logger.info(f"\n🔍 Проверка: в raw_.USER_CADR_EDIT теперь {count_after:,} строк")

        if count_after < row_count * 0.9:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Вставлено только {count_after} из {row_count} строк ({count_after*100//row_count}%)!")
            return False

        # === Шаг 5: Статистика по сменам и бригадам ===
        logger.info("\n📊 Статистика:")
        dst_cursor.execute("""
            SELECT smena, COUNT(*) AS cnt
            FROM raw_.USER_CADR_EDIT
            WHERE deleted = 0 OR deleted IS NULL
            GROUP BY smena
            ORDER BY smena
        """)
        for row in dst_cursor.fetchall():
            logger.info(f"   Смена {row[0]}: {row[1]} активных сотрудников")

        dst_cursor.execute("""
            SELECT brigada, COUNT(*) AS cnt
            FROM raw_.USER_CADR_EDIT
            WHERE deleted = 0 OR deleted IS NULL
            GROUP BY brigada
            ORDER BY brigada
        """)
        for row in dst_cursor.fetchall():
            logger.info(f"   Бригада '{row[0]}': {row[1]} сотрудников")

        logger.info("\n" + "=" * 80)
        logger.info("✅ ПЕРЕЗАПИСЬ USER_CADR_EDIT ЗАВЕРШЕНА УСПЕШНО")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        src.close()
        dst.close()

def main():
    logger = setup_logging()

    start_time = datetime.now()
    success = reload_user_cadr_edit(logger)
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"⏱️ Общее время: {duration:.2f} сек")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
