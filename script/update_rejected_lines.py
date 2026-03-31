#!/usr/bin/env python3
"""
Обновление данных об отклонённых строках в заказах
Прямой запрос к ILS.dbo.SHIPMENT_DETAIL → dwh.rejected_lines_detail
Запускается каждые 5 минут
Полная перезапись таблицы (TRUNCATE + INSERT)
"""

import pymssql
from datetime import datetime
import os
import sys

# === Параметры подключения к источнику ILS ===
ILS_SERVER = '10.7.0.248'
ILS_PORT = 1433
ILS_DATABASE = 'ils'
ILS_USER = 'manhreader'
ILS_PASSWORD = 'August2021'

# === Параметры подключения к целевой БД ===
ANALYTICS_SERVER = '10.7.0.27'
ANALYTICS_DATABASE = 'olap2_fixed'
ANALYTICS_USER = 'sa'
ANALYTICS_PASSWORD = 'Rdflhfn600'


def get_ils_connection():
    """Подключение к ILS"""
    return pymssql.connect(
        server=ILS_SERVER,
        port=ILS_PORT,
        user=ILS_USER,
        password=ILS_PASSWORD,
        database=ILS_DATABASE,
        tds_version='7.0'
    )


def get_analytics_connection():
    """Подключение к аналитической базе"""
    return pymssql.connect(
        server=ANALYTICS_SERVER,
        user=ANALYTICS_USER,
        password=ANALYTICS_PASSWORD,
        database=ANALYTICS_DATABASE,
        charset='UTF-8'
    )


def fetch_rejected_lines_from_ils(log):
    """Загрузить отклонённые строки из ILS"""

    conn = get_ils_connection()
    try:
        cursor = conn.cursor()

        # Запрос с фильтрами (как в ТЗ)
        # STATUS1 = '100' — отклонённые строки
        # Исключаем только явный "ОТКАЗ", всё остальное включаем (включая NULL)
        query = """
        SELECT
            sd.SHIPMENT_ID,
            sd.ITEM,
            i.DESCRIPTION AS ITEM_DESC,
            sd.REQUESTED_QTY,
            sd.QUANTITY_UM,
            sd.PICK_LOC,
            sd.PICK_ZONE,
            sd.DATE_TIME_STAMP
        FROM dbo.SHIPMENT_DETAIL sd WITH (NOLOCK)
        LEFT JOIN dbo.ITEM i WITH (NOLOCK)
            ON sd.ITEM COLLATE DATABASE_DEFAULT = i.ITEM COLLATE DATABASE_DEFAULT
        WHERE
            sd.STATUS1 = '100'
            AND (sd.PICK_LOC <> N'ОТКАЗ' OR sd.PICK_LOC IS NULL)
        ORDER BY sd.DATE_TIME_STAMP DESC
        """

        log(f"📤 Запрос к ILS.dbo.SHIPMENT_DETAIL...")
        cursor.execute(query)

        rows = []
        for row in cursor.fetchall():
            rows.append({
                'SHIPMENT_ID': row[0],
                'ITEM': row[1],
                'ITEM_DESC': row[2],
                'REQUESTED_QTY': row[3],
                'QUANTITY_UM': row[4],
                'PICK_LOC': row[5],
                'PICK_ZONE': row[6],
                'DATE_TIME_STAMP': row[7]
            })

        log(f"✅ Найдено отклонённых строк: {len(rows)}")
        return rows

    finally:
        conn.close()


def update_dwh_rejected_lines(rows, log):
    """Обновить dwh.rejected_lines_detail (ПОЛНАЯ ПЕРЕЗАПИСЬ)"""
    
    conn = get_analytics_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Очистка таблицы (TRUNCATE)
        log("🗑️ Очистка dwh.rejected_lines_detail...")
        cursor.execute("TRUNCATE TABLE dwh.rejected_lines_detail")
        log("   ✅ Таблица очищена")
        
        # 2. Вставка данных
        if rows:
            log(f"➕ Вставка {len(rows)} записей...")
            
            insert_query = """
                INSERT INTO dwh.rejected_lines_detail 
                (SHIPMENT_ID, ITEM, ITEM_DESC, REQUESTED_QTY, QUANTITY_UM, PICK_LOC, PICK_ZONE, DATE_TIME_STAMP)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Вставляем пакетами по 100 строк
            batch_size = 100
            inserted_count = 0
            
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(rows) + batch_size - 1) // batch_size
                
                cursor.executemany(insert_query, [
                    (
                        row['SHIPMENT_ID'],
                        row['ITEM'],
                        row['ITEM_DESC'],
                        row['REQUESTED_QTY'],
                        row['QUANTITY_UM'],
                        row['PICK_LOC'],
                        row['PICK_ZONE'],
                        row['DATE_TIME_STAMP']
                    )
                    for row in batch
                ])
                conn.commit()
                
                inserted_count += len(batch)
                log(f"   Пакет {batch_num}/{total_batches}: {len(batch)} записей")
            
            log(f"✅ Вставлено записей: {inserted_count}")
        else:
            log("ℹ️ Нет данных для вставки")
        
        return True
        
    except Exception as e:
        conn.rollback()
        log(f"❌ Ошибка при обновлении: {e}")
        raise
    finally:
        conn.close()


def verify_data(log):
    """Проверить данные после загрузки"""
    
    conn = get_analytics_connection()
    try:
        cursor = conn.cursor()
        
        # Проверить количество записей
        cursor.execute("SELECT COUNT(*) FROM dwh.rejected_lines_detail")
        count = cursor.fetchone()[0]
        log(f"📊 В таблице: {count:,} записей")
        
        # Проверить последние данные
        cursor.execute("""
            SELECT TOP 1 SHIPMENT_ID, DATE_TIME_STAMP 
            FROM dwh.rejected_lines_detail 
            ORDER BY DATE_TIME_STAMP DESC
        """)
        row = cursor.fetchone()
        if row:
            log(f"📍 Последняя запись: {row[0]} ({row[1]})")
        
        return True
        
    except Exception as e:
        log(f"❌ Ошибка проверки: {e}")
        return False
    finally:
        conn.close()


def run_update():
    """Основная функция обновления"""
    
    # Простое логирование в stdout
    def log(message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{timestamp} - INFO - {message}")
    
    log("=" * 70)
    log("🚀 Обновление отклонённых строк (rejected_lines)")
    log("=" * 70)
    log(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)
    
    try:
        # 1. Загрузить данные из ILS
        rows = fetch_rejected_lines_from_ils(log)
        
        # 2. Обновить dwh.rejected_lines_detail
        update_dwh_rejected_lines(rows, log)
        
        # 3. Проверить данные
        verify_data(log)
        
        log("=" * 70)
        log("✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО")
        log("=" * 70)
        
        return True
        
    except Exception as e:
        log(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_update()
    sys.exit(0 if success else 1)
