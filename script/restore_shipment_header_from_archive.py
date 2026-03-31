#!/usr/bin/env python3
"""
ВОССТАНОВЛЕНИЕ raw_.SHIPMENT_HEADER из архива AR_SHIPMENT_HEADER
Выгружает данные порциями по 4 месяца (чтобы не нагружать основную базу)
НЕ удаляет существующие данные - только INSERT!
"""

import pymssql
import logging
import os
import sys
from datetime import datetime, timedelta

# === Параметры подключения к источнику (основная база) ===
SRC_SERVER = '10.7.0.248'
SRC_PORT = 1433
SRC_DATABASE = 'ils'
SRC_USER = 'manhreader'
SRC_PASSWORD = 'August2021'

# === Параметры подключения к целевой БД (аналитическая) ===
DST_SERVER = '10.7.0.27'
DST_DATABASE = 'olap2_fixed'
DST_USER = 'sa'
DST_PASSWORD = 'Rdflhfn600'

# === Период выгрузки ===
# Скрипт автоматически определит последнюю загруженную дату
# и продолжит с неё. Можно указать принудительно через аргументы.
DEFAULT_START_DATE = None  # None = автоматически определить
MONTHS_PER_RUN = 4  # Сколько месяцев выгружать за один запуск

# Таблицы
SRC_TABLE = 'AR_SHIPMENT_HEADER'  # Архивная таблица в основной базе
DST_TABLE = 'SHIPMENT_HEADER'      # Целевая таблица в аналитической базе

