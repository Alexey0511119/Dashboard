-- ============================================================================
-- ДИАГНОСТИКА 3-ДНЕВНОГО ЦИКЛА ОБНОВЛЕНИЯ
-- Скрипт для проверки состояния данных после обновления
-- ============================================================================
USE olap2_fixed;
GO

PRINT '=== ДИАГНОСТИКА 3-ДНЕВНОГО ЦИКЛА ===';
PRINT 'Дата проверки: ' + CAST(GETDATE() AS NVARCHAR(50));

-- ====== ПЕРЕМЕННЫЕ ======
DECLARE @period_days INT = 3;
DECLARE @cutoff_date DATE;
DECLARE @end_date DATE;

-- Получаем актуальный период из данных
SELECT
    @end_date = MAX(CAST(date_time_stamp AS DATE)),
    @cutoff_date = DATEADD(DAY, -@period_days, MAX(CAST(date_time_stamp AS DATE)))
FROM raw_.WORK_INSTRUCTION_VIEW2 WITH (NOLOCK)
WHERE CONDITION = 'closed' AND INSTRUCTION_TYPE = 'Detail';

PRINT 'Период проверки: ' + CONVERT(NVARCHAR(50), @cutoff_date, 104) + ' - ' + CONVERT(NVARCHAR(50), @end_date, 104);
PRINT '';

-- ============================================================================
-- 1. ПРОВЕРКА RAW_.ТАБЛИЦ (источники)
-- ============================================================================
PRINT '=== 1. ПРОВЕРКА RAW_.ТАБЛИЦ ===';

SELECT 
    'raw_.WORK_INSTRUCTION_VIEW2' AS таблица,
    COUNT(*) AS всего_записей,
    SUM(CASE WHEN DATE_TIME_STAMP >= @cutoff_date THEN 1 ELSE 0 END) AS за_3_дня
FROM raw_.WORK_INSTRUCTION_VIEW2 WITH (NOLOCK);

SELECT 
    'raw_.TRANSACTION_HISTORY' AS таблица,
    COUNT(*) AS всего_записей,
    SUM(CASE WHEN DATE_TIME_STAMP >= @cutoff_date THEN 1 ELSE 0 END) AS за_3_дня
FROM raw_.TRANSACTION_HISTORY WITH (NOLOCK);

SELECT 
    'raw_.USER_CADR_EDIT (active)' AS таблица,
    COUNT(*) AS всего_записей,
    0 AS за_3_дня
FROM raw_.USER_CADR_EDIT WITH (NOLOCK)
WHERE deleted = 0;

PRINT '';

-- ============================================================================
-- 2. ПРОВЕРКА DWH.ТАБЛИЦ (целевые)
-- ============================================================================
PRINT '=== 2. ПРОВЕРКА DWH.ТАБЛИЦ ===';

SELECT 
    'dwh.operations_enriched' AS таблица,
    COUNT(*) AS всего_записей,
    SUM(CASE WHEN date >= @cutoff_date THEN 1 ELSE 0 END) AS за_3_дня,
    MIN(date) AS мин_дата,
    MAX(date) AS макс_дата
FROM dwh.operations_enriched WITH (NOLOCK);

SELECT 
    'dwh.fact_operation' AS таблица,
    COUNT(*) AS всего_записей,
    SUM(CASE WHEN date_key >= @cutoff_date THEN 1 ELSE 0 END) AS за_3_дня,
    MIN(date_key) AS мин_дата,
    MAX(date_key) AS макс_дата
FROM dwh.fact_operation WITH (NOLOCK);

SELECT 
    'dwh.fact_penalty' AS таблица,
    COUNT(*) AS всего_записей,
    SUM(CASE WHEN date_key >= @cutoff_date THEN 1 ELSE 0 END) AS за_3_дня,
    MIN(date_key) AS мин_дата,
    MAX(date_key) AS макс_дата
FROM dwh.fact_penalty WITH (NOLOCK);

SELECT 
    'dwh.orders_enriched' AS таблица,
    COUNT(*) AS всего_записей,
    SUM(CASE WHEN date >= @cutoff_date THEN 1 ELSE 0 END) AS за_3_дня,
    MIN(date) AS мин_дата,
    MAX(date) AS макс_дата
FROM dwh.orders_enriched WITH (NOLOCK);

