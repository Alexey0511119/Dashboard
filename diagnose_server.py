"""
Диагностический скрипт для проверки работы дашборда на сервере
Запуск: python diagnose_server.py
"""
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print("ДИАГНОСТИКА ДАШБОРДА НА СЕРВЕРЕ")
print("=" * 80)

# 1. Проверка импортов
print("\n[1/7] Проверка импортов...")
try:
    import dash
    print("  ✅ dash импортирован")
except Exception as e:
    print(f"  ❌ dash: {e}")

try:
    import pyodbc
    print("  ✅ pyodbc импортирован")
except Exception as e:
    print(f"  ❌ pyodbc: {e}")

try:
    import pandas
    print("  ✅ pandas импортирован")
except Exception as e:
    print(f"  ❌ pandas: {e}")

# 2. Проверка подключения к БД
print("\n[2/7] Проверка подключения к БД...")
try:
    from data.mssql_client import mssql_client, test_connection
    
    if test_connection():
        print("  ✅ Подключение к БД успешно")
        
        # Проверяем версию SQL Server
        result = mssql_client.execute("SELECT @@VERSION")
        if result:
            print(f"  📋 Версия: {result[0][0][:100]}...")
    else:
        print("  ❌ Не удалось подключиться к БД")
except Exception as e:
    print(f"  ❌ Ошибка подключения: {e}")
    import traceback
    traceback.print_exc()

# 3. Проверка VIEW dm.v_employees_shift_daily
print("\n[3/7] Проверка dm.v_employees_shift_daily...")
try:
    from data.queries_mssql import get_employees_on_shift_new, get_positions_list_new, get_brigades_list_new
    
    employees, stats = get_employees_on_shift_new()
    positions = get_positions_list_new()
    brigades = get_brigades_list_new()
    
    print(f"  ✅ Сотрудников на смене: {len(employees)}")
    print(f"  ✅ Должностей: {len(positions)}")
    print(f"  ✅ Участков: {len(brigades)}")
    
    if employees:
        print(f"  📋 Первый сотрудник: {employees[0]}")
    if positions:
        print(f"  📋 Должности: {positions[:5]}")
    if brigades:
        print(f"  📋 Участки: {brigades[:5]}")
        
except Exception as e:
    print(f"  ❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

# 4. Проверка основных VIEW
print("\n[4/7] Проверка основных VIEW...")
views_to_check = [
    ('dm.v_order_timeliness_by_delivery', 'Своевременность заказов'),
    ('dm.v_earnings_daily', 'Заработок'),
    ('dm.v_performance_detailed', 'Производительность'),
    ('dm.v_storage_current_status', 'Ячейки хранения'),
    ('dm.v_order_accuracy_daily', 'Точность заказов'),
]

for view_name, description in views_to_check:
    try:
        query = f"SELECT COUNT(*) FROM {view_name}"
        result = mssql_client.execute(query)
        if result:
            count = result[0][0]
            print(f"  ✅ {description} ({view_name}): {count} записей")
        else:
            print(f"  ⚠️  {description} ({view_name}): нет данных")
    except Exception as e:
        print(f"  ❌ {description} ({view_name}): {e}")

# 5. Проверка данных за текущий период
print("\n[5/7] Проверка данных за последние 7 дней...")
try:
    from datetime import datetime, timedelta
    from data.queries_mssql import get_performance_data
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    print(f"  📅 Период: {start_date} - {end_date}")
    
    perf_data = get_performance_data(start_date, end_date)
    print(f"  ✅ Данные производительности: {len(perf_data)} записей")
    
    if perf_data:
        print(f"  📋 Первый сотрудник: {perf_data[0].get('Сотрудник', 'N/A')}")
    else:
        print("  ⚠️  Нет данных за указанный период!")
        
except Exception as e:
    print(f"  ❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

# 6. Проверка кэша
print("\n[6/7] Проверка кэша...")
try:
    from data.mssql_client import get_cache_stats
    
    stats = get_cache_stats()
    print(f"  ✅ Кэш: {stats}")
except Exception as e:
    print(f"  ⚠️  Не удалось получить статистику кэша: {e}")

# 7. Проверка сетевых настроек
print("\n[7/7] Проверка сетевых настроек...")
try:
    import socket
    
    # Проверяем доступность сервера БД
    db_host = '10.7.0.27'
    db_port = 1433
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((db_host, db_port))
    sock.close()
    
    if result == 0:
        print(f"  ✅ Сервер БД {db_host}:{db_port} доступен")
    else:
        print(f"  ❌ Сервер БД {db_host}:{db_port} НЕ доступен (код ошибки: {result})")
        
except Exception as e:
    print(f"  ❌ Ошибка проверки сети: {e}")

# Итог
print("\n" + "=" * 80)
print("ДИАГНОСТИКА ЗАВЕРШЕНА")
print("=" * 80)
print("\nЕсли есть ошибки (❌) - это причина проблем с данными.")
print("Если все проверки пройдены (✅) - проблема может быть в:")
print("  - Настройках firewall")
print("  - Правах доступа к БД")
print("  - Отсутствии данных за текущий период")
print("  - Проблемах с запуском Dash приложения")
