#!/usr/bin/env python3
"""
ОРКЕСТРАТОР: Запускает весь 3-дневный ETL пайплайн последовательно.

Порядок выполнения:
1. reload_3days.py       - Обновляет сырые данные в raw_.таблицах за 3 дня
2. reload_locations.py   - Полная перезапись LOCATION_INVENTORY
3. run_update_dwh.py 3   - Обновляет аналитические таблицы dwh.* и dm.*

Все шаги выполняются в одном процессе. При ошибке любого шага - остановка.
"""
import sys
import os
import logging
import subprocess
from datetime import datetime
from typing import Callable, Tuple

# === Конфигурация ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Скрипты
RELOAD_3DAYS_SCRIPT = os.path.join(SCRIPT_DIR, 'reload_3days.py')  # 3-дневная версия
RELOAD_7DAYS_SCRIPT = os.path.join(SCRIPT_DIR, 'reload_7days.py')  # 7-дневная версия
RELOAD_LOCATIONS_SCRIPT = os.path.join(SCRIPT_DIR, 'reload_locations.py')
RUN_UPDATE_DWH_SCRIPT = os.path.join(SCRIPT_DIR, 'run_update_dwh.py')

# === Логирование ===
def setup_logging():
    """Настройка логирования"""
    log_file = os.path.join(LOG_DIR, f"pipeline_3days_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# === Шаг 1: Обновление сырых данных ===
def step1_reload_raw_data(logger: logging.Logger) -> Tuple[bool, str]:
    """
    ШАГ 1: Обновление сырых данных в raw_.таблицах за 3 дня.
    """
    logger.info("=" * 80)
    logger.info("ШАГ 1: Обновление сырых данных (reload_3days.py)")
    logger.info("=" * 80)

    if not os.path.exists(RELOAD_3DAYS_SCRIPT):
        return False, f"Скрипт не найден: {RELOAD_3DAYS_SCRIPT}"

    try:
        logger.info(f"🚀 Запуск: {RELOAD_3DAYS_SCRIPT}")
        logger.info("-" * 80)
        
        # Запускаем с онлайн-выводом
        process = subprocess.Popen(
            [sys.executable, RELOAD_3DAYS_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Читаем вывод в реальном времени
        for line in process.stdout:
            line = line.strip()
            if line:
                logger.info(f"  {line}")
        
        process.wait()
        
        logger.info("-" * 80)
        
        if process.returncode == 0:
            logger.info("✅ ШАГ 1 завершён успешно")
            return True, "OK"
        else:
            logger.error(f"❌ ШАГ 1 завершился с ошибкой (код {process.returncode})")
            return False, f"reload_3days.py failed with code {process.returncode}"
            
    except subprocess.TimeoutExpired:
        logger.error("❌ ШАГ 1 превысил таймаут (30 минут)")
        return False, "Timeout expired"
    except Exception as e:
        logger.error(f"❌ Ошибка ШАГ 1: {e}")
        return False, str(e)

# === Шаг 2: Обновление локаций ===
def step2_reload_locations(logger: logging.Logger) -> Tuple[bool, str]:
    """
    ШАГ 2: Полная перезапись LOCATION_INVENTORY.
    """
    logger.info("=" * 80)
    logger.info("ШАГ 2: Перезапись LOCATION_INVENTORY (reload_locations.py)")
    logger.info("=" * 80)

    if not os.path.exists(RELOAD_LOCATIONS_SCRIPT):
        return False, f"Скрипт не найден: {RELOAD_LOCATIONS_SCRIPT}"

    try:
        logger.info(f"🚀 Запуск: {RELOAD_LOCATIONS_SCRIPT}")
        logger.info("-" * 80)
        
        # Запускаем с онлайн-выводом
        process = subprocess.Popen(
            [sys.executable, RELOAD_LOCATIONS_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Читаем вывод в реальном времени
        for line in process.stdout:
            line = line.strip()
            if line:
                logger.info(f"  {line}")
        
        process.wait()
        
        logger.info("-" * 80)
        
        if process.returncode == 0:
            logger.info("✅ ШАГ 2 завершён успешно")
            return True, "OK"
        else:
            logger.error(f"❌ ШАГ 2 завершился с ошибкой (код {process.returncode})")
            return False, f"reload_locations.py failed with code {process.returncode}"

    except subprocess.TimeoutExpired:
        logger.error("❌ ШАГ 2 превысил таймаут (30 минут)")
        return False, "Timeout expired"
    except Exception as e:
        logger.error(f"❌ Ошибка ШАГ 2: {e}")
        return False, str(e)

# === Шаг 3: Обновление DWH таблиц ===
def step3_update_dwh_tables(logger: logging.Logger) -> Tuple[bool, str]:
    """
    ШАГ 3: Обновление аналитических таблиц dwh.* и dm.* за 3 дня.
    """
    logger.info("=" * 80)
    logger.info("ШАГ 3: Обновление DWH таблиц (run_update_dwh.py 3)")
    logger.info("=" * 80)

    if not os.path.exists(RUN_UPDATE_DWH_SCRIPT):
        return False, f"Скрипт не найден: {RUN_UPDATE_DWH_SCRIPT}"

    try:
        logger.info(f"🚀 Запуск: {RUN_UPDATE_DWH_SCRIPT} 3")
        logger.info("-" * 80)
        
        # Запускаем с онлайн-выводом
        process = subprocess.Popen(
            [sys.executable, RUN_UPDATE_DWH_SCRIPT, '3'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Читаем вывод в реальном времени
        for line in process.stdout:
            line = line.strip()
            if line:
                logger.info(f"  {line}")
        
        process.wait()
        
        logger.info("-" * 80)
        
        if process.returncode == 0:
            logger.info("✅ ШАГ 3 завершён успешно")
            return True, "OK"
        else:
            logger.error(f"❌ ШАГ 3 завершился с ошибкой (код {process.returncode})")
            return False, f"run_update_dwh.py failed with code {process.returncode}"

    except subprocess.TimeoutExpired:
        logger.error("❌ ШАГ 3 превысил таймаут (60 минут)")
        return False, "Timeout expired"
    except Exception as e:
        logger.error(f"❌ Ошибка ШАГ 3: {e}")
        return False, str(e)

# === Основной пайплайн ===
def run_pipeline() -> bool:
    """
    Запускает весь пайплайн из 3 шагов.
    """
    logger = setup_logging()
    
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 20 + "3-ДНЕВНЫЙ ETL ПАЙПЛАЙН" + " " * 33 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info(f"📅 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📁 Директория: {SCRIPT_DIR}")
    logger.info("=" * 80)
    
    start_time = datetime.now()
    
    # ШАГ 1
    success, message = step1_reload_raw_data(logger)
    if not success:
        logger.error(f"🛑 ПАЙПЛАЙН ОСТАНОВЛЕН на ШАГЕ 1: {message}")
        return False
    logger.info("")
    
    # ШАГ 2
    success, message = step2_reload_locations(logger)
    if not success:
        logger.error(f"🛑 ПАЙПЛАЙН ОСТАНОВЛЕН на ШАГЕ 2: {message}")
        return False
    logger.info("")
    
    # ШАГ 3
    success, message = step3_update_dwh_tables(logger)
    if not success:
        logger.error(f"🛑 ПАЙПЛАЙН ОСТАНОВЛЕН на ШАГЕ 3: {message}")
        return False
    logger.info("")
    
    # Итоги
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 25 + "ПАЙПЛАЙН ЗАВЕРШЁН" + " " * 32 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info(f"✅ Все шаги выполнены успешно")
    logger.info(f"⏱️ Общее время: {duration:.2f} сек ({duration/60:.2f} мин)")
    logger.info(f"📅 Время завершения: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    return True

# === 7-дневный пайплайн ===
def run_pipeline_7days() -> bool:
    """
    Запускает 7-дневный пайплайн (для запуска в 23:59).
    """
    logger = setup_logging()
    
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 20 + "7-ДНЕВНЫЙ ETL ПАЙПЛАЙН" + " " * 33 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info(f"📅 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    start_time = datetime.now()
    
    # ШАГ 1: reload_7days.py
    logger.info("=" * 80)
    logger.info("ШАГ 1: Обновление сырых данных (reload_7days.py)")
    logger.info("=" * 80)
    
    reload_7days_script = os.path.join(SCRIPT_DIR, 'reload_7days.py')
    if not os.path.exists(reload_7days_script):
        logger.error(f"Скрипт не найден: {reload_7days_script}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, reload_7days_script],
            capture_output=True,
            text=True,
            timeout=1800
        )
        
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                logger.info(f"  {line}")
        
        if result.returncode != 0:
            logger.error(f"❌ ШАГ 1 завершился с ошибкой (код {result.returncode})")
            return False
            
        logger.info("✅ ШАГ 1 завершён успешно")
        
    except Exception as e:
        logger.error(f"❌ Ошибка ШАГ 1: {e}")
        return False
    
    logger.info("")
    
    # ШАГ 2: reload_locations.py (тот же)
    success, message = step2_reload_locations(logger)
    if not success:
        logger.error(f"🛑 ПАЙПЛАЙН ОСТАНОВЛЕН на ШАГЕ 2: {message}")
        return False
    logger.info("")
    
    # ШАГ 3: update_dwh_7days.sql
    logger.info("=" * 80)
    logger.info("ШАГ 3: Обновление DWH таблиц за 7 дней (run_update_dwh.py 7)")
    logger.info("=" * 80)
    
    try:
        result = subprocess.run(
            [sys.executable, RUN_UPDATE_DWH_SCRIPT, '7'],
            capture_output=True,
            text=True,
            timeout=3600
        )
        
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                logger.info(f"  {line}")
        
        if result.returncode != 0:
            logger.error(f"❌ ШАГ 3 завершился с ошибкой (код {result.returncode})")
            return False
            
        logger.info("✅ ШАГ 3 завершён успешно")
        
    except Exception as e:
        logger.error(f"❌ Ошибка ШАГ 3: {e}")
        return False
    
    # Итоги
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("=" * 80)
    logger.info("✅ 7-ДНЕВНЫЙ ПАЙПЛАЙН ЗАВЕРШЁН УСПЕШНО")
    logger.info(f"⏱️ Общее время: {duration:.2f} сек ({duration/60:.2f} мин)")
    logger.info("=" * 80)
    
    return True

# === Точка входа ===
def main():
    if len(sys.argv) < 2:
        print("Использование: python pipeline_3days.py [3|7]")
        print("  3 - запустить 3-дневный пайплайн (каждые 10 минут)")
        print("  7 - запустить 7-дневный пайплайн (в 23:59)")
        sys.exit(1)
    
    try:
        pipeline_type = int(sys.argv[1])
        if pipeline_type == 3:
            success = run_pipeline()
        elif pipeline_type == 7:
            success = run_pipeline_7days()
        else:
            raise ValueError("Тип должен быть 3 или 7")
    except ValueError as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
