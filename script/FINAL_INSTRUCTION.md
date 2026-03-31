# 🚀 ОБНОВЛЕНИЕ LOCATION - ОДИН СКРИПТ + REAL-TIME ДАШБОРД

## 📋 Архитектура

```
ILS.dbo.LOCATION (10.7.0.248)
    ↓
    ├─(update_locations_all.py)─> raw_.LOCATION (10.7.0.27)
    │                             ↓
    │                             sp_update_location_snapshot
    │                             ↓
    │                             dwh.fact_location_snapshot
    │                             ↓
    │                             VIEW (без кэша!)
    └────────────────────────────> Дашборд (real-time)
```

---

## 📁 Файлы

| # | Файл | Назначение |
|---|------|-----------|
| 1 | `update_locations_all.py` | **ОДИН скрипт**: ILS → raw → DWH |
| 2 | `create_update_location_procedure.sql` | Хранимая процедура |
| 3 | `data/queries_mssql.py` | Изменён (отключён кэш для ячеек) |

---

## ⚙️ НАСТРОЙКА

### ШАГ 1: Создать процедуру (если ещё не создана)

```bash
# В SSMS: olap2_fixed
c:\Users\A.Gorbatenko\Documents\Dashboard\script\create_update_location_procedure.sql
```

---

### ШАГ 2: Настроить cron (Linux) или Task Scheduler (Windows)

#### **Linux (cron):**

```bash
# Открыть crontab
crontab -e

# Добавить задачу (каждую минуту)
* * * * * cd /home/admin1/script && python update_locations_all.py >> /home/admin1/script/logs/cron.log 2>&1
```

#### **Windows (Task Scheduler):**

1. **Create Basic Task**
2. **Name:** `Location Update`
3. **Trigger:** Daily → **Advanced:**
   - ✅ Repeat every: **1 minute**
   - ✅ for duration: **Indefinitely**
4. **Action:** Start a program
   - **Program:** `c:\Users\A.Gorbatenko\Documents\Dashboard\script\update_locations_all.py`
   - **Start in:** `c:\Users\A.Gorbatenko\Documents\Dashboard\script`
5. ✅ **Run with highest privileges**

---

### ШАГ 3: Тестовый запуск

```bash
cd c:\Users\A.Gorbatenko\Documents\Dashboard
python script/update_locations_all.py
```

**Ожидаемый результат:**
```
🚀 Обновление LOCATION (ILS → raw → DWH)
📍 Последнее изменение в raw_.LOCATION: 2026-03-27 14:58:00
📤 Запрос изменений из ILS с 2026-03-27 14:53:00
✅ Найдено изменений из ILS: 15
✅ raw_.LOCATION: 10 новых, 5 обновлённых
🔄 Вызов процедуры sp_update_location_snapshot...
✅ dwh.fact_location_snapshot обновлена
📊 raw_.LOCATION: 22,360 записей
📊 Empty: 5,432
📊 Occupied: 16,928
✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО
```

---

### ШАГ 4: Проверка дашборда

1. **Откройте дашборд**
2. **Проверьте карточку "Ячейки хранения"** — данные должны обновляться без задержек
3. **Откройте модальное окно** — данные должны быть актуальными

---

## 🔧 ОТКЛЮЧЕНИЕ КЭША

### Изменения в `data/queries_mssql.py`:

**Было:**
```python
result = execute_query_cached(query)  # С кэшем
```

**Стало:**
```python
result = mssql_client.execute(query)  # Без кэша
```

### Функции без кэша:

- `get_storage_cells_stats()` — карточка ячеек
- `get_all_storage_data()` — модальное окно

---

## 📊 Логи

```
script/logs/
└── update_locations_YYYYMMDD_HHMMSS.log
```

Пример:
```
2026-03-27 15:00:00 - INFO - ======================================================================
2026-03-27 15:00:00 - INFO - 🚀 Обновление LOCATION (ILS → raw → DWH)
2026-03-27 15:00:01 - INFO - 📍 Последнее изменение в raw_.LOCATION: 2026-03-27 14:59:30
2026-03-27 15:00:01 - INFO - 📤 Запрос изменений из ILS с 2026-03-27 14:54:30
2026-03-27 15:00:02 - INFO - ✅ Найдено изменений из ILS: 15
2026-03-27 15:00:03 - INFO - ✅ raw_.LOCATION: 10 новых, 5 обновлённых
2026-03-27 15:00:03 - INFO - 🔄 Вызов процедуры sp_update_location_snapshot...
2026-03-27 15:00:04 - INFO - ✅ dwh.fact_location_snapshot обновлена
2026-03-27 15:00:04 - INFO - 📊 raw_.LOCATION: 22,360 записей
2026-03-27 15:00:04 - INFO - 📊 Empty: 5,432
2026-03-27 15:00:04 - INFO - 📊 Occupied: 16,928
2026-03-27 15:00:04 - INFO - ======================================================================
2026-03-27 15:00:04 - INFO - ✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО
```

---

## ✅ ИТОГ

| Что было | Что стало |
|----------|-----------|
| 2 скрипта | **1 скрипт** |
| 2 задачи в cron/Task Scheduler | **1 задача** |
| Кэш (задержка 30-60 сек) | **Real-time (без кэша)** |
| Сложная архитектура | **Простая архитектура** |

---

## 🎯 ГОТОВО!

Данные обновляются **каждую минуту** и отображаются в дашборде **без задержек**! 🚀
