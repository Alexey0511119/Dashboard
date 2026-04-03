import pyodbc
import threading
import logging
from queue import Queue
from datetime import datetime

# Production логгер - отключен для производительности
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# MSSQL конфигурация
MSSQL_CONFIG = {
    'server': '10.7.0.27',
    'port': 1433,
    'database': 'olap2_fixed',
    'user': 'sa',
    'password': 'Rdflhfn600'
}

class MSSQLConnectionPool:
    """Пул соединений для MSSQL - значительно ускоряет работу"""
    
    def __init__(self, pool_size=10, max_overflow=5):
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self._pool = Queue(maxsize=pool_size + max_overflow)
        self._lock = threading.Lock()
        self._created_connections = 0
        
        # Создаем начальный пул соединений
        for _ in range(pool_size):
            conn = self._create_connection()
            if conn:
                self._pool.put(conn)
    
    def _create_connection(self):
        """Создание нового соединения"""
        try:
            conn = pyodbc.connect(
                f"DRIVER={{SQL Server}};"
                f"SERVER={MSSQL_CONFIG['server']},{MSSQL_CONFIG['port']};"
                f"DATABASE={MSSQL_CONFIG['database']};"
                f"UID={MSSQL_CONFIG['user']};"
                f"PWD={MSSQL_CONFIG['password']};"
                f"TrustServerCertificate=yes;",
                timeout=30,
                # Оптимизации для скорости
                autocommit=True
            )
            return conn
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            return None
    
    def get_connection(self):
        """Получение соединения из пула"""
        try:
            # Пробуем получить из пула
            conn = self._pool.get_nowait()
            # Проверяем, живо ли соединение
            try:
                conn.cursor().execute("SELECT 1")
                return conn
            except:
                # Соединение мертво, создаем новое
                return self._create_connection()
        except:
            # Пул пуст, создаем новое соединение
            with self._lock:
                if self._created_connections < self.pool_size + self.max_overflow:
                    self._created_connections += 1
                    return self._create_connection()
            # Если достигли лимита, ждем
            try:
                conn = self._pool.get(timeout=10)
                return conn
            except:
                return None
    
    def return_connection(self, conn):
        """Возврат соединения в пул"""
        if conn:
            try:
                self._pool.put_nowait(conn)
            except:
                pass
    
    def close_all(self):
        """Закрытие всех соединений"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except:
                pass


class MSSQLClient:
    """Оптимизированный клиент для MS SQL Server с пулом соединений"""

    def __init__(self, pool_size=10):
        self.connection_pool = MSSQLConnectionPool(pool_size=pool_size)
        self._local = threading.local()
    
    def execute(self, query, params=None):
        """Выполнение SQL запроса с использованием пула соединений"""
        conn = None
        try:
            conn = self.connection_pool.get_connection()
            if not conn:
                logger.error("No available connection")
                return []
            
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if cursor.description:
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
                # Преобразуем в список списков для совместимости
                result = [list(row) for row in rows]
                return result
            return []
            
        except Exception as e:
            logger.error(f"SQL Error: {e}")
            return []
        finally:
            if conn:
                self.connection_pool.return_connection(conn)
    
    def execute_many(self, queries_with_params):
        """Пакетное выполнение нескольких запросов"""
        results = []
        conn = None
        try:
            conn = self.connection_pool.get_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            for query, params in queries_with_params:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if cursor.description:
                    rows = cursor.fetchall()
                    results.append([list(row) for row in rows])
                else:
                    results.append([])
            
            return results
            
        except Exception as e:
            logger.error(f"SQL Error in execute_many: {e}")
            return [[] for _ in queries_with_params]
        finally:
            if conn:
                self.connection_pool.return_connection(conn)


# Создание оптимизированного клиента с пулом из 10 соединений
mssql_client = MSSQLClient(pool_size=10)

# Простой кэш с TTL для запросов
import time
import hashlib

query_cache = {}
cache_timestamps = {}
cache_lock = threading.Lock()

def execute_query_cached(query, params=None, ttl=300):
    """Выполнение запроса с кэшированием и TTL"""
    # Создаем уникальный ключ кэша
    cache_key_raw = f"{query}_{str(params)}"
    cache_key = hashlib.md5(cache_key_raw.encode()).hexdigest()
    
    current_time = time.time()
    
    # Проверяем кэш
    with cache_lock:
        if cache_key in query_cache and cache_key in cache_timestamps:
            if current_time - cache_timestamps[cache_key] < ttl:
                return query_cache[cache_key]
            else:
                # Удаляем устаревшие данные
                del query_cache[cache_key]
                del cache_timestamps[cache_key]
    
    # Выполняем запрос
    try:
        result = mssql_client.execute(query, params)
        
        # Сохраняем в кэш
        with cache_lock:
            query_cache[cache_key] = result
            cache_timestamps[cache_key] = current_time
        
        return result
    except Exception as e:
        logger.error(f"Cache execution error: {e}")
        return []


def clear_cache():
    """Очистка всего кэша"""
    with cache_lock:
        query_cache.clear()
        cache_timestamps.clear()


def get_cache_stats():
    """Получение статистики кэша"""
    with cache_lock:
        return {
            'cached_queries': len(query_cache),
            'total_size': len(query_cache)
        }


def test_connection():
    """Тест подключения к БД"""
    try:
        result = mssql_client.execute("SELECT @@VERSION")
        if result:
            return True
        return False
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False


if __name__ == "__main__":
    if test_connection():
        print("✅ Подключение к MS SQL Server успешно")
    else:
        print("❌ Ошибка подключения")
