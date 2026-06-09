"""
Клиент для MS SQL Server - ОПТИМИЗИРОВАН ДЛЯ СЛАБОГО СЕРВЕРА
"""
import pyodbc
import threading
import logging
import time
import hashlib

logger = logging.getLogger(__name__)

# MSSQL конфигурация
MSSQL_CONFIG = {
    'server': '10.7.0.27',
    'port': 1433,
    'database': 'olap2_fixed',
    'user': 'sa',
    'password': 'Rdflhfn600'
}

# МИНИМАЛЬНЫЙ ПУЛ - всего 2 соединения!
_MAX_CONNECTIONS = 2
_connection_pool = []
_pool_lock = threading.Lock()
_connection_counter = 0


def _get_connection():
    """Получение соединения с защитой от перегрузки"""
    global _connection_counter
    
    # Если уже много активных соединений - ждем
    with _pool_lock:
        if _connection_counter >= _MAX_CONNECTIONS:
            logger.debug("Max connections reached, reusing from pool")
    
    # Ищем живое соединение
    with _pool_lock:
        for i, conn in enumerate(_connection_pool):
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                _connection_counter += 1
                return _connection_pool.pop(i)
            except:
                try:
                    conn.close()
                except:
                    pass
                _connection_pool.pop(i)
                break
    
    # Создаем новое если не превышен лимит
    with _pool_lock:
        if _connection_counter < _MAX_CONNECTIONS:
            try:
                conn = pyodbc.connect(
                    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                    f"SERVER={MSSQL_CONFIG['server']},{MSSQL_CONFIG['port']};"
                    f"DATABASE={MSSQL_CONFIG['database']};"
                    f"UID={MSSQL_CONFIG['user']};"
                    f"PWD={MSSQL_CONFIG['password']};"
                    f"TrustServerCertificate=yes;"
                    f"Connection Timeout=15;"
                    f"Query Timeout=15;"
                    f"ApplicationIntent=READONLY;",
                    timeout=15,
                    autocommit=True
                )
                _connection_counter += 1
                return conn
            except Exception as e:
                logger.error(f"Failed to create connection: {e}")
                return None
    
    # Ждем освобождения соединения (максимум 5 секунд)
    for _ in range(25):  # 25 * 0.2 = 5 секунд
        time.sleep(0.2)
        with _pool_lock:
            if _connection_pool:
                conn = _connection_pool.pop(0)
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.close()
                    _connection_counter += 1
                    return conn
                except:
                    try:
                        conn.close()
                    except:
                        pass
    
    logger.warning("Timeout waiting for connection")
    return None


def _return_connection(conn):
    """Возврат соединения в пул"""
    global _connection_counter
    
    if conn:
        with _pool_lock:
            _connection_counter -= 1
            
            # Проверяем живо ли соединение
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                
                if len(_connection_pool) < _MAX_CONNECTIONS:
                    _connection_pool.append(conn)
                else:
                    conn.close()
            except:
                try:
                    conn.close()
                except:
                    pass


def execute_query(query, params=None):
    """Выполнение запроса с защитой от таймаутов"""
    conn = None
    try:
        conn = _get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        # Короткие таймауты
        try:
            cursor.execute("SET LOCK_TIMEOUT 5000")  # 5 секунд
            cursor.execute("SET QUERY_GOVERNOR_COST_LIMIT 1000")  # Ограничение сложности
        except:
            pass
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if cursor.description:
            # Ограничиваем количество возвращаемых строк
            rows = cursor.fetchmany(10000)  # Максимум 10000 строк
            result = [list(row) for row in rows]
            cursor.close()
            return result
        
        cursor.close()
        return []
        
    except Exception as e:
        logger.error(f"SQL Error: {e}")
        return []
    finally:
        if conn:
            _return_connection(conn)


# Кэш с длительным TTL
query_cache = {}
cache_timestamps = {}
cache_lock = threading.Lock()


def execute_query_cached(query, params=None, ttl=300):  # 5 минут по умолчанию
    """Выполнение с кэшированием"""
    if ttl == 0:
        return execute_query(query, params)
    
    cache_key = hashlib.md5(f"{query}_{str(params)}".encode()).hexdigest()
    current_time = time.time()
    
    with cache_lock:
        if cache_key in query_cache:
            if current_time - cache_timestamps[cache_key] < ttl:
                return query_cache[cache_key]
    
    result = execute_query(query, params)
    
    if result:  # Кэшируем только непустые результаты
        with cache_lock:
            query_cache[cache_key] = result
            cache_timestamps[cache_key] = current_time
    
    return result


def clear_cache():
    with cache_lock:
        query_cache.clear()
        cache_timestamps.clear()


# Совместимость
mssql_client = type('obj', (object,), {
    'execute': staticmethod(execute_query)
})()


def test_connection():
    try:
        result = execute_query("SELECT 1")
        return bool(result)
    except:
        return False