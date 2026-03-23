-- ============================================================================
-- ЧАСТЬ 2: СОЗДАНИЕ VIEW dm.v_employees_on_shift_raw
-- Схема: dm (olap2_fixed)
-- ============================================================================

USE olap2_fixed;

IF OBJECT_ID('dm.v_employees_on_shift_raw', 'V') IS NOT NULL
    DROP VIEW dm.v_employees_on_shift_raw;

CREATE VIEW dm.v_employees_on_shift_raw AS
SELECT
    id,
    date_key,
    smena,
    user_name,
    fio,
    brigada,
    position,
    first_operation_time,
    CASE
        WHEN first_operation_time IS NOT NULL THEN FORMAT(first_operation_time, 'HH:mm')
        ELSE '--:--'
    END AS first_activity_time,
    total_operations,
    created_at,
    updated_at
FROM dm.employees_on_shift_raw;

PRINT '✅ View dm.v_employees_on_shift_raw создано.';
