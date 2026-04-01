# 📘 3-ДНЕВНЫЙ ЦИКЛ ОБНОВЛЕНИЯ DWH

## 📋 Описание

Автоматизированный 3-дневный цикл обновления витрин данных для дашборда производительности.

## 🎯 Назначение

Обеспечение актуальности данных дашборда с минимальной задержкой (обновление каждые 10 минут).

---

## 📁 ФАЙЛЫ 3-ДНЕВНОГО ЦИКЛА

### Основные скрипты (Python)

| № | Файл | Назначение |
|---|------|------------|
| 1 | `pipeline_3days.py` | **ОРКЕСТРАТОР** — запускает весь пайплайн последовательно |
| 2 | `reload_3days.py` | Выгрузка сырых данных за 3 дня (raw_.таблицы) |
| 3 | `reload_locations.py` | Полная перезапись LOCATION_INVENTORY |
| 4 | `run_update_dwh.py` | Выполнение SQL-скриптов обновления DWH |

### SQL-скрипты

| № | Файл | Назначение |
|---|------|------------|
| 5 | `update_dwh_3days_simple.sql` | **ОСНОВНОЙ** — обновление DWH за 3 дня (оптимизированная версия) |
| 6 | `update_procedures_3days_full.sql` | Процедуры для fact_operation, fact_penalty и других таблиц |
| 7 | `create_indexes_3days.sql` | Создание индексов для оптимизации скорости |
| 8 | `diagnose_3days_cycle.sql` | Диагностика состояния 3-дневного цикла |

### Вспомогательные файлы

| № | Файл | Назначение |
|---|------|------------|
| 9 | `run_pipeline.sh` | Bash-скрипт для cron |
| 10 | `crontab` | Расписание запуска (каждые 10 минут) |

---

## 🔄 ПОРЯДОК ВЫПОЛНЕНИЯ

```
┌─────────────────────────────────────────────────────────────┐
│                    pipeline_3days.py                        │
│                    (ОРКЕСТРАТОР)                            │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌────────────────┐  ┌─────────────────┐
│ Шаг 1:        │  │ Шаг 2:         │  │ Шаг 3:          │
│ reload_3days  │  │ reload_        │  │ run_update_dwh  │
│               │  │ locations      │  │ 3               │
│ Сырые данные  │  │ Локации        │  │ DWH таблицы     │
└───────────────┘  └────────────────┘  └─────────────────┘
```

### Детальное описание шагов

#### **ШАГ 1: reload_3days.py**
- Выгружает данные из источника (10.7.0.248/ils, sk)
- Обновляет **только за последние 3 дня**
- Таблицы: WORK_INSTRUCTION_VIEW2, TRANSACTION_HISTORY, USER_CADR_EDIT, и др. (21 таблица)
- Проверка целостности: если вставлено < 90% данных → ошибка

#### **ШАГ 2: reload_locations.py**
- **Полная перезапись** LOCATION_INVENTORY (TRUNCATE + INSERT)
- Все данные из источника

#### **ШАГ 3: run_update_dwh.py 3**
1. Создаёт процедуры из `update_procedures_3days_full.sql`
2. Выполняет `update_dwh_3days_simple.sql`

**Что обновляется:**
- **Справочники:** dim_employee, dim_work_type
- **Кэши:** placement_cache, pick_cache (полная перезапись)
- **operations_enriched:** DELETE за 3 дня + INSERT новых (не TRUNCATE!)
- **fact_operation:** DELETE за 3 дня + INSERT новых (не TRUNCATE!)
- **fact_penalty:** DELETE за 3 дня + INSERT новых (не TRUNCATE!)
- **fact_location_snapshot:** ПОЛНАЯ ПЕРЕЗАПИСЬ (так и задумано)
- **Остальные таблицы:** orders_enriched, fines_enriched, transaction_events и др.

---

## 🔧 ИСПРАВЛЕННЫЕ ПРОБЛЕМЫ

### ❌ Проблема 1: `DELETE FROM operations_enriched` удалял ВСЁ
**Было:**
```sql
DELETE FROM dwh.operations_enriched WHERE date >= @cutoff_date;
-- Если @cutoff_date = NULL или неправильное → удалялось ВСЁ
```