SELECT 
    'dwh.fines_enriched' AS таблица,
    COUNT(*) AS всего_записей,
    SUM(CASE WHEN date >= @cutoff_date THEN 1 ELSE 0 END) AS за_3_дня,
    MIN(date) AS мин_дата,
    MAX(date) AS макс_дата
FROM dwh.fines_enriched WITH (NOLOCK);

SELECT 
    'dwh.transaction_events' AS таблица,
    COUNT(*) AS всего_записей,
    SUM(CASE WHEN date_key >= @cutoff_date THEN 1 ELSE 0 END) AS за_3_дня,
    MIN(date_key) AS мин_дата,
    MAX(date_key) AS макс_дата
FROM dwh.transaction_events WITH (NOLOCK);

-- dwh.fact_location_snapshot обновляется отдельно (не по 3-дневному циклу)
-- PRINT 'dwh.fact_location_snapshot - обновляется через sp_update_location_snapshot';

PRINT '';

-- ============================================================================
-- 3. ПРОВЕРКА КЭШЕЙ
-- ============================================================================
PRINT '=== 3. ПРОВЕРКА КЭШЕЙ ===';

SELECT 
    'dwh.placement_cache' AS таблица,
    COUNT(*) AS записей
FROM dwh.placement_cache WITH (NOLOCK);

SELECT 
    'dwh.pick_cache' AS таблица,
    COUNT(*) AS записей
FROM dwh.pick_cache WITH (NOLOCK);

PRINT '';

-- ============================================================================
-- 4. ПРОВЕРКА СПРАВОЧНИКОВ
-- ============================================================================
PRINT '=== 4. ПРОВЕРКА СПРАВОЧНИКОВ ===';

SELECT 
    'dm.dim_employee' AS таблица,
    COUNT(*) AS всего,
    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS активных
FROM dm.dim_employee WITH (NOLOCK);

SELECT 
    'dm.dim_work_type' AS таблица,
    COUNT(*) AS всего
FROM dm.dim_work_type WITH (NOLOCK);

PRINT '';

-- ============================================================================
-- 5. ПРОВЕРКА ДОПОЛНИТЕЛЬНЫХ ТАБЛИЦ
-- ============================================================================
PRINT '=== 5. ПРОВЕРКА ДОПОЛНИТЕЛЬНЫХ ТАБЛИЦ ===';

SELECT 
    'dwh.orders_timeliness' AS таблица,
    COUNT(*) AS всего_записей,
    SUM(CASE WHEN date >= @cutoff_date THEN 1 ELSE 0 END) AS за_3_дня
FROM dwh.orders_timeliness WITH (NOLOCK);

SELECT 
    'dwh.order_accuracy_daily' AS таблица,
    COUNT(*) AS всего_записей,
    SUM(CASE WHEN date >= @cutoff_date THEN 1 ELSE 0 END) AS за_3_дня
FROM dwh.order_accuracy_daily WITH (NOLOCK);

SELECT 
    'dwh.rejected_lines_detail' AS таблица,
    COUNT(*) AS всего_записей,
    SUM(CASE WHEN CAST(DATE_TIME_STAMP AS DATE) >= @cutoff_date THEN 1 ELSE 0 END) AS за_3_дня
FROM dwh.rejected_lines_detail WITH (NOLOCK);

SELECT 
    'dwh.fact_hourly_errors' AS таблица,
    COUNT(*) AS всего_записей,
    0 AS за_3_дня
FROM dwh.fact_hourly_errors WITH (NOLOCK);

SELECT 
    'dwh.fact_hourly_delays' AS таблица,
    COUNT(*) AS всего_записей,
    0 AS за_3_дня
FROM dwh.fact_hourly_delays WITH (NOLOCK);

SELECT 
    'dm.employee_work_idle_summary' AS таблица,
    COUNT(*) AS всего_записей,
    SUM(CASE WHEN date_key >= @cutoff_date THEN 1 ELSE 0 END) AS за_3_дня
FROM dm.employee_work_idle_summary WITH (NOLOCK);

PRINT '';

-- ============================================================================
-- 6. ПРОВЕРКА ГРУЗЧИКОВ
-- ============================================================================
PRINT '=== 6. ПРОВЕРКА ГРУЗЧИКОВ ===';