# Логирование
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    log_file = os.path.join(LOG_DIR, f"restore_shipment_header_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def get_last_loaded_date(dst_cursor, logger):
    """Определить последнюю загруженную дату в целевой таблице"""
    try:
        logger.info("📊 Определение последней загруженной даты...")
        dst_cursor.execute("""
            SELECT MAX(DATE_TIME_STAMP) AS last_date
            FROM raw_.SHIPMENT_HEADER
            WHERE DATE_TIME_STAMP IS NOT NULL
        """)
        result = dst_cursor.fetchone()
        if result and result[0]:
            last_date = result[0]
            logger.info(f"   ✓ Последняя загруженная дата: {last_date}")
            return last_date
        else:
            logger.info("   ℹ️  Таблица пустая, начинаем с 2024-01-01")
            return datetime(2024, 1, 1)
    except Exception as e:
        logger.warning(f"   ⚠ Не удалось определить последнюю дату: {e}")
        logger.info("   ℹ️  Начинаем с 2024-01-01")
        return datetime(2024, 1, 1)


def get_date_range_from_args(dst_cursor, logger):
    """Получить период из аргументов командной строки или определить автоматически"""
    from datetime import timedelta
    
    # Если указаны аргументы - используем их
    if len(sys.argv) >= 3:
        start_date = datetime.strptime(sys.argv[1], '%Y-%m-%d')
        end_date = datetime.strptime(sys.argv[2], '%Y-%m-%d')
        logger.info(f"📅 Период указан в аргументах: {start_date.date()} по {end_date.date()}")
        return start_date, end_date
    
    # Иначе определяем автоматически
    # Проверяем данные в таблице ИГНОРИРУЯ 2026 год (это свежие данные из ILS)
    logger.info("📊 Проверка архивных данных в таблице (игнорируем 2026 год)...")
    dst_cursor.execute("""
        SELECT 
            MIN(DATE_TIME_STAMP) AS min_date,
            MAX(DATE_TIME_STAMP) AS max_date
        FROM raw_.SHIPMENT_HEADER
        WHERE DATE_TIME_STAMP IS NOT NULL
          AND DATE_TIME_STAMP < '2026-01-01'
    """)
    result = dst_cursor.fetchone()
    
    if result and result[0]:
        min_date = result[0]
        max_date = result[1]
        logger.info(f"   ✓ Минимальная архивная дата: {min_date}")
        logger.info(f"   ✓ Максимальная архивная дата: {max_date}")
        
        # Архив уже загружен, продолжаем с максимальной даты
        logger.info("   ✓ Архив уже загружен, продолжаем с последней архивной даты")
        start_date = max_date + timedelta(days=1)
    else:
        logger.info("   ⚠️  Архивных данных за 2024-2025 не найдено")
        logger.info("   ℹ️  Начинаем загрузку архива с 2024-01-01")
        start_date = datetime(2024, 1, 1)
    
    # Конец периода - через 4 месяца
    end_date = start_date + timedelta(days=MONTHS_PER_RUN * 30)
    
    # Округляем до конца месяца
    end_date = end_date.replace(day=1) + timedelta(days=31)
    end_date = end_date.replace(day=1)
    
    logger.info(f"📅 Автоматически определённый период: {start_date.date()} по {end_date.date()}")
    
    return start_date, end_date


def restore_shipment_header(logger):
    """Восстановление данных из архива за указанный период"""

    start_time = datetime.now()
    src = None
    dst = None

    try:
        # Подключение к целевой БД (для определения периода)
        logger.info("=" * 80)
        logger.info("🔄 ВОССТАНОВЛЕНИЕ raw_.SHIPMENT_HEADER из AR_SHIPMENT_HEADER")
        logger.info("=" * 80)
        
        logger.info("1. Подключение к целевой БД (для определения периода)...")
        dst = pymssql.connect(
            server=DST_SERVER,
            user=DST_USER,
            password=DST_PASSWORD,
            database=DST_DATABASE,
            charset='UTF-8'
        )
        dst_cursor = dst.cursor()
        logger.info("   ✓ Подключение установлено")
        
        # Определяем период
        start_date, end_date = get_date_range_from_args(dst_cursor, logger)
        
        # Закрываем подключение (оно будет reopened ниже)
        dst.close()
        
        logger.info(f"⚠️  Режим: ТОЛЬКО INSERT (существующие данные НЕ удаляются)")
        logger.info("=" * 80)

        # Подключение к источнику
        logger.info("2. Подключение к источнику (ILS.AR_SHIPMENT_HEADER)...")
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
        logger.info("3. Подключение к целевой БД (olap2_fixed)...")
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
        """, (DST_TABLE,))

        columns = [row[0] for row in dst_cursor.fetchall()]
        if not columns:
            logger.error(f"   ❌ Таблица raw_.{DST_TABLE} не найдена или не содержит колонок")
            return False

        column_list = ", ".join(columns)
        logger.info(f"   ✓ Найдено колонок: {len(columns)}")

        # Считаем количество записей в источнике
        logger.info("\n4. Подсчёт записей в источнике...")
        count_query = f"""
            SELECT COUNT(*) 
            FROM {SRC_TABLE}
            WHERE DATE_TIME_STAMP >= %s AND DATE_TIME_STAMP < %s
        """
        src_cursor.execute(count_query, (start_date, end_date))
        source_count = src_cursor.fetchone()[0]
        logger.info(f"   📊 Найдено записей в источнике: {source_count:,}")

        if source_count == 0:
            logger.warning("   ⚠ В источнике нет данных за указанный период!")
            return True

        # Считаем количество записей в целевой таблице (для проверки дублей)
        logger.info("\n5. Проверка существующих данных в целевой таблице...")
        dst_cursor.execute(f"""
            SELECT COUNT(*) 
            FROM raw_.{DST_TABLE}
            WHERE DATE_TIME_STAMP >= %s AND DATE_TIME_STAMP < %s
        """, (start_date, end_date))
        target_count = dst_cursor.fetchone()[0]
        logger.info(f"   📊 Уже есть записей в target: {target_count:,}")

        if target_count > 0:
            logger.warning(f"   ⚠️  ВНИМАНИЕ: В target уже есть {target_count:,} записей за этот период!")
            logger.warning(f"   ⚠️  Новые данные будут вставлены (возможны дубликаты по SHIPMENT_ID)")

        # Читаем данные из источника
        logger.info("\n6. Чтение данных из источника...")
        select_query = f"""
            SELECT {column_list}
            FROM {SRC_TABLE}
            WHERE DATE_TIME_STAMP >= %s AND DATE_TIME_STAMP < %s
            ORDER BY DATE_TIME_STAMP
        """
        src_cursor.execute(select_query, (start_date, end_date))
        rows = src_cursor.fetchall()
        row_count = len(rows)
        logger.info(f"   ✓ Прочитано строк: {row_count:,}")

        if row_count == 0:
            logger.warning("   ⚠ Данные не найдены!")
            return True

        # Вставляем данные (без удаления!)
        logger.info(f"\n7. Вставка {row_count:,} строк (INSERT, без удаления)...")

        placeholders = ",".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO raw_.{DST_TABLE} ({column_list}) VALUES ({placeholders})"

        # Вставляем пакетами по 5000 строк
        batch_size = 5000
        inserted_count = 0
        error_count = 0
        duplicate_count = 0

        for i in range(0, row_count, batch_size):
            batch = rows[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (row_count + batch_size - 1) // batch_size

            try:
                dst_cursor.executemany(insert_sql, batch)
                inserted_count += len(batch)
                logger.info(f"   ✓ Пакет {batch_num}/{total_batches}: {len(batch):,} строк")
            except Exception as batch_error:
                error_str = str(batch_error)
                if 'PRIMARY KEY' in error_str or 'duplicate' in error_str.lower():
                    # Дубликаты - вставляем по одной строке
                    logger.warning(f"   ⚠ Пакет {batch_num}: обнаружены дубликаты, вставляем по одной строке...")
                    for single_row in batch:
                        try:
                            dst_cursor.execute(insert_sql, single_row)
                            inserted_count += 1
                        except Exception as row_error:
                            if 'PRIMARY KEY' in str(row_error) or 'duplicate' in str(row_error).lower():
                                duplicate_count += 1
                            else:
                                error_count += 1
                                logger.warning(f"      ⚠ Ошибка строки: {row_error}")
                else:
                    error_count += len(batch)
                    logger.warning(f"   ⚠ Ошибка пакета {batch_num}: {batch_error}")

        dst.commit()

        # Итоги
        logger.info(f"\n✅ Вставлено записей: {inserted_count:,}")
        logger.info(f"⚠️  Пропущено дубликатов: {duplicate_count:,}")
        logger.info(f"❌ Ошибок: {error_count:,}")

        # Финальная проверка
        logger.info("\n8. Финальная проверка...")
        dst_cursor.execute(f"""
            SELECT COUNT(*) 
            FROM raw_.{DST_TABLE}
            WHERE DATE_TIME_STAMP >= %s AND DATE_TIME_STAMP < %s
        """, (start_date, end_date))
        final_count = dst_cursor.fetchone()[0]
        logger.info(f"   📊 Итого записей в target за период: {final_count:,}")

        # Общая статистика по таблице
        logger.info("\n9. Общая статистика по таблице...")
        dst_cursor.execute(f"""
            SELECT 
                MIN(DATE_TIME_STAMP) AS min_date,
                MAX(DATE_TIME_STAMP) AS max_date,
                COUNT(*) AS total_count
            FROM raw_.{DST_TABLE}
            WHERE DATE_TIME_STAMP IS NOT NULL
        """)
        stats = dst_cursor.fetchone()
        if stats and stats[0]:
            logger.info(f"   ✓ Всего записей: {stats[2]:,}")
            logger.info(f"   ✓ Мин. дата: {stats[0]}")
            logger.info(f"   ✓ Макс. дата: {stats[1]}")

        # Итоги
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info("\n" + "=" * 80)
        logger.info("✅ ВОССТАНОВЛЕНИЕ ЗАВЕРШЕНО")
        logger.info("=" * 80)
        logger.info(f"Период: {start_date} по {end_date}")
        logger.info(f"Вставлено записей: {inserted_count:,}")
        logger.info(f"Пропущено дубликатов: {duplicate_count:,}")
        logger.info(f"Время выполнения: {duration:.2f} сек ({duration/60:.2f} мин)")
        logger.info("=" * 80)

        # Подсказка для следующего запуска
        logger.info("\n📋 СЛЕДУЮЩИЙ ЗАПУСК:")
        logger.info(f"   python restore_shipment_header_from_archive.py {end_date} 2024-08-31")
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

    logger.info("🚀 ВОССТАНОВЛЕНИЕ SHIPMENT_HEADER ИЗ АРХИВА")
    logger.info("📅 Период будет определён автоматически (или указан в аргументах)")
    logger.info("⚠️  Режим: ТОЛЬКО INSERT (существующие данные НЕ удаляются)")

    success = restore_shipment_header(logger)

    if success:
        logger.info("\n✅ ГОТОВО! Данные восстановлены")
        logger.info("\n📋 ДЛЯ СЛЕДУЮЩЕГО ЗАПУСКА:")
        logger.info("   Просто выполните: python restore_shipment_header_from_archive.py")
        logger.info("   Скрипт автоматически продолжит с последней даты")
        return 0
    else:
        logger.error("\n❌ ОШИБКА при восстановлении")
        return 1


if __name__ == "__main__":
    sys.exit(main())