**Стало:**
```sql
-- Добавлена проверка @cutoff_date перед удалением
IF @cutoff_date IS NULL
BEGIN
    PRINT '❌ ОШИБКА: @cutoff_date = NULL! Пропускаем обновление.';
    RETURN;
END

DELETE FROM dwh.operations_enriched WHERE date >= @cutoff_date;
-- Теперь удаляются ТОЛЬКО данные за 3 дня
```

---

### ❌ Проблема 2: `TRUNCATE` в процедурах fact_operation/fact_penalty
**Было:**
```sql
TRUNCATE TABLE dwh.fact_operation;  -- ❌ Удаляло ВСЁ!
```

**Стало:**
```sql
DELETE FROM dwh.fact_operation WHERE date_key >= @cutoff_date;  -- ✅ Только за 3 дня
```

---

### ❌ Проблема 3: `DELETE` без `WHERE` для дополнительных таблиц
**Было:**
```sql
DELETE FROM dwh.orders_enriched;  -- ❌ Полное удаление!
DELETE FROM dwh.fines_enriched;   -- ❌ Полное удаление!
```

**Стало:**
```sql
DELETE FROM dwh.orders_enriched WHERE date >= @cutoff_date;  -- ✅ За 3 дня
DELETE FROM dwh.fines_enriched WHERE date >= @cutoff_date;   -- ✅ За 3 дня
```

---

### ❌ Проблема 4: Отсутствие проверок целостности
**Добавлено:**
- Проверка `@cutoff_date IS NULL` перед началом обновления
- Проверка: если вставлено < 90% данных → ошибка
- Проверка: подозрительно мало данных для важных таблиц
- Логирование даты отсечки

---

## 🚀 БЫСТРЫЙ СТАРТ

### 1. Создание индексов (один раз)
```bash
sqlcmd -S 10.7.0.27 -U sa -P Rdflhfn600 -d olap2_fixed \
       -i /home/admin1/script/base/create_indexes_3days.sql
```

### 2. Запуск 3-дневного пайплайна
```bash
# Единичный запуск
python3 /home/admin1/script/base/pipeline_3days.py 3

# Или через cron (каждые 10 минут)
*/10 * * * * /home/admin1/script/base/run_pipeline.sh
```

### 3. Диагностика
```bash
sqlcmd -S 10.7.0.27 -U sa -P Rdflhfn600 -d olap2_fixed \
       -i /home/admin1/script/base/diagnose_3days_cycle.sql
```

---

## 📊 ТАБЛИЦЫ, КОТОРЫЕ ОБНОВЛЯЮТСЯ

### raw_.таблицы (сырые данные)
| Таблица | Метод обновления | Период |
|---------|-----------------|--------|
| WORK_INSTRUCTION_VIEW2 | DELETE + INSERT | 3 дня |
| TRANSACTION_HISTORY | DELETE + INSERT | 3 дня |
| USER_CADR_EDIT | DELETE + INSERT | 3 дня |
| SHIPMENT_HEADER | DELETE + INSERT | 3 дня |
| SHIPMENT_DETAIL | DELETE + INSERT | 3 дня |
| UPLOAD_RECEIPT_HEADER | DELETE + INSERT | 3 дня |
| UPLOAD_RECEIPT_DETAIL | DELETE + INSERT | 3 дня |
| UPLOAD_RECEIPT_CONTAINER | DELETE + INSERT | 3 дня |
| LOCATION_INVENTORY | **TRUNCATE + INSERT** | **Полностью** |
| eks_peremer_ZX_KPP | DELETE + INSERT | 3 дня |
| Shtraf_Edit | DELETE + INSERT | 3 дня |
| labor_management | DELETE + INSERT | 3 дня |
| ORDER_HEADER | DELETE + INSERT | 3 дня |
| ORDER_DETAIL | DELETE + INSERT | 3 дня |
| RECEIPT_HEADER | DELETE + INSERT | 3 дня |
| RECEIPT_DETAIL | DELETE + INSERT | 3 дня |
| DOWNLOAD_* | DELETE + INSERT | 3 дня |
| UPLOAD_ORDER_* | DELETE + INSERT | 3 дня |
| CYCLE_COUNT_REQUEST | DELETE + INSERT | 3 дня |

### dwh.таблицы (витрины)
| Таблица | Метод обновления | Период |
|---------|-----------------|--------|
| operations_enriched | DELETE + INSERT | 3 дня |
| fact_operation | DELETE + INSERT | 3 дня |
| fact_penalty | DELETE + INSERT | 3 дня |
| fact_location_snapshot | **TRUNCATE + INSERT** | **Полностью** |
| orders_enriched | DELETE + INSERT | 3 дня |
| fines_enriched | DELETE + INSERT | 3 дня |
| transaction_events | DELETE + INSERT | 3 дня |
| placement_cache | **TRUNCATE + INSERT** | **Полностью** |
| pick_cache | **TRUNCATE + INSERT** | **Полностью** |
| cube_shipment_detail | DELETE + INSERT | 3 дня |
| receipts_status | **TRUNCATE + INSERT** | **Полностью** |
| orders_timeliness | DELETE + INSERT | 3 дня |
| order_accuracy_daily | DELETE + INSERT | 3 дня |
| rejected_lines_detail | DELETE + INSERT | 3 дня |
| fact_hourly_errors | DELETE + INSERT | **ВЕЛЬ период** | ⚠️ Изменено: пересчитывается за весь период |
| fact_hourly_delays | DELETE + INSERT | **ВЕЛЬ период** | ⚠️ Изменено: пересчитывается за весь период |
| placement_operations | DELETE + INSERT | 3 дня |

### dm.таблицы (справочники)
| Таблица | Метод обновления | Период |
|---------|-----------------|--------|
| dim_employee | UPSERT | Актуальные |
| dim_work_type | MERGE | По данным |
| employee_work_idle_summary | DELETE + INSERT | 3 дня |

---

## 🔍 ДИАГНОСТИКА

### Проверка количества записей
```sql
-- Общее состояние
SELECT 'dwh.operations_enriched' AS tbl, COUNT(*) AS cnt FROM dwh.operations_enriched;
SELECT 'dwh.operations_enriched (3 дня)' AS tbl, COUNT(*) AS cnt 
FROM dwh.operations_enriched WHERE date >= '2026-03-23';

SELECT 'dwh.fact_operation' AS tbl, COUNT(*) AS cnt FROM dwh.fact_operation;
SELECT 'dwh.fact_operation (3 дня)' AS tbl, COUNT(*) AS cnt 
FROM dwh.fact_operation WHERE date_key >= '2026-03-23';

SELECT 'dwh.fact_penalty' AS tbl, COUNT(*) AS cnt FROM dwh.fact_penalty;
SELECT 'dwh.fact_penalty (3 дня)' AS tbl, COUNT(*) AS cnt 
FROM dwh.fact_penalty WHERE date_key >= '2026-03-23';
```

### Проверка даты отсечки
```sql
SELECT 
    MAX(CAST(date_time_stamp AS DATE)) AS max_date,
    DATEADD(DAY, -3, MAX(CAST(date_time_stamp AS DATE))) AS cutoff_date
FROM raw_.WORK_INSTRUCTION_VIEW2
WHERE CONDITION = 'closed' AND INSTRUCTION_TYPE = 'Detail';
```

### Проверка целостности
```sql
-- Операции без сотрудника
SELECT COUNT(*) AS orphan_operations
FROM dwh.operations_enriched o
WHERE NOT EXISTS (
    SELECT 1 FROM dm.dim_employee e 
    WHERE o.user_name COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT
);

-- Операции с будущими датами
SELECT COUNT(*) AS future_operations
FROM dwh.operations_enriched
WHERE date > CAST(GETDATE() AS DATE);
```

---

## ⚙️ НАСТРОЙКА CRON

### Файл: `/etc/cron.d/dashboard_3days`
```bash
# 3-дневный цикл обновления (каждые 10 минут)
*/10 * * * * admin1 /home/admin1/script/base/run_pipeline.sh >> /var/log/dashboard_3days.log 2>&1

# 7-дневный цикл (в 23:59 ежедневно)
59 23 * * * admin1 /home/admin1/script/base/pipeline_3days.py 7 >> /var/log/dashboard_7days.log 2>&1
```

### Перезапуск cron
```bash
sudo systemctl restart cron
```

---

## 📝 ЛОГИРОВАНИЕ

### Расположение логов
```
/home/admin1/script/base/logs/
├── pipeline_3days_YYYYMMDD_HHMMSS.log
├── reload_3days_YYYYMMDD_HHMMSS.log
├── reload_locations_YYYYMMDD_HHMMSS.log
├── update_dwh_3days_YYYYMMDD_HHMMSS.log
└── ...
```

### Системные логи
```bash
# Просмотр логов cron
grep CRON /var/log/syslog | grep pipeline

# Просмотр последних ошибок
tail -100 /var/log/syslog | grep -i error
```

---

## 🛠 УСТРАНЕНИЕ НЕИСПРАВНОСТЕЙ

### Проблема: После обновления 0 записей в operations_enriched

**Причина:** `reload_3days.py` не загрузил данные или `@cutoff_date` неправильное

**Решение:**
1. Проверить логи `reload_3days_*.log`
2. Проверить дату отсечки:
   ```sql
   SELECT MAX(CAST(date_time_stamp AS DATE)) AS max_date
   FROM raw_.WORK_INSTRUCTION_VIEW2;
   ```
3. Если данных нет — перезапустить `reload_3days.py`

---

### Проблема: Ошибка "Timeout expired"

**Причина:** SQL-скрипт выполняется дольше 60 минут

**Решение:**
1. Проверить индексы: `create_indexes_3days.sql`
2. Обновить статистику: `EXEC sp_updatestats;`
3. Увеличить таймаут в `run_update_dwh.py`

---

### Проблема: Дубликаты в fact_operation

**Причина:** Повторный запуск без правильного `DELETE`

**Решение:**
1. Проверить, что используется `DELETE WHERE date_key >= @cutoff_date`
2. Проверить значение `@cutoff_date`
3. Очистить дубликаты вручную:
   ```sql
   WITH Dups AS (
       SELECT *, ROW_NUMBER() OVER (PARTITION BY reference_id, start_time ORDER BY date_key) AS rn
       FROM dwh.fact_operation
   )
   DELETE FROM Dups WHERE rn > 1;
   ```

---

## 📈 ОПТИМИЗАЦИЯ СКОРОСТИ

### Целевое время выполнения
- **reload_3days.py:** < 3 минут
- **reload_locations.py:** < 2 минут
- **run_update_dwh.py:** < 3 минут
- **Общее время:** < 8 минут ✅

### Факторы, влияющие на скорость
1. **Индексы** — обязательно выполнить `create_indexes_3days.sql`
2. **Статистика** — регулярно обновлять `EXEC sp_updatestats;`
3. **Размер пакетов** — в `reload_3days.py` используется 10000 строк
4. **TABLOCK** — используется для быстрой вставки

---

## ✅ КОНТРОЛЬНЫЙ СПИСОК ПЕРЕД ЗАПУСКОМ

- [ ] Выполнен `create_indexes_3days.sql`
- [ ] Проверено подключение к источнику (10.7.0.248)
- [ ] Проверено подключение к целевой БД (10.7.0.27)
- [ ] Существует таблица `raw_.WORK_INSTRUCTION_VIEW2`
- [ ] Существует таблица `dwh.operations_enriched`
- [ ] Существует таблица `dm.dim_employee`
- [ ] Настроен cron для автоматического запуска
- [ ] Настроено логирование

---

## 📞 ПОДДЕРЖКА

При возникновении проблем:
1. Проверить логи в `/home/admin1/script/base/logs/`
2. Выполнить `diagnose_3days_cycle.sql`
3. Проверить системные логи: `tail -100 /var/log/syslog`

---

**Версия:** 2.0  
**Дата обновления:** 2026-03-26  
**Статус:** ✅ Исправлено и протестировано
