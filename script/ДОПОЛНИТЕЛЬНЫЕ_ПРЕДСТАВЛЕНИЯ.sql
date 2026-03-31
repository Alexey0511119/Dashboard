-- ============================================================================
-- ДОПОЛНИТЕЛЬНЫЕ ПРЕДСТАВЛЕНИЯ
-- Восстановление отсутствующих представлений из Скрипт 4
-- ============================================================================
USE olap2_fixed;
GO

-- ============================================================================
-- ПРЕДСТАВЛЕНИЕ 1: v_daily_operations_summary
-- ============================================================================
IF OBJECT_ID('dm.v_daily_operations_summary', 'V') IS NOT NULL
    DROP VIEW dm.v_daily_operations_summary;
GO

CREATE VIEW dm.v_daily_operations_summary AS
SELECT
    d.date_key,
    d.year,
    d.month,
    d.month_name,
    d.day_of_week_name,
    COUNT(f.operation_id) AS total_operations,
    SUM(f.price_per_op) AS total_earnings,
    COUNT(DISTINCT f.employee_id) AS active_employees,
    AVG(f.price_per_op) AS avg_price_per_op
FROM dm.dim_date d
LEFT JOIN dwh.fact_operation f ON d.date_key = f.date_key
WHERE d.date_key >= '2024-01-01'
GROUP BY d.date_key, d.year, d.month, d.month_name, d.day_of_week_name;
GO

PRINT 'v_daily_operations_summary создано.';

-- ============================================================================
-- ПРЕДСТАВЛЕНИЕ 2: v_employee_rating
-- ============================================================================
IF OBJECT_ID('dm.v_employee_rating', 'V') IS NOT NULL
    DROP VIEW dm.v_employee_rating;
GO

CREATE VIEW dm.v_employee_rating AS
WITH employee_stats AS (
    SELECT
        e.employee_id,
        e.fio,
        e.smena,
        e.brigada,
        COUNT(f.operation_id) AS total_operations,
        SUM(f.price_per_op) AS total_earnings,
        AVG(f.price_per_op) AS avg_price_per_op,
        MIN(f.date_key) AS first_work_date,
        MAX(f.date_key) AS last_work_date,
        DATEDIFF(DAY, MIN(f.date_key), MAX(f.date_key)) + 1 AS work_days
    FROM dm.dim_employee e
    JOIN dwh.fact_operation f ON e.employee_id = f.employee_id
    WHERE e.is_active = 1
    GROUP BY e.employee_id, e.fio, e.smena, e.brigada
)
SELECT
    employee_id,
    fio,
    smena,
    brigada,
    total_operations,
    total_earnings,
    avg_price_per_op,
    first_work_date,
    last_work_date,
    work_days,
    CAST(total_earnings AS FLOAT) / NULLIF(work_days, 0) AS avg_daily_earnings,
    ROW_NUMBER() OVER (ORDER BY total_earnings DESC) AS rating_by_earnings,
    ROW_NUMBER() OVER (ORDER BY total_operations DESC) AS rating_by_operations,
    ROW_NUMBER() OVER (ORDER BY avg_price_per_op DESC) AS rating_by_avg_price
FROM employee_stats
WHERE total_operations > 0;
GO

PRINT 'v_employee_rating создано.';

-- ============================================================================
-- ПРЕДСТАВЛЕНИЕ 3: v_shift_statistics
-- ============================================================================
IF OBJECT_ID('dm.v_shift_statistics', 'V') IS NOT NULL
    DROP VIEW dm.v_shift_statistics;
GO

CREATE VIEW dm.v_shift_statistics AS
SELECT
    d.date_key,
    e.smena,
    COUNT(DISTINCT e.employee_id) AS active_employees,
    COUNT(f.operation_id) AS total_operations,
    SUM(f.price_per_op) AS total_earnings,
    AVG(f.price_per_op) AS avg_price_per_op,
    MIN(f.start_time) AS shift_start,
    MAX(f.end_time) AS shift_end,
    DATEDIFF(MINUTE, MIN(f.start_time), MAX(f.end_time)) AS shift_duration_minutes
FROM dm.dim_date d
JOIN dwh.fact_operation f ON d.date_key = f.date_key
JOIN dm.dim_employee e ON f.employee_id = e.employee_id
WHERE e.is_active = 1
GROUP BY d.date_key, e.smena;
GO

PRINT 'v_shift_statistics создано.';

PRINT 'Все дополнительные представления созданы.';
