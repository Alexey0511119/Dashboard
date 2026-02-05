import pyodbc
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import threading

# MSSQL конфигурация
MSSQL_CONFIG = {
    'server': '10.7.0.48',
    'port': 1433,
    'database': 'olap2_fixed',
    'user': 'sa',
    'password': 'Rdflhfn600'
}

class MSSQLClient:
    """Клиент для MS SQL Server"""
    
    def __init__(self):
        self.server = '10.7.0.48'
        self.port = MSSQL_CONFIG['port']
        self.database = MSSQL_CONFIG['database']
        self.user = MSSQL_CONFIG['user']
        self.password = MSSQL_CONFIG['password']
        self.connection_string = (
            f"DRIVER={{SQL Server}};"
            f"SERVER={self.server},{self.port};"
            f"DATABASE={self.database};"
            f"UID={self.user};"
            f"PWD={self.password};"
            f"TrustServerCertificate=yes;"
        )
        
    def execute(self, query, params=None):
        """Выполнение SQL запроса"""
        try:
            conn = pyodbc.connect(self.connection_string, timeout=30)
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            result = []
            columns = [column[0] for column in cursor.description] if cursor.description else []
            
            rows = cursor.fetchall()
            for row in rows:
                result.append(row)
                
            conn.close()
            return result
            
        except Exception as e:
            print(f"SQL Error: {e}")
            print(f"Query: {query}")
            return []

# Создание клиента MS SQL
mssql_client = MSSQLClient()

# Кэширование для оптимизации запросов
cache_lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=5)

def execute_query_cached(query, params=None, ttl=300):
    """Выполнение запроса с кэшированием"""
    cache_key = f"{query}_{str(params)}"
    
    @lru_cache(maxsize=128)
    def cached_execution(cache_key):
        try:
            result = mssql_client.execute(query, params)
            return result
        except Exception as e:
            print(f"Cache execution error: {e}")
            return []
    
    return cached_execution(cache_key)

def test_connection():
    """Тест подключения к БД"""
    try:
        result = mssql_client.execute("SELECT @@VERSION")
        if result:
            print("✅ Подключение к MS SQL Server успешно")
            print(f"Версия: {result[0][0]}")
            return True
        else:
            print("❌ Не удалось подключиться к MS SQL Server")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def get_available_views():
    """Получение списка всех view в схеме dm"""
    query = """
    SELECT TABLE_NAME 
    FROM INFORMATION_SCHEMA.VIEWS 
    WHERE TABLE_SCHEMA = 'dm'
    ORDER BY TABLE_NAME
    """
    result = mssql_client.execute(query)
    return [row[0] for row in result] if result else []

def test_view(view_name, limit=5):
    """Тестирование view с ограничением количества записей"""
    try:
        query = f"SELECT TOP {limit} * FROM dm.{view_name}"
        result = mssql_client.execute(query)
        
        if result:
            print(f"\n✅ {view_name}: {len(result)} записей (показано первых {limit})")
            
            # Получаем названия колонок
            columns_query = f"""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'dm' AND TABLE_NAME = '{view_name}'
            ORDER BY ORDINAL_POSITION
            """
            columns_result = mssql_client.execute(columns_query)
            columns = [row[0] for row in columns_result] if columns_result else []
            
            print(f"Колонки: {', '.join(columns)}")
            
            # Показываем первые несколько строк
            for i, row in enumerate(result[:3]):  # Только первые 3 строки
                print(f"  Строка {i+1}: {row}")
            
            return True, columns
        else:
            print(f"❌ {view_name}: нет данных")
            return False, []
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании {view_name}: {e}")
        return False, []

if __name__ == "__main__":
    test_connection()
    views = get_available_views()
    print(f"\nДоступные view в схеме dm:")
    for view in views:
        print(f"  - {view}")
