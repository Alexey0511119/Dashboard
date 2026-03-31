# 🚀 БЫСТРЫЙ СТАРТ: НАСТРОЙКА LINKED SERVER ETL В DBEAVER

## 📋 ЧТО БУДЕТ СДЕЛАНО

Настраиваем быстрое обновление DWH через **Linked Server** с использованием **DBeaver**.

**Текущая скорость:** ~8 минут (Python + cron)  
**Ожидаемая скорость:** ~1-2 минуты (Linked Server + SQL Agent) ✅

---

## 📁 ФАЙЛЫ ДЛЯ НАСТРОЙКИ

Все файлы находятся в: `c:\Users\A.Gorbatenko\Documents\Dashboard\script\`

| № | Файл | Назначение | Время |
|---|------|------------|-------|
| 1 | `setup_linked_server_dbeaver.sql` | Настройка Linked Server | 1 мин |
| 2 | `update_procedures_3days_linked.sql` | Создание процедур | 30 сек |
| 3 | `setup_sql_agent_job.sql` | Настройка расписания | 30 сек |
| 4 | `update_dwh_3days_linked.sql` | Тестовое обновление | 1-2 мин |
| 5 | `diagnose_linked_server.sql` | Диагностика | 30 сек |

---

## 🔧 ПОШАГОВАЯ ИНСТРУКЦИЯ

### ⏱ Общее время настройки: ~5 минут

---

### ШАГ 1: Настройка Linked Server

**Файл:** `setup_linked_server_dbeaver.sql`

1. Откройте **DBeaver**
2. Подключитесь к `10.7.0.27` (olap2_fixed)
3. Откройте файл `setup_linked_server_dbeaver.sql`
   - Файл → Открыть файл → выберите файл
   - Или перетащите файл в окно DBeaver
4. Нажмите **Ctrl+Enter** (выполнить скрипт)
5. Дождитесь завершения
6. Проверьте вывод во вкладке **Output**

**Ожидаемый результат:**
```
✅ ILS_SOURCE создан
✅ SK_SOURCE создан
✅ ILS_SOURCE: подключение успешно
✅ SK_SOURCE: подключение успешно
```

**Проверка (выполните в SQL Editor):**
```sql
SELECT TOP 5 * FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2;
SELECT TOP 5 * FROM SK_SOURCE.sk.dbo.eks_peremer_ZX_KPP;
```

---

### ШАГ 2: Создание процедур

**Файл:** `update_procedures_3days_linked.sql`

1. Откройте файл `update_procedures_3days_linked.sql`
2. Нажмите **Ctrl+Enter**
3. Дождитесь завершения

**Ожидаемый результат:**
```
✅ Процедура dwh.usp_update_fact_operation_3days_linked создана
✅ Процедура dwh.usp_update_fact_penalty_3days_linked создана
```

---

### ШАГ 3: Настройка SQL Agent Job

**Файл:** `setup_sql_agent_job.sql`

1. Откройте файл `setup_sql_agent_job.sql`
2. Нажмите **Ctrl+Enter**
3. Дождитесь завершения

**Ожидаемый результат:**
```
✅ Задача ETL_3DAYS_UPDATE создана
✅ Расписание настроено: каждые 10 минут
```

**Проверка:**
```sql
-- Статус задачи
SELECT name, enabled 
FROM msdb.dbo.sysjobs 
WHERE name = 'ETL_3DAYS_UPDATE';

-- Расписание
EXEC msdb.dbo.sp_help_jobschedule @job_name = N'ETL_3DAYS_UPDATE';
```

---

### ШАГ 4: Тестовый запуск

**Файл:** `update_dwh_3days_linked.sql`

1. Откройте файл `update_dwh_3days_linked.sql`
2. Нажмите **Ctrl+Enter**
3. Следите за выводом (займёт 1-2 минуты)

**Ожидаемый результат:**
```
📊 Период обновления: 23.03.2026 - 26.03.2026
✅ Вставлено операций: 500000 строк
✅ fact_operation обновлена
✅ fact_penalty обновлена
=== УСПЕШНОЕ ЗАВЕРШЕНИЕ ===
```

**Проверка результата:**
```sql
-- Количество записей
SELECT 'operations_enriched' AS tbl, COUNT(*) AS cnt FROM dwh.operations_enriched;
SELECT 'operations_enriched (3 дня)' AS tbl, COUNT(*) AS cnt 
    FROM dwh.operations_enriched WHERE date >= DATEADD(DAY, -3, GETDATE());

