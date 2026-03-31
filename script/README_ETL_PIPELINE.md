# 🚀 ETL Pipeline для обновления данных Dashboard

## 📁 Структура файлов

```
Скрипты операций и суммы сделки/
├── Python-скрипты (ETL):
│   ├── reload_3days.py          # Обновление raw_.таблиц за 3 дня
│   ├── reload_7days.py          # Обновление raw_.таблиц за 7 дней
│   ├── reload_locations.py      # Полная перезапись LOCATION_INVENTORY
│   ├── run_update_dwh.py        # Выполнение SQL-скрипта обновления DWH
│   └── pipeline_3days.py        # ОРКЕСТРАТОР: запускает все 3 шага последовательно
│
├── SQL-скрипты:
│   ├── update_dwh_3days.sql     # Обновление dwh.* и dm.* за 3 дня
│   ├── update_dwh_7days.sql     # Обновление dwh.* и dm.* за 7 дней
│   └── Full                     # Полный скрипт создания таблиц (первоначальная инициализация)
│
├── Логи:
│   └── logs/
│       ├── reload_3days_*.log
│       ├── reload_7days_*.log
│       ├── reload_locations_*.log
│       ├── run_update_dwh_*.log
│       └── pipeline_3days_*.log
│
└── Документация:
    ├── README_update_dwh.md     # Документация по SQL-скриптам
    └── README_ETL_PIPELINE.md   # Этот файл
```

---

## 🎯 Назначение скриптов

### 1. `reload_3days.py`
**Что делает:** Обновляет сырые данные в таблицах `raw_.` за последние 3 дня.

**Какие таблицы:**
- 18 таблиц из `ils` (ORDER_DETAIL, ORDER_HEADER, WORK_INSTRUCTION_VIEW2, и т.д.)
- 2 таблицы из `sk` (eks_peremer_ZX_KPP, Shtraf_Edit)

**Как работает:**
```python
# Для каждой таблицы:
1. DELETE FROM raw_.table WHERE date >= @cutoff_date (3 дня назад)
2. SELECT * FROM source WHERE date >= @cutoff_date
3. INSERT INTO raw_.table VALUES (...)
```

**Когда запускать:** Каждые 10 минут (в составе пайплайна)

---

### 2. `reload_7days.py`
**Что делает:** Обновляет сырые данные в таблицах `raw_.` за последние 7 дней.

**Отличие от reload_3days.py:** Только период (7 дней вместо 3)

**Когда запускать:** Ежедневно в 23:59 (в составе 7-дневного пайплайна)

---

### 3. `reload_locations.py`
**Что делает:** Полная перезапись таблицы `raw_.LOCATION_INVENTORY`

**Как работает:**
```python
1. TRUNCATE TABLE raw_.LOCATION_INVENTORY
2. SELECT * FROM ils.LOCATION_INVENTORY
3. INSERT INTO raw_.LOCATION_INVENTORY VALUES (...)
```

**Когда запускать:** После `reload_3days.py` или `reload_7days.py`

---

### 4. `run_update_dwh.py`
**Что делает:** Выполняет SQL-скрипт обновления аналитических таблиц

**Параметры:**
```bash
python run_update_dwh.py 3  # Обновить за 3 дня
python run_update_dwh.py 7  # Обновить за 7 дней
```

**Что обновляет:**
- **Справочники** (`dm.dim_employee`, `dm.dim_work_type`) — UPSERT
- **Промежуточные таблицы** (`dwh.operations_enriched`, `dwh.placement_cache`) — DELETE + INSERT
- **Фактовые таблицы** (`dwh.fact_operation`, `dwh.fact_penalty`) — SWAP через временную таблицу
- **Локации** (`dwh.fact_location_snapshot`) — Полная перезапись

---

### 5. `pipeline_3days.py` (ОРКЕСТРАТОР)
**Что делает:** Запускает весь 3-дневный ETL пайплайн последовательно

**Порядок выполнения:**
```
ШАГ 1: reload_3days.py       → Обновление raw_.таблиц за 3 дня
ШАГ 2: reload_locations.py   → Перезапись LOCATION_INVENTORY
ШАГ 3: run_update_dwh.py 3   → Обновление dwh.* и dm.* за 3 дня
```

**Когда запускать:** Каждые 10 минут

**Пример запуска:**
```bash
python pipeline_3days.py 3
```

---

## 📋 Расписание запуска

### 3-дневный цикл (каждые 10 минут)
```bash
*/10 * * * * python /path/to/pipeline_3days.py 3
```

**Что происходит:**
1. `reload_3days.py` обновляет `raw_.` таблицы за 3 дня
2. `reload_locations.py` полностью перезаписывает `LOCATION_INVENTORY`
3. `run_update_dwh.py 3` обновляет `dwh.*` и `dm.*` таблицы за 3 дня

---

### 7-дневный цикл (ежедневно в 23:59)
```bash
59 23 * * * python /path/to/pipeline_3days.py 7
```

**Что происходит:**
1. `reload_7days.py` обновляет `raw_.` таблицы за 7 дней
2. `reload_locations.py` полностью перезаписывает `LOCATION_INVENTORY`
3. `run_update_dwh.py 7` обновляет `dwh.*` и `dm.*` таблицы за 7 дней

---

## 🔧 Установка и настройка

### 1. Требования
```bash
pip install pymssql
```

### 2. Проверка подключения
Убедитесь, что есть доступ к серверам:
- `10.7.0.248` (источник: ils, sk)
- `10.7.0.27` (целевая: olap2_fixed)

