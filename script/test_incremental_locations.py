#!/usr/bin/env python3
"""
Тестовый запуск инкрементальной загрузки LOCATION
Проверяет подключение, данные и готовность к автоматической загрузке
"""

import pymssql
from datetime import datetime, timedelta
import sys

# === Параметры подключения ===
ILS_SERVER = '10.7.0.248'
ILS_PORT = 1433
ILS_DATABASE = 'ils'
ILS_USER = 'manhreader'
ILS_PASSWORD = 'August2021'

ANALYTICS_SERVER = '10.7.0.27'
ANALYTICS_DATABASE = 'olap2_fixed'
ANALYTICS_USER = 'sa'
ANALYTICS_PASSWORD = 'Rdflhfn600'


def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_step(text):
    print(f"\n📍 {text}")


def print_success(text):
    print(f"✅ {text}")


def print_error(text):
    print(f"❌ {text}")


def print_info(text):
    print(f"ℹ️  {text}")


def test_ils_connection():
    """Проверка подключения к ILS"""
    print_step("Проверка подключения к ILS (10.7.0.248)")
    
    try:
        conn = pymssql.connect(
            server=ILS_SERVER,
            port=ILS_PORT,
            user=ILS_USER,
            password=ILS_PASSWORD,
            database=ILS_DATABASE,
            tds_version='7.0'
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        conn.close()
        
        print_success(f"Подключено к ILS: {version[:50]}...")
        return True
        
    except Exception as e:
        print_error(f"Не удалось подключиться к ILS: {e}")
        return False


def test_analytics_connection():
    """Проверка подключения к аналитической базе"""
    print_step("Проверка подключения к olap2_fixed (10.7.0.27)")
    
    try:
        conn = pymssql.connect(
            server=ANALYTICS_SERVER,
            user=ANALYTICS_USER,
            password=ANALYTICS_PASSWORD,
            database=ANALYTICS_DATABASE,
            charset='UTF-8'
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        conn.close()
        
        print_success(f"Подключено к olap2_fixed: {version[:50]}...")
        return True
        
    except Exception as e:
        print_error(f"Не удалось подключиться к olap2_fixed: {e}")
        return False


def test_raw_location_table():
    """Проверка таблицы raw_.LOCATION"""
    print_step("Проверка таблицы raw_.LOCATION")
    
    try:
        conn = pymssql.connect(
            server=ANALYTICS_SERVER,
            user=ANALYTICS_USER,
            password=ANALYTICS_PASSWORD,
            database=ANALYTICS_DATABASE,
            charset='UTF-8'
        )
        
        cursor = conn.cursor()
        
        # Проверить существование таблицы
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'raw_' AND TABLE_NAME = 'LOCATION'
        """)
        
        exists = cursor.fetchone()[0]
        
        if exists == 0:
            print_error("Таблица raw_.LOCATION не существует!")
            print_info("Создайте таблицу через: reload_3days.py или вручную")
            conn.close()
            return False
        
        # Проверить количество записей
        cursor.execute("SELECT COUNT(*) FROM raw_.LOCATION")
        count = cursor.fetchone()[0]
        
        print_success(f"Таблица существует, записей: {count:,}")
        
        # Проверить структуру
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'raw_' AND TABLE_NAME = 'LOCATION'
            ORDER BY ORDINAL_POSITION
        """)
        
        columns = cursor.fetchall()
        print_info(f"Колонок в таблице: {len(columns)}")
        
        # Проверить DATE_TIME_STAMP
        has_timestamp = any(col[0] == 'DATE_TIME_STAMP' for col in columns)
        if has_timestamp:
            print_success("Поле DATE_TIME_STAMP существует")
        else:
            print_error("Поле DATE_TIME_STAMP не найдено!")
        
        conn.close()
        return has_timestamp
        
    except Exception as e:
        print_error(f"Ошибка: {e}")
        return False


def test_dwh_location_snapshot():
    """Проверка таблицы dwh.fact_location_snapshot"""
    print_step("Проверка таблицы dwh.fact_location_snapshot")
    
    try:
        conn = pymssql.connect(
            server=ANALYTICS_SERVER,
            user=ANALYTICS_USER,
            password=ANALYTICS_PASSWORD,
            database=ANALYTICS_DATABASE,
            charset='UTF-8'
        )
        
        cursor = conn.cursor()
        
        # Проверить существование таблицы
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'fact_location_snapshot'
        """)
        
        exists = cursor.fetchone()[0]
        
        if exists == 0:
            print_error("Таблица dwh.fact_location_snapshot не существует!")
            print_info("Создайте таблицу через SQL-скрипт")
            conn.close()
            return False
        
        # Проверить количество записей
        cursor.execute("SELECT COUNT(*) FROM dwh.fact_location_snapshot")
        count = cursor.fetchone()[0]
        
        print_success(f"Таблица существует, записей: {count:,}")
        
        # Проверить данные по статусам
        cursor.execute("""
            SELECT status, COUNT(*) AS количество
            FROM dwh.fact_location_snapshot
            GROUP BY status
        """)
        
        rows = cursor.fetchall()
        
        if rows:
            print_info("Данные по статусам:")
            for row in rows:
                print(f"   {row[0]}: {row[1]:,}")
        else:
            print_error("Таблица пустая!")
            print_info("Выполните первичную загрузку данных")
        
        # Проверить структуру
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'fact_location_snapshot'
            ORDER BY ORDINAL_POSITION
        """)
        
        columns = cursor.fetchall()
        print_info(f"Колонок в таблице: {len(columns)}")
        
        # Проверить last_modified
        has_last_modified = any(col[0] == 'last_modified' for col in columns)
        if has_last_modified:
            print_success("Поле last_modified существует")
        else:
            print_info("Поле last_modified не найдено (не критично)")
        
        conn.close()
        return True
        
    except Exception as e:
        print_error(f"Ошибка: {e}")
        return False


