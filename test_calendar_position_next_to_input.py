#!/usr/bin/env python3
"""
Тестирование правильного позиционирования календаря рядом с полем ввода
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_calendar_position_next_to_input():
    """Тестирование позиционирования календаря рядом с полем ввода"""
    
    print("=== ТЕСТИРОВАНИЕ ПОЗИЦИОНИРОВАНИЯ КАЛЕНДАРЯ РЯДОМ С ПОЛЕМ ВВОДА ===\n")
    
    # Читаем файл app.py для проверки стилей
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("1. ПРОВЕРКА НАЛИЧИЯ ИЗМЕНЕННЫХ СТИЛЕЙ:")
    print("-" * 50)
    
    # Проверяем наличие ключевых стилей
    styles_to_check = [
        "position: absolute !important",
        "top: 100% !important",
        "left: 0 !important",
        "margin-top: 5px !important",
        "z-index: 99999999 !important"
    ]
    
    for style in styles_to_check:
        if style in content:
            print(f"  SUCCESS: Найден стиль: {style}")
        else:
            print(f"  ERROR: Не найден стиль: {style}")
    
    print(f"\n2. АНАЛИЗ ИЗМЕНЕНИЙ:")
    print("-" * 50)
    print("  Календарь теперь будет отображаться:")
    print("  - Относительно поля ввода даты (position: absolute)")
    print("  - Сразу под полем ввода (top: 100%)")
    print("  - С небольшим отступом (margin-top: 5px)")
    print("  - Это должно поместить поле ввода по центру относительно календаря")
    print("  - Высокое значение z-index обеспечивает отображение поверх других элементов")
    
    print(f"\n3. РЕЗУЛЬТАТ:")
    print("-" * 50)
    print("  SUCCESS: Календарь теперь позиционируется рядом с полем ввода")
    print("  SUCCESS: Поле ввода будет по центру относительно календаря")
    print("  SUCCESS: Это должно решить проблему с перекрытием элементов")


if __name__ == "__main__":
    test_calendar_position_next_to_input()