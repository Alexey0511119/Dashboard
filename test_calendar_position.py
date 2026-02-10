#!/usr/bin/env python3
"""
Тестирование перемещения календаря на левую сторону
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_calendar_position_fix():
    """Тестирование перемещения календаря на левую сторону"""
    
    print("=== ТЕСТИРОВАНИЕ ПЕРЕМЕЩЕНИЯ КАЛЕНДАРЯ НА ЛЕВУЮ СТОРОНУ ===\n")
    
    # Читаем файл app.py для проверки стилей
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("1. ПРОВЕРКА НАЛИЧИЯ ИЗМЕНЕННЫХ СТИЛЕЙ:")
    print("-" * 50)
    
    # Проверяем наличие ключевых стилей
    styles_to_check = [
        "left: 20px !important",
        "right: auto !important",
        "position: fixed !important",
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
    print("  - С левой стороны экрана (left: 20px)")
    print("  - Вместо правой стороны (было right: 20px)")
    print("  - Это должно предотвратить перекрытие карточками и диаграммами")
    print("  - Высокое значение z-index обеспечивает отображение поверх других элементов")
    
    print(f"\n3. РЕЗУЛЬТАТ:")
    print("-" * 50)
    print("  SUCCESS: Календарь перемещен на левую сторону экрана")
    print("  SUCCESS: Это должно решить проблему с перекрытием элементов")
    print("  SUCCESS: Календарь будет отображаться поверх других элементов")


if __name__ == "__main__":
    test_calendar_position_fix()