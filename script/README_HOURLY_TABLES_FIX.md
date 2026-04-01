# Исправление: Обновление fact_hourly_errors и fact_hourly_delays за ВЕСЬ период

## 📋 Проблема

Таблицы `dwh.fact_hourly_errors` и `dwh.fact_hourly_delays` обновлялись только за последние 3 дня, что приводило к потере исторических данных для диаграмм "Топ 5 проблемных часов" и "Топ 5 часов с ошибками".

## ✅ Решение

Изменена логика обновления таблиц - теперь они пересчитываются за **ВЕЛЬ период** (все доступные данные).

---

## 📁 Измененные файлы

### 1. `script/update_dwh_3days.sql`
**Изменения:**
- Убран фильтр `WHERE date >= @cutoff_date` для `fact_hourly_errors`
- Убран фильтр `WHERE date >= @cutoff_date` для `fact_hourly_delays`
- `DELETE FROM table WHERE hour IN (...)` заменено на `DELETE FROM table` (полная очистка)

**Строки:** 1274-1330

### 2. `script/update_procedures_3days_full.sql`
**Изменения:**
- Процедура `dwh.usp_update_fact_hourly_errors_3days` - убран фильтр по `@cutoff_date`
- Процедура `dwh.usp_update_fact_hourly_delays_3days` - убран фильтр по `@cutoff_date`
- Параметр `@cutoff_date` сохранен для совместимости, но не используется

**Строки:** 751-833

### 3. `script/README_3DAYS_CYCLE.md`
**Изменения:**
- Обновлена документация по таблицам `fact_hourly_errors` и `fact_hourly_delays`
- Добавлены пометки "⚠️ Изменено: пересчитывается за весь период"

---

## 🚀 Применение на сервере

### Вариант A: Обновление процедур (рекомендуется)

```bash
# 1. Подключиться к серверу
ssh admin1@olap-server

# 2. Перейти в директорию скриптов
cd /home/admin1/script

# 3. Применить обновленные процедуры
/opt/mssql-tools18/bin/sqlcmd -S 10.7.0.27 -U sa -P Rdflhfn600 -d olap2_fixed \
  -i update_procedures_3days_full.sql
```

### Вариант B: Полное обновление через пайплайн

После применения процедур, следующий запуск пайплайна автоматически обновит таблицы за весь период:

```bash
# Пайплайн запустится автоматически по cron
# Или вручную:
cd /home/admin1/script
source venv/bin/activate
python pipeline_3days.py 3
```

---

## 📊 Результат

### До изменений:
- ❌ Диаграммы показывали данные только за последние 3 дня
- ❌ При запуске раз в 3 дня - данные затирались

### После изменений:
- ✅ Диаграммы показывают данные за **ВЕЛЬ период**
- ✅ Данные накапливаются и не затираются
- ✅ Точная статистика по проблемным часам и часам с ошибками

---

## 🔍 Проверка

```sql
-- Проверить количество записей
SELECT 
    'fact_hourly_errors' AS таблица,
    COUNT(*) AS записей
FROM dwh.fact_hourly_errors
UNION ALL
SELECT 
    'fact_hourly_delays' AS таблица,
    COUNT(*) AS записей
FROM dwh.fact_hourly_delays;

-- Проверить данные за весь период
SELECT TOP 10 *
FROM dwh.fact_hourly_delays
ORDER BY pct_delayed DESC;

SELECT TOP 10 *
FROM dwh.fact_hourly_errors
ORDER BY pct_errors DESC;
```

---

## 📝 Примечания

1. **Параметр `@cutoff_date`** сохранен в процедурах для обратной совместимости
2. **Полная очистка таблиц** (`DELETE FROM table`) обеспечивает корректный пересчет
3. **Время выполнения** может незначительно увеличиться из-за большего объема данных
4. **7-дневный пайплайн** (`update_dwh_7days.sql`) требует аналогичных изменений при необходимости

---

## 📅 Дата изменения

2026-03-31
