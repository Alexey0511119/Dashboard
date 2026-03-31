-- ============================================================================
-- ПРОВЕРКА: Какое имя используется в данных?
-- ============================================================================

USE olap2_fixed;

-- ====== 1. Проверяем данные в v_performance_detailed ======
SELECT TOP 10
    Сотрудник,
    date_key,
    Общее_кол_операций
FROM dm.v_performance_detailed
ORDER BY date_key DESC;

-- ====== 2. Проверяем данные в employee_work_idle_summary ======
SELECT TOP 10
    user_name,
    fio,
    date_key,
    total_work_min,
    total_idle_min
FROM dm.employee_work_idle_summary
ORDER BY date_key DESC;

-- ====== 3. Сравниваем имена ======
SELECT 
    'v_performance_detailed' AS источник,
    Сотрудник AS имя,
    COUNT(*) AS количество
FROM dm.v_performance_detailed
GROUP BY Сотрудник
ORDER BY COUNT(*) DESC;

SELECT 
    'employee_work_idle_summary' AS источник,
    fio AS имя,
    COUNT(*) AS количество
FROM dm.employee_work_idle_summary
GROUP BY fio
ORDER BY COUNT(*) DESC;

-- ====== 4. Проверяем, есть ли совпадения ======
SELECT TOP 20
    pd.Сотрудник AS fio_v_performance,
    eis.fio AS fio_in_idle,
    eis.user_name AS user_name_in_idle,
    eis.date_key,
    eis.total_work_min
FROM dm.v_performance_detailed pd
LEFT JOIN dm.employee_work_idle_summary eis
    ON pd.Сотрудник = eis.fio
    AND pd.date_key = eis.date_key
WHERE pd.date_key >= DATEADD(DAY, -7, GETDATE())
ORDER BY pd.date_key DESC;