SELECT 'fact_operation' AS tbl, COUNT(*) AS cnt FROM dwh.fact_operation;
SELECT 'fact_penalty' AS tbl, COUNT(*) AS cnt FROM dwh.fact_penalty;
```

---

### ШАГ 5: Диагностика

**Файл:** `diagnose_linked_server.sql`

1. Откройте файл `diagnose_linked_server.sql`
2. Нажмите **Ctrl+Enter**
3. Изучите вывод

**Ожидаемый результат:**
```
✅ ILS_SOURCE доступен
✅ SK_SOURCE доступен
✅ Проблем не найдено. Система работает нормально.
```

---

## ✅ КОНТРОЛЬНЫЙ СПИСОК

После настройки проверьте:

- [ ] **Linked Server созданы:**
  ```sql
  SELECT name FROM sys.linked_servers WHERE name IN ('ILS_SOURCE', 'SK_SOURCE');
  ```

- [ ] **Данные доступны:**
  ```sql
  SELECT COUNT(*) FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2;
  ```

- [ ] **Процедуры созданы:**
  ```sql
  SELECT name FROM sys.procedures WHERE name LIKE '%linked%';
  ```

- [ ] **Задача настроена:**
  ```sql
  SELECT name, enabled FROM msdb.dbo.sysjobs WHERE name = 'ETL_3DAYS_UPDATE';
  ```

- [ ] **Тестовый запуск успешен:**
  ```sql
  SELECT COUNT(*) FROM dwh.operations_enriched WHERE date >= DATEADD(DAY, -3, GETDATE());
  ```

---

## 🔍 МОНИТОРИНГ

### Проверка последнего выполнения

```sql
SELECT TOP 1 * FROM dbo.etl_job_log ORDER BY run_date DESC;
```

### Проверка истории задач

```sql
SELECT TOP 10
    h.run_date,
    h.run_duration / 100 AS duration_sec,
    CASE h.run_status 
        WHEN 0 THEN '❌ Ошибка'
        WHEN 1 THEN '✅ Успех'
    END AS status
FROM msdb.dbo.sysjobhistory h
JOIN msdb.dbo.sysjobs j ON h.job_id = j.job_id
WHERE j.name = 'ETL_3DAYS_UPDATE'
ORDER BY h.run_date DESC;
```

### Проверка данных

```sql
-- Операции по дням
SELECT 
    CAST(date AS DATE) AS date_key,
    COUNT(*) AS operations_count
FROM dwh.operations_enriched
GROUP BY CAST(date AS DATE)
ORDER BY date_key DESC;
```

---

## 🛠 УСТРАНЕНИЕ ПРОБЛЕМ

### Ошибка: "Cannot create an instance of OLE DB provider"

**Решение:** Скрипт автоматически попробует другие провайдеры. Если не помогло:

1. Откройте `setup_linked_server_dbeaver.sql`
2. Найдите строку с `SQLNCLI11`
3. Замените на `MSDASQL`
4. Выполните заново

---

### Ошибка: "Login failed for user 'manhreader'"

**Решение:**
1. Проверьте пароль в скрипте (должен быть `August2021`)
2. Проверьте доступность сервера 10.7.0.248
3. Убедитесь, что пользователь `manhreader` существует на источнике

---

### Задача не выполняется

**Решение:**
```sql
-- Проверить статус Agent
EXEC master.dbo.xp_servicecontrol N'QueryState', N'SQLServerAgent';

-- Включить задачу
EXEC msdb.dbo.sp_update_job @job_name = 'ETL_3DAYS_UPDATE', @enabled = 1;

-- Запустить вручную
EXEC msdb.dbo.sp_start_job @job_name = 'ETL_3DAYS_UPDATE';
```

---

### Таймаут выполнения

**Решение:**
```sql
-- Увеличить таймаут Linked Server
EXEC sp_serveroption 'ILS_SOURCE', 'query timeout', '1200';
EXEC sp_serveroption 'SK_SOURCE', 'query timeout', '1200';

-- Обновить статистику
EXEC sp_updatestats;
```

---

## 📊 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ

| Параметр | Значение |
|----------|----------|
| **Время настройки** | ~5 минут |
| **Время выполнения ETL** | 1-2 минуты |
| **Количество записей** | ~500K - 1M операций |
| **Частота обновления** | Каждые 10 минут |
| **Автоматизация** | SQL Server Agent ✅ |

---

## 📞 ПОДДЕРЖКА

При проблемах:

1. Выполните `diagnose_linked_server.sql`
2. Проверьте логи:
   ```sql
   SELECT * FROM dbo.etl_job_log ORDER BY run_date DESC;
   ```
3. Проверьте историю Agent:
   ```sql
   SELECT TOP 20 * FROM msdb.dbo.sysjobhistory ORDER BY run_date DESC;
   ```

---

**Версия:** 2.0  
**Дата:** 2026-03-26  
**Статус:** ✅ Готово для DBeaver  
**Скорость:** 1-2 минуты вместо 8 минут
