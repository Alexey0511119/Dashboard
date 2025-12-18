import urllib.parse
import requests
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import threading

from config.clickhouse_config import CLICKHOUSE_CONFIG

class ClickHouseHTTPClient:
    """HTTP клиент для ClickHouse"""
    
    def __init__(self, config):
        self.host = config['host']
        self.port = config['port']
        self.database = config.get('database', 'default')
        self.user = config.get('user', 'default')
        self.password = config.get('password', '')
        self.base_url = f"http://{self.host}:{self.port}/"
        
    def execute(self, query, params=None):
        """Выполнение SQL запроса через HTTP интерфейс"""
        try:
            if params:
                for key, value in params.items():
                    if isinstance(value, str):
                        query = query.replace(f'%({key})s', f"'{value}'")
                    else:
                        query = query.replace(f'%({key})s', str(value))
            
            encoded_query = urllib.parse.quote(query)
            url = f"{self.base_url}?database={self.database}&query={encoded_query}"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                result = []
                lines = response.text.strip().split('\n')
                for line in lines:
                    if line.strip():
                        columns = line.split('\t')
                        result.append(columns)
                return result
            else:
                return []
                
        except Exception:
            return []

# Создание клиента ClickHouse
clickhouse_client = ClickHouseHTTPClient(CLICKHOUSE_CONFIG)

# Кэширование для оптимизации запросов
cache_lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=5)

def execute_query_cached(query, params=None, ttl=300):
    """Выполнение запроса с кэшированием"""
    cache_key = f"{query}_{str(params)}"
    
    @lru_cache(maxsize=128)
    def cached_execution(cache_key):
        try:
            result = clickhouse_client.execute(query, params)
            return result
        except Exception:
            return []
    
    return cached_execution(cache_key)