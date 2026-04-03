# 🔧 Исправление: Диаграммы показывают неверные данные

## 📋 Проблема

Диаграммы "Топ 5 проблемных часов" и "Топ 5 часов с ошибками" показывали **неверные данные**, несмотря на изменение логики обновления таблиц.

---

## 🔍 ПРИЧИНА НАЙДЕНА

### Старая логика (НЕ РАБОТАЛА):

```sql
-- 1. orders_timeliness обновлялась ЧАСТИЧНО (SWAP)
SELECT * INTO dwh.orders_timeliness_tmp
FROM dwh.orders_timeliness
WHERE date < @cutoff_date;  # <-- Сохранялись СТАРЫЕ данные

INSERT INTO dwh.orders_timeliness_tmp
SELECT ... FROM raw_.WORK_INSTRUCTION_VIEW2
WHERE date >= @cutoff_date;  # <-- Добавлялись новые за 3 дня

-- 2. fact_hourly_* считались из orders_timeliness
SELECT ... INTO dwh.fact_hourly_errors
FROM dwh.orders_timeliness  # <-- Использовались СТАРЫЕ + новые данные!
```

**Результат:** `fact_hourly_errors` считался из **смеси старых и новых данных**, что приводило к некорректным результатам!

---

### Новая логика (РАБОТАЕТ):

```sql
-- 1. orders_timeliness пересоздается ПОЛНОСТЬЮ
DROP TABLE IF EXISTS dwh.orders_timeliness;

SELECT ... INTO dwh.orders_timeliness
FROM raw_.WORK_INSTRUCTION_VIEW2  # <-- ВСЕ данные из источника
WHERE ...  # <-- Без фильтра по датам!

-- 2. fact_hourly_* считаются из обновленной orders_timeliness
DELETE FROM dwh.fact_hourly_errors;

INSERT INTO dwh.fact_hourly_errors
SELECT ... FROM dwh.orders_timeliness  # <-- Только АКТУАЛЬНЫЕ данные!
```

**Результат:** `fact_hourly_errors` считается из **полных актуальных данных**!

---

## 📁 Измененные файлы

### 1. `script/update_dwh_3days.sql` (строки 1205-1265)
**Изменения:**
- Убран SWAP (`SELECT * INTO ... WHERE date < @cutoff_date`)
- Добавлено полное пересоздание (`DROP TABLE ... SELECT ... INTO`)
- Убран фильтр `WHERE date >= @cutoff_date`

### 2. `script/update_procedures_3days_full.sql` (строки 696-751)
**Изменения:**
- Процедура `usp_update_orders_timeliness_3days` обновлена
- Убран фильтр по `@cutoff_date`
- Параметр сохранен для совместимости

---

## 🚀 Применение на сервере

```bash
# 1. Подключиться к серверу
ssh admin1@olap-server

# 2. Перейти в директорию скриптов
cd /home/admin1/script

# 3. Применить обновленные процедуры
/opt/mssql-tools18/bin/sqlcmd -S 10.7.0.27 -U sa -P Rdflhfn600 -d olap2_fixed \
  -i update_procedures_3days_full.sql

# 4. Запустить пайплайн для обновления данных
source venv/bin/activate
python pipeline_3days.py 3
```

---

## 📊 Результат

### До изменений:
- ❌ `orders_timeliness` содержала **старые + новые** данные
- ❌ `fact_hourly_*` считались из **некорректных** данных
- ❌ Диаграммы показывали **неверную** статистику

### После изменений:
- ✅ `orders_timeliness` пересоздается **полностью** из `raw_.WORK_INSTRUCTION_VIEW2`
- ✅ `fact_hourly_*` считаются из **актуальных** данных
- ✅ Диаграммы показывают **корректную** статистику за **весь период**

---

## 🔍 Проверка

```sql
-- 1. Проверить количество записей в orders_timeliness
SELECT 
    COUNT(*) AS записей,
    MIN(date) AS мин_дата,
    MAX(date) AS макс_дата
FROM dwh.orders_timeliness;

-- 2. Проверить данные в fact_hourly_delays
SELECT TOP 20 *
FROM dwh.fact_hourly_delays
ORDER BY pct_delayed DESC;

-- 3. Проверить данные в fact_hourly_errors
SELECT TOP 20 *
FROM dwh.fact_hourly_errors
ORDER BY pct_errors DESC;

-- 4. Сверить с исходными данными
SELECT
    DATEPART(HOUR, START_DATE_TIME) AS hour,
    COUNT(*) AS total_orders,
    SUM(CASE WHEN timeliness_status = 'Просрочено' THEN 1 ELSE 0 END) AS delayed_orders
FROM dwh.orders_timeliness
GROUP BY DATEPART(HOUR, START_DATE_TIME)
ORDER BY delayed_orders DESC;
```

---

## 📅 Дата изменения

2026-03-31

---

## 📝 Примечания

1. **Время выполнения** может увеличиться из-за полного пересоздания таблиц
2. **Параметр `@cutoff_date`** сохранен для обратной совместимости
3. **7-дневный пайплайн** (`update_dwh_7days.sql`) требует аналогичных изменений
