#!/usr/bin/env python3
"""
Выполняет SQL-скрипт обновления DWH таблиц через sqlcmd.
"""
import subprocess
import logging
import os
import sys
from datetime import datetime

# === Конфигурация ===
DST_SERVER = '10.7.0.27'
DST_DATABASE = 'olap2_fixed'
DST_USER = 'sa'
DST_PASSWORD = 'Rdflhfn600'

# Путь к SQL-файлам
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SQL_FILE_3DAYS = os.path.join(SCRIPT_DIR, 'update_dwh_3days_simple.sql')  # Упрощённая версия
SQL_FILE_7DAYS = os.path.join(SCRIPT_DIR, 'update_dwh_7days.sql')
PROCEDURES_FILE = os.path.join(SCRIPT_DIR, 'update_procedures_3days_full.sql')  # Полный пакет процедур

# Логирование
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging(script_name: str):
    """Настройка логирования"""
    log_file = os.path.join(LOG_DIR, f"{script_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def run_sqlcmd(sql_file: str, logger: logging.Logger) -> bool:
    """
    Выполняет SQL-файл через sqlcmd.
    """
    if not os.path.exists(sql_file):
        logger.error(f"❌ SQL-файл не найден: {sql_file}")
        return False

    logger.info(f"📄 SQL-файл: {sql_file}")
    logger.info(f"🔌 Сервер: {DST_SERVER}/{DST_DATABASE}")

    # Полный путь к sqlcmd (для cron)
    SQLCMD_PATH = '/opt/mssql-tools18/bin/sqlcmd'
    
    # Команда sqlcmd с отключением шифрования
    # Убрали флаг '-b' - sqlcmd возвращает 1 даже при предупреждениях
    cmd = [
        SQLCMD_PATH,
        '-S', DST_SERVER,
        '-U', DST_USER,
        '-P', DST_PASSWORD,
        '-d', DST_DATABASE,
        '-i', sql_file,
        '-C',  # Отключить проверку SSL-сертификата
    ]
    
    logger.info(f"🚀 Запуск sqlcmd...")
    start_time = datetime.now()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,  # Захватываем stdout и stderr
            text=True,
            timeout=3600  # 60 минут максимум
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # ПИШЕМ ВЕСЬ ВЫВОД В ЛОГ (и stdout и stderr)
        if result.stdout:
            logger.info("=== STDOUT (полный вывод): ===")
            for line in result.stdout.split('\n'):
                if line.strip():
                    logger.info(f"  {line}")
        
        if result.stderr:
            logger.info("=== STDERR (ошибки/предупреждения): ===")
            for line in result.stderr.split('\n'):
                if line.strip():
                    logger.info(f"  {line}")
        
        # Проверяем на реальные фатальные ошибки
        has_fatal_error = False
        
        if result.stderr:
            for line in result.stderr.split('\n'):
                # Фатальные ошибки: Level 20+, timeout, connection errors
                if 'Level 20' in line or 'Level 21' in line or 'Level 22' in line:
                    has_fatal_error = True
                    break
                if 'timeout' in line.lower():
                    has_fatal_error = True
                    break
                if 'connection' in line.lower() and 'failed' in line.lower():
                    has_fatal_error = True
                    break
        
        # Если есть "ОБНОВЛЕНИЕ ЗАВЕРШЕНО" в выводе - скрипт выполнился до конца
        script_completed = False
        if result.stdout and 'ОБНОВЛЕНИЕ ЗАВЕРШЕНО' in result.stdout:
            script_completed = True
        
        if script_completed and not has_fatal_error:
            logger.info(f"✅ SQL-скрипт успешно выполнен!")
            logger.info(f"  Время выполнения: {duration:.2f} сек ({duration/60:.2f} мин)")
            return True
        elif has_fatal_error:
            logger.error(f"❌ Фатальная ошибка SQL")
            return False
        else:
            logger.warning(f"⚠️ Скрипт не завершился нормально (код {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Таймаут выполнения (60 минут)")
        return False
    except FileNotFoundError:
        logger.error("❌ sqlcmd не найден! Установите SQL Server Command Line Tools")
        logger.info("  Попробуйте: sudo apt-get install mssql-tools")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return False

def run_update(period_days: int) -> bool:
    """
    Запускает скрипт обновления для указанного периода.
    """
    script_name = f"update_dwh_{period_days}days"
    sql_file = SQL_FILE_3DAYS if period_days == 3 else SQL_FILE_7DAYS

    logger = setup_logging(script_name)

    logger.info("=" * 80)
    logger.info(f"🚀 ЗАПУСК ОБНОВЛЕНИЯ DWH ЗА {period_days} ДНЯ")
    logger.info("=" * 80)
    logger.info(f"📅 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📄 SQL-файл: {sql_file}")
    logger.info("=" * 80)

    # Для 3-дневного: сначала создаём процедуры
    if period_days == 3:
        logger.info("📋 Создание процедур 3-дневного обновления...")
        if os.path.exists(PROCEDURES_FILE):
            logger.info("📄 Файл процедур найден: " + PROCEDURES_FILE)
            proc_success = run_sqlcmd(PROCEDURES_FILE, logger)
            if not proc_success:
                logger.warning("⚠️ Процедуры созданы с предупреждениями, продолжаем...")
        else:
            logger.error("❌ Файл процедур не найден: " + PROCEDURES_FILE)
            return False

    # Запускаем основной скрипт обновления
    success = run_sqlcmd(sql_file, logger)

    logger.info("=" * 80)
    if success:
        logger.info(f"✅ ОБНОВЛЕНИЕ ЗА {period_days} ДНЯ ЗАВЕРШЕНО УСПЕШНО")
    else:
        logger.error(f"❌ ОБНОВЛЕНИЕ ЗА {period_days} ДНЯ ЗАВЕРШЕНО С ОШИБКАМИ")
    logger.info("=" * 80)

    return success

def main():
    """Точка входа"""
    if len(sys.argv) < 2:
        print("Использование: python run_update_dwh.py [3|7]")
        print("  3 - обновить за 3 дня")
        print("  7 - обновить за 7 дней")
        sys.exit(1)
    
    try:
        period = int(sys.argv[1])
        if period not in [3, 7]:
            raise ValueError("Период должен быть 3 или 7")
    except ValueError as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
    
    success = run_update(period)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
