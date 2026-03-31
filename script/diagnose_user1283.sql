-- ============================================================================
-- ДИАГНОСТИКА: Поиск USER1283 в TRANSACTION_HISTORY
-- Проверяем регистр, пробелы и точное написание
-- ============================================================================

USE olap2_fixed;

-- ====== 1. Ищем все варианты написания USER1283 ======
SELECT 
    USER_STAMP AS [Точное написание в базе],
    COUNT(*) AS [Количество записей],
    MIN(DATE_TIME_STAMP) AS [Первая запись],
    MAX(DATE_TIME_STAMP) AS [Последняя запись]
FROM raw_.TRANSACTION_HISTORY
WHERE 
    TRANSACTION_TYPE = '20'
    AND (
        USER_STAMP = 'USER1283'
        OR USER_STAMP = 'user1283'
        OR USER_STAMP = 'User1283'
        OR LOWER(USER_STAMP) = 'user1283'
        OR USER_STAMP LIKE '%1283%'
    )
    AND DATE_TIME_STAMP IS NOT NULL
GROUP BY USER_STAMP
ORDER BY USER_STAMP;

-- ====== 2. Проверяем, есть ли вообще такие пользователи в TRANSACTION_HISTORY ======
SELECT TOP 20
    USER_STAMP,
    COUNT(*) AS cnt
FROM raw_.TRANSACTION_HISTORY
WHERE TRANSACTION_TYPE = '20'
GROUP BY USER_STAMP
ORDER BY cnt DESC;

-- ====== 3. Проверяем USER_CADR_EDIT ======
SELECT 
    user_name AS [Точное написание в USER_CADR_EDIT],
    fio,
    smena,
    brigada,
    position,
    deleted
FROM raw_.USER_CADR_EDIT
WHERE 
    LOWER(user_name) = 'user1283'
    OR user_name = 'USER1283'
    OR user_name = 'user1283'
ORDER BY deleted;

-- ====== 4. Проверяем COLLATION базы ======
SELECT 
    DATABASEPROPERTYEX('olap2_fixed', 'Collation') AS DatabaseCollation;

-- ====== 5. Проверяем COLLATION полей ======
SELECT 
    'TRANSACTION_HISTORY.USER_STAMP' AS поле,
    COLLATIONPROPERTY(c.collation_name, 'CodePage') AS CodePage,
    c.collation_name
FROM sys.columns c
JOIN sys.tables t ON c.object_id = t.object_id
WHERE t.name = 'TRANSACTION_HISTORY' AND c.name = 'USER_STAMP'
UNION ALL
SELECT 
    'USER_CADR_EDIT.user_name' AS поле,
    COLLATIONPROPERTY(c.collation_name, 'CodePage') AS CodePage,
    c.collation_name
FROM sys.columns c
JOIN sys.tables t ON c.object_id = t.object_id
WHERE t.name = 'USER_CADR_EDIT' AND c.name = 'user_name';

-- ====== 6. Ищем с пробелами и невидимыми символами ======
SELECT 
    USER_STAMP AS [Оригинал],
    LEN(USER_STAMP) AS [Длина],
    DATALENGTH(USER_STAMP) AS [Байт],
    CAST(USER_STAMP AS VARBINARY(100)) AS [Hex],
    COUNT(*) AS [Кол-во]
FROM raw_.TRANSACTION_HISTORY
WHERE 
    TRANSACTION_TYPE = '20'
    AND USER_STAMP LIKE '%1283%'
GROUP BY USER_STAMP
ORDER BY USER_STAMP;

-- ====== 7. Проверяем, есть ли в итоговой таблице ======
SELECT *
FROM dm.employee_work_idle_summary
WHERE 
    LOWER(user_name) LIKE '%1283%'
    OR user_name LIKE '%1283%';
