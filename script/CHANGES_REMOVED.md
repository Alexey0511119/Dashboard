# 🗑️ УДАЛЕНО ИЗ СКРИПТОВ ОБНОВЛЕНИЯ

## Что было удалено

Все упоминания о `fact_location_snapshot` и связанных таблицах были удалены из скриптов обновления, так как теперь используется **отдельная система обновления через sp_update_location_snapshot**.

---

## 📁 Изменённые файлы

### 1. **`Full`** (ШАГ 17)

**Было:**
```sql
-- ====== ШАГ 17: fact_location_snapshot ======
CREATE TABLE dwh.fact_location_snapshot (...);
INSERT INTO dwh.fact_location_snapshot ...
-- Заполнение через LOCATION_INVENTORY
```

**Стало:**
```sql
-- ====== ШАГ 17: Пропущено ======
-- Обновление dwh.fact_location_snapshot выполняется через:
-- - процедуру dwh.sp_update_location_snapshot
-- - скрипт update_locations_all.py (каждую минуту)
```

---

### 2. **`create_indexes_3days.sql`**

**Удалено:**
```sql
-- fact_location_snapshot - снимки локаций
CREATE INDEX IX_FACT_LOCATION_SNAPSHOT_DATE ON dwh.fact_location_snapshot (date_key);
CREATE INDEX IX_FACT_LOCATION_SNAPSHOT_LOC ON dwh.fact_location_snapshot (location);
```

**Причина:** Индексы теперь создаются в `create_update_location_procedure.sql`

---

### 3. **`diagnose_3days_cycle.sql`**

**Удалено:**
```sql
SELECT 'dwh.fact_location_snapshot' AS таблица, ...
SELECT '📊 fact_location_snapshot', ...
```

**Заменено на:**
```sql
-- dwh.fact_location_snapshot обновляется отдельно (не по 3-дневному циклу)
```

---

### 4. **`check_storage_data.sql`**

**Перемещён в:** `script/old/check_storage_data.sql`

**Причина:** Устарел, использует старую логику

---

## ✅ НОВАЯ АРХИТЕКТУРА

```
ILS.dbo.LOCATION (10.7.0.248)
    ↓
    ├─(update_locations_all.py, каждую минуту)─> raw_.LOCATION
    │                                             ↓
    │                                             sp_update_location_snapshot
    │                                             ↓
    │                                             dwh.fact_location_snapshot
    │                                             ↓
    └──────────────────────────────────────────> VIEW (без кэша)
                                                  ↓
                                                Дашборд
```

---

## 📦 Используемые файлы

| Файл | Назначение |
|------|-----------|
| `update_locations_all.py` | Обновление ILS → raw → DWH (каждую минуту) |
| `create_update_location_procedure.sql` | Создание хранимой процедуры |
| `data/queries_mssql.py` | Отключён кэш для ячеек (real-time) |

---

## 🚀 НАСТРОЙКА CRON

```bash
# Каждую минуту
* * * * * cd /home/admin1/script && python update_locations_all.py >> logs/cron.log 2>&1
```

---

## 📊 МОНИТОРИНГ

```sql
-- Проверить raw_.LOCATION
SELECT COUNT(*) FROM raw_.LOCATION;
SELECT MAX(DATE_TIME_STAMP) FROM raw_.LOCATION;

-- Проверить dwh.fact_location_snapshot
SELECT status, COUNT(*) FROM dwh.fact_location_snapshot GROUP BY status;

-- Проверить VIEW
SELECT TOP 5 * FROM dm.v_storage_cells_current;
```

---

## ✅ ИТОГ

| Что было | Что стало |
|----------|-----------|
| Обновление в составе 3-дневного цикла | **Отдельное обновление каждую минуту** |
| 2 скрипта (raw + DWH) | **1 скрипт** (update_locations_all.py) |
| Кэш (задержка) | **Real-time (без кэша)** |
| Сложная логика с LOCATION_INVENTORY | **Простая логика через LOCATION_STS** |

---

**Дата:** 27 марта 2026 г.  
**Версия:** 3.0 (финальная)