def test_views():
    """Проверка VIEW"""
    print_step("Проверка VIEW для дашборда")
    
    try:
        conn = pymssql.connect(
            server=ANALYTICS_SERVER,
            user=ANALYTICS_USER,
            password=ANALYTICS_PASSWORD,
            database=ANALYTICS_DATABASE,
            charset='UTF-8'
        )
        
        cursor = conn.cursor()
        
        views = [
            'dm.v_storage_current_status',
            'dm.v_storage_cells_current',
            'dm.v_storage_by_zone_current',
            'dm.v_storage_by_type_current',
            'dm.v_storage_by_work_zone_current'
        ]
        
        for view in views:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {view}")
                count = cursor.fetchone()[0]
                print_success(f"{view}: {count:,} записей")
            except Exception as e:
                print_error(f"{view}: ошибка ({e})")
        
        conn.close()
        return True
        
    except Exception as e:
        print_error(f"Ошибка: {e}")
        return False


def test_incremental_load():
    """Тест инкрементальной загрузки"""
    print_step("Тест инкрементальной загрузки")
    
    try:
        # Получить последнее изменение
        conn = pymssql.connect(
            server=ANALYTICS_SERVER,
            user=ANALYTICS_USER,
            password=ANALYTICS_PASSWORD,
            database=ANALYTICS_DATABASE,
            charset='UTF-8'
        )
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MAX(DATE_TIME_STAMP) 
            FROM raw_.LOCATION 
            WHERE DATE_TIME_STAMP IS NOT NULL
        """)
        
        result = cursor.fetchone()
        last_ts = result[0] if result and result[0] else None
        
        if last_ts:
            print_success(f"Последнее изменение: {last_ts}")
            
            # Посчитать изменения за последние 5 минут
            from datetime import timedelta
            buffer = datetime.now() - timedelta(minutes=5)
            
            cursor.execute("""
                SELECT COUNT(*) 
                FROM raw_.LOCATION 
                WHERE DATE_TIME_STAMP > %s
            """, (buffer,))
            
            changes = cursor.fetchone()[0]
            print_info(f"Изменений за последние 5 минут: {changes}")
        else:
            print_error("Нет данных о времени изменений")
        
        conn.close()
        return True
        
    except Exception as e:
        print_error(f"Ошибка: {e}")
        return False


def main():
    """Основная функция"""
    print_header("ТЕСТ ИНКРЕМЕНТАЛЬНОЙ ЗАГРУЗКИ LOCATION")
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 1. Проверка подключений
    results.append(("ILS подключение", test_ils_connection()))
    results.append(("Analytics подключение", test_analytics_connection()))
    
    # 2. Проверка таблиц
    results.append(("raw_.LOCATION", test_raw_location_table()))
    results.append(("dwh.fact_location_snapshot", test_dwh_location_snapshot()))
    
    # 3. Проверка VIEW
    results.append(("VIEW для дашборда", test_views()))
    
    # 4. Тест загрузки
    results.append(("Инкрементальная загрузка", test_incremental_load()))
    
    # Итоги
    print_header("РЕЗУЛЬТАТЫ ПРОВЕРКИ")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nИтого: {passed}/{total} проверок пройдено")
    
    if passed == total:
        print_success("Все системы готовы к инкрементальной загрузке!")
        print_info("\nСледующие шаги:")
        print("1. Настройте Windows Task Scheduler")
        print("2. Запустите incremental_locations_raw.py")
        print("3. Запустите incremental_locations_dwh.py")
        print("4. Проверьте логи в script/logs/")
        return 0
    else:
        print_error("Есть проблемы! Устраните их перед запуском.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
