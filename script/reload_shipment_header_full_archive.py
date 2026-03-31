#!/usr/bin/env python3
"""
ПОЛНАЯ ПЕРЕЗАПИСЬ raw_.SHIPMENT_HEADER за ВСЁ время (с 01.01.2024 по сегодня)
Источники:
1. AR_SHIPMENT_HEADER (архив) - данные до 2026 года
2. SHIPMENT_HEADER (актуальная) - данные за 2026 год

Внимание: Таблица будет полностью очищена перед загрузкой!
"""

import pymssql
import logging
import os
import sys
from datetime import datetime, timedelta

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

# === Период выгрузки ===
START_DATE = '2024-01-01'  # Начало периода
END_DATE = datetime.now().strftime('%Y-%m-%d')  # Сегодня

# Таблицы
SRC_ARCHIVE_TABLE = 'AR_SHIPMENT_HEADER'  # Архивная таблица
SRC_CURRENT_TABLE = 'SHIPMENT_HEADER'      # Актуальная таблица
DST_TABLE = 'SHIPMENT_HEADER'              # Целевая таблица

# Логирование
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    log_file = os.path.join(LOG_DIR, f"reload_shipment_header_full_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def load_data_from_source(src_cursor, dst, dst_cursor, table_name, date_from, date_to, logger, columns=None):
    """Загрузка данных из указанной таблицы"""
    
    logger.info(f"\n📥 Загрузка из {table_name} ({date_from} по {date_to})...")
    
    # Получаем колонки (только один раз для первой таблицы)
    if columns is None:
        dst_cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'raw_' AND TABLE_NAME = %s
            AND COLUMN_NAME NOT IN ('ROW_ID', 'row_hash')
            ORDER BY ORDINAL_POSITION
        """, (DST_TABLE,))
        
        columns = [row[0] for row in dst_cursor.fetchall()]
        if not columns:
            logger.error(f"   ❌ Таблица raw_.{DST_TABLE} не найдена")
            return 0, []
        
        logger.info(f"   ✓ Найдено колонок: {len(columns)}")
    
    column_list = ", ".join(columns)
    
    # Считаем количество записей
    count_query = f"""
        SELECT COUNT(*) 
        FROM {table_name}
        WHERE DATE_TIME_STAMP >= %s AND DATE_TIME_STAMP < %s
    """
    src_cursor.execute(count_query, (date_from, date_to))
    source_count = src_cursor.fetchone()[0]
    logger.info(f"   📊 Найдено записей: {source_count:,}")
    
    if source_count == 0:
        logger.info("   ℹ️  Нет данных за указанный период")
        return 0, columns
    
    # Читаем данные
    select_query = f"""
        SELECT {column_list}
        FROM {table_name}
        WHERE DATE_TIME_STAMP >= %s AND DATE_TIME_STAMP < %s
        ORDER BY DATE_TIME_STAMP
    """
    src_cursor.execute(select_query, (date_from, date_to))
    rows = src_cursor.fetchall()
    logger.info(f"   ✓ Прочитано строк: {len(rows):,}")
    
    # Вставляем данные
    if rows:
        placeholders = ",".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO raw_.{DST_TABLE} ({column_list}) VALUES ({placeholders})"
        
        batch_size = 10000
        inserted_count = 0
        error_count = 0
        duplicate_count = 0
        
        logger.info(f"   📊 Вставка {len(rows):,} строк (пакеты по {batch_size:,})...")
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(rows) + batch_size - 1) // batch_size
            
            try:
                dst_cursor.executemany(insert_sql, batch)
                inserted_count += len(batch)
                logger.info(f"      Пакет {batch_num}/{total_batches}: {len(batch):,} строк")
            except Exception as batch_error:
                error_str = str(batch_error)
                if 'PRIMARY KEY' in error_str or 'duplicate' in error_str.lower():
                    logger.warning(f"      ⚠ Пакет {batch_num}: обнаружены дубликаты...")
                    for single_row in batch:
                        try:
                            dst_cursor.execute(insert_sql, single_row)
                            inserted_count += 1
                        except Exception as row_error:
                            if 'PRIMARY KEY' in str(row_error) or 'duplicate' in str(row_error).lower():
                                duplicate_count += 1
                            else:
                                error_count += 1
                else:
                    error_count += len(batch)
                    logger.warning(f"      ⚠ Ошибка пакета {batch_num}: {batch_error}")
        
        dst.commit()
        logger.info(f"   ✅ Вставлено: {inserted_count:,} | Дубликатов: {duplicate_count:,} | Ошибок: {error_count:,}")
        
        return inserted_count, columns
    
    return 0, columns


def reload_shipment_header_full(logger):
    """Полная перезапись таблицы SHIPMENT_HEADER"""

    logger.info("=" * 80)
    logger.info("🔄 ПОЛНАЯ ПЕРЕЗАПИСЬ raw_.SHIPMENT_HEADER")
    logger.info(f"   Период: {START_DATE} по {END_DATE}")
    logger.info(f"   Источники: AR_SHIPMENT_HEADER (архив) + SHIPMENT_HEADER (актуальная)")
    logger.info("   ⚠️  ВНИМАНИЕ: Таблица будет полностью очищена!")
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

        # Очищаем целевую таблицу (TRUNCATE)
        logger.info("\n3. ⚠️  Очистка целевой таблицы (TRUNCATE)...")
        dst_cursor.execute(f"TRUNCATE TABLE raw_.{DST_TABLE}")
        logger.info(f"   ✓ Таблица raw_.{DST_TABLE} полностью очищена")

        # ЗАГРУЗКА ИЗ АРХИВА (до 2026 года)
        logger.info("\n" + "=" * 80)
        logger.info("📂 ЗАГРУЗКА ИЗ АРХИВА (AR_SHIPMENT_HEADER)")
        logger.info("=" * 80)
        
        total_inserted = 0
        columns = []
        
        # Загружаем из архива по 4 месяца
        current_date = datetime.strptime(START_DATE, '%Y-%m-%d')
        end_date = datetime.strptime(END_DATE, '%Y-%m-%d')
        
        batch_num = 0
        columns = None  # Ещё не получены
        
        while current_date < end_date:
            batch_num += 1
            period_end = current_date + timedelta(days=4 * 30)  # 4 месяца
            if period_end > end_date:
                period_end = end_date
            
            logger.info(f"\n📦 Пакет {batch_num}: {current_date.date()} по {period_end.date()}")
            
            inserted, columns = load_data_from_source(
                src_cursor, dst, dst_cursor, 
                SRC_ARCHIVE_TABLE,
                current_date.strftime('%Y-%m-%d'),
                period_end.strftime('%Y-%m-%d'),
                logger,
                columns=columns  # Передаём columns (None для первого раза)
            )
            
            total_inserted += inserted
            current_date = period_end
        
        # ЗАГРУЗКА ИЗ АКТУАЛЬНОЙ (2026 год)
        logger.info("\n" + "=" * 80)
        logger.info("📂 ЗАГРУЗКА ИЗ АКТУАЛЬНОЙ ТАБЛИЦЫ (SHIPMENT_HEADER)")
        logger.info("=" * 80)
        
        inserted, columns = load_data_from_source(
            src_cursor, dst, dst_cursor,
            SRC_CURRENT_TABLE,
            '2026-01-01',
            END_DATE,
            logger,
            columns=columns  # Используем те же columns
        )
        
        total_inserted += inserted

        # Финальная проверка
        logger.info("\n" + "=" * 80)
        logger.info("📊 ФИНАЛЬНАЯ ПРОВЕРКА")
        logger.info("=" * 80)
        
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
            logger.info(f"   ✅ Загружено за период: {START_DATE} по {END_DATE}")
        else:
            logger.warning("   ⚠️  Таблица пуста после загрузки!")

        # Итоги
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info("\n" + "=" * 80)
        logger.info("✅ ПОЛНАЯ ПЕРЕЗАПИСЬ ЗАВЕРШЕНА")
        logger.info("=" * 80)
        logger.info(f"Всего загружено записей: {total_inserted:,}")
        logger.info(f"Время выполнения: {duration:.2f} сек ({duration/60:.2f} мин)")
        logger.info(f"Период данных: {START_DATE} по {END_DATE}")
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

    logger.info("🚀 ПОЛНАЯ ПЕРЕЗАПИСЬ SHIPMENT_HEADER ИЗ АРХИВА И АКТУАЛЬНОЙ ТАБЛИЦЫ")
    logger.info(f"📅 Период: {START_DATE} по {END_DATE}")
    logger.info("⚠️  ВНИМАНИЕ: Таблица raw_.SHIPMENT_HEADER будет полностью очищена!")
    
    response = input("\nВы уверены? Введите 'YES' для продолжения: ")
    if response != 'YES':
        logger.info("❌ Операция отменена пользователем")
        return 1

    success = reload_shipment_header_full(logger)

    if success:
        logger.info("\n✅ ГОТОВО! Таблица полностью обновлена")
        return 0
    else:
        logger.error("\n❌ ОШИБКА при перезаписи")
        return 1


if __name__ == "__main__":
    sys.exit(main())
