# ⚡ БЫСТРЫЙ СТАРТ: НАСТРОЙКА LINKED SERVER ETL

## 📋 ЧТО БУДЕТ СДЕЛАНО

Переход с Python + cron на **Linked Server + SQL Agent** для ускорения ETL в 5-10 раз.

**Текущая скорость:** ~8 минут
**Ожидаемая скорость:** ~1-2 минуты ✅

---

## 🔧 ПОШАГОВАЯ ИНСТРУКЦИЯ ДЛЯ DBEAVER

### ШАГ 1: Настройка Linked Server (единоразово)

**⚠️ ВАЖНО:** Используем DBeaver вместо sqlcmd!

1. Откройте **DBeaver**
2. Подключитесь к серверу `10.7.0.27` (olap2_fixed)
3. Откройте файл: `setup_linked_server_dbeaver.sql`
4. Нажмите **Ctrl+Enter** (выполнить)
5. Проверьте вывод во вкладке **Output**

**Или выполните по частям:**
```sql
-- В новом SQL Editor (F3)
-- Скопируйте и выполните содержимое setup_linked_server_dbeaver.sql
```

**Проверка:**
```sql
SELECT TOP 5 * FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2;
SELECT TOP 5 * FROM SK_SOURCE.sk.dbo.eks_peremer_ZX_KPP;
```

---

### ШАГ 2: Создание процедур

1. Откройте файл: `update_procedures_3days_linked.sql`
2. Нажмите **Ctrl+Enter** (выполнить)

### ШАГ 3: Настройка SQL Agent Job

1. Откройте файл: `setup_sql_agent_job.sql`
2. Нажмите **Ctrl+Enter** (выполнить)

**Проверка:**
```sql
-- Статус задачи
EXEC msdb.dbo.sp_help_job @job_name = N'ETL_3DAYS_UPDATE';

-- Расписание
EXEC msdb.dbo.sp_help_jobschedule @job_name = N'ETL_3DAYS_UPDATE';
```

---

### ШАГ 4: Тестовый запуск

**Ручной запуск через DBeaver:**

1. Откройте файл: `update_dwh_3days_linked.sql`
2. Нажмите **Ctrl+Enter** (выполнить)
3. Следите за выводом во вкладке **Output**

**Или через SQL Agent:**
```sql
EXEC msdb.dbo.sp_start_job @job_name = N'ETL_3DAYS_UPDATE';
```

**Проверка результата:**
```sql
-- Количество записей
SELECT 'operations_enriched' AS tbl, COUNT(*) AS cnt FROM dwh.operations_enriched;
SELECT 'fact_operation' AS tbl, COUNT(*) AS cnt FROM dwh.fact_operation;
SELECT 'fact_penalty' AS tbl, COUNT(*) AS cnt FROM dwh.fact_penalty;

-- Логи
SELECT * FROM dbo.etl_job_log ORDER BY run_date DESC;
```

---

### ШАГ 5: Полная диагностика

1. Откройте файл: `diagnose_linked_server.sql`
2. Нажмите **Ctrl+Enter** (выполнить)
3. Изучите вывод

---

## 📊 СРАВНЕНИЕ: БЫЛО vs СТАЛО

| Параметр | Python + cron | Linked Server + Agent |
|----------|---------------|----------------------|
| **Скорость** | ~8 мин | ~1-2 мин ✅ |
| **Надёжность** | Зависит от Python | Встроен в SQL Server ✅ |
| **Логирование** | Файлы | SQL Server Agent ✅ |
| **Мониторинг** | Сложно | Встроенный ✅ |
| **Расписание** | cron (10 мин) | SQL Agent (10 мин) ✅ |
| **Сложность** | 3 скрипта | 1 скрипт ✅ |
| **Отладка** | Сложно | SSMS + профайлер ✅ |

---

## 🗂 ФАЙЛЫ

| Файл | Назначение |
|------|------------|
| `setup_linked_server.sql` | Настройка Linked Server |
| `update_dwh_3days_linked.sql` | Основное обновление |
| `update_procedures_3days_linked.sql` | Процедуры fact таблиц |
| `setup_sql_agent_job.sql` | Настройка расписания |
| `diagnose_linked_server.sql` | Диагностика |
| `README_LINKED_SERVER.md` | Полная документация |

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
        WHEN 0 THEN 'Ошибка'
        WHEN 1 THEN 'Успех'
    END AS status
FROM msdb.dbo.sysjobhistory h
JOIN msdb.dbo.sysjobs j ON h.job_id = j.job_id
WHERE j.name = 'ETL_3DAYS_UPDATE'
ORDER BY h.run_date DESC;
```

### Проверка данных

```sql
-- Операции за 3 дня
SELECT 
    CAST(date AS DATE) AS date_key,
    COUNT(*) AS operations_count
FROM dwh.operations_enriched
WHERE date >= DATEADD(DAY, -3, GETDATE())
GROUP BY CAST(date AS DATE)
ORDER BY date_key DESC;
```

---

## 🛠 УСТРАНЕНИЕ ПРОБЛЕМ

### Linked Server недоступен

```sql
-- Пересоздать Linked Server
EXEC sp_dropserver 'ILS_SOURCE', 'droplogins';
-- Выполнить setup_linked_server.sql заново
```

### Задача не выполняется

```sql
-- Проверить статус Agent
EXEC master.dbo.xp_servicecontrol N'QueryState', N'SQLServerAgent';

-- Запустить Agent
EXEC master.dbo.xp_servicecontrol N'Start', N'SQLServerAgent';

-- Включить задачу
EXEC msdb.dbo.sp_update_job @job_name = 'ETL_3DAYS_UPDATE', @enabled = 1;
```

### Таймаут выполнения

```sql
-- Увеличить таймаут
EXEC sp_serveroption 'ILS_SOURCE', 'query timeout', '1200';
```

---

## ✅ КОНТРОЛЬНЫЙ СПИСОК

- [ ] Linked Server настроены (`ILS_SOURCE`, `SK_SOURCE`)
- [ ] Тестовый запрос работает
- [ ] Процедуры созданы
- [ ] SQL Agent запущен
- [ ] Задача `ETL_3DAYS_UPDATE` создана
- [ ] Задача включена
- [ ] Тестовый запуск успешен
- [ ] Логи записываются
- [ ] Диагностика пройдена

---

## 📞 ПОДДЕРЖКА

При проблемах:
1. Выполнить `diagnose_linked_server.sql`
2. Проверить логи: `SELECT * FROM dbo.etl_job_log`
3. Проверить историю Agent: `msdb.dbo.sysjobhistory`

---

**Время настройки:** ~15 минут
**Ожидаемая скорость:** 1-2 минуты
**Статус:** ✅ Готово
