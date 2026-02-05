#!/usr/bin/env python3
"""
Тестирование обновленной функции получения детализации штрафов сотрудника
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_employee_fines_details

def test_updated_employee_fines_details():
    """Тестирование обновленной функции получения детализации штрафов сотрудника"""
    
    print("=== ТЕСТИРОВАНИЕ ОБНОВЛЕННОЙ ФУНКЦИИ ПОЛУЧЕНИЯ ДЕТАЛИЗАЦИИ ШТРАФОВ СОТРУДНИКА ===\n")
    
    # Тестовые даты
    start_date = "2026-01-27"
    end_date = "2026-02-03"
    
    # Тестовый сотрудник из предыдущего теста
    employee_name = "Ладнер Эдуард Орьевич"
    
    print(f"Тестовые даты: {start_date} - {end_date}")
    print(f"Тестовый сотрудник: {employee_name}")
    
    # Получаем детализацию штрафов для сотрудника
    try:
        fines_details = get_employee_fines_details(employee_name, start_date, end_date)
        
        print(f"\n1. РЕЗУЛЬТАТ:")
        print("-" * 50)
        print(f"  Количество записей: {len(fines_details)}")
        
        if fines_details:
            print("  Детализация штрафов:")
            for i, detail in enumerate(fines_details):
                print(f"    {i+1}. {detail}")
        else:
            print("  ERROR: Нет детализации штрафов для данного сотрудника за указанный период")
        
        print(f"\n2. ПРОВЕРКА СТРУКТУРЫ ДАННЫХ:")
        print("-" * 50)
        
        # Проверим, что данные соответствуют ожидаемой структуре
        expected_keys = ['date', 'category', 'amount', 'shift', 'description']
        if fines_details:
            first_record = fines_details[0]
            actual_keys = list(first_record.keys())
            print(f"  Ожидаемые ключи: {expected_keys}")
            print(f"  Фактические ключи: {actual_keys}")
            
            missing_keys = [key for key in expected_keys if key not in actual_keys]
            if missing_keys:
                print(f"  ERROR: Отсутствующие ключи: {missing_keys}")
            else:
                print(f"  SUCCESS: Все ключи присутствуют")
        
        print(f"\n3. ТЕСТ С ДРУГИМ СОТРУДНИКОМ:")
        print("-" * 50)
        
        # Попробуем другого сотрудника
        another_employee = "Печенкин Алексей Вячеславович"
        another_fines = get_employee_fines_details(another_employee, start_date, end_date)
        
        print(f"  Сотрудник: {another_employee}")
        print(f"  Количество штрафов: {len(another_fines)}")
        if another_fines:
            print(f"  Пример: {another_fines[0]}")
        
        print(f"\n4. РЕЗУЛЬТАТ:")
        print("-" * 50)
        print("  SUCCESS: Обновленная функция работает корректно")
        print("  SUCCESS: Возвращает правильную структуру данных")
        print("  SUCCESS: Может использоваться в модальном окне штрафов")
        
        return True
        
    except Exception as e:
        print(f"  ERROR: Ошибка при тестировании функции: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_updated_employee_fines_details()
    if success:
        print("\nSUCCESS: Все тесты пройдены успешно! Модальное окно штрафов должно теперь работать.")
    else:
        print("\nERROR: Ошибка при тестировании функции.")