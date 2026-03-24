-- ============================================================================
-- ПРОВЕРКА: Тестирование новой таблицы dm.employee_work_idle_summary
-- ============================================================================

USE olap2_fixed;

-- ====== 1. Общая статистика по таблице ======
SELECT 
    'ОБЩАЯ СТАТИСТИКА' AS раздел,
    COUNT(*) AS всего_записей,
    COUNT(DISTINCT user_name) AS сотрудников,
    COUNT(DISTINCT date_key) AS дней,
    MIN(date_key) AS мин_дата,
    MAX(date_key) AS макс_дата
FROM dm.employee_work_idle_summary;

-- ====== 2. Проверка для конкретного пользователя (например, a.belash) ======
SELECT 
    'ПРОВЕРКА A.BELASH' AS раздел,
    COUNT(*) AS дней_с_данными,
    SUM(total_work_min) AS всего_работал_мин,
    SUM(total_idle_min) AS всего_простаивал_мин,
    AVG(work_percentage) AS средний_%_работы,
    AVG(idle_percentage) AS средний_%_простоя,
    SUM(idle_10_20) AS простоев_10_20,
    SUM(idle_20_30) AS простоев_20_30,
    SUM(idle_30_60) AS простоев_30_60,
    SUM(idle_60plus) AS простоев_60plus
FROM dm.employee_work_idle_summary
WHERE LOWER(user_name) = 'a.belash';

-- ====== 3. Детальные данные за последний день ======
SELECT TOP 10
    user_name AS [Логин],
    fio AS [ФИО],
    date_key AS [Дата],
    first_op_time AS [Первая операция],
    last_op_time AS [Последняя операция],
    total_period_min AS [Период (мин)],
    total_work_min AS [Работа (мин)],
    total_idle_min AS [Простой (мин)],
    work_percentage AS [Работа %],
    idle_percentage AS [Простой %],
    idle_10_20 AS [10-20],
    idle_20_30 AS [20-30],
    idle_30_60 AS [30-60],
    idle_60plus AS [60+]
FROM dm.employee_work_idle_summary
ORDER BY date_key DESC, user_name;

-- ====== 4. Сверка с исходными данными TRANSACTION_HISTORY ======
SELECT 
    'СВЕРКА С TRANSACTION_HISTORY' AS раздел,
    LOWER(th.USER_STAMP) AS user_name,
    CAST(th.DATE_TIME_STAMP AS DATE) AS date_key,
    COUNT(*) AS операций_в_транзакциях,
    MIN(th.DATE_TIME_STAMP) AS первая_операция,
    MAX(th.DATE_TIME_STAMP) AS последняя_операция,
    DATEDIFF(MINUTE, MIN(th.DATE_TIME_STAMP), MAX(th.DATE_TIME_STAMP)) AS период_мин
FROM raw_.TRANSACTION_HISTORY th
WHERE 
    th.DATE_TIME_STAMP IS NOT NULL
    AND th.USER_STAMP IS NOT NULL
    AND CAST(th.DATE_TIME_STAMP AS DATE) = (SELECT MAX(date_key) FROM dm.employee_work_idle_summary)
GROUP BY LOWER(th.USER_STAMP), CAST(th.DATE_TIME_STAMP AS DATE)
ORDER BY user_name, date_key;

-- ====== 5. Топ-10 сотрудников по проценту работы ======
SELECT TOP 10
    user_name AS [Логин],
    fio AS [ФИО],
    COUNT(*) AS дней,
    AVG(work_percentage) AS средний_%_работы,
    AVG(idle_percentage) AS средний_%_простоя,
    SUM(total_work_min) AS всего_работал_мин,
    SUM(total_idle_min) AS всего_простаивал_мин
FROM dm.employee_work_idle_summary
GROUP BY user_name, fio
ORDER BY AVG(work_percentage) DESC;

-- ====== 6. Проверка данных за сегодня ======
SELECT 
    'ЗА СЕГОДНЯ' AS раздел,
    COUNT(*) AS записей,
    COUNT(DISTINCT user_name) AS сотрудников
FROM dm.employee_work_idle_summary
WHERE date_key = CAST(GETDATE() AS DATE);
