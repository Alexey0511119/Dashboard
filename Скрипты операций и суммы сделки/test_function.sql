-- ============================================================================
-- ПРОВЕРКА: Тестирование функции get_employee_idle_intervals
-- ============================================================================

USE olap2_fixed;

-- ====== 1. Проверяем структуру таблицы ======
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'dm'
  AND TABLE_NAME = 'employee_work_idle_summary'
ORDER BY ORDINAL_POSITION;

-- ====== 2. Проверяем данные за период ======
-- Период за последние 30 дней
DECLARE @start_date DATE = DATEADD(DAY, -30, GETDATE());
DECLARE @end_date DATE = GETDATE();

SELECT 
    'Данные за период' AS проверка,
    @start_date AS start_date,
    @end_date AS end_date,
    COUNT(*) AS количество_записей
FROM dm.employee_work_idle_summary
WHERE date_key BETWEEN @start_date AND @end_date;

-- ====== 3. Проверяем конкретный запрос функции ======
-- Замените имя на реальное из дашборда
DECLARE @employee_name NVARCHAR(100) = N'%'; -- Все сотрудники

SELECT TOP 20
    user_name,
    fio,
    date_key,
    idle_10_20,
    idle_20_30,
    idle_30_60,
    idle_60plus,
    total_idle_min,
    total_work_min,
    work_percentage,
    idle_percentage
FROM dm.employee_work_idle_summary
WHERE (LOWER(user_name) LIKE LOWER(@employee_name) OR LOWER(fio) LIKE LOWER(@employee_name))
  AND date_key BETWEEN @start_date AND @end_date
ORDER BY date_key DESC;

-- ====== 4. Агрегация по сотруднику (как в функции) ======
SELECT 
    user_name,
    fio,
    COUNT(*) AS days_count,
    SUM(idle_10_20) AS total_idle_10_20,
    SUM(idle_20_30) AS total_idle_20_30,
    SUM(idle_30_60) AS total_idle_30_60,
    SUM(idle_60plus) AS total_idle_60plus,
    SUM(total_idle_min) AS total_idle_minutes,
    SUM(total_work_min) AS total_work_minutes,
    AVG(work_percentage) AS avg_work_percentage,
    AVG(idle_percentage) AS avg_idle_percentage
FROM dm.employee_work_idle_summary
WHERE date_key BETWEEN @start_date AND @end_date
GROUP BY user_name, fio
ORDER BY total_work_minutes DESC;

-- ====== 5. Сверка с TRANSACTION_HISTORY ======
-- Проверяем, есть ли данные в источнике
SELECT TOP 20
    LOWER(th.USER_STAMP) AS user_name,
    CAST(th.DATE_TIME_STAMP AS DATE) AS date_key,
    COUNT(*) AS operations_count,
    MIN(th.DATE_TIME_STAMP) AS first_op,
    MAX(th.DATE_TIME_STAMP) AS last_op
FROM raw_.TRANSACTION_HISTORY th
WHERE th.DATE_TIME_STAMP IS NOT NULL
  AND th.USER_STAMP IS NOT NULL
GROUP BY LOWER(th.USER_STAMP), CAST(th.DATE_TIME_STAMP AS DATE)
ORDER BY date_key DESC;
