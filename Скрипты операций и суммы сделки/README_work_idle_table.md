# 📊 Подключение таблицы времени работы и простоя сотрудников

## 📋 Описание изменений

Все изменения связаны с подключением новой таблицы `dm.employee_work_idle_summary` для расчёта времени работы и простоя сотрудников на основе данных из `TRANSACTION_HISTORY`.

---

## 🗂️ Изменённые файлы

### 1. **data/queries_mssql.py**

#### Добавленные функции:

**`get_employee_idle_intervals(employee_name, start_date, end_date)`**
- Получает данные о простоях сотрудника из новой таблицы
- Возвращает словарь с новыми категориями: `idle_10_20`, `idle_20_30`, `idle_30_60`, `idle_60plus`
- Также возвращает: `total_idle_minutes`, `total_work_minutes`, `work_percentage`, `idle_percentage`

**`get_employee_work_idle_detail(employee_name, start_date, end_date)`**
- Получает детальные данные по дням для timeline-диаграммы
- Возвращает все поля из `dm.employee_work_idle_summary`

---

### 2. **components/charts.py**

#### Изменённая функция:

**`create_idle_intervals_bar_echarts(idle_counts)`**
- **Старые категории:** `5-10 мин`, `10-30 мин`, `30-60 мин`, `>1 часа`
- **Новые категории:** `10-20 мин`, `20-30 мин`, `30-60 мин`, `60+ мин`
- Использует новые ключи словаря: `idle_10_20`, `idle_20_30`, `idle_30_60`, `idle_60plus`

---

### 3. **callbacks/modal_callbacks.py**

#### Изменения в `handle_analytics_modal`:

1. **Импорт новых функций:**
   ```python
   from data.queries_mssql import (
       ...,
       get_employee_idle_intervals, get_employee_work_idle_detail
   )
   ```

2. **Расчёт времени работы:**
   - **Было:** Фиксированные 8 часов (`work_hours = 8.0`)
   - **Стало:** Реальные данные из таблицы (`total_work_minutes` из `get_employee_idle_intervals`)

3. **Форматирование времени работы:**
   - **Было:** `f"{int(work_hours)}ч 0м"`
   - **Стало:** `f"{work_hours_val}ч {work_mins_val}м"` (реальные минуты)

4. **Диаграммы:**
   - `time_distribution_pie` — использует реальные `total_work_minutes` и `total_idle_minutes`
   - `idle_intervals_bar` — использует новые категории из `get_employee_idle_intervals`

---

## 📁 Новые файлы

### 1. **Скрипты операций и суммы сделки/create_employee_work_idle_table_fixed.sql**
- Создаёт таблицу `dm.employee_work_idle_summary`
- Заполняет данными из `TRANSACTION_HISTORY`
- Учитывает разный регистр имён (`LOWER()`)
- Устраняет дубликаты (`SELECT DISTINCT`)

### 2. **Скрипты операций и суммы сделки/final_setup_work_idle_table.sql**
- Итоговый скрипт для развёртывания
- Объединяет создание и заполнение
- Включает проверку данных

### 3. **Скрипты операций и суммы сделки/test_new_idle_table.sql**
- Тестовые запросы для проверки таблицы
- 6 проверок: общая статистика, сверка с источниками, топ сотрудников

### 4. **Скрипты операций и суммы сделки/check_a_belash_records.sql**
- Проверка данных для конкретного пользователя
- Вывод всех записей из `TRANSACTION_HISTORY`

### 5. **Скрипты операций и суммы сделки/check_a_belash_summary.sql**
- Проверка расчётных данных для пользователя
- Вывод данных из `dm.employee_work_idle_summary`

### 6. **Скрипты операций и суммы сделки/diagnose_data_range.sql**
- Диагностика диапазона данных
- Сравнение количества дней в источнике и приёмнике

### 7. **Скрипты операций и суммы сделки/diagnose_user1283.sql**
- Поиск проблем с регистрами имён
- Проверка COLLATION базы данных

---

## 🏗️ Структура новой таблицы

