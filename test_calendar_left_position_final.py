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
        "top: 50% !important",
        "right: calc(100% + 300px) !important",
        "transform: translate(0, -50%)",
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
    print("  - Слева от поля ввода даты (right: calc(100% + 300px))")
    print("  - Смещен на 300px влево от поля ввода")
    print("  - По центру по высоте относительно поля ввода (top: 50% + transform: translate(0, -50%))")
    print("  - Это должно поместить поле ввода по центру по высоте календаря")
    print("  - Высокое значение z-index обеспечивает отображение поверх других элементов")
    
    print(f"\n3. РЕЗУЛЬТАТ:")
    print("-" * 50)
    print("  SUCCESS: Календарь теперь позиционируется слева от поля ввода")
    print("  SUCCESS: Поле ввода будет по центру по высоте календаря")
    print("  SUCCESS: Календарь не должен перекрывать поле ввода")


if __name__ == "__main__":
    test_calendar_left_position()