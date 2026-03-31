# ИНКРЕМЕНТАЛЬНАЯ ЗАГРУЗКА ЯЧЕЕК (LOCATION)

## 📋 Описание

Система инкрементальной загрузки данных о ячейках хранения из основной базы ILS в аналитическую базу `olap2_fixed`.

### Принцип работы

```
ILS.dbo.LOCATION ──(каждые 30 сек)──> raw_.LOCATION ──(каждые 30 сек)──> dwh.fact_location_snapshot
     (основная база)       (сырые данные)               (агрегированная таблица для дашборда)
```

### Преимущества

- ✅ **Минимальная нагрузка** на основную базу (только изменения)
- ✅ **Данные почти реального времени** (задержка 30-60 секунд)
- ✅ **Не нужно менять код дашборда** (VIEW работают с dwh.fact_location_snapshot)
- ✅ **Автоматическая работа** через Windows Task Scheduler

---

## 📁 Файлы

| Файл | Назначение |
|------|-----------|
| `incremental_locations_raw.py` | Загрузка из ILS в raw_.LOCATION |
| `incremental_locations_dwh.py` | Загрузка из raw_.LOCATION в dwh.fact_location_snapshot |
| `run_incremental_raw.bat` | BAT-файл для запуска raw-загрузки |
| `run_incremental_dwh.bat` | BAT-файл для запуска DWH-загрузки |

---

## ⚙️ НАСТРОЙКА

### ШАГ 1: Добавить поле `last_modified` (опционально)

```sql
USE olap2_fixed;
GO

-- Добавить поле для отслеживания изменений
ALTER TABLE dwh.fact_location_snapshot 
ADD last_modified DATETIME2 NULL;
GO

-- Создать индекс для ускорения поиска
CREATE INDEX IX_location_snapshot_modified 
ON dwh.fact_location_snapshot (location, last_modified)
INCLUDE (status, location_type, allocation_zone, work_zone, locating_zone);
GO
```

**Примечание:** Скрипт работает и без этого поля (использует DATE_TIME_STAMP из raw_.LOCATION).

---

### ШАГ 2: Первичная загрузка всех данных

Перед инкрементальной загрузкой нужно заполнить таблицу всеми данными:

```sql
USE olap2_fixed;
GO

-- Очистить таблицу (если нужно)
TRUNCATE TABLE dwh.fact_location_snapshot;
GO

-- Загрузить все данные
INSERT INTO dwh.fact_location_snapshot 
(date_key, location, status, location_type, locating_zone, allocation_zone, work_zone, source_system)
SELECT
    CAST(GETDATE() AS DATE) AS date_key,
    l.LOCATION AS location,
    CASE
        WHEN l.LOCATION_STS = 'Empty' THEN 'Empty'
        WHEN l.LOCATION_STS IN ('Picking', 'Storage') THEN 'Occupied'
        ELSE 'Available'
    END AS status,
    l.LOCATION_TYPE AS location_type,
    l.LOCATING_ZONE AS locating_zone,
    l.ALLOCATION_ZONE AS allocation_zone,
    l.WORK_ZONE AS work_zone,
    'WMS' AS source_system
FROM ILS.dbo.LOCATION l WITH (NOLOCK)
WHERE
    l.LOCATION_STS IS NOT NULL
    AND l.LOCATION_STS != 'Frozen'
    AND (l.LOCATION_CLASS = 'Inventory' OR l.LOCATION_CLASS IS NULL)
    AND l.LOCATION_TYPE NOT IN ('Брак/бой DMG', 'Напольная', 'Улица KC', 'Ячейки KSP');
GO

-- Проверить
SELECT 
    status, 
    COUNT(*) AS количество
FROM dwh.fact_location_snapshot 
GROUP BY status;
GO
```

---

### ШАГ 3: Настроить Windows Task Scheduler

#### Для raw-загрузки:

1. Откройте **Task Scheduler** → **Create Basic Task**
2. **Name:** `Location Incremental Load (RAW)`
3. **Trigger:** Daily
4. **Advanced settings:**
   - ✅ Repeat task every: **1 minute**
   - ✅ for a duration of: **Indefinitely**
5. **Action:** Start a program
   - **Program/script:** `c:\Users\A.Gorbatenko\Documents\Dashboard\script\run_incremental_raw.bat`
   - **Start in:** `c:\Users\A.Gorbatenko\Documents\Dashboard\script`
6. ✅ **Run with highest privileges**

#### Для DWH-загрузки:

1. Откройте **Task Scheduler** → **Create Basic Task**
2. **Name:** `Location Incremental Load (DWH)`
3. **Trigger:** Daily
4. **Advanced settings:**
   - ✅ Repeat task every: **1 minute**
   - ✅ for a duration of: **Indefinitely**
