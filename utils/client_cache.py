"""
Клиентское кэширование данных в браузере
"""
import json
import hashlib
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ClientCacheManager:
    """Менеджер кэша на стороне клиента"""
    
    # TTL кэша по умолчанию (5 минут)
    DEFAULT_TTL_SECONDS = 300
    
    # Максимальное время хранения кэша при обновлении ETL (3 часа)
    MAX_STALE_TTL_SECONDS = 10800
    
    @staticmethod
    def create_cache_key(data_type, params=None):
        """
        Создание уникального ключа для кэширования
        
        Args:
            data_type: Тип данных ('performance', 'fines', 'productivity', etc.)
            params: Параметры запроса (даты, фильтры)
        
        Returns:
            str: MD5 хэш для ключа кэша
        """
        key_data = f"{data_type}_{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    @staticmethod
    def prepare_cache_data(data, ttl_seconds=None, is_stale=False):
        """
        Подготовка данных для сохранения в клиентский кэш
        
        Args:
            data: Данные для кэширования
            ttl_seconds: Время жизни кэша в секундах
            is_stale: Флаг устаревших данных (при обновлении ETL)
        
        Returns:
            dict: Подготовленные данные с метаданными
        """
        if ttl_seconds is None:
            ttl_seconds = ClientCacheManager.DEFAULT_TTL_SECONDS
        
        now = datetime.now()
        
        return {
            'data': data,
            'timestamp': now.isoformat(),
            'expires_at': (now + timedelta(seconds=ttl_seconds)).isoformat(),
            'is_stale': is_stale,
            'version': '2.0'
        }
    
    @staticmethod
    def is_cache_valid(cached_data):
        """
        Проверка валидности кэша
        
        Args:
            cached_data: Данные из кэша (распарсенный JSON)
        
        Returns:
            bool: True если кэш валиден
        """
        if not cached_data:
            return False
        
        try:
            # Если данные помечены как stale - проверяем максимальный TTL
            if cached_data.get('is_stale', False):
                timestamp = datetime.fromisoformat(cached_data.get('timestamp', ''))
                max_age = timedelta(seconds=ClientCacheManager.MAX_STALE_TTL_SECONDS)
                return datetime.now() - timestamp < max_age
            
            # Обычная проверка по expires_at
            expires_at = datetime.fromisoformat(cached_data.get('expires_at', ''))
            return datetime.now() < expires_at
            
        except (ValueError, TypeError, KeyError) as e:
            logger.debug(f"Cache validation error: {e}")
            return False
    
    @staticmethod
    def get_cached_value(cached_data, key, default=None):
        """
        Безопасное получение значения из кэша
        
        Args:
            cached_data: Данные из кэша
            key: Ключ для извлечения
            default: Значение по умолчанию
        
        Returns:
            Извлеченное значение или default
        """
        if not ClientCacheManager.is_cache_valid(cached_data):
            return default
        
        return cached_data.get('data', {}).get(key, default)
    
    @staticmethod
    def should_use_cache(client_cache_json, etl_is_updating):
        """
        Определяет, нужно ли использовать клиентский кэш
        
        Args:
            client_cache_json: JSON строка с кэшем
            etl_is_updating: Статус обновления ETL
        
        Returns:
            tuple: (should_use, cached_data)
        """
        if not client_cache_json:
            return False, None
        
        try:
            cached = json.loads(client_cache_json) if isinstance(client_cache_json, str) else client_cache_json
            
            # Если ETL обновляется - используем кэш если он не слишком старый
            if etl_is_updating:
                if ClientCacheManager.is_cache_valid(cached):
                    return True, cached
                else:
                    return False, None
            
            # Если ETL не обновляется - используем кэш только если он свежий
            if ClientCacheManager.is_cache_valid(cached) and not cached.get('is_stale', False):
                return True, cached
            else:
                return False, None
                
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"Error parsing client cache: {e}")
            return False, None