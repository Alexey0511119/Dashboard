-- ============================================================================
-- ИТОГОВЫЙ СКРИПТ: Подключение новой таблицы времени работы и простоя
-- ============================================================================
-- Этот скрипт создает таблицу dm.employee_work_idle_summary и заполняет её
-- данными из TRANSACTION_HISTORY для расчёта времени работы и простоя сотрудников
-- ============================================================================

USE olap2_fixed;

-- ====== ЧАСТЬ 1: Создание таблицы ======
PRINT '=== ЧАСТЬ 1: Создание таблицы dm.employee_work_idle_summary ===';

IF OBJECT_ID('dm.employee_work_idle_summary', 'U') IS NOT NULL
    DROP TABLE dm.employee_work_idle_summary;

CREATE TABLE dm.employee_work_idle_summary (
    user_name           NVARCHAR(100) COLLATE DATABASE_DEFAULT NOT NULL,
    fio                 NVARCHAR(200) COLLATE DATABASE_DEFAULT NOT NULL,
    date_key            DATE NOT NULL,
    first_op_time       DATETIME2(0) NOT NULL,
    last_op_time        DATETIME2(0) NOT NULL,
    total_period_min    INT NOT NULL,
    total_idle_min      INT NOT NULL DEFAULT 0,
    total_work_min      INT NOT NULL,
    work_percentage     DECIMAL(5,2) NOT NULL,
    idle_percentage     DECIMAL(5,2) NOT NULL,
    idle_10_20          INT NOT NULL DEFAULT 0,
    idle_20_30          INT NOT NULL DEFAULT 0,
    idle_30_60          INT NOT NULL DEFAULT 0,
    idle_60plus         INT NOT NULL DEFAULT 0,
    CONSTRAINT PK_employee_work_idle_summary PRIMARY KEY (user_name, date_key)
);

PRINT 'Таблица создана.';

-- ====== ЧАСТЬ 2: Заполнение таблицы ======
PRINT '=== ЧАСТЬ 2: Заполнение таблицы данными ===';

WITH unique_ops AS (
    SELECT DISTINCT
        LOWER(th.USER_STAMP) COLLATE DATABASE_DEFAULT AS user_name,
        CAST(th.DATE_TIME_STAMP AS DATE) AS date_key,
        th.DATE_TIME_STAMP AS op_time
    FROM raw_.TRANSACTION_HISTORY th
    WHERE 
        th.DATE_TIME_STAMP IS NOT NULL
        AND th.USER_STAMP IS NOT NULL
),
numbered_ops AS (
    SELECT
        user_name,
        date_key,
        op_time,
        ROW_NUMBER() OVER (
            PARTITION BY user_name, date_key
            ORDER BY op_time
        ) AS rn
    FROM unique_ops
),
daily_bounds AS (
    SELECT
        user_name,
        date_key,
        MIN(op_time) AS first_op_time,
        MAX(op_time) AS last_op_time
    FROM unique_ops
    GROUP BY user_name, date_key
),
idle_gaps AS (
    SELECT
        curr.user_name,
        curr.date_key,
        DATEDIFF(MINUTE, curr.op_time, next_op.op_time) AS gap_minutes
    FROM numbered_ops curr
    JOIN numbered_ops next_op
        ON curr.user_name = next_op.user_name
        AND curr.date_key = next_op.date_key
        AND curr.rn + 1 = next_op.rn
    WHERE DATEDIFF(MINUTE, curr.op_time, next_op.op_time) >= 10
),
idle_summary AS (
    SELECT
        user_name,
        date_key,
        SUM(gap_minutes) AS total_idle_min,
        SUM(CASE WHEN gap_minutes >= 10 AND gap_minutes < 20 THEN 1 ELSE 0 END) AS idle_10_20,
        SUM(CASE WHEN gap_minutes >= 20 AND gap_minutes < 30 THEN 1 ELSE 0 END) AS idle_20_30,
        SUM(CASE WHEN gap_minutes >= 30 AND gap_minutes < 60 THEN 1 ELSE 0 END) AS idle_30_60,
        SUM(CASE WHEN gap_minutes >= 60 THEN 1 ELSE 0 END) AS idle_60plus
    FROM idle_gaps
    GROUP BY user_name, date_key
),
employee_data AS (
    SELECT
        db.user_name,
        db.date_key,
        db.first_op_time,
        db.last_op_time,
        DATEDIFF(MINUTE, db.first_op_time, db.last_op_time) AS total_period_min,
        COALESCE(idle.total_idle_min, 0) AS total_idle_min,
        COALESCE(idle.idle_10_20, 0) AS idle_10_20,
        COALESCE(idle.idle_20_30, 0) AS idle_20_30,
        COALESCE(idle.idle_30_60, 0) AS idle_30_60,
        COALESCE(idle.idle_60plus, 0) AS idle_60plus,
        uce.fio
    FROM daily_bounds db
    LEFT JOIN idle_summary idle
        ON db.user_name = idle.user_name
        AND db.date_key = idle.date_key
    LEFT JOIN (
        SELECT DISTINCT
            LOWER(user_name) COLLATE DATABASE_DEFAULT AS user_name,
            FIRST_VALUE(fio) OVER (PARTITION BY LOWER(user_name) ORDER BY deleted, user_name) AS fio
        FROM raw_.USER_CADR_EDIT
        WHERE user_name IS NOT NULL
    ) uce
        ON db.user_name COLLATE DATABASE_DEFAULT = uce.user_name COLLATE DATABASE_DEFAULT
)
INSERT INTO dm.employee_work_idle_summary (
    user_name,
    fio,
    date_key,
    first_op_time,
    last_op_time,
    total_period_min,
    total_idle_min,
    total_work_min,
    work_percentage,
    idle_percentage,
    idle_10_20,
    idle_20_30,
    idle_30_60,
    idle_60plus
)
SELECT DISTINCT
    user_name,
    ISNULL(fio, user_name) AS fio,
    date_key,
    CAST(first_op_time AS DATETIME2(0)) AS first_op_time,
    CAST(last_op_time AS DATETIME2(0)) AS last_op_time,
    total_period_min,
    total_idle_min,
    total_period_min - total_idle_min AS total_work_min,
    CASE 
        WHEN total_period_min > 0 
        THEN CAST(ROUND((total_period_min - total_idle_min) * 100.0 / total_period_min, 2) AS DECIMAL(5,2))
        ELSE 0.00
    END AS work_percentage,
    CASE 
        WHEN total_period_min > 0 
        THEN CAST(ROUND(total_idle_min * 100.0 / total_period_min, 2) AS DECIMAL(5,2))
        ELSE 0.00
    END AS idle_percentage,
    idle_10_20,
    idle_20_30,
    idle_30_60,
    idle_60plus
FROM employee_data;

PRINT 'Таблица заполнена.';

-- ====== ЧАСТЬ 3: Проверка ======
PRINT '=== ЧАСТЬ 3: Проверка данных ===';

SELECT 
    'СТАТИСТИКА' AS раздел,
    COUNT(*) AS всего_записей,
    COUNT(DISTINCT user_name) AS сотрудников,
    COUNT(DISTINCT date_key) AS дней,
    MIN(date_key) AS мин_дата,
    MAX(date_key) AS макс_дата
FROM dm.employee_work_idle_summary;

PRINT 'Готово!';
