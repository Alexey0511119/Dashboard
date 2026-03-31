-- ============================================================================
-- БЫСТРАЯ ДИАГНОСТИКА ПОСЛЕ ОБНОВЛЕНИЯ
-- ============================================================================
USE olap2_fixed;
GO

PRINT '=== ДИАГНОСТИКА СОСТОЯНИЯ ДАННЫХ ===';
PRINT 'Дата проверки: ' + CAST(GETDATE() AS NVARCHAR(50));

-- 1. Проверка raw_.таблиц
PRINT '';
PRINT '=== 1. RAW_.ТАБЛИЦЫ ===';
SELECT 
    'raw_.WORK_INSTRUCTION_VIEW2' AS таблица,
    COUNT(*) AS всего,
    SUM(CASE WHEN DATE_TIME_STAMP >= '2026-03-22' THEN 1 ELSE 0 END) AS за_3_дня
FROM raw_.WORK_INSTRUCTION_VIEW2 WITH (NOLOCK);

SELECT 
    'raw_.TRANSACTION_HISTORY' AS таблица,
    COUNT(*) AS всего,
    SUM(CASE WHEN DATE_TIME_STAMP >= '2026-03-22' THEN 1 ELSE 0 END) AS за_3_дня
FROM raw_.TRANSACTION_HISTORY WITH (NOLOCK);

-- 2. Проверка dwh.таблиц
PRINT '';
PRINT '=== 2. DWH.ТАБЛИЦЫ ===';
SELECT 
    'dwh.operations_enriched' AS таблица,
    COUNT(*) AS всего,
    SUM(CASE WHEN date >= '2026-03-22' THEN 1 ELSE 0 END) AS за_3_дня,
    MAX(date) AS макс_дата
FROM dwh.operations_enriched WITH (NOLOCK);

SELECT 
    'dwh.fact_operation' AS таблица,
    COUNT(*) AS всего,
    SUM(CASE WHEN date_key >= '2026-03-22' THEN 1 ELSE 0 END) AS за_3_дня,
    MAX(date_key) AS макс_дата
FROM dwh.fact_operation WITH (NOLOCK);

SELECT 
    'dwh.fact_penalty' AS таблица,
    COUNT(*) AS всего,
    SUM(CASE WHEN date_key >= '2026-03-22' THEN 1 ELSE 0 END) AS за_3_дня,
    MAX(date_key) AS макс_дата
FROM dwh.fact_penalty WITH (NOLOCK);

-- 3. Проверка времени последнего обновления
PRINT '';
PRINT '=== 3. ВРЕМЯ ПОСЛЕДНЕГО ОБНОВЛЕНИЯ ===';
SELECT 
    'operations_enriched' AS таблица,
    MAX(START_DATE_TIME) AS последняя_операция
FROM dwh.operations_enriched WITH (NOLOCK);

SELECT 
    'fact_operation' AS таблица,
    MAX(start_time) AS последняя_операция
FROM dwh.fact_operation WITH (NOLOCK);

-- 4. Проверка зависших процессов
PRINT '';
PRINT '=== 4. ЗАВЕРШЁННЫЕ ПРОЦЕССЫ ===';
SELECT 
    session_id,
    command,
    percent_complete,
    estimated_completion_time / 1000.0 AS eta_sec,
    DB_NAME(database_id) AS db_name
FROM sys.dm_exec_requests
WHERE command LIKE '%INSERT%' 
   OR command LIKE '%DELETE%'
   OR command LIKE '%CREATE INDEX%';

PRINT '';
PRINT '=== ДИАГНОСТИКА ЗАВЕРШЕНА ===';
