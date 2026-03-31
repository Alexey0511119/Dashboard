# 🔧 НАСТРОЙКА LINKED SERVER ЧЕРЕЗ DBEAVER

## 📋 ЧТО НУЖНО

- **DBeaver** (уже установлен)
- Подключение к серверу аналитики `10.7.0.27` (уже есть)
- Права `sa` на сервере 10.7.0.27 (есть)

---

## 🚀 ПОШАГОВАЯ ИНСТРУКЦИЯ

### ШАГ 1: Откройте DBeaver

1. Запустите DBeaver
2. Найдите подключение к `10.7.0.27` (olap2_fixed)
3. **Дважды кликните** для подключения

---

### ШАГ 2: Создание Linked Server для ILS

1. Откройте **SQL Editor** (F3)
2. Скопируйте и выполните следующий скрипт:

```sql
USE [master];
GO

-- Удаляем старый (если есть)
IF EXISTS (SELECT 1 FROM sys.linked_servers WHERE name = 'ILS_SOURCE')
BEGIN
    EXEC sp_droplinkedsrvlogin 'ILS_SOURCE', NULL;
    EXEC sp_dropserver 'ILS_SOURCE', 'droplogins';
END
GO

-- Создаём ILS_SOURCE
EXEC sp_addlinkedserver
    @server = N'ILS_SOURCE',
    @srvproduct = N'',
    @provider = N'SQLNCLI11',
    @datasrc = N'10.7.0.248',
    @catalog = N'ils';
GO

-- Настраиваем
EXEC sp_serveroption 'ILS_SOURCE', 'data access', 'true';
EXEC sp_serveroption 'ILS_SOURCE', 'rpc', 'true';
EXEC sp_serveroption 'ILS_SOURCE', 'rpc out', 'true';
EXEC sp_serveroption 'ILS_SOURCE', 'remote proc transaction promotion', 'false';
EXEC sp_serveroption 'ILS_SOURCE', 'lazy schema validation', 'true';
EXEC sp_serveroption 'ILS_SOURCE', 'query timeout', '900';
GO

-- Добавляем логин
EXEC sp_addlinkedsrvlogin
    @rmtsrvname = 'ILS_SOURCE',
    @useself = 'false',
    @locallogin = NULL,
    @rmtuser = 'manhreader',
    @rmtpassword = 'August2021';
GO

PRINT '✅ ILS_SOURCE создан';
```

3. Нажмите **Ctrl+Enter** (выполнить скрипт)
4. Проверьте вывод вкладки **Output**

---

### ШАГ 3: Создание Linked Server для SK

В новом окне SQL Editor выполните:

```sql
USE [master];
GO

-- Удаляем старый (если есть)
IF EXISTS (SELECT 1 FROM sys.linked_servers WHERE name = 'SK_SOURCE')
BEGIN
    EXEC sp_droplinkedsrvlogin 'SK_SOURCE', NULL;
    EXEC sp_dropserver 'SK_SOURCE', 'droplogins';
END
GO

-- Создаём SK_SOURCE
EXEC sp_addlinkedserver
    @server = N'SK_SOURCE',
    @srvproduct = N'',
    @provider = N'SQLNCLI11',
    @datasrc = N'10.7.0.248',
    @catalog = N'sk';
GO

-- Настраиваем
EXEC sp_serveroption 'SK_SOURCE', 'data access', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'rpc', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'rpc out', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'remote proc transaction promotion', 'false';
EXEC sp_serveroption 'SK_SOURCE', 'lazy schema validation', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'query timeout', '900';
GO

-- Добавляем логин
EXEC sp_addlinkedsrvlogin
    @rmtsrvname = 'SK_SOURCE',
    @useself = 'false',
    @locallogin = NULL,
    @rmtuser = 'manhreader',
    @rmtpassword = 'August2021';
GO

PRINT '✅ SK_SOURCE создан';
```

---

### ШАГ 4: Проверка подключения

Выполните запрос:

```sql
-- Проверка ILS_SOURCE
SELECT TOP 5 * FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2;

-- Проверка SK_SOURCE
SELECT TOP 5 * FROM SK_SOURCE.sk.dbo.eks_peremer_ZX_KPP;
```

**Если видите данные** ✅ — Linked Server работают!

---

### ШАГ 5: Создание процедур

1. Откройте файл в DBeaver:
   ```
   c:\Users\A.Gorbatenko\Documents\Dashboard\script\update_procedures_3days_linked.sql
   ```
   (ПКМ на файле → Open With → DBeaver SQL Editor)

2. Или скопируйте содержимое файла и вставьте в SQL Editor
3. Выполните (**Ctrl+Enter**)

---

### ШАГ 6: Настройка SQL Agent Job

**Вариант A: Через скрипт**

1. Откройте в DBeaver:
   ```
   c:\Users\A.Gorbatenko\Documents\Dashboard\script\setup_sql_agent_job.sql
   ```

2. Выполните скрипт

**Вариант B: Вручную**

DBeaver не поддерживает графическое управление SQL Agent. Используйте скрипт выше.

---

### ШАГ 7: Тестовый запуск

```sql
-- Запуск задачи
EXEC msdb.dbo.sp_start_job @job_name = N'ETL_3DAYS_UPDATE';

-- Проверка статуса
SELECT TOP 5
    j.name AS job_name,
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

---

## 🔍 ДИАГНОСТИКА В DBEAVER

### Проверка Linked Server

```sql
-- Список всех Linked Server
SELECT 
    name AS linked_server,
    provider,
    data_source,
    is_data_access_enabled
FROM sys.linked_servers;

-- Проверка ILS_SOURCE
EXEC sp_testlinkedserver N'ILS_SOURCE';

-- Проверка SK_SOURCE
EXEC sp_testlinkedserver N'SK_SOURCE';
```

### Если ошибка при создании

**Ошибка:** `Cannot create an instance of OLE DB provider`

**Решение:** Используйте альтернативный provider:

```sql
-- Вместо SQLNCLI11 попробуйте MSDASQL
EXEC sp_addlinkedserver
    @server = N'ILS_SOURCE',
    @srvproduct = N'SQL Server',
    @provider = N'MSDASQL',
    @provstr = 'DRIVER={SQL Server};SERVER=10.7.0.248;DATABASE=ils;UID=manhreader;PWD=August2021;';
```

---

## 📊 БЫСТРАЯ ПРОВЕРКА

```sql
-- 1. Проверка Linked Server
SELECT name FROM sys.linked_servers WHERE name IN ('ILS_SOURCE', 'SK_SOURCE');

-- 2. Проверка данных на источнике
SELECT COUNT(*) AS source_count 
FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2 
WHERE CONDITION = 'closed' AND INSTRUCTION_TYPE = 'Detail';

-- 3. Проверка данных в цели
SELECT COUNT(*) AS target_count 
FROM dwh.operations_enriched;

-- 4. Проверка процедур
SELECT name FROM sys.procedures 
WHERE name LIKE '%update_fact%' AND name LIKE '%linked%';

-- 5. Проверка задачи
SELECT name, enabled FROM msdb.dbo.sysjobs WHERE name = 'ETL_3DAYS_UPDATE';
```

---

## 🛠 ЕСЛИ SQLNCLI11 НЕДОСТУПЕН

Попробуйте другие provider'ы:

```sql
-- Вариант 1: SQLNCLI (старый драйвер)
EXEC sp_addlinkedserver
    @server = N'ILS_SOURCE',
    @provider = N'SQLNCLI',
    @datasrc = N'10.7.0.248',
    @catalog = N'ils';

-- Вариант 2: OLE DB
EXEC sp_addlinkedserver
    @server = N'ILS_SOURCE',
    @provider = N'MSDASQL',
    @provstr = 'DRIVER={SQL Server};SERVER=10.7.0.248;DATABASE=ils;';

-- Вариант 3: .NET SqlClient
EXEC sp_addlinkedserver
    @server = N'ILS_SOURCE',
    @provider = N'SQLNCLI11.1',
    @datasrc = N'10.7.0.248',
    @catalog = N'ils';
```

---

## ✅ КОНТРОЛЬНЫЙ СПИСОК

- [ ] DBeaver подключён к 10.7.0.27
- [ ] ILS_SOURCE создан и доступен
- [ ] SK_SOURCE создан и доступен
- [ ] Проверочные запросы возвращают данные
- [ ] Процедуры созданы
- [ ] SQL Agent Job настроен
- [ ] Тестовый запуск успешен

---

## 📁 ФАЙЛЫ ДЛЯ DBEAVER

| Файл | Как использовать |
|------|------------------|
| `setup_linked_server_oledb.sql` | Открыть в DBeaver → Выполнить |
| `update_procedures_3days_linked.sql` | Открыть в DBeaver → Выполнить |
| `setup_sql_agent_job.sql` | Открыть в DBeaver → Выполнить |
| `update_dwh_3days_linked.sql` | Открыть в DBeaver → Выполнить для теста |
| `diagnose_linked_server.sql` | Открыть в DBeaver → Выполнить для проверки |

---

**Версия:** 1.0  
**Дата:** 2026-03-26  
**Статус:** ✅ Работает в DBeaver