```sql
dm.employee_work_idle_summary (
    user_name           NVARCHAR(100),   -- Логин пользователя
    fio                 NVARCHAR(200),   -- ФИО
    date_key            DATE,            -- Дата
    first_op_time       DATETIME2(0),    -- Первая операция
    last_op_time        DATETIME2(0),    -- Последняя операция
    total_period_min    INT,             -- Общий период (мин)
    total_idle_min      INT,             -- Время простоя (мин)
    total_work_min      INT,             -- Время работы (мин)
    work_percentage     DECIMAL(5,2),    -- % работы
    idle_percentage     DECIMAL(5,2),    -- % простоя
    idle_10_20          INT,             -- Простой 10-20 мин
    idle_20_30          INT,             -- Простой 20-30 мин
    idle_30_60          INT,             -- Простой 30-60 мин
    idle_60plus         INT              -- Простой 60+ мин
)
```

**Первичный ключ:** `(user_name, date_key)`

---

## 🔄 Логика расчёта

### 1. **Время работы**
```
total_period_min = DATEDIFF(MINUTE, first_op_time, last_op_time)
total_work_min = total_period_min - total_idle_min
```

### 2. **Время простоя**
- Считаются разрывы между операциями **≥ 10 минут**
- Суммируются все разрывы за день

### 3. **Проценты**
```
work_percentage = (total_work_min / total_period_min) * 100
idle_percentage = (total_idle_min / total_period_min) * 100
```

### 4. **Категории простоев**
| Категория | Описание |
|-----------|----------|
| `idle_10_20` | 10–20 минут |
| `idle_20_30` | 20–30 минут |
| `idle_30_60` | 30–60 минут |
| `idle_60plus` | 60+ минут |

---

## 🚀 Инструкция по развёртыванию

### Шаг 1: Создание и заполнение таблицы
```sql
-- Запустить в DBeaver
:load c:\Users\A.Gorbatenko\Documents\Dashboard\Скрипты операций и суммы сделки\final_setup_work_idle_table.sql
```

### Шаг 2: Проверка данных
```sql
-- Запустить в DBeaver
:load c:\Users\A.Gorbatenko\Documents\Dashboard\Скрипты операций и суммы сделки\test_new_idle_table.sql
```

### Шаг 3: Перезапуск приложения
```bash
# Остановить приложение
# Запустить заново app.py
python app.py
```

---

## ✅ Проверка работы

### 1. Проверка в модальном окне аналитики
- Открыть модальное окно производительности сотрудника
- Проверить карточку **"Время работы"** — должны быть реальные данные
- Проверить диаграмму **"Распределение времени работы"** — должны быть реальные проценты
- Проверить диаграмму **"Периоды простоя"** — новые категории (10-20, 20-30, 30-60, 60+)

### 2. SQL проверка
```sql
SELECT TOP 20 * FROM dm.employee_work_idle_summary ORDER BY date_key DESC;
```

---

## 🔧 Возможные проблемы и решения

### Проблема 1: Ошибка дублирования ключа
**Решение:** Скрипт использует `SELECT DISTINCT` для устранения дубликатов

### Проблема 2: Конфликт COLLATION
**Решение:** Явное приведение `COLLATE DATABASE_DEFAULT` во всех JOIN

### Проблема 3: Разный регистр имён
**Решение:** Использование `LOWER()` для всех сравнений

### Проблема 4: Нет данных за период
**Решение:** Проверить наличие данных в `TRANSACTION_HISTORY`:
```sql
SELECT COUNT(*) FROM raw_.TRANSACTION_HISTORY 
WHERE DATE_TIME_STAMP >= '2024-01-01';
```

---

## 📊 Источник данных

**Таблица:** `raw_.TRANSACTION_HISTORY`
- **Поля:** `USER_STAMP`, `DATE_TIME_STAMP`
- **Присоединение:** `raw_.USER_CADR_EDIT` для `fio`
- **Фильтры:** `DATE_TIME_STAMP IS NOT NULL`, `USER_STAMP IS NOT NULL`
- **Без фильтров по `TRANSACTION_TYPE`** — берутся все записи

---

## 📝 Примечания

1. **Порог простоя:** от 10 минут (не 5, как было раньше)
2. **Конец рабочего дня:** определяется по последней операции (не фиксированные 20:30)
3. **Начало рабочего дня:** определяется по первой операции
4. **Учёт всех сотрудников:** данные для всех, кто есть в `TRANSACTION_HISTORY`

---

## 📅 Дата создания документации
24 марта 2026 г.
