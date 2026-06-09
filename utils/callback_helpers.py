"""
Вспомогательные функции для безопасных callback'ов
Предотвращает падение сервера при ошибках в Pattern-Matching callback'ах
"""
import logging
import json
import dash
from functools import wraps

logger = logging.getLogger(__name__)


def safe_pattern_callback(func):
    """
    Декоратор для безопасного выполнения callback'ов с Pattern-Matching
    Перехватывает IndexError и другие исключения, предотвращая падение сервера
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except IndexError as e:
            logger.warning(f"Pattern-matching index error in {func.__name__}: {e}")
            raise dash.exceptions.PreventUpdate
        except dash.exceptions.PreventUpdate:
            raise
        except Exception as e:
            logger.error(f"Error in pattern callback {func.__name__}: {e}", exc_info=True)
            raise dash.exceptions.PreventUpdate
    return wrapper


def safe_callback(func):
    """
    Декоратор для безопасного выполнения любых callback'ов
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except dash.exceptions.PreventUpdate:
            raise
        except Exception as e:
            logger.error(f"Callback error in {func.__name__}: {e}", exc_info=True)
            raise dash.exceptions.PreventUpdate
    return wrapper


def validate_pattern_input(triggered_input, data_list, index_name='index'):
    """
    Проверяет валидность pattern-matching input
    
    Args:
        triggered_input: Объект из ctx.triggered[0]
        data_list: Список данных, из которого берется элемент
        index_name: Имя поля с индексом в JSON
    
    Returns:
        index или None если невалидный
    """
    if not triggered_input:
        return None
    
    # Проверяем, что есть значение value (клик был)
    value = triggered_input.get('value')
    if value is None:
        return None
    
    # Если это список кликов (ALL), проверяем что есть хотя бы один клик
    if isinstance(value, list):
        if not any(value):
            return None
    
    try:
        prop_id = triggered_input['prop_id'].split('.')[0]
        button_json = json.loads(prop_id.replace("'", '"'))
        
        if index_name not in button_json:
            logger.warning(f"Index '{index_name}' not found in pattern: {button_json}")
            return None
        
        idx = button_json[index_name]
        
        if data_list is None:
            logger.warning("Data list is None")
            return None
        
        if idx < 0 or idx >= len(data_list):
            logger.warning(f"Index {idx} out of range [0..{len(data_list)-1}]")
            return None
        
        return idx
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse pattern JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Error validating pattern input: {e}")
        return None


def safe_get_from_list(data_list, index, default=None):
    """Безопасное получение элемента из списка"""
    if data_list and isinstance(data_list, list) and 0 <= index < len(data_list):
        return data_list[index]
    return default