-- ============================================================================
-- ПРОВЕРКА VIEW dm.v_employees_shift_daily
-- ============================================================================

-- 1. Проверяем, есть ли данные во view
PRINT '=== ВСЕ ДАННЫЕ ИЗ VIEW ===';
SELECT TOP 20 * FROM dm.v_employees_shift_daily
ORDER BY fio;

-- 2. Проверяем количество записей по сменам
PRINT '';
PRINT '=== КОЛИЧЕСТВО СОТРУДНИКОВ ПО СМЕНАМ ===';
SELECT 
    smena,
    COUNT(*) AS total_employees,
    SUM(CASE WHEN status_on_shift = 'Не вышел' THEN 1 ELSE 0 END) AS not_came,
    SUM(CASE WHEN status_on_shift = 'На смене' THEN 1 ELSE 0 END) AS on_shift
FROM dm.v_employees_shift_daily
GROUP BY smena;

-- 3. Проверяем, какая смена должна работать сегодня (4-дневный цикл от 11.12.2025)
PRINT '';
PRINT '=== ОПРЕДЕЛЕНИЕ ТЕКУЩЕЙ СМЕНЫ ===';
DECLARE @today DATE = CAST(GETDATE() AS DATE);
DECLARE @base_date DATE = '2025-12-11';
DECLARE @days_diff INT = DATEDIFF(DAY, @base_date, @today);
DECLARE @cycle_position INT = @days_diff % 4;
DECLARE @today_shift VARCHAR(10);

SET @today_shift = CASE 
    WHEN @cycle_position IN (0, 1) THEN '1'
    ELSE '2'
END;

SELECT 
    @today AS today_date,
    @base_date AS base_date,
    @days_diff AS days_difference,
    @cycle_position AS cycle_position,
    @today_shift AS todays_shift;

-- 4. Проверяем данные для текущей смены
PRINT '';
PRINT '=== ДАННЫЕ ДЛЯ ТЕКУЩЕЙ СМЕНЫ (' + @today_shift + ') ===';
SELECT 
    fio,
    position,
    brigada,
    smena,
    first_operation_time,
    total_operations,
    status_on_shift
FROM dm.v_employees_shift_daily
WHERE smena = @today_shift
ORDER BY fio;

-- 5. Проверяем исходные данные в USER_CADR_EDIT
PRINT '';
PRINT '=== СОТРУДНИКИ В USER_CADR_EDIT (для проверки) ===';
SELECT TOP 20
    user_name,
    fio,
    brigada,
    position,
    smena,
    deleted
FROM USER_CADR_EDIT
WHERE 
    (deleted = 0 OR deleted IS NULL)
    AND brigada IS NOT NULL AND brigada != ''
    AND brigada != 'Управление'
    AND position IS NOT NULL AND position != ''
ORDER BY fio;
