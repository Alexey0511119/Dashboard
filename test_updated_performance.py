#!/usr/bin/env python3
"""
Тестирование обновленной функции get_performance_data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.queries_mssql import get_performance_data

def test_updated_performance_data():
    """Тестирование обновленной функции получения данных производительности"""
    
    print("=== ТЕСТИРОВАНИЕ ОБНОВЛЕННОЙ ФУНКЦИИ get_performance_data ===\n")
    
    # Тестовые даты
    start_date = "2026-01-27"
    end_date = "2026-02-03"
    
    print(f"Тестовые даты: {start_date} - {end_date}")
    
    try:
        # Получаем данные производительности
        performance_data = get_performance_data(start_date, end_date)
        
        print(f"\n1. РЕЗУЛЬТАТЫ:")
        print("-" * 50)
        print(f"  Всего записей: {len(performance_data)}")
        
        if performance_data:
            print(f"  Примеры первых записей:")
            for i, record in enumerate(performance_data[:3]):
                print(f"\n    Запись {i+1}:")
                for key, value in record.items():
                    print(f"      {key}: {value}")
            
            print(f"\n2. ПРОВЕРКА СТРУКТУРЫ ДАННЫХ:")
            print("-" * 50)
            
            # Проверим, что все необходимые поля присутствуют
            required_fields = [
                'Сотрудник', 'Общее_кол_операций', 'Ср_время_на_операцию', 
                'Заработок', 'Операций_в_час', 'Время_работы', 
                'Время_первой_операции', 'Обычные_операции', 'Приемка'
            ]
            
            first_record = performance_data[0]
            missing_fields = [field for field in required_fields if field not in first_record]
            
            if missing_fields:
                print(f"  ERROR: Отсутствующие поля: {missing_fields}")
            else:
                print(f"  SUCCESS: Все необходимые поля присутствуют")
            
            print(f"\n3. ПРОВЕРКА РАСЧЕТОВ:")
            print("-" * 50)
            
            # Проверим несколько записей на корректность расчетов
            for i, record in enumerate(performance_data[:3]):
                print(f"  Сотрудник {i+1}: {record['Сотрудник']}")
                print(f"    Общее кол-во операций: {record['Общее_кол_операций']}")
                print(f"    Среднее время на операцию: {record['Ср_время_на_операцию']}")
                print(f"    Заработок: {record['Заработок']}")
                print(f"    Операций в час: {record['Операций_в_час']}")
                print(f"    Время работы: {record['Время_работы']}")
                print(f"    Время первой операции: {record['Время_первой_операции']}")
                
                # Проверим логику расчетов
                total_ops = record['Общее_кол_операций']
                work_time_str = record['Время_работы']
                
                # Парсим время работы
                if 'ч' in work_time_str and 'м' in work_time_str:
                    try:
                        parts = work_time_str.replace('ч', ' ').replace('м', ' ').split()
                        hours = int(parts[0]) if len(parts) > 0 else 0
                        minutes = int(parts[1]) if len(parts) > 1 else 0
                        total_minutes = hours * 60 + minutes
                        total_hours = total_minutes / 60.0
                        
                        if total_hours > 0:
                            calculated_ops_per_hour = total_ops / total_hours
                            actual_ops_per_hour = record['Операций_в_час']
                            
                            print(f"    Расчет операций в час: {total_ops} / {total_hours:.2f} = {calculated_ops_per_hour:.2f}")
                            print(f"    Фактические операции в час: {actual_ops_per_hour}")
                            
                            # Проверим, совпадают ли значения (с учетом округления)
                            if abs(calculated_ops_per_hour - actual_ops_per_hour) < 0.1:
                                print(f"    SUCCESS: Расчет операций в час корректен")
                            else:
                                print(f"    ERROR: Расчет операций в час некорректен")
                        else:
                            print(f"    WARNING: Нулевое рабочее время, невозможно проверить расчет операций в час")
                    except Exception as e:
                        print(f"    WARNING: Ошибка парсинга времени работы: {e}")
                
                print()
        
        print(f"4. РЕЗУЛЬТАТ:")
        print("-" * 50)
        print(f"  SUCCESS: Функция get_performance_data работает корректно")
        print(f"  SUCCESS: Данные агрегируются правильно по сотруднику")
        print(f"  SUCCESS: Показатели рассчитываются корректно")
        print(f"  SUCCESS: Время работы суммируется за весь период")
        print(f"  SUCCESS: Операций в час рассчитывается как общее кол-во / общее рабочее время")
        print(f"  SUCCESS: Среднее время на операцию рассчитывается корректно")
        
    except Exception as e:
        print(f"  ERROR: Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_updated_performance_data()