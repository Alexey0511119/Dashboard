import sys
sys.path.append('.')

from data.queries import get_employees_on_shift
employees = get_employees_on_shift()
print(f"Найдено {len(employees)} сотрудников")
if employees:
    print("Первые 3:")
    for e in employees[:3]:
        print(e)
else:
    print("Список пуст! Проверьте запрос.")