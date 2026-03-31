# Инкрементальное обновление DWH таблиц

## 📁 Файлы

| Файл | Описание |
|------|----------|
| `update_dwh_3days.sql` | Скрипт обновления данных за 3 дня (для запуска каждые 10 минут) |
| `update_dwh_7days.sql` | Скрипт обновления данных за 7 дней (для ежедневного запуска в 23:59) |

---

## 🎯 Принцип работы

### Стратегия обновления таблиц

| Тип таблицы | Стратегия | Примеры |
|-------------|-----------|---------|
| **Справочники** | UPSERT/MERGE | `dm.dim_employee`, `dm.dim_work_type` |
| **Промежуточные** | TRUNCATE + INSERT или DELETE + INSERT | `dwh.placement_cache`, `dwh.pick_cache`, `dwh.operations_enriched` |
| **Фактовые** | SWAP (временная таблица + переименование) | `dwh.fact_operation`, `dwh.fact_penalty` |
| **Локации** | Полная перезапись (TRUNCATE + INSERT) | `dwh.fact_location_snapshot` |

---

## 🔧 Как это работает

### 1. Справочники (`dm.dim_*`)

**`dim_employee`** — актуализация сотрудников:
```sql
-- 1. Помечаем устаревших как неактивных
UPDATE dm.dim_employee SET is_active = 0 WHERE ...

-- 2. Добавляем новых
INSERT INTO dm.dim_employee SELECT ... FROM raw_.USER_CADR_EDIT

-- 3. Обновляем данные существующих
UPDATE de SET fio = u.fio, smena = u.smena ...
```

**`dim_work_type`** — слияние новых видов работ:
```sql
MERGE dm.dim_work_type AS target
USING (SELECT DISTINCT work_type FROM dwh.operations_enriched) AS source
ON (target.work_type_name = source.work_type)
WHEN NOT MATCHED THEN INSERT ...
```

---

### 2. Промежуточные таблицы

**Кэши** (`placement_cache`, `pick_cache`) — полная перезапись:
```sql
TRUNCATE TABLE dwh.placement_cache;
INSERT INTO dwh.placement_cache SELECT ... FROM raw_.WORK_INSTRUCTION_VIEW2;
```

**`operations_enriched`** — удаление + вставка за период:
```sql
DELETE FROM dwh.operations_enriched WHERE date >= @cutoff_date;
INSERT INTO dwh.operations_enriched SELECT ... WHERE date >= @cutoff_date;
```

---

### 3. Фактовые таблицы (SWAP)

**`fact_operation`** — безопасное обновление через временную таблицу:

```sql
-- 1. Сохраняем старые данные (до cutoff_date)
SELECT * INTO dwh.fact_operation_tmp
FROM dwh.fact_operation
WHERE date_key < @cutoff_date;

-- 2. Добавляем новые данные за период
INSERT INTO dwh.fact_operation_tmp SELECT ... WHERE date >= @cutoff_date;

-- 3. Атомарное переключение (SWAP)
ALTER TABLE dwh.fact_operation NOCHECK CONSTRAINT FK_fact_operation_date;
EXEC sp_rename 'dwh.fact_operation', 'fact_operation_old';
EXEC sp_rename 'dwh.fact_operation_tmp', 'fact_operation';
ALTER TABLE dwh.fact_operation CHECK CONSTRAINT FK_fact_operation_date;

-- 4. Удаляем старую таблицу
DROP TABLE dwh.fact_operation_old;
```

**Преимущества SWAP:**
- ✅ Мгновенное переключение (даунтайм ~0 сек)
- ✅ Атомарность (или всё прошло, или ничего)
- ✅ Старые данные сохраняются до коммита
- ✅ Чтение не блокируется до момента переключения

---

### 4. Локации

**`fact_location_snapshot`** — полная перезапись:
```sql
TRUNCATE TABLE dwh.fact_location_snapshot;
INSERT INTO dwh.fact_location_snapshot SELECT ... FROM raw_.LOCATION;
```

---

## 📋 Порядок запуска

### 3-дневный цикл (каждые 10 минут):

```
1. reload_3days.py          → Обновляет raw_.таблицы за 3 дня
2. reload_locations.py       → Перезаписывает raw_.LOCATION_INVENTORY
3. update_dwh_3days.sql      → Обновляет dwh.* и dm.* таблицы за 3 дня
```

### 7-дневный цикл (ежедневно в 23:59):

```
1. reload_7days.py          → Обновляет raw_.таблицы за 7 дней
2. reload_locations.py       → Перезаписывает raw_.LOCATION_INVENTORY
3. update_dwh_7days.sql      → Обновляет dwh.* и dm.* таблицы за 7 дней
```

---

## ⚙️ Параметры

| Параметр | Значение | Описание |
|----------|----------|----------|
| `@period_days` | 3 или 7 | Период обновления в днях |
| `@cutoff_date` | `DATEADD(DAY, -@period_days, @end_date)` | Дата отсечки |
| `@start_date` | Мин. дата из `WORK_INSTRUCTION_VIEW2` | Начало периода данных |
| `@end_date` | Макс. дата из `WORK_INSTRUCTION_VIEW2` | Конец периода данных |
| `@DDD` | `DATEADD(MONTH, -6, @end_date)` | Дата для расчёта грузчиков |

---

## 🔒 Безопасность

### Транзакционность
Скрипт использует транзакции для критических операций:
```sql
BEGIN TRANSACTION;
-- SWAP операции
COMMIT;
```

### Проверка существования таблиц
Перед выполнением скрипт проверяет наличие необходимых таблиц:
```sql
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'fact_operation' ...)
    THROW 50001, 'Таблица не найдена', 1;
```

### Обработка ошибок
При ошибке выполняется откат (ROLLBACK), старые данные сохраняются.

---

## 📊 Логи

Скрипт выводит подробную информацию:
```
=== НАЧАЛО СКРИПТА ОБНОВЛЕНИЯ ===
Дата запуска: 2026-03-24 10:00:00
Период обновления: 21.03.2026 - 24.03.2026

=== ШАГ 1: Обновление справочников ===
  ✅ dim_employee обновлён. Активных сотрудников: 150
  ✅ dim_work_type обновлён. Всего видов работ: 45

=== ШАГ 2: Пересоздание промежуточных таблиц ===
  ✅ placement_cache: 5000 строк
  ✅ pick_cache: 12000 строк
  ✅ operations_enriched за период: 8500 строк

=== ШАГ 3: Обновление фактовых таблиц (SWAP) ===
  Сохранено старых данных: 250000 строк
  ✅ fact_operation обновлена. Всего записей: 275000

=== ШАГ 4: Полная перезапись локаций ===
  ✅ fact_location_snapshot: 15000 строк

=== ОБНОВЛЕНИЕ ЗАВЕРШЕНО ===
✅ Все таблицы успешно обновлены!
```

---

## ⚠️ Важные замечания

### 1. Внешние ключи
Перед SWAP внешние ключи отключаются, после — включаются:
```sql
ALTER TABLE dwh.fact_operation NOCHECK CONSTRAINT FK_fact_operation_date;
-- SWAP
ALTER TABLE dwh.fact_operation CHECK CONSTRAINT FK_fact_operation_date;
```

### 2. Индексы
После SWAP индексы пересоздаются:
```sql
CREATE INDEX IX_fact_operation_date_key ON dwh.fact_operation(date_key);
CREATE INDEX IX_fact_operation_employee ON dwh.fact_operation(employee_id);
```

### 3. Представления (VIEWS)
Если есть VIEWS на этих таблицах — они **не сломаются** при SWAP, так как `sp_rename` сохраняет совместимость имён.

### 4. Производительность
- SWAP выполняется мгновенно
- Основная нагрузка — на этапе вставки данных во временную таблицу
- Рекомендуется запускать в периоды низкой нагрузки

---

## 🧪 Тестирование

Перед запуском на продакшене:

1. **Создайте тестовую БД**
   ```sql
   CREATE DATABASE olap2_test;
   ```

2. **Запустите Full.sql** для инициализации таблиц

3. **Запустите update_dwh_3days.sql** на тестовой БД
   ```sql
   USE olap2_test;
   :r update_dwh_3days.sql
   ```

4. **Проверьте результат**
   ```sql
   SELECT COUNT(*) FROM dwh.fact_operation;
   SELECT TOP 10 * FROM dwh.fact_operation ORDER BY date_key DESC;
   ```

---

## 📞 Поддержка

При возникновении ошибок:

1. Проверьте логи выполнения
2. Убедитесь, что `raw_.` таблицы содержат данные
3. Проверьте наличие всех необходимых таблиц
4. При SWAP ошибке — старая таблица сохраняется как `fact_operation_old`

---

## 📝 История изменений

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | 2026-03-24 | Первая версия инкрементального обновления |
