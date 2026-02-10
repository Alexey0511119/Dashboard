#!/usr/bin/env python3
"""
Поиск всех элементов с z-index в CSS
"""

import sys
import os
import re

def find_all_zindex_values():
    """Поиск всех значений z-index в CSS"""
    
    print("=== ПОИСК ВСЕХ Z-INDEX ЗНАЧЕНИЙ В CSS ===\n")
    
    # Читаем файл app.py
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Найдем все z-index значения
    z_index_pattern = r'z-index\s*:\s*(\d+|inherit|auto|initial)'
    matches = re.findall(z_index_pattern, content)
    
    print(f"Найдено {len(matches)} значений z-index:\n")
    
    # Разделим числовые и нечисловые значения
    numeric_values = []
    non_numeric_values = []
    
    for match in matches:
        if match.isdigit():
            numeric_values.append(int(match))
        else:
            non_numeric_values.append(match)
    
    # Показываем числовые значения в порядке убывания
    if numeric_values:
        print("Числовые значения z-index (в порядке убывания):")
        sorted_numeric = sorted(set(numeric_values), reverse=True)
        for val in sorted_numeric[:20]:  # Показываем первые 20 уникальных значений
            count = numeric_values.count(val)
            print(f"  {val} (встречается {count} раз)")
    
    if non_numeric_values:
        print(f"\nНе числовые значения: {set(non_numeric_values)}")
    
    print(f"\nАнализ потенциальных конфликтов:")
    print("-" * 50)
    
    # Найдем элементы, которые могут конфликтовать
    elements_with_high_zindex = []
    
    # Ищем элементы с высокими z-index значениями
    element_pattern = r'(\.[^{]+)\s*{[^}]*z-index\s*:\s*(\d+)'
    element_matches = re.findall(element_pattern, content)
    
    for selector, z_value in element_matches:
        z_val = int(z_value)
        if z_val > 1000:  # Показываем только высокие значения
            elements_with_high_zindex.append((selector.strip(), z_val))
    
    if elements_with_high_zindex:
        print("Элементы с высоким z-index (>1000):")
        for selector, z_val in sorted(elements_with_high_zindex, key=lambda x: x[1], reverse=True):
            print(f"  {selector}: {z_val}")
    else:
        print("Не найдено элементов с высоким z-index")
    
    print(f"\nРекомендации:")
    print("-" * 50)
    print("Для решения проблемы с календарем рекомендуется установить z-index")
    print("для элементов календаря выше максимального найденного значения")
    
    max_z = max(numeric_values) if numeric_values else 0
    recommended_z = max_z + 1000  # Добавляем запас
    print(f"Максимальное найденное значение: {max_z}")
    print(f"Рекомендуемое значение для календаря: {recommended_z}")


if __name__ == "__main__":
    find_all_zindex_values()