SELECT 
    'raw_.gruz_operations' AS таблица,
    COUNT(*) AS всего_записей,
    SUM(CASE WHEN date_key >= @cutoff_date THEN 1 ELSE 0 END) AS за_3_дня,
    COUNT(DISTINCT user_name) AS уникальных_пользователей
FROM raw_.gruz_operations WITH (NOLOCK);

PRINT '';

-- ============================================================================
-- 7. ДЕТАЛЬНАЯ ПРОВЕРКА OPERATIONS_ENRICHED
-- ============================================================================
PRINT '=== 7. ДЕТАЛЬНАЯ ПРОВЕРКА OPERATIONS_ENRICHED ===';

-- Распределение по типам операций
SELECT 
    WORK_TYPE AS тип_операции,
    COUNT(*) AS количество,
    SUM(CASE WHEN date >= @cutoff_date THEN 1 ELSE 0 END) AS за_3_дня
FROM dwh.operations_enriched WITH (NOLOCK)
GROUP BY WORK_TYPE
ORDER BY количество DESC;

-- Распределение по датам (последние 7 дней)
SELECT 
    date AS дата,
    COUNT(*) AS количество_операций,
    COUNT(DISTINCT user_name) AS уникальных_сотрудников,
    SUM(duration_sec) / 3600.0 AS всего_часов
FROM dwh.operations_enriched WITH (NOLOCK)
WHERE date >= DATEADD(DAY, -7, @end_date)
GROUP BY date
ORDER BY date;

PRINT '';

-- ============================================================================
-- 8. ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ
-- ============================================================================
PRINT '=== 8. ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ ===';

-- Проверка: есть ли операции без сотрудника
SELECT 
    'Операции без сотрудника' AS проверка,
    COUNT(*) AS проблемных_записей
FROM dwh.operations_enriched o WITH (NOLOCK)
WHERE NOT EXISTS (
    SELECT 1 FROM dm.dim_employee e 
    WHERE o.user_name COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT
);

-- Проверка: есть ли операции с будущими датами
SELECT 
    'Операции с будущими датами' AS проверка,
    COUNT(*) AS проблемных_записей
FROM dwh.operations_enriched WITH (NOLOCK)
WHERE date > CAST(GETDATE() AS DATE);

-- Проверка: есть ли fact_operation без связи с dim_employee
SELECT 
    'fact_operation без сотрудника' AS проверка,
    COUNT(*) AS проблемных_записей
FROM dwh.fact_operation f WITH (NOLOCK)
WHERE NOT EXISTS (
    SELECT 1 FROM dm.dim_employee e WHERE f.employee_id = e.employee_id
);

-- Проверка: есть ли fact_penalty без связи с dim_employee
SELECT 
    'fact_penalty без сотрудника' AS проверка,
    COUNT(*) AS проблемных_записей
FROM dwh.fact_penalty f WITH (NOLOCK)
WHERE NOT EXISTS (
    SELECT 1 FROM dm.dim_employee e WHERE f.employee_id = e.employee_id
);

PRINT '';

-- ============================================================================
-- 9. ИТОГОВАЯ СТАТИСТИКА
-- ============================================================================
PRINT '=== 9. ИТОГОВАЯ СТАТИСТИКА ===';

SELECT 
    '📊 operations_enriched' AS метрика,
    CAST(COUNT(*) AS NVARCHAR) + ' записей' AS значение
FROM dwh.operations_enriched WITH (NOLOCK)
WHERE date >= @cutoff_date
UNION ALL
SELECT 
    '📊 fact_operation',
    CAST(COUNT(*) AS NVARCHAR) + ' записей'
FROM dwh.fact_operation WITH (NOLOCK)
WHERE date_key >= @cutoff_date
UNION ALL
SELECT 
    '📊 fact_penalty',
    CAST(COUNT(*) AS NVARCHAR) + ' записей'
FROM dwh.fact_penalty WITH (NOLOCK)
WHERE date_key >= @cutoff_date;
-- fact_location_snapshot обновляется отдельно
-- SELECT
--     '📊 fact_location_snapshot',
--     CAST(COUNT(*) AS NVARCHAR) + ' локаций'
-- FROM dwh.fact_location_snapshot WITH (NOLOCK);

PRINT '';
PRINT '=== ДИАГНОСТИКА ЗАВЕРШЕНА ===';
