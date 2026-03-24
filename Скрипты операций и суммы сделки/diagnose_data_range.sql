-- ============================================================================
-- ДИАГНОСТИКА: Проверка данных в TRANSACTION_HISTORY и employee_work_idle_summary
-- ============================================================================

USE olap2_fixed;

-- ====== 1. Проверяем диапазон дат в TRANSACTION_HISTORY ======
SELECT 
    'TRANSACTION_HISTORY' AS source_table,
    COUNT(*) AS total_records,
    MIN(CAST(DATE_TIME_STAMP AS DATE)) AS min_date,
    MAX(CAST(DATE_TIME_STAMP AS DATE)) AS max_date,
    DATEDIFF(DAY, MIN(CAST(DATE_TIME_STAMP AS DATE)), MAX(CAST(DATE_TIME_STAMP AS DATE))) AS days_range
FROM raw_.TRANSACTION_HISTORY
WHERE 
    TRANSACTION_TYPE = '20'
    AND DATE_TIME_STAMP IS NOT NULL
    AND USER_STAMP IS NOT NULL;

-- ====== 2. Проверяем диапазон дат в employee_work_idle_summary ======
SELECT 
    'employee_work_idle_summary' AS source_table,
    COUNT(*) AS total_records,
    MIN(date_key) AS min_date,
    MAX(date_key) AS max_date,
    DATEDIFF(DAY, MIN(date_key), MAX(date_key)) AS days_range
FROM dm.employee_work_idle_summary;

-- ====== 3. Сколько дней доступно для a.belash в TRANSACTION_HISTORY ======
SELECT 
    COUNT(DISTINCT CAST(DATE_TIME_STAMP AS DATE)) AS days_with_operations,
    MIN(CAST(DATE_TIME_STAMP AS DATE)) AS first_date,
    MAX(CAST(DATE_TIME_STAMP AS DATE)) AS last_date
FROM raw_.TRANSACTION_HISTORY
WHERE 
    TRANSACTION_TYPE = '20'
    AND USER_STAMP = 'a.belash'
    AND DATE_TIME_STAMP IS NOT NULL;

-- ====== 4. Сколько дней есть для a.belash в employee_work_idle_summary ======
SELECT 
    COUNT(*) AS days_in_summary,
    MIN(date_key) AS first_date,
    MAX(date_key) AS last_date
FROM dm.employee_work_idle_summary
WHERE user_name = 'a.belash';

-- ====== 5. Какие даты есть в employee_work_idle_summary (все) ======
SELECT DISTINCT date_key
FROM dm.employee_work_idle_summary
ORDER BY date_key;

-- ====== 6. Проверяем, есть ли данные за конкретную дату (например, 01.03.2026) ======
DECLARE @check_date DATE = '2026-03-01';

SELECT 
    'Запрошенная дата: ' + CONVERT(NVARCHAR(50), @check_date, 104) AS info;

SELECT 
    COUNT(*) AS records_count_for_date,
    MIN(DATE_TIME_STAMP) AS first_op,
    MAX(DATE_TIME_STAMP) AS last_op
FROM raw_.TRANSACTION_HISTORY
WHERE 
    TRANSACTION_TYPE = '20'
    AND USER_STAMP = 'a.belash'
    AND CAST(DATE_TIME_STAMP AS DATE) = @check_date;

-- ====== 7. Проверяем, есть ли расчёт для запрошенной даты в итоговой таблице ======
SELECT *
FROM dm.employee_work_idle_summary
WHERE user_name = 'a.belash' 
  AND date_key = @check_date;