### 3. Инициализация
Перед первым запуском пайплайна выполните `Full.sql` для создания всех таблиц:
```sql
USE olap2_fixed;
:r Full
```

### 4. Тестовый запуск
```bash
# Запустить 3-дневный пайплайн вручную
cd "Скрипты операций и суммы сделки"
python pipeline_3days.py 3
```

---

## 📊 Логи

Все скрипты записывают логи в папку `logs/`:

```
logs/
├── reload_3days_20260324_100000.log
├── reload_locations_20260324_100300.log
├── run_update_dwh_20260324_100500.log
└── pipeline_3days_20260324_100000.log
```

**Формат логов:**
```
2026-03-24 10:00:00,123 - INFO - ================================================================================
2026-03-24 10:00:00,123 - INFO - 🚀 ЗАПУСК ОБНОВЛЕНИЯ DWH ЗА 3 ДНЯ
2026-03-24 10:00:00,123 - INFO - ================================================================================
2026-03-24 10:00:01,456 - INFO - 📄 Чтение SQL-файла: update_dwh_3days.sql
2026-03-24 10:00:02,789 - INFO - ✅ SQL-файл прочитан. Размер: 45,678 символов
...
```

---

## ⚠️ Важные замечания

### 1. Последовательность выполнения
**Критично:** Скрипты должны выполняться строго по порядку!

```
✅ Правильно:
reload_3days.py → reload_locations.py → run_update_dwh.py

❌ Неправильно:
run_update_dwh.py → reload_3days.py (данные устареют!)
```

### 2. Блокировка от параллельных запусков
Если пайплайн выполняется дольше 10 минут, следующий запуск не должен стартовать.

**Решение (flock для Linux):**
```bash
# В cron или systemd
*/10 * * * * flock -n /tmp/pipeline_3days.lock python /path/to/pipeline_3days.py 3
```

**Для Windows (Task Scheduler):**
- Установить галочку "Не запускать новую копию, если выполняется текущая"

### 3. Транзакционность SQL
`update_dwh_3days.sql` выполняется в транзакции:
```sql
BEGIN TRANSACTION;
-- Все команды
COMMIT;
```

При ошибке — откат (ROLLBACK).

### 4. Время выполнения
| Скрипт | Ожидаемое время |
|--------|-----------------|
| `reload_3days.py` | 2-5 минут |
| `reload_locations.py` | 1-3 минуты |
| `run_update_dwh.py 3` | 3-10 минут |
| **Всего пайплайн** | **6-18 минут** |

Если выполняется дольше — проверить:
- Скорость сети между серверами
- Наличие индексов в `raw_.` таблицах
- Блокировки (locks) в SQL Server

---

## 🧪 Тестирование

### 1. Запуск на тестовой БД
```sql
-- Создать тестовую БД
CREATE DATABASE olap2_test;

-- Выполнить Full.sql для инициализации
USE olap2_test;
:r Full
```

### 2. Запустить пайплайн
```bash
# Изменить подключение в скриптах на olap2_test
python pipeline_3days.py 3
```

### 3. Проверить результат
```sql
USE olap2_test;

-- Количество записей
SELECT COUNT(*) FROM dwh.fact_operation;

-- Данные за последние 3 дня
SELECT TOP 100 * FROM dwh.fact_operation ORDER BY date_key DESC;

-- Проверка периода
SELECT MIN(date_key) AS min_date, MAX(date_key) AS max_date FROM dwh.fact_operation;
```

---

## 📞 Поддержка

### Частые ошибки

#### 1. "Таблица не найдена"
```
❌ Таблица dwh.fact_operation не найдена
```
**Решение:** Запустить `Full.sql` для инициализации таблиц.

#### 2. "Timeout expired"
```
❌ ШАГ 1 превысил таймаут (30 минут)
```
**Решение:**
- Увеличить таймаут в `pipeline_3days.py`
- Проверить скорость сети
- Оптимизировать индексы

#### 3. "Login failed"
```
❌ Ошибка подключения к базе данных
```
**Решение:** Проверить учётные данные в конфигурации скриптов.

---

## 📈 Мониторинг

### 1. Проверка последнего запуска
```sql
SELECT TOP 10 * FROM raw_.etl_log ORDER BY created_date DESC;
```

### 2. Проверка актуальности данных
```sql
-- Максимальная дата в fakt_operation
SELECT MAX(date_key) AS last_date FROM dwh.fact_operation;

-- Должно быть >= сегодняшней дата
```

### 3. Проверка количества записей
```sql
SELECT 
    'fact_operation' AS table_name, COUNT(*) AS row_count FROM dwh.fact_operation
UNION ALL
SELECT 'fact_penalty', COUNT(*) FROM dwh.fact_penalty
UNION ALL
SELECT 'fact_location_snapshot', COUNT(*) FROM dwh.fact_location_snapshot;
```

---

## 📝 История изменений

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | 2026-03-24 | Первая версия ETL пайплайна |

---

## ✅ Чек-лист перед запуском

- [ ] Установлен `pymssql`
- [ ] Есть доступ к `10.7.0.248` и `10.7.0.27`
- [ ] Выполнен `Full.sql` для создания таблиц
- [ ] Создана папка `logs/`
- [ ] Протестировано на тестовой БД
- [ ] Настроено расписание (cron/systemd/Task Scheduler)
- [ ] Настроено логирование
- [ ] Настроен мониторинг

---

**Готово! Теперь у вас есть полноценный ETL пайплайн для обновления данных Dashboard! 🎉**
