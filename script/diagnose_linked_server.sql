-- ============================================================================
-- ДИАГНОСТИКА LINKED SERVER И 3-ДНЕВНОГО ETL
-- Сервер аналитики: 10.7.0.27 (olap2_fixed)
-- ============================================================================

USE olap2_fixed;
GO

PRINT '╔' + REPLICATE('=', 78) + '╗';
PRINT '║' + SPACE(25) + 'ДИАГНОСТИКА ETL (LINKED SERVER)' + SPACE(22) + '║';
PRINT '╚' + REPLICATE('=', 78) + '╝';
PRINT '';
PRINT '📅 Время проверки: ' + CAST(GETDATE() AS NVARCHAR(50));
PRINT '';

-- ============================================================================
-- 1. ПРОВЕРКА LINKED SERVER
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '1. ПРОВЕРКА LINKED SERVER';
PRINT '═' + REPLICATE('=', 78);

SELECT 
    name AS linked_server_name,
    product,
    provider,
    data_source,
    is_remote_login_enabled,
    is_rpc_out_enabled,
    is_data_access_enabled
FROM sys.linked_servers
WHERE name IN ('ILS_SOURCE', 'SK_SOURCE');
GO

-- Тест подключения
PRINT '';
PRINT 'Тест подключения к ILS_SOURCE...';
BEGIN TRY
    SELECT TOP 1 
        '✅ ILS_SOURCE доступен' AS status,
        COUNT(*) OVER () AS total_tables
    FROM ILS_SOURCE.ils.INFORMATION_SCHEMA.TABLES WITH (NOLOCK);
END TRY
BEGIN CATCH
    SELECT '❌ ILS_SOURCE: ' + ERROR_MESSAGE() AS status;
END CATCH

PRINT '';
PRINT 'Тест подключения к SK_SOURCE...';
BEGIN TRY
    SELECT TOP 1 
        '✅ SK_SOURCE доступен' AS status,
        COUNT(*) OVER () AS total_tables
    FROM SK_SOURCE.sk.INFORMATION_SCHEMA.TABLES WITH (NOLOCK);
END TRY
BEGIN CATCH
    SELECT '❌ SK_SOURCE: ' + ERROR_MESSAGE() AS status;
END CATCH
GO

-- ============================================================================
-- 2. ПРОВЕРКА ИСТОЧНИКОВ ДАННЫХ
-- ============================================================================
PRINT '';
PRINT '═' + REPLICATE('=', 78);
PRINT '2. ПРОВЕРКА ИСТОЧНИКОВ ДАННЫХ (на источнике)';
PRINT '═' + REPLICATE('=', 78);

-- WORK_INSTRUCTION_VIEW2
PRINT '';
PRINT 'WORK_INSTRUCTION_VIEW2:';
SELECT 
    'WIV2' AS table_name,
    COUNT(*) AS total_rows,
    MIN(CAST(date_time_stamp AS DATE)) AS min_date,
    MAX(CAST(date_time_stamp AS DATE)) AS max_date,
    DATEADD(DAY, -3, MAX(CAST(date_time_stamp AS DATE))) AS expected_cutoff
FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2 WITH (NOLOCK)
WHERE CONDITION = 'closed' AND INSTRUCTION_TYPE = 'Detail';

-- TRANSACTION_HISTORY
PRINT '';
PRINT 'TRANSACTION_HISTORY (за 3 дня):';
SELECT 
    'TH' AS table_name,
    COUNT(*) AS total_rows,
    MIN(CAST(date_time_stamp AS DATE)) AS min_date,
    MAX(CAST(date_time_stamp AS DATE)) AS max_date
FROM ILS_SOURCE.ils.dbo.TRANSACTION_HISTORY WITH (NOLOCK)
WHERE CAST(date_time_stamp AS DATE) >= DATEADD(DAY, -3, GETDATE());

-- USER_CADR_EDIT
PRINT '';
PRINT 'USER_CADR_EDIT (активные):';
SELECT 
    'UCE' AS table_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN deleted = 0 THEN 1 ELSE 0 END) AS active_users
FROM ILS_SOURCE.ils.dbo.USER_CADR_EDIT WITH (NOLOCK);

-- eks_peremer_ZX_KPP (из SK)
PRINT '';
PRINT 'eks_peremer_ZX_KPP (за 3 дня):';
SELECT 
    'KPP' AS table_name,
    COUNT(*) AS total_rows,
    MIN(CAST(date_time_stamp AS DATE)) AS min_date,
    MAX(CAST(date_time_stamp AS DATE)) AS max_date
FROM SK_SOURCE.sk.dbo.eks_peremer_ZX_KPP WITH (NOLOCK)
WHERE CAST(date_time_stamp AS DATE) >= DATEADD(DAY, -3, GETDATE());

-- Shtraf_Edit (из SK)
PRINT '';
PRINT 'Shtraf_Edit (за 3 дня):';
SELECT 
    'SHTRAF' AS table_name,
    COUNT(*) AS total_rows,
    MIN(CAST(date_time_stamp AS DATE)) AS min_date,
    MAX(CAST(date_time_stamp AS DATE)) AS max_date
FROM SK_SOURCE.sk.dbo.Shtraf_Edit WITH (NOLOCK)
WHERE CAST(date_time_stamp AS DATE) >= DATEADD(DAY, -3, GETDATE());
GO

-- ============================================================================
-- 3. ПРОВЕРКА ЦЕЛЕВЫХ ТАБЛИЦ
-- ============================================================================
PRINT '';
PRINT '═' + REPLICATE('=', 78);
PRINT '3. ПРОВЕРКА ЦЕЛЕВЫХ ТАБЛИЦ (на аналитике)';
PRINT '═' + REPLICATE('=', 78);

DECLARE @cutoff_date DATE = DATEADD(DAY, -3, GETDATE());

-- operations_enriched
PRINT '';
PRINT 'dwh.operations_enriched:';
SELECT 
    'operations_enriched' AS table_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN date >= @cutoff_date THEN 1 ELSE 0 END) AS rows_last_3_days,
    MIN(date) AS min_date,
    MAX(date) AS max_date
FROM dwh.operations_enriched WITH (NOLOCK);

-- fact_operation
PRINT '';
PRINT 'dwh.fact_operation:';
SELECT 
    'fact_operation' AS table_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN date_key >= @cutoff_date THEN 1 ELSE 0 END) AS rows_last_3_days,
    MIN(date_key) AS min_date,
    MAX(date_key) AS max_date
FROM dwh.fact_operation WITH (NOLOCK);

-- fact_penalty
PRINT '';
PRINT 'dwh.fact_penalty:';
SELECT 
    'fact_penalty' AS table_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN date_key >= @cutoff_date THEN 1 ELSE 0 END) AS rows_last_3_days,
    MIN(date_key) AS min_date,
    MAX(date_key) AS max_date
FROM dwh.fact_penalty WITH (NOLOCK);

-- placement_cache
PRINT '';
PRINT 'dwh.placement_cache:';
SELECT 
    'placement_cache' AS table_name,
    COUNT(*) AS total_rows
FROM dwh.placement_cache WITH (NOLOCK);

-- pick_cache
PRINT '';
PRINT 'dwh.pick_cache:';
SELECT 
    'pick_cache' AS table_name,
    COUNT(*) AS total_rows
FROM dwh.pick_cache WITH (NOLOCK);
GO

-- ============================================================================
-- 4. ПРОВЕРКА СПРАВОЧНИКОВ
-- ============================================================================
PRINT '';
PRINT '═' + REPLICATE('=', 78);
PRINT '4. ПРОВЕРКА СПРАВОЧНИКОВ';
PRINT '═' + REPLICATE('=', 78);

-- dim_employee
PRINT '';
PRINT 'dm.dim_employee:';
SELECT 
    'dim_employee' AS table_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_employees,
    SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) AS inactive_employees
FROM dm.dim_employee WITH (NOLOCK);

-- dim_work_type
PRINT '';
PRINT 'dm.dim_work_type:';
SELECT 
    'dim_work_type' AS table_name,
    COUNT(*) AS total_rows
FROM dm.dim_work_type WITH (NOLOCK);
GO

-- ============================================================================
-- 5. ПРОВЕРКА ПРОЦЕДУР
-- ============================================================================
PRINT '';
PRINT '═' + REPLICATE('=', 78);
PRINT '5. ПРОВЕРКА ХРАНИМЫХ ПРОЦЕДУР';
PRINT '═' + REPLICATE('=', 78);

SELECT 
    SCHEMA_NAME(schema_id) AS schema_name,
    name AS procedure_name,
    create_date,
    modify_date
FROM sys.procedures
WHERE name LIKE '%update_fact%' 
   OR name LIKE '%update_3days%'
ORDER BY schema_name, name;
GO

-- ============================================================================
-- 6. ПРОВЕРКА SQL AGENT JOB
-- ============================================================================
PRINT '';
PRINT '═' + REPLICATE('=', 78);
PRINT '6. ПРОВЕРКА SQL AGENT JOB';
PRINT '═' + REPLICATE('=', 78);

-- Статус задачи
PRINT '';
PRINT 'Статус задачи ETL_3DAYS_UPDATE:';
SELECT 
    j.name AS job_name,
    CASE j.enabled WHEN 1 THEN '✅ Включена' ELSE '❌ Отключена' END AS status,
    CASE 
        WHEN ja.start_execution_date IS NULL THEN 'Не выполняется'
        WHEN ja.stop_execution_date IS NULL THEN '⏳ Выполняется'
        WHEN ja.start_execution_date > ja.stop_execution_date THEN '⏳ Выполняется'
        ELSE '✅ Ожидает'
    END AS execution_status,
    ja.start_execution_date,
    ja.stop_execution_date
FROM msdb.dbo.sysjobs j
LEFT JOIN msdb.dbo.sysjobactivity ja ON j.job_id = ja.job_id
WHERE j.name = 'ETL_3DAYS_UPDATE';

-- Последние выполнения
PRINT '';
PRINT 'Последние 10 выполнений:';
SELECT TOP 10
    j.name AS job_name,
    h.run_date,
    h.run_time,
    h.run_duration / 100 AS duration_sec,
    CASE h.run_status 
        WHEN 0 THEN '❌ Ошибка'
        WHEN 1 THEN '✅ Успех'
        WHEN 2 THEN '⏳ Повтор'
        WHEN 3 THEN '⏸ Отменено'
    END AS status,
    LEFT(h.message, 100) AS message
FROM msdb.dbo.sysjobhistory h
JOIN msdb.dbo.sysjobs j ON h.job_id = j.job_id
WHERE j.name = 'ETL_3DAYS_UPDATE'
    AND h.step_id = 0  -- Общий результат задачи
ORDER BY h.run_date DESC, h.run_time DESC;
GO

-- ============================================================================
-- 7. ПРОВЕРКА ЛОГОВ ETL
-- ============================================================================
PRINT '';
PRINT '═' + REPLICATE('=', 78);
PRINT '7. ПРОВЕРКА ЛОГОВ ETL';
PRINT '═' + REPLICATE('=', 78);

IF OBJECT_ID('dbo.etl_job_log', 'U') IS NOT NULL
BEGIN
    PRINT '';
    PRINT 'Последние 10 записей в etl_job_log:';
    
    SELECT TOP 10
        log_id,
        job_name,
        run_date,
        status,
        operations_count,
        fact_operation_count,
        fact_penalty_count
    FROM dbo.etl_job_log
    ORDER BY run_date DESC;
END
ELSE
BEGIN
    PRINT '';
    PRINT '⚠️ Таблица etl_job_log не существует';
END
GO

-- ============================================================================
-- 8. ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ
-- ============================================================================
PRINT '';
PRINT '═' + REPLICATE('=', 78);
PRINT '8. ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ';
PRINT '═' + REPLICATE('=', 78);

-- Операции без сотрудника
PRINT '';
PRINT 'Операции без сотрудника (orphan records):';
SELECT 
    'orphan_operations' AS check_name,
    COUNT(*) AS count
FROM dwh.operations_enriched o WITH (NOLOCK)
WHERE NOT EXISTS (
    SELECT 1 FROM dm.dim_employee e WITH (NOLOCK)
    WHERE o.user_name COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT
);

-- Операции с будущими датами
PRINT '';
PRINT 'Операции с будущими датами:';
SELECT 
    'future_operations' AS check_name,
    COUNT(*) AS count
FROM dwh.operations_enriched WITH (NOLOCK)
WHERE date > CAST(GETDATE() AS DATE);

-- Дубликаты в fact_operation
PRINT '';
PRINT 'Дубликаты в fact_operation:';
SELECT 
    'duplicate_fact_operations' AS check_name,
    COUNT(*) AS count
FROM (
    SELECT reference_id, start_time, COUNT(*) AS cnt
    FROM dwh.fact_operation WITH (NOLOCK)
    GROUP BY reference_id, start_time
    HAVING COUNT(*) > 1
) AS dups;

-- fact_operation без сотрудника
PRINT '';
PRINT 'fact_operation без сотрудника:';
SELECT 
    'orphan_fact_operations' AS check_name,
    COUNT(*) AS count
FROM dwh.fact_operation f WITH (NOLOCK)
WHERE NOT EXISTS (
    SELECT 1 FROM dm.dim_employee e WITH (NOLOCK)
    WHERE f.employee_id = e.employee_id
);
GO

-- ============================================================================
-- 9. СРАВНЕНИЕ ИСТОЧНИК ↔ ЦЕЛЬ
-- ============================================================================
PRINT '';
PRINT '═' + REPLICATE('=', 78);
PRINT '9. СРАВНЕНИЕ: ИСТОЧНИК vs ЦЕЛЬ (за 3 дня)';
PRINT '═' + REPLICATE('=', 78);

-- Операции: источник vs цель
PRINT '';
PRINT 'Операции (WIV2 → operations_enriched):';
SELECT 
    'source' AS location,
    COUNT(*) AS count
FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2 WITH (NOLOCK)
WHERE CONDITION = 'closed' 
    AND INSTRUCTION_TYPE = 'Detail'
    AND CAST(START_DATE_TIME AS DATE) >= @cutoff_date
UNION ALL
SELECT 
    'target' AS location,
    COUNT(*) AS count
FROM dwh.operations_enriched WITH (NOLOCK)
WHERE date >= @cutoff_date;

-- Приемка: источник vs цель
PRINT '';
PRINT 'Приемка (TRANSACTION_HISTORY → operations_enriched):';
SELECT 
    'source' AS location,
    COUNT(*) AS count
FROM ILS_SOURCE.ils.dbo.TRANSACTION_HISTORY WITH (NOLOCK)
WHERE TRANSACTION_TYPE = '20'
    AND CAST(DATE_TIME_STAMP AS DATE) >= @cutoff_date
UNION ALL
SELECT 
    'target' AS location,
    COUNT(*) AS count
FROM dwh.operations_enriched WITH (NOLOCK)
WHERE WORK_TYPE = 'Приемка'
    AND date >= @cutoff_date;

-- Перемер: источник vs цель
PRINT '';
PRINT 'Перемер ZX KPP (eks_peremer_ZX_KPP → operations_enriched):';
SELECT 
    'source' AS location,
    COUNT(*) AS count
FROM SK_SOURCE.sk.dbo.eks_peremer_ZX_KPP WITH (NOLOCK)
WHERE CAST(date_time_stamp AS DATE) >= @cutoff_date
UNION ALL
SELECT 
    'target' AS location,
    COUNT(*) AS count
FROM dwh.operations_enriched WITH (NOLOCK)
WHERE WORK_TYPE = 'Перемер ZX KPP'
    AND date >= @cutoff_date;
GO

-- ============================================================================
-- 10. РЕКОМЕНДАЦИИ
-- ============================================================================
PRINT '';
PRINT '═' + REPLICATE('=', 78);
PRINT '10. РЕКОМЕНДАЦИИ';
PRINT '═' + REPLICATE('=', 78);

DECLARE @issues TABLE (issue NVARCHAR(500));

-- Проверка на проблемы
INSERT INTO @issues (issue)
SELECT '⚠️ Linked Server ILS_SOURCE недоступен'
WHERE NOT EXISTS (
    SELECT TOP 1 1 FROM ILS_SOURCE.ils.INFORMATION_SCHEMA.TABLES
);

INSERT INTO @issues (issue)
SELECT '⚠️ Linked Server SK_SOURCE недоступен'
WHERE NOT EXISTS (
    SELECT TOP 1 1 FROM SK_SOURCE.sk.INFORMATION_SCHEMA.TABLES
);

INSERT INTO @issues (issue)
SELECT '⚠️ operations_enriched: 0 записей за 3 дня'
WHERE NOT EXISTS (
    SELECT TOP 1 1 FROM dwh.operations_enriched 
    WHERE date >= @cutoff_date
);

INSERT INTO @issues (issue)
SELECT '⚠️ fact_operation: найдены дубликаты'
WHERE EXISTS (
    SELECT TOP 1 1
    FROM dwh.fact_operation
    GROUP BY reference_id, start_time
    HAVING COUNT(*) > 1
);

INSERT INTO @issues (issue)
SELECT '⚠️ SQL Agent Job отключен'
WHERE EXISTS (
    SELECT 1 FROM msdb.dbo.sysjobs 
    WHERE name = 'ETL_3DAYS_UPDATE' AND enabled = 0
);

-- Вывод проблем
IF EXISTS (SELECT 1 FROM @issues)
BEGIN
    PRINT '';
    PRINT 'Найдены проблемы:';
    SELECT issue FROM @issues;
END
ELSE
BEGIN
    PRINT '';
    PRINT '✅ Проблем не найдено. Система работает нормально.';
END

PRINT '';
PRINT '═' + REPLICATE('=', 78);
PRINT 'ДИАГНОСТИКА ЗАВЕРШЕНА';
PRINT '═' + REPLICATE('=', 78);
GO
