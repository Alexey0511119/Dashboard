-- ============================================================================
-- АНАЛИЗ СТРУКТУРЫ ТАБЛИЦ И ИНДЕКСОВ
-- ============================================================================

PRINT '=== ИНДЕКСЫ НА raw_.TRANSACTION_HISTORY ===';
EXEC sp_helpindex 'raw_.TRANSACTION_HISTORY';

PRINT '';
PRINT '=== КОЛИЧЕСТВО ЗАПИСЕЙ ЗА СЕГОДНЯ ===';
SELECT 
    CAST(DATE_TIME_STAMP AS DATE) AS date,
    COUNT(*) AS records_count
FROM raw_.TRANSACTION_HISTORY
WHERE DATE_TIME_STAMP >= CAST(GETDATE() AS DATE)
GROUP BY CAST(DATE_TIME_STAMP AS DATE);

PRINT '';
PRINT '=== ВСЕГО ЗАПИСЕЙ В ТАБЛИЦЕ ===';
SELECT COUNT(*) AS total_records FROM raw_.TRANSACTION_HISTORY;

PRINT '';
PRINT '=== СТРУКТУРА USER_CADR_EDIT ===';
EXEC sp_help 'USER_CADR_EDIT';

PRINT '';
PRINT '=== ИНДЕКСЫ НА USER_CADR_EDIT ===';
EXEC sp_helpindex 'USER_CADR_EDIT';

PRINT '';
PRINT '=== УНИКАЛЬНЫХ USER_NAME ЗА СЕГОДНЯ ===';
SELECT COUNT(DISTINCT USER_NAME) AS unique_users
FROM raw_.TRANSACTION_HISTORY
WHERE DATE_TIME_STAMP >= CAST(GETDATE() AS DATE);
