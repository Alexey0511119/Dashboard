-- ============================================================================
-- ЧАСТЬ 3: СОЗДАНИЕ VIEW dm.v_employees_shift_daily (ВЕРСИЯ 3)
-- Схема: dm (olap2_fixed)
-- Источник: raw_.TRANSACTION_HISTORY + USER_CADR_EDIT
-- 
-- Исправления:
-- - Поле deleted имеет тип BIT (0/1), а не VARCHAR
-- - Исключает бригаду "Управление"
-- ============================================================================

IF OBJECT_ID('dm.v_employees_shift_daily', 'V') IS NOT NULL
    DROP VIEW dm.v_employees_shift_daily;

CREATE VIEW dm.v_employees_shift_daily AS
WITH today_ops AS (
    -- Агрегация операций только за сегодня
    SELECT 
        USER_NAME,
        MIN(DATE_TIME_STAMP) AS first_operation_time,
        COUNT(*) AS total_operations
    FROM raw_.TRANSACTION_HISTORY
    WHERE DATE_TIME_STAMP >= CAST(GETDATE() AS DATE)
      AND DATE_TIME_STAMP < DATEADD(DAY, 1, CAST(GETDATE() AS DATE))
    GROUP BY USER_NAME
)
SELECT
    uce.user_name,
    uce.fio,
    uce.brigada,
    uce.position,
    uce.smena,
    CAST(GETDATE() AS DATE) AS date_key,
    t.first_operation_time,
    ISNULL(t.total_operations, 0) AS total_operations,
    -- Статус: 'Не вышел' если не было операций
    CASE 
        WHEN t.first_operation_time IS NULL THEN 'Не вышел'
        WHEN t.total_operations = 0 THEN 'Без операций'
        ELSE 'На смене'
    END AS status_on_shift
FROM USER_CADR_EDIT uce
LEFT JOIN today_ops t ON uce.user_name = t.USER_NAME
WHERE
    -- deleted = 0 (False) означает "не уволен"
    (uce.deleted = 0 OR uce.deleted IS NULL)
    AND uce.brigada IS NOT NULL AND uce.brigada != ''
    AND uce.brigada != 'Управление'
    AND uce.position IS NOT NULL AND uce.position != ''
    AND uce.smena IN ('1', '2');

PRINT '✅ View dm.v_employees_shift_daily создано (версия 3).';