5. **Action:** Start a program
   - **Program/script:** `c:\Users\A.Gorbatenko\Documents\Dashboard\script\run_incremental_dwh.bat`
   - **Start in:** `c:\Users\A.Gorbatenko\Documents\Dashboard\script`
6. ✅ **Run with highest privileges**

---

### ШАГ 4: Проверка работы

#### Запустить вручную:

```bash
cd c:\Users\A.Gorbatenko\Documents\Dashboard
python script\incremental_locations_raw.py
python script\incremental_locations_dwh.py
```

#### Проверить логи:

```
c:\Users\A.Gorbatenko\Documents\Dashboard\script\logs\
├── incremental_locations_raw_20260327_120000.log
├── incremental_locations_dwh_20260327_120000.log
```

#### Проверить данные:

```sql
-- 1. Проверить raw_.LOCATION
SELECT 
    COUNT(*) AS total_rows,
    MAX(DATE_TIME_STAMP) AS last_update
FROM raw_.LOCATION;

-- 2. Проверить dwh.fact_location_snapshot
SELECT 
    status, 
    COUNT(*) AS количество
FROM dwh.fact_location_snapshot 
GROUP BY status;

-- 3. Проверить VIEW
SELECT TOP 5 * FROM dm.v_storage_cells_current;
SELECT TOP 5 * FROM dm.v_storage_current_status;
```

---

## 🔧 ПАРАМЕТРЫ

### В скриптах можно изменить:

| Параметр | Значение | Описание |
|----------|----------|----------|
| `INCREMENT_BUFFER_MINUTES` | 5 | Буфер времени (на случай задержек) |
| Частота запуска | 1 минута | В Task Scheduler |

---

## 📊 МОНИТОРИНГ

### Логи содержат:

```
2026-03-27 12:00:00 - INFO - ============================================================
2026-03-27 12:00:00 - INFO - 🚀 Начало инкрементальной загрузки LOCATION (raw)
2026-03-27 12:00:00 - INFO - ============================================================
2026-03-27 12:00:01 - INFO - 📍 Последнее изменение в raw_.LOCATION: 2026-03-27 11:59:30
2026-03-27 12:00:01 - INFO - 📤 Запрос изменений с 2026-03-27 11:54:30
2026-03-27 12:00:02 - INFO - ✅ Найдено изменений: 15
2026-03-27 12:00:03 - INFO - ✅ Загружено: 10 новых, 5 обновлённых
2026-03-27 12:00:03 - INFO - ============================================================
2026-03-27 12:00:03 - INFO - ✅ Загрузка завершена: 15 записей
2026-03-27 12:00:03 - INFO - ============================================================
```

### Метрики:

- **Количество изменений** — сколько ячеек изменилось
- **Время выполнения** — обычно 1-3 секунды
- **Ошибки** — логируются в файл

---

## ❗ УСТРАНЕНИЕ ПРОБЛЕМ

### Ошибка: "Нет данных в raw_.LOCATION"

**Решение:** Запустите полную загрузку через `reload_3days.py` или вручную через SQL.

### Ошибка: "Invalid object name 'raw_.LOCATION'"

**Решение:** Убедитесь, что таблица создана в базе `olap2_fixed`.

### Ошибка: "Timeout expired"

**Решение:** Увеличьте timeout в подключении или проверьте нагрузку на сервер.

### Дашборд показывает старые данные

**Решение:**
1. Проверьте, что Task Scheduler работает
2. Проверьте логи на ошибки
3. Проверьте, что VIEW обновляются:
   ```sql
   SELECT COUNT(*) FROM dm.v_storage_cells_current;
   ```

---

## 📈 ПРОИЗВОДИТЕЛЬНОСТЬ

| Метрика | Значение |
|---------|----------|
| Среднее время загрузки | 1-3 секунды |
| Задержка данных | 30-60 секунд |
| Нагрузка на ILS | Минимальная (только изменения) |
| Размер лога за день | ~1-5 МБ |

---

## 🔄 ОБНОВЛЕНИЕ

При изменении структуры таблицы LOCATION:

1. Обновите список полей в `incremental_locations_raw.py`
2. Перезапустите Task Scheduler
3. Проверьте логи

---

## ✅ ЧЕК-ЛИСТ ЗАПУСКА

- [ ] Добавлено поле `last_modified` (опционально)
- [ ] Выполнена первичная загрузка всех данных
- [ ] Созданы задачи в Task Scheduler
- [ ] Проверена работа вручную
- [ ] Настроено логирование
- [ ] Проверено отображение в дашборде

---

**Готово!** 🎉 Данные обновляются автоматически каждые 30-60 секунд.
