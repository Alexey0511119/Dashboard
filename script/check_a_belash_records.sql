-- ============================================================================
-- ПРОВЕРКА: Все записи a.belash в TRANSACTION_HISTORY за период с 01.03.2026
-- Вывод ВСЕХ строк со ВСЕЙ информацией
-- ============================================================================

USE olap2_fixed;

-- ====== Все строки со всей информацией ======
SELECT 
    th.*,
    uce.fio,
    uce.smena,
    uce.brigada,
    uce.position
FROM raw_.TRANSACTION_HISTORY th
LEFT JOIN raw_.USER_CADR_EDIT uce
    ON th.USER_STAMP COLLATE DATABASE_DEFAULT = uce.user_name COLLATE DATABASE_DEFAULT
    AND uce.deleted = 0
WHERE 
    th.USER_STAMP = 'a.belash'
    AND th.DATE_TIME_STAMP >= '2026-03-01'
    AND th.DATE_TIME_STAMP IS NOT NULL
ORDER BY th.DATE_TIME_STAMP;
