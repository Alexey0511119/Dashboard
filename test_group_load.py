# Тестирование функции get_group_load_monitor

import sys
sys.path.append('c:/Users/A.Gorbatenko/Documents/Dashboard')

from data.queries_mssql import get_group_load_monitor

print("Вызываем get_group_load_monitor()...")
try:
    data = get_group_load_monitor()
    print(f"Получено данных: {len(data)}")
    if data:
        print("\nПервые 3 записи:")
        for item in data[:3]:
            print(f"  - {item.get('group_name')}: {item.get('work_type')} = {item.get('open_tasks_count')} зад.")
    else:
        print("Данные пустые!")
except Exception as e:
    print(f"Ошибка: {e}")
    import traceback
    traceback.print_exc()
