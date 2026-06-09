"""
Проверка статуса ETL обновления данных
"""
import logging
from datetime import datetime
from data.mssql_client import mssql_client

logger = logging.getLogger(__name__)


class ETLChecker:
    """Класс для проверки статуса ETL процессов"""
    
    @staticmethod
    def get_status():
        """
        Проверяет статус обновления ETL
        
        Returns:
            dict: {
                'is_updating': bool,
                'raw_start_time': datetime or None,
                'last_success_time': datetime or None,
                'can_load_fresh_data': bool
            }
        """
        query = """
        WITH last_raw_running AS (
            SELECT TOP 1 
                last_start,
                process_name,
                last_status
            FROM dwh.etl_metadata
            WHERE process_name = 'raw_3days' 
              AND last_status = 'running'
            ORDER BY last_start DESC
        )
        SELECT 
            lr.last_start as raw_start_time,
            CASE 
                WHEN EXISTS (
                    SELECT 1 
                    FROM dwh.etl_metadata
                    WHERE process_name = 'dwh_3days' 
                      AND last_status = 'success'
                      AND last_end > lr.last_start
                ) THEN 0
                ELSE 1
            END as is_updating,
            (
                SELECT TOP 1 last_end
                FROM dwh.etl_metadata
                WHERE process_name = 'dwh_3days' 
                  AND last_status = 'success'
                ORDER BY last_end DESC
            ) as last_success_time
        FROM last_raw_running lr
        UNION ALL
        SELECT 
            NULL as raw_start_time,
            0 as is_updating,
            (
                SELECT TOP 1 last_end
                FROM dwh.etl_metadata
                WHERE process_name = 'dwh_3days' 
                  AND last_status = 'success'
                ORDER BY last_end DESC
            ) as last_success_time
        WHERE NOT EXISTS (
            SELECT 1 
            FROM dwh.etl_metadata 
            WHERE process_name = 'raw_3days' 
              AND last_status = 'running'
        )
        """
        
        try:
            result = mssql_client.execute(query)
            
            if result and len(result) > 0:
                row = result[0]
                is_updating = bool(row[1]) if row[1] is not None else False
                
                # Парсим даты если они есть
                raw_start_time = None
                if row[0]:
                    if isinstance(row[0], datetime):
                        raw_start_time = row[0]
                    elif isinstance(row[0], str):
                        raw_start_time = datetime.fromisoformat(row[0].replace('Z', '+00:00'))
                
                last_success_time = None
                if row[2]:
                    if isinstance(row[2], datetime):
                        last_success_time = row[2]
                    elif isinstance(row[2], str):
                        last_success_time = datetime.fromisoformat(row[2].replace('Z', '+00:00'))
                
                return {
                    'is_updating': is_updating,
                    'raw_start_time': raw_start_time,
                    'last_success_time': last_success_time,
                    'can_load_fresh_data': not is_updating
                }
            else:
                # Если данных нет - считаем что обновление не идет
                return {
                    'is_updating': False,
                    'raw_start_time': None,
                    'last_success_time': None,
                    'can_load_fresh_data': True
                }
                
        except Exception as e:
            logger.error(f"Error checking ETL status: {e}")
            # В случае ошибки - разрешаем загрузку данных
            return {
                'is_updating': False,
                'raw_start_time': None,
                'last_success_time': None,
                'can_load_fresh_data': True,
                'error': str(e)
            }
    
    @staticmethod
    def quick_check():
        """
        Быстрая проверка - только статус обновления
        Используется для polling
        """
        query = """
        SELECT 
            CASE 
                WHEN EXISTS (
                    SELECT 1 
                    FROM dwh.etl_metadata 
                    WHERE process_name = 'raw_3days' 
                      AND last_status = 'running'
                      AND NOT EXISTS (
                          SELECT 1 
                          FROM dwh.etl_metadata dwh
                          WHERE dwh.process_name = 'dwh_3days' 
                            AND dwh.last_status = 'success'
                            AND dwh.last_end > etl.last_start
                      )
                ) THEN 1
                ELSE 0
            END as is_updating
        FROM (SELECT 1) t
        LEFT JOIN (
            SELECT TOP 1 last_start
            FROM dwh.etl_metadata
            WHERE process_name = 'raw_3days' 
              AND last_status = 'running'
            ORDER BY last_start DESC
        ) etl ON 1=1
        """
        
        try:
            result = mssql_client.execute(query)
            if result and len(result) > 0:
                return bool(result[0][0]) if result[0][0] is not None else False
            return False
        except Exception as e:
            logger.error(f"Error in quick ETL check: {e}")
            return False