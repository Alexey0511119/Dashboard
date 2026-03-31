-- ============================================================================
-- ЧАСТЬ 3: СОЗДАНИЕ VIEW dm.v_employees_shift_daily (ОПТИМИЗИРОВАННАЯ ВЕРСИЯ)
-- Схема: dm (olap2_fixed)
-- Источник: raw_.TRANSACTION_HISTORY + USER_CADR_EDIT
-- 
-- Оптимизация:
-- 1. Фильтрация по текущему дню в подзапросе
-- 2. Предварительная фильтрация USER_CADR_EDIT
-- 3. Создание индекса на TRANSACTION_HISTORY
-- ============================================================================

-- Сначала создадим индекс на TRANSACTION_HISTORY для ускорения
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes 
    WHERE name = 'IX_TRANSACTION_HISTORY_date_user' 
    AND object_id = OBJECT_ID('raw_.TRANSACTION_HISTORY')
)
CREATE NONCLUSTERED INDEX IX_TRANSACTION_HISTORY_date_user
ON raw_.TRANSACTION_HISTORY(DATE_TIME_STAMP, USER_NAME);

PRINT '✅ Индекс создан.';

-- Теперь создаем view
IF OBJECT_ID('dm.v_employees_shift_daily', 'V') IS NOT NULL
    DROP VIEW dm.v_employees_shift_daily;

CREATE VIEW dm.v_employees_shift_daily AS
WITH today_ops AS (
    -- Быстрая выборка только за сегодня
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
    t.USER_NAME AS user_name,
    uce.fio,
    uce.brigada,
    uce.position,
    uce.smena,
    CAST(GETDATE() AS DATE) AS date_key,
    t.first_operation_time,
    t.total_operations
FROM today_ops t
INNER JOIN (
    -- Предварительно отфильтрованные сотрудники
    SELECT user_name, fio, brigada, position, smena
    FROM USER_CADR_EDIT
    WHERE deleted = 'False'
      AND brigada IS NOT NULL AND brigada != ''
      AND position IS NOT NULL AND position != ''
) uce ON t.USER_NAME = uce.user_name;

PRINT '✅ View dm.v_employees_shift_daily создано.';
