#!/usr/bin/env python3
"""
Обновление dwh.fact_location_snapshot из raw_.LOCATION
Вызывает хранимую процедуру dwh.sp_update_location_snapshot
Запускается каждые 30-60 секунд через Task Scheduler
"""

import pymssql
from datetime import datetime
import logging
import os
import sys

# === Параметры подключения к аналитической БД ===
DST_SERVER = '10.7.0.27'
DST_DATABASE = 'olap2_fixed'
DST_USER = 'sa'
DST_PASSWORD = 'Rdflhfn600'

# === Параметры обновления ===
BUFFER_MINUTES = 5  # Буфер времени на случай задержек
DEBUG_MODE = False  # Режим отладки (показывать детали)

# === Логирование ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    log_file = os.path.join(LOG_DIR, f"update_location_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def call_update_procedure(logger):
    """Вызвать хранимую процедуру обновления"""
    
    logger.info("Подключение к olap2_fixed...")
    
    conn = pymssql.connect(
        server=DST_SERVER,
        user=DST_USER,
        password=DST_PASSWORD,
        database=DST_DATABASE,
        charset='UTF-8'
    )
    
    try:
        cursor = conn.cursor()
        
        logger.info(f"Вызов процедуры dwh.sp_update_location_snapshot (buffer={BUFFER_MINUTES} мин)...")
        
        # Вызвать хранимую процедуру
        cursor.execute("""
            EXEC dwh.sp_update_location_snapshot 
                @buffer_minutes = %s, 
                @debug = %s
        """, (BUFFER_MINUTES, 1 if DEBUG_MODE else 0))
        
        conn.commit()
        
        logger.info("✅ Процедура выполнена успешно")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при выполнении процедуры: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


def verify_update(logger):
    """Проверить, что данные обновились"""
    
    conn = pymssql.connect(
        server=DST_SERVER,
        user=DST_USER,
        password=DST_PASSWORD,
        database=DST_DATABASE,
        charset='UTF-8',
        as_dict=True  # ✅ ВАЖНО: добавляем as_dict=True
    )
    
    try:
        cursor = conn.cursor()
        
        # Проверить количество записей по статусам
        cursor.execute("""
            SELECT status, COUNT(*) AS количество
            FROM dwh.fact_location_snapshot
            GROUP BY status
        """)
        
        rows = cursor.fetchall()
        
        logger.info("📊 Статусы в таблице:")
        for row in rows:
            logger.info(f"   {row['status']}: {row['количество']:,}")
        
        # Проверить последнее время изменения
        cursor.execute("""
            SELECT MAX(last_modified) AS last_ts
            FROM dwh.fact_location_snapshot
            WHERE last_modified IS NOT NULL
        """)
        
        result = cursor.fetchone()
        last_ts = result['last_ts'] if result else None
        
        if last_ts:
            logger.info(f"📍 Последнее изменение: {last_ts}")
        else:
            logger.warning("⚠️ Нет данных о времени изменений")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки: {e}")
        return False
        
    finally:
        conn.close()


def run_update():
    """Основная функция обновления"""
    
    logger = setup_logging()
    logger.info("=" * 70)
    logger.info("🚀 Начало обновления dwh.fact_location_snapshot")
    logger.info("=" * 70)
    logger.info(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Буфер времени: {BUFFER_MINUTES} мин")
    logger.info(f"Режим отладки: {DEBUG_MODE}")
    logger.info("=" * 70)
    
    try:
        # 1. Вызвать процедуру
        success = call_update_procedure(logger)
        
        if not success:
            logger.error("❌ Процедура завершилась с ошибкой")
            return False
        
        # 2. Проверить данные
        verify_update(logger)
        
        logger.info("=" * 70)
        logger.info("✅ Обновление завершено успешно")
        logger.info("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_update()
    sys.exit(0 if success else 1)