#!/usr/bin/env python3
"""
ПОЛНАЯ ПЕРЕЗАПИСЬ raw_.SHIPMENT_HEADER за ВСЁ время
Использует правильное поле DATE_TIME_STAMP вместо PLANNED_SHIP_DATE
"""

import pymssql
import logging
import os
import sys
from datetime import datetime

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

# === Таблица ===
TABLE_NAME = 'SHIPMENT_HEADER'
TARGET_TABLE = 'SHIPMENT_HEADER'

# Логирование
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    log_file = os.path.join(LOG_DIR, f"reload_shipment_header_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def reload_shipment_header_full(logger):
    """Полная перезапись таблицы SHIPMENT_HEADER (TRUNCATE + INSERT)"""

    logger.info("=" * 80)
    logger.info("🔄 ПОЛНАЯ ПЕРЕЗАПИСЬ raw_.SHIPMENT_HEADER")
    logger.info("   Используется поле DATE_TIME_STAMP (вместо PLANNED_SHIP_DATE)")
    logger.info("=" * 80)

    start_time = datetime.now()
    src = None
    dst = None

    try:
        # Подключение к источнику
        logger.info("1. Подключение к источнику (ILS)...")
        src = pymssql.connect(
            server=SRC_SERVER,
            port=SRC_PORT,
            user=SRC_USER,
            password=SRC_PASSWORD,
            database=SRC_DATABASE,
            tds_version='7.0'
        )
        logger.info("   ✓ Подключение к источнику установлено")

        # Подключение к целевой БД
        logger.info("2. Подключение к целевой БД (olap2_fixed)...")
        dst = pymssql.connect(
            server=DST_SERVER,
            user=DST_USER,
            password=DST_PASSWORD,
            database=DST_DATABASE,
            charset='UTF-8'
        )
        logger.info("   ✓ Подключение к целевой БД установлено")

        src_cursor = src.cursor()
        dst_cursor = dst.cursor()

        # Получаем колонки из целевой таблицы
        logger.info("\n3. Получение структуры таблицы...")
        dst_cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'raw_' AND TABLE_NAME = %s
            AND COLUMN_NAME NOT IN ('ROW_ID', 'row_hash')
            ORDER BY ORDINAL_POSITION
        """, (TARGET_TABLE,))

        columns = [row[0] for row in dst_cursor.fetchall()]
        if not columns:
            logger.error(f"   ❌ Таблица raw_.{TARGET_TABLE} не найдена или не содержит колонок")
            return False

        column_list = ", ".join(columns)
        logger.info(f"   ✓ Найдено колонок: {len(columns)}")

        # Читаем ВСЕ данные из источника
        logger.info("\n4. Чтение данных из источника (ВСЕ данные за всё время)...")
        query = f"SELECT {column_list} FROM {TABLE_NAME}"
        logger.info(f"   Выполняется запрос: {query}")

        src_cursor.execute(query)
        rows = src_cursor.fetchall()
        row_count = len(rows)
        logger.info(f"   ✓ Прочитано строк: {row_count:,}")

        if row_count == 0:
            logger.warning("   ⚠ В источнике нет данных!")
            return True

        # Очищаем целевую таблицу (TRUNCATE)
        logger.info("\n5. Очистка целевой таблицы (TRUNCATE)...")
        dst_cursor.execute(f"TRUNCATE TABLE raw_.{TARGET_TABLE}")
        logger.info(f"   ✓ Таблица raw_.{TARGET_TABLE} полностью очищена")

        # Вставляем данные
        logger.info(f"\n6. Загрузка {row_count:,} строк...")

        placeholders = ",".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO raw_.{TARGET_TABLE} ({column_list}) VALUES ({placeholders})"

        # Загружаем пакетами по 5000 строк
        batch_size = 5000
        loaded_count = 0
        total_batches = (row_count + batch_size - 1) // batch_size

        for i in range(0, row_count, batch_size):
            batch = rows[i:i + batch_size]
            batch_num = i // batch_size + 1

            try:
                dst_cursor.executemany(insert_sql, batch)
                dst.commit()
                loaded_count += len(batch)
                logger.info(f"   ✓ Пакет {batch_num}/{total_batches}: {len(batch):,} строк")
            except Exception as batch_error:
                logger.warning(f"   ⚠ Ошибка в пакете {batch_num}: {batch_error}")
                # Пробуем по одной строке
                for single_row in batch:
                    try:
                        dst_cursor.execute(insert_sql, single_row)
                        loaded_count += 1
                    except Exception as row_error:
                        logger.warning(f"      ⚠ Ошибка строки: {row_error}")
                        continue
                dst.commit()
                logger.info(f"   ✓ Пакет {batch_num} загружен по одной строке")

        # Проверка результата
        logger.info("\n7. Проверка загрузки...")
        dst_cursor.execute(f"SELECT COUNT(*) FROM raw_.{TARGET_TABLE}")
        count_in_target = dst_cursor.fetchone()[0]

        logger.info(f"   Загружено строк: {loaded_count:,}")
        logger.info(f"   Строк в target: {count_in_target:,}")

        if row_count == count_in_target:
            logger.info("   ✅ ПОЛНОЕ СООТВЕТСТВИЕ: все данные загружены")
        else:
            logger.warning(f"   ⚠ НЕСООТВЕТСТВИЕ: source={row_count}, target={count_in_target}")

        # Проверка по датам
        logger.info("\n8. Проверка данных по DATE_TIME_STAMP...")
        dst_cursor.execute(f"""
            SELECT 
                MIN(DATE_TIME_STAMP) AS min_date,
                MAX(DATE_TIME_STAMP) AS max_date,
                COUNT(*) AS total_count
            FROM raw_.{TARGET_TABLE}
            WHERE DATE_TIME_STAMP IS NOT NULL
        """)
        date_row = dst_cursor.fetchone()
        if date_row and date_row[0]:
            logger.info(f"   ✓ Мин. дата: {date_row[0]}")
            logger.info(f"   ✓ Макс. дата: {date_row[1]}")
            logger.info(f"   ✓ Записей с DATE_TIME_STAMP: {date_row[2]:,}")

        # Логирование в etl_log
        logger.info("\n9. Логирование в etl_log...")
        try:
            dst_cursor.execute("""
                IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES
                               WHERE TABLE_SCHEMA = 'raw_' AND TABLE_NAME = 'etl_log')
                CREATE TABLE raw_.etl_log (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    table_name NVARCHAR(100),
                    rows_loaded INT,
                    status NVARCHAR(20),
                    error_message NVARCHAR(MAX),
                    created_date DATETIME DEFAULT GETDATE()
                )
            """)

            dst_cursor.execute("""
                INSERT INTO raw_.etl_log (table_name, rows_loaded, status)
                VALUES (%s, %s, %s)
            """, (TABLE_NAME, loaded_count, 'Success'))

            dst.commit()
            logger.info("   ✅ Лог записан")
        except Exception as log_error:
            logger.warning(f"   ⚠ Ошибка логирования: {log_error}")

        # Итоги
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info("\n" + "=" * 80)
        logger.info("✅ ПОЛНАЯ ПЕРЕЗАПИСЬ ЗАВЕРШЕНА")
        logger.info("=" * 80)
        logger.info(f"Таблица: {TABLE_NAME}")
        logger.info(f"Загружено записей: {loaded_count:,}")
        logger.info(f"Время выполнения: {duration:.2f} сек ({duration/60:.2f} мин)")
        logger.info(f"Дата загрузки: {start_time}")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if src:
            src.close()
        if dst:
            dst.close()


def main():
    logger = setup_logging()

    logger.info("🚀 ЗАПУСК ПОЛНОЙ ПЕРЕЗАПИСИ SHIPMENT_HEADER")
    logger.info("ВНИМАНИЕ: Будет выполнена ПОЛНАЯ перезапись таблицы!")
    logger.info("Используется поле DATE_TIME_STAMP (вместо PLANNED_SHIP_DATE)")

    success = reload_shipment_header_full(logger)

    if success:
        logger.info("\n✅ ГОТОВО! SHIPMENT_HEADER полностью обновлён")
        return 0
    else:
        logger.error("\n❌ ОШИБКА при перезаписи SHIPMENT_HEADER")
        return 1


if __name__ == "__main__":
    sys.exit(main())
