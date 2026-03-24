-- ============================================================================
-- ДИАГНОСТИКА: Проверка данных в новой таблице
-- ============================================================================

USE olap2_fixed;

-- ====== 1. Есть ли данные в таблице? ======
SELECT 
    'ВСЕГО ЗАПИСЕЙ' AS проверка,
    COUNT(*) AS количество
FROM dm.employee_work_idle_summary;

-- ====== 2. Данные за последние 7 дней ======
SELECT TOP 50
    user_name,
    fio,
    date_key,
    first_op_time,
    last_op_time,
    total_period_min,
    total_work_min,
    total_idle_min,
    work_percentage,
    idle_percentage,
    idle_10_20,
    idle_20_30,
    idle_30_60,
    idle_60plus
FROM dm.employee_work_idle_summary
ORDER BY date_key DESC;

-- ====== 3. Проверка для конкретного сотрудника (из дашборда) ======
-- Замените имя на то, которое отображается в дашборде
SELECT 
    'ПРОВЕРКА ПО СОТРУДНИКУ' AS проверка,
    user_name,
    fio,
    date_key,
    total_work_min,
    total_idle_min,
    work_percentage,
    idle_percentage,
    idle_10_20,
    idle_20_30,
    idle_30_60,
    idle_60plus
FROM dm.employee_work_idle_summary
WHERE date_key >= DATEADD(DAY, -7, GETDATE())
ORDER BY date_key DESC;

-- ====== 4. Агрегированные данные по всем сотрудникам ======
SELECT 
    COUNT(DISTINCT user_name) AS сотрудников,
    COUNT(DISTINCT date_key) AS дней,
    SUM(total_work_min) AS всего_работал_мин,
    SUM(total_idle_min) AS всего_простаивал_мин,
    AVG(work_percentage) AS средний_%_работы,
    SUM(idle_10_20) AS простоев_10_20,
    SUM(idle_20_30) AS простоев_20_30,
    SUM(idle_30_60) AS простоев_30_60,
    SUM(idle_60plus) AS простоев_60plus
FROM dm.employee_work_idle_summary;
