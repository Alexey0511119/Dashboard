"""
Диагностика callback-ов для дашборда (MS SQL версия)
Запустите: python diagnose_callbacks.py
"""
import sys
import importlib
import inspect
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def check_callback_decorators():
    """Проверяет все callback-функции на наличие кэширования"""
    print("\n=== ПРОВЕРКА CALLBACK ФАЙЛОВ ===\n")
    
    callback_files = [
        'callbacks.main_callbacks',
        'callbacks.modal_callbacks', 
        'callbacks.tab_callbacks'
    ]
    
    for module_name in callback_files:
        try:
            module = importlib.import_module(module_name)
            print(f"📁 {module_name}:")
            
            for name, obj in inspect.getmembers(module):
                if hasattr(obj, '_callback_def'):
                    print(f"   🔹 Callback: {name}")
                    
                    # Проверяем наличие prevent_initial_call
                    if hasattr(obj, '_prevent_initial_call'):
                        print(f"      ⚠️ prevent_initial_call = {obj._prevent_initial_call}")
                    
                    # Проверяем исходный код
                    try:
                        source = inspect.getsource(obj)
                        if '@cache.memoize' in source or '@flask_caching' in source:
                            print(f"      🚨 НАЙДЕНО КЭШИРОВАНИЕ!")
                        if 'lru_cache' in source or '@lru_cache' in source:
                            print(f"      🚨 НАЙДЕНО lru_cache кэширование!")
                        if 'prevent_initial_call' in source:
                            print(f"      ⚠️ prevent_initial_call в коде")
                    except:
                        pass
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    print("\n" + "="*50)

def check_app_config():
    """Проверяет конфигурацию app.py"""
    print("\n=== ПРОВЕРКА APP.PY ===\n")
    
    try:
        import app
        print(f"📱 App type: {type(app.app)}")
        
        # Проверяем наличие Flask-Caching
        if hasattr(app, 'cache'):
            print(f"🚨 Найден cache объект: {type(app.cache)}")
            if hasattr(app.cache, 'config'):
                print(f"   Конфигурация кэша: {app.cache.config}")
        
        # Проверяем наличие after_request
        if hasattr(app.app, 'server'):
            after_req = getattr(app.app.server, 'after_request_funcs', {})
            if after_req:
                print(f"✅ Найдены after_request функции:")
                for name, funcs in after_req.items():
                    print(f"   - {name}: {len(funcs)} функций")
            else:
                print(f"⚠️ НЕТ after_request функций - кэш браузера не отключается")
        
        # Проверяем suppress_callback_exceptions
        if hasattr(app.app, 'config'):
            suppress = app.app.config.get('suppress_callback_exceptions')
            print(f"   suppress_callback_exceptions = {suppress}")
            
    except Exception as e:
        print(f"❌ Ошибка при импорте app: {e}")

def check_data_loading():
    """Проверяет как загружаются данные из MS SQL"""
    print("\n=== ПРОВЕРКА ЗАГРУЗКИ ДАННЫХ ИЗ MS SQL ===\n")
    
    modules_to_check = [
        'data.mssql_client',
        'data.queries_mssql'
    ]
    
    for module_name in modules_to_check:
        try:
            module = importlib.import_module(module_name)
            print(f"📊 {module_name}:")
            
            for name, obj in inspect.getmembers(module):
                if 'productivity' in name.lower() or 'performance' in name.lower():
                    print(f"   🔸 Функция: {name}")
                    
                    # Проверяем декораторы
                    if hasattr(obj, 'cache_clear'):
                        print(f"      🚨 Имеет метод cache_clear - используется lru_cache!")
                    
                    # Проверяем глобальные переменные
                    if hasattr(module, '_cache') or hasattr(module, 'CACHE'):
                        print(f"      ⚠️ Найдена глобальная переменная кэша")
                        
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")

def check_tab_structure():
    """Проверяет структуру вкладки производительности"""
    print("\n=== ПРОВЕРКА ВКЛАДКИ ПРОИЗВОДИТЕЛЬНОСТИ ===\n")
    
    try:
        from components.tabs import productivity_tab
        
        # Ищем создание DataTable
        source = inspect.getsource(productivity_tab)
        
        if 'data=' in source and 'DataTable' in source:
            print("✅ Найдено создание DataTable")
            
            # Проверяем откуда берутся данные
            if 'initial_data' in source or 'df.' in source:
                print("⚠️ Данные могут загружаться статически при инициализации")
            
            # Проверяем наличие id
            import re
            ids = re.findall(r'id=[\'"]([^\'"]+)[\'"]', source)
            if ids:
                print(f"   ID компонентов: {', '.join(set(ids))}")
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def check_mssql_data():
    """Проверяет актуальность данных в MS SQL"""
    print("\n=== ПРОВЕРКА ДАННЫХ В MS SQL ===\n")
    
    try:
        from data.mssql_client import get_mssql_connection
        
        conn = get_mssql_connection()
        cursor = conn.cursor()
        
        # Проверяем последние записи в таблицах
        queries = [
            ("Сотрудники на смене", 
             """SELECT TOP 1 MAX(ShiftDate) as last_date, COUNT(*) as count 
                FROM dbo.EmployeesOnShift WITH (NOLOCK)"""),
            ("Операции сотрудников", 
             """SELECT TOP 1 MAX(OperationDate) as last_date, COUNT(*) as count 
                FROM dbo.EmployeeOperations WITH (NOLOCK)"""),
            ("Производительность", 
             """SELECT TOP 1 MAX(ReportDate) as last_date, COUNT(*) as count 
                FROM dbo.EmployeeProductivity WITH (NOLOCK)""")
        ]
        
        for name, query in queries:
            try:
                cursor.execute(query)
                result = cursor.fetchone()
                if result:
                    print(f"📈 {name}:")
                    print(f"   Последняя дата: {result[0]}")
                    print(f"   Количество записей: {result[1]}")
            except Exception as e:
                print(f"⚠️ {name}: ошибка - {e}")
        
        cursor.close()
        conn.close()
                
    except Exception as e:
        print(f"❌ Не удалось подключиться к MS SQL: {e}")

def check_global_variables():
    """Проверяет глобальные переменные с данными"""
    print("\n=== ПРОВЕРКА ГЛОБАЛЬНЫХ ПЕРЕМЕННЫХ ===\n")
    
    try:
        import data.mssql_client as mssql
        import data.queries_mssql as queries
        
        # Ищем глобальные переменные DataFrame
        for module in [mssql, queries]:
            for var_name in dir(module):
                if not var_name.startswith('_'):
                    var = getattr(module, var_name)
                    if 'DataFrame' in str(type(var)):
                        print(f"⚠️ Найден глобальный DataFrame: {var_name} в {module.__name__}")
                        print(f"   Размер: {len(var)} строк")
                        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    print("\n" + "🔍 ДИАГНОСТИКА ПРОБЛЕМЫ ОБНОВЛЕНИЯ ДАННЫХ (MS SQL) 🔍")
    print("="*60)
    
    check_app_config()
    check_callback_decorators()
    check_data_loading()
    check_tab_structure()
    check_mssql_data()
    check_global_variables()
    
    print("\n" + "="*60)
    print("📋 РЕКОМЕНДАЦИИ:")
    print("1. Если найден cache объект - добавьте очистку кэша в callback")
    print("2. Если нет after_request - добавьте отключение кэша браузера")
    print("3. Если данные загружаются при инициализации - перенесите в callback")
    print("4. Если есть глобальные DataFrame - замените на функции с запросами")
    print("5. Проверьте, что запросы выполняются с WITH (NOLOCK) или READ UNCOMMITTED")