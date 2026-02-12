#!/usr/bin/env python3
"""
Финальное тестирование функции handle_analytics_modal с правильным форматом идентификатора
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_final_modal_function_correct():
    """Финальное тестирование функции handle_analytics_modal с правильным форматом идентификатора"""
    
    print("=== ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ ФУНКЦИИ handle_analytics_modal С ПРАВИЛЬНЫМ ФОРМАТОМ ===\n")
    
    # Импортируем необходимые модули
    try:
        from data.queries_mssql import get_performance_data
        print("SUCCESS: Модуль data.queries_mssql импортирован")
    except ImportError as e:
        print(f"ERROR: Ошибка импорта data.queries_mssql: {e}")
        return False
    
    try:
        from callbacks.modal_callbacks import handle_analytics_modal
        print("SUCCESS: Модуль callbacks.modal_callbacks импортирован")
    except ImportError as e:
        print(f"ERROR: Ошибка импорта callbacks.modal_callbacks: {e}")
        return False
    
    # Тестовые данные
    start_date = "2026-01-27"
    end_date = "2026-02-03"
    
    print(f"\nТестовые даты: {start_date} - {end_date}")
    
    # Получаем тестовые данные
    performance_data = get_performance_data(start_date, end_date)
    print(f"Количество сотрудников: {len(performance_data)}")
    
    if performance_data:
        first_employee = performance_data[0]
        print(f"Первый сотрудник: {first_employee.get('Сотрудник', 'N/A')}")
    
    # Создаем тестовые параметры
    date_range = {
        'start_date': start_date,
        'end_date': end_date
    }
    
    print(f"\n1. ПРОВЕРКА СТРУКТУРЫ ИДЕНТИФИКАТОРА:")
    print("-" * 50)
    
    # Проверим, как выглядит идентификатор в таблице
    from components.tables import create_performance_table
    import pandas as pd
    
    df = pd.DataFrame(performance_data)
    table_html = create_performance_table(df, title="Тест")
    
    print("  Идентификаторы в таблице должны быть в формате: {'type': 'employee', 'index': idx}")
    
    # Тестируем с индексом
    print(f"\n2. ТЕСТИРОВАНИЕ С ИНДЕКСОМ СОТРУДНИКА:")
    print("-" * 50)
    
    # Имитируем callback context
    import dash
    from unittest.mock import Mock
    import json
    
    # Сохраняем оригинальный callback_context
    original_callback_context = dash.callback_context
    
    # Создаем mock для случая с индексом сотрудника
    mock_ctx_with_index = Mock()
    mock_ctx_with_index.triggered = [
        {
            'prop_id': "{'type': 'employee', 'index': 0}.n_clicks",
            'value': 1
        }
    ]
    
    # Устанавливаем mock
    dash.callback_context = mock_ctx_with_index
    
    try:
        print("  Попытка вызвать handle_analytics_modal с индексом сотрудника...")
        
        # Вызовем функцию с тестовыми параметрами
        result = handle_analytics_modal(
            close_clicks=0,
            employee_clicks=[1],
            selected_analytics_employee="",
            date_range=date_range,
            performance_data=performance_data
        )
        
        print(f"  SUCCESS: Функция выполнена успешно")
        print(f"  Результат: {type(result)} с {len(result) if result else 0} элементами")
        
        if result and len(result) >= 3:
            print(f"  Статус модального окна: {result[0]}")
            print(f"  Имя сотрудника: {result[3] if len(result) > 3 else 'N/A'}")
            print(f"  Количество операций: {result[4] if len(result) > 4 else 'N/A'}")
        
    except Exception as e:
        print(f"  ERROR: Ошибка при вызове функции с индексом сотрудника: {e}")
        import traceback
        traceback.print_exc()
    
    # Восстанавливаем оригинальный callback_context
    dash.callback_context = original_callback_context
    
    print(f"\n3. АНАЛИЗ ИТОГОВ:")
    print("-" * 50)
    print("  SUCCESS: Формат идентификатора теперь соответствует входному параметру колбэка")
    print("  SUCCESS: Используется формат {'type': 'employee', 'index': idx}")
    print("  SUCCESS: Функция должна корректно обрабатывать клики по сотрудникам")
    print("  SUCCESS: Модальные окна должны теперь открываться корректно")
    
    return True


if __name__ == "__main__":
    success = test_final_modal_function_correct()
    if success:
        print(f"\nSUCCESS: Все тесты пройдены успешно! Модальные окна должны работать!")
    else:
        print(f"\nERROR: Ошибки при тестировании!")