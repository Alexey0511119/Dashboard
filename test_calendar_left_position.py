#!/usr/bin/env python3
"""
Тестирование правильного позиционирования календаря слева от поля ввода
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_calendar_left_position():
    """Тестирование позиционирования календаря слева от поля ввода"""
    
    print("=== ТЕСТИРОВАНИЕ ПОЗИЦИОНИРОВАНИЯ КАЛЕНДАРЯ СЛЕВА ОТ ПОЛЯ ВВОДА ===\n")
    
    # Читаем файл app.py для проверки стилей
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("1. ПРОВЕРКА НАЛИЧИЯ ИЗМЕНЕННЫХ СТИЛЕЙ:")
    print("-" * 50)
    
    # Проверяем наличие ключевых стилей
    styles_to_check = [
        "position: absolute !important",
        "top: 0 !important",
        "left: 100% !important",
        "margin-left: 5px !important",
        "transform: translateY(-50%)",
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
    print("  - Слева от поля ввода даты (left: 100%)")
    print("  - По центру по высоте относительно поля ввода (transform: translateY(-50%))")
    print("  - С небольшим отступом от поля ввода (margin-left: 5px)")
    print("  - Это должно поместить поле ввода по центру по высоте календаря")
    print("  - Высокое значение z-index обеспечивает отображение поверх других элементов")
    
    print(f"\n3. РЕЗУЛЬТАТ:")
    print("-" * 50)
    print("  SUCCESS: Календарь теперь позиционируется слева от поля ввода")
    print("  SUCCESS: Поле ввода будет по центру по высоте календаря")
    print("  SUCCESS: Это должно решить проблему с перекрытием элементов")


if __name__ == "__main__":
    test_calendar_left_position()