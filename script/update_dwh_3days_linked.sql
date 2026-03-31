-- ============================================================================
-- БЫСТРОЕ ОБНОВЛЕНИЕ DWH ЗА 3 ДНЯ ЧЕРЕЗ LINKED SERVER
-- Сервер аналитики: 10.7.0.27 (olap2_fixed)
-- Сервер источник: 10.7.0.248 (ils, sk)
-- 
-- Преимущества:
--   - Прямой INSERT INTO ... SELECT без промежуточного Python
--   - Минимальное логгирование (FAST INSERT)
--   - Пакетная обработка данных
--   - Выполнение через SQL Server Agent
-- ============================================================================

USE olap2_fixed;
GO

PRINT '╔' + REPLICATE('=', 78) + '╗';
PRINT '║' + SPACE(20) + '3-ДНЕВНЫЙ ETL ЧЕРЕЗ LINKED SERVER' + SPACE(26) + '║';
PRINT '╚' + REPLICATE('=', 78) + '╝';
PRINT '';
PRINT '📅 Время начала: ' + CAST(GETDATE() AS NVARCHAR(50));
PRINT '';

-- ====== ПЕРЕМЕННЫЕ ======
DECLARE @period_days INT = 3;
DECLARE @cutoff_date DATE;
DECLARE @end_date DATE;
DECLARE @start_date DATE;
DECLARE @cnt INT;
DECLARE @rows_affected INT;
DECLARE @sql NVARCHAR(MAX);

-- Получаем период из данных на источнике
SELECT
    @start_date = MIN(CAST(date_time_stamp AS DATE)),
    @end_date = MAX(CAST(date_time_stamp AS DATE))
FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2 WITH (NOLOCK)
WHERE CONDITION = 'closed' AND INSTRUCTION_TYPE = 'Detail';

SET @cutoff_date = DATEADD(DAY, -@period_days, @end_date);

-- ПРОВЕРКА: если @cutoff_date NULL, останавливаемся
IF @cutoff_date IS NULL
BEGIN
    PRINT '❌ ОШИБКА: @cutoff_date = NULL! Нет данных в WORK_INSTRUCTION_VIEW2 на источнике';
    PRINT '❌ Обновление прервано.';
    RETURN;
END

PRINT '📊 Период обновления: ' + CONVERT(NVARCHAR(50), @cutoff_date, 104) + ' - ' + CONVERT(NVARCHAR(50), @end_date, 104);
PRINT '📊 Дней данных: ' + CAST(DATEDIFF(DAY, @cutoff_date, @end_date) AS NVARCHAR(10));
PRINT '';

-- ============================================================================
-- ШАГ 1: Справочники (dim_employee, dim_work_type)
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT 'ШАГ 1: Обновление справочников';
PRINT '═' + REPLICATE('=', 78);

-- dim_employee — UPSERT
PRINT '🔄 Обновление dm.dim_employee...';

-- 1.1 Помечаем устаревших как неактивных
UPDATE de
SET is_active = 0, valid_to = GETDATE()
FROM dm.dim_employee de
WHERE de.is_active = 1
AND NOT EXISTS (
    SELECT 1 FROM ILS_SOURCE.ils.dbo.USER_CADR_EDIT u WITH (NOLOCK)
    WHERE LOWER(de.user_name) = LOWER(u.user_name) AND u.deleted = 0
);

-- 1.2 Добавляем новых
INSERT INTO dm.dim_employee (user_name, fio, smena, brigada, position, is_active, valid_from, valid_to)
SELECT DISTINCT
    u.user_name,
    ISNULL(u.fio, u.user_name) AS fio,
    ISNULL(u.smena, '-') AS smena,
    ISNULL(u.brigada, '-') AS brigada,
    u.position,
    1,
    GETDATE(),
    '2099-12-31'
FROM ILS_SOURCE.ils.dbo.USER_CADR_EDIT u WITH (NOLOCK)
WHERE u.deleted = 0
AND NOT EXISTS (
    SELECT 1 FROM dm.dim_employee de
    WHERE LOWER(de.user_name) = LOWER(u.user_name) AND de.is_active = 1
);

-- 1.3 Обновляем существующих
UPDATE de
SET de.fio = u.fio, de.smena = u.smena, de.brigada = u.brigada, de.position = u.position
FROM dm.dim_employee de
JOIN ILS_SOURCE.ils.dbo.USER_CADR_EDIT u WITH (NOLOCK)
    ON LOWER(de.user_name) COLLATE DATABASE_DEFAULT = LOWER(u.user_name) COLLATE DATABASE_DEFAULT
WHERE u.deleted = 0 AND de.is_active = 1;

SELECT @cnt = COUNT(*) FROM dm.dim_employee WHERE is_active = 1;
PRINT '  ✅ dim_employee обновлён. Активных: ' + CAST(@cnt AS NVARCHAR);

-- dim_work_type — MERGE
PRINT '🔄 Обновление dm.dim_work_type...';

MERGE dm.dim_work_type AS target
USING (
    SELECT DISTINCT work_type
    FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2 WITH (NOLOCK)
    WHERE work_type IS NOT NULL
) AS source
ON (target.work_type_name = source.work_type)
WHEN NOT MATCHED THEN
    INSERT (work_type_name, work_category, complexity_level)
    VALUES (
        source.work_type,
        CASE
            WHEN source.work_type LIKE N'%Ревизия%' THEN N'Ревизия'
            WHEN source.work_type LIKE N'%Размещение%' THEN N'Размещение'
            WHEN source.work_type LIKE N'%Отбор%' THEN N'Отбор'
            WHEN source.work_type LIKE N'%Прием%' THEN N'Приемка'
            WHEN source.work_type LIKE N'%Перемещение%' THEN N'Перемещение'
            WHEN source.work_type LIKE N'%Пополнение%' THEN N'Пополнение'
            WHEN source.work_type LIKE N'%Погрузка%' THEN N'Погрузка'
            WHEN source.work_type LIKE N'%Накопление%' THEN N'Накопление'
            WHEN source.work_type LIKE N'%Трансферт%' THEN N'Трансферт'
            ELSE N'Прочее'
        END,
        CASE
            WHEN source.work_type LIKE N'%Ревизия%' THEN 3
            WHEN source.work_type LIKE N'%Размещение%' THEN 2
            WHEN source.work_type LIKE N'%Отбор%' THEN 2
            ELSE 1
        END
    );

-- Добавляем специальные виды работ
IF NOT EXISTS (SELECT 1 FROM dm.dim_work_type WHERE work_type_name = N'Приемка')
    INSERT INTO dm.dim_work_type VALUES (N'Приемка', N'Приемка', 1);
IF NOT EXISTS (SELECT 1 FROM dm.dim_work_type WHERE work_type_name = N'Приемка WH2')
    INSERT INTO dm.dim_work_type VALUES (N'Приемка WH2', N'Приемка', 1);
IF NOT EXISTS (SELECT 1 FROM dm.dim_work_type WHERE work_type_name = N'Перемер ZX KPP')
    INSERT INTO dm.dim_work_type VALUES (N'Перемер ZX KPP', N'Перемер', 2);
IF NOT EXISTS (SELECT 1 FROM dm.dim_work_type WHERE work_type_name = N'Перемер с прихода')
    INSERT INTO dm.dim_work_type VALUES (N'Перемер с прихода', N'Перемер', 2);

SELECT @cnt = COUNT(*) FROM dm.dim_work_type;
PRINT '  ✅ dim_work_type обновлён. Всего: ' + CAST(@cnt AS NVARCHAR);
PRINT '';

-- ============================================================================
-- ШАГ 2: Промежуточные таблицы (кэши)
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT 'ШАГ 2: Пересоздание кэшей';
PRINT '═' + REPLICATE('=', 78);

-- placement_cache — полная перезапись
PRINT '🔄 Пересоздание dwh.placement_cache...';
TRUNCATE TABLE dwh.placement_cache;

INSERT INTO dwh.placement_cache WITH (TABLOCK)
SELECT
    REFERENCE_ID, REFERENCE_TYPE, WORK_TYPE, ITEM, TO_LOC,
    COMPLETED_BY_USER, START_DATE_TIME, END_DATE_TIME
FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2 WITH (NOLOCK)
WHERE
    INSTRUCTION_TYPE = 'Detail' AND CONDITION = 'closed'
    AND WORK_TYPE LIKE N'Размещение%'
    AND START_DATE_TIME IS NOT NULL AND END_DATE_TIME IS NOT NULL;

SELECT @cnt = COUNT(*) FROM dwh.placement_cache;
PRINT '  ✅ placement_cache: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- pick_cache — полная перезапись
PRINT '🔄 Пересоздание dwh.pick_cache...';
TRUNCATE TABLE dwh.pick_cache;

INSERT INTO dwh.pick_cache WITH (TABLOCK)
SELECT
    REFERENCE_ID, REFERENCE_TYPE, WORK_TYPE, PARENT_INSTR, ITEM, FROM_LOC,
    COMPLETED_BY_USER, START_DATE_TIME, END_DATE_TIME
FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2 WITH (NOLOCK)
WHERE
    INSTRUCTION_TYPE = 'Detail' AND CONDITION = 'closed'
    AND WORK_TYPE IN (
        N'Отбор ME', N'Отбор ZX 10-20', N'Отбор ZX 30-50', N'Отбор ZX 30-50 комп',
        N'Отбор ZX КПП', N'Отбор негабарит', N'Отбор транзит',
        N'Отбор WH2 ZX 10-20', N'Отбор WH2 ZX 30-50', N'Отбор WH2 ME', N'Отбор WH2 негабарит'
    )
    AND START_DATE_TIME IS NOT NULL AND END_DATE_TIME IS NOT NULL;

SELECT @cnt = COUNT(*) FROM dwh.pick_cache;
PRINT '  ✅ pick_cache: ' + CAST(@cnt AS NVARCHAR) + ' строк';
PRINT '';

-- ============================================================================
-- ШАГ 3: operations_enriched — ГЛАВНАЯ ТАБЛИЦА
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT 'ШАГ 3: Обновление operations_enriched';
PRINT '═' + REPLICATE('=', 78);

-- Проверка данных перед началом
SELECT @cnt = COUNT(*) FROM dwh.operations_enriched WITH (NOLOCK);
PRINT '  📊 operations_enriched до обновления: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- Проверка количества данных на источнике
SELECT @cnt = COUNT(*)
FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2 WITH (NOLOCK)
WHERE
    INSTRUCTION_TYPE = 'Detail' AND CONDITION = 'closed'
    AND CAST(START_DATE_TIME AS DATE) >= @cutoff_date;

PRINT '  📊 Найдено операций на источнике: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- Создаём временную таблицу для данных за 3 дня
IF OBJECT_ID('tempdb..#ops_temp', 'U') IS NOT NULL DROP TABLE #ops_temp;

SELECT
    w.REFERENCE_ID, w.REFERENCE_TYPE, w.WORK_TYPE, w.ITEM, w.TO_LOC,
    w.COMPLETED_BY_USER AS user_name, w.START_DATE_TIME, w.END_DATE_TIME,
    DATEDIFF(SECOND, w.START_DATE_TIME, w.END_DATE_TIME) AS duration_sec,
    COALESCE(sp.price, 0) AS price_per_op,
    CAST(w.START_DATE_TIME AS DATE) AS date,
    u.fio, u.smena, u.position
INTO #ops_temp
FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2 w WITH (NOLOCK)
LEFT JOIN ILS_SOURCE.ils.dbo.USER_CADR_EDIT u WITH (NOLOCK)
    ON w.COMPLETED_BY_USER COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT AND u.deleted = 0
LEFT JOIN ILS_SOURCE.ils.dbo.sdelka_price sp WITH (NOLOCK)
    ON w.WORK_TYPE COLLATE DATABASE_DEFAULT = sp.work_type COLLATE DATABASE_DEFAULT
LEFT JOIN ILS_SOURCE.ils.dbo.ITEM i WITH (NOLOCK)
    ON w.ITEM COLLATE DATABASE_DEFAULT = i.ITEM COLLATE DATABASE_DEFAULT
WHERE
    w.INSTRUCTION_TYPE = 'Detail' AND w.CONDITION = 'closed'
    AND w.START_DATE_TIME IS NOT NULL AND w.END_DATE_TIME IS NOT NULL
    AND u.smena IN ('1', '2')
    AND w.WORK_TYPE NOT IN (
        N'Отбор ME', N'Отбор ZX 10-20', N'Отбор ZX 30-50', N'Отбор ZX 30-50 комп',
        N'Отбор ZX КПП', N'Отбор негабарит', N'Отбор транзит',
        N'Отбор WH2 ZX 10-20', N'Отбор WH2 ZX 30-50', N'Отбор WH2 ME', N'Отбор WH2 негабарит',
        N'Размещение ME', N'Размещение ZX 10-15', N'Размещение ZX 20-50', N'Размещение КС',
        N'Размещение NG', N'Размещение WH2', N'Размещение брака/боя', N'Размещение транзит',
        N'Размещение ZX КПП'
    )
    AND CAST(w.START_DATE_TIME AS DATE) >= @cutoff_date;

SELECT @cnt = COUNT(*) FROM #ops_temp;
PRINT '  📊 Подготовлено операций: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- Удаляем старые данные за 3 дня
DELETE FROM dwh.operations_enriched WHERE date >= @cutoff_date;
SET @rows_affected = @@ROWCOUNT;
PRINT '  🗑️ Удалено старых записей: ' + CAST(@rows_affected AS NVARCHAR);

-- Вставляем новые данные с TABLOCK для скорости
INSERT INTO dwh.operations_enriched WITH (TABLOCK)
SELECT
    REFERENCE_ID, REFERENCE_TYPE, WORK_TYPE, ITEM, TO_LOC,
    user_name, START_DATE_TIME, END_DATE_TIME, duration_sec,
    price_per_op, date, fio, smena, position
FROM #ops_temp;

SET @rows_affected = @@ROWCOUNT;
PRINT '  ✅ Вставлено операций: ' + CAST(@rows_affected AS NVARCHAR) + ' строк';

-- Обновляем цену для KSP
UPDATE o
SET price_per_op = CASE WHEN i.user_def1 = N'AABL' THEN 110.40 ELSE 62.80 END
FROM dwh.operations_enriched o WITH (ROWLOCK)
JOIN ILS_SOURCE.ils.dbo.ITEM i WITH (NOLOCK) 
    ON o.ITEM COLLATE DATABASE_DEFAULT = i.ITEM COLLATE DATABASE_DEFAULT
WHERE o.WORK_TYPE = N'Отбор KSP' AND o.date >= @cutoff_date;

PRINT '  ✅ KSP цены обновлены';

-- ============================================================================
-- ДОПОЛНИТЕЛЬНЫЕ ИСТОЧНИКИ для operations_enriched
-- ============================================================================

-- Приемка из TRANSACTION_HISTORY
PRINT '🔄 Вставка приемки из TRANSACTION_HISTORY...';

INSERT INTO dwh.operations_enriched WITH (TABLOCK)
SELECT
    NULL AS REFERENCE_ID, 'Приемка' AS REFERENCE_TYPE, 'Приемка' AS WORK_TYPE,
    NULL AS ITEM, NULL AS TO_LOC,
    th.USER_STAMP AS user_name, th.DATE_TIME_STAMP AS START_DATE_TIME,
    DATEADD(SECOND, 60, th.DATE_TIME_STAMP) AS END_DATE_TIME,
    60 AS duration_sec, 18.70 AS price_per_op,
    CAST(th.DATE_TIME_STAMP AS DATE) AS date, u.fio, u.smena, u.position
FROM ILS_SOURCE.ils.dbo.TRANSACTION_HISTORY th WITH (NOLOCK)
INNER JOIN ILS_SOURCE.ils.dbo.USER_CADR_EDIT u WITH (NOLOCK)
    ON th.USER_STAMP COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
    AND u.deleted = 0 AND u.smena IN ('1', '2')
WHERE
    th.TRANSACTION_TYPE = '20'
    AND th.DATE_TIME_STAMP IS NOT NULL
    AND CAST(th.DATE_TIME_STAMP AS DATE) >= @cutoff_date;

PRINT '  ✅ Вставлено приемки: ' + CAST(@@ROWCOUNT AS NVARCHAR) + ' строк';

-- Приемка WH2
PRINT '🔄 Вставка приемки WH2...';

INSERT INTO dwh.operations_enriched WITH (TABLOCK)
SELECT
    NULL AS REFERENCE_ID, 'Приемка WH2' AS REFERENCE_TYPE, 'Приемка WH2' AS WORK_TYPE,
    NULL AS ITEM, NULL AS TO_LOC,
    th.USER_STAMP AS user_name, th.DATE_TIME_STAMP AS START_DATE_TIME,
    DATEADD(SECOND, 60, th.DATE_TIME_STAMP) AS END_DATE_TIME,
    60 AS duration_sec, 8.50 AS price_per_op,
    CAST(th.DATE_TIME_STAMP AS DATE) AS date, u.fio, u.smena, u.position
FROM ILS_SOURCE.ils.dbo.TRANSACTION_HISTORY th WITH (NOLOCK)
INNER JOIN ILS_SOURCE.ils.dbo.USER_CADR_EDIT u WITH (NOLOCK)
    ON th.USER_STAMP COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
    AND u.deleted = 0 AND u.smena IN ('1', '2')
WHERE
    th.TRANSACTION_TYPE = '20'
    AND th.WAREHOUSE = 'WH2'
    AND th.DATE_TIME_STAMP IS NOT NULL
    AND CAST(th.DATE_TIME_STAMP AS DATE) >= @cutoff_date;

PRINT '  ✅ Вставлено приемки WH2: ' + CAST(@@ROWCOUNT AS NVARCHAR) + ' строк';

-- Перемер ZX KPP (из SK)
PRINT '🔄 Вставка перемера ZX KPP...';

INSERT INTO dwh.operations_enriched WITH (TABLOCK)
SELECT
    NULL AS REFERENCE_ID, 'Перемер ZX KPP' AS REFERENCE_TYPE, 'Перемер ZX KPP' AS WORK_TYPE,
    NULL AS ITEM, NULL AS TO_LOC,
    p.user_name, p.date_time_stamp AS START_DATE_TIME,
    DATEADD(SECOND, 60, p.date_time_stamp) AS END_DATE_TIME,
    60 AS duration_sec, 52.30 AS price_per_op,
    CAST(p.date_time_stamp AS DATE) AS date, u.fio, u.smena, u.position
FROM SK_SOURCE.sk.dbo.eks_peremer_ZX_KPP p WITH (NOLOCK)
INNER JOIN ILS_SOURCE.ils.dbo.USER_CADR_EDIT u WITH (NOLOCK)
    ON p.user_name COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
    AND u.deleted = 0 AND u.smena IN ('1', '2')
WHERE
    p.date_time_stamp IS NOT NULL
    AND CAST(p.date_time_stamp AS DATE) >= @cutoff_date;

PRINT '  ✅ Вставлено перемера ZX KPP: ' + CAST(@@ROWCOUNT AS NVARCHAR) + ' строк';

-- Итоговая проверка
SELECT @cnt = COUNT(*) FROM dwh.operations_enriched WITH (NOLOCK);
PRINT '  📊 operations_enriched после обновления: ' + CAST(@cnt AS NVARCHAR) + ' строк';
SELECT @cnt = COUNT(*) FROM dwh.operations_enriched WITH (NOLOCK) WHERE date >= @cutoff_date;
PRINT '  📊 operations_enriched за 3 дня: ' + CAST(@cnt AS NVARCHAR) + ' строк';
PRINT '';

-- ============================================================================
-- ШАГ 4: Вызов процедур для fact таблиц
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT 'ШАГ 4: Обновление фактовых таблиц';
PRINT '═' + REPLICATE('=', 78);

-- Проверка существования процедур
IF OBJECT_ID('dwh.usp_update_fact_operation_3days_linked', 'P') IS NOT NULL
BEGIN
    EXEC dwh.usp_update_fact_operation_3days_linked @cutoff_date;
    PRINT '  ✅ fact_operation обновлена';
END
ELSE
BEGIN
    PRINT '  ⚠️ Процедура dwh.usp_update_fact_operation_3days_linked не найдена';
END

IF OBJECT_ID('dwh.usp_update_fact_penalty_3days_linked', 'P') IS NOT NULL
BEGIN
    EXEC dwh.usp_update_fact_penalty_3days_linked @cutoff_date;
    PRINT '  ✅ fact_penalty обновлена';
END
ELSE
BEGIN
    PRINT '  ⚠️ Процедура dwh.usp_update_fact_penalty_3days_linked не найдена';
END

PRINT '';

-- ============================================================================
-- ИТОГИ
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT 'ОБНОВЛЕНИЕ ЗАВЕРШЕНО';
PRINT '═' + REPLICATE('=', 78);
PRINT '📅 Время завершения: ' + CAST(GETDATE() AS NVARCHAR(50));
PRINT '';

-- Финальная статистика
PRINT '=== ФИНАЛЬНАЯ СТАТИСТИКА ===';
SELECT 'dwh.operations_enriched' AS tbl, COUNT(*) AS cnt FROM dwh.operations_enriched WITH (NOLOCK);
SELECT 'dwh.operations_enriched (3 дня)' AS tbl, COUNT(*) AS cnt FROM dwh.operations_enriched WITH (NOLOCK) WHERE date >= @cutoff_date;
SELECT 'dwh.fact_operation' AS tbl, COUNT(*) AS cnt FROM dwh.fact_operation WITH (NOLOCK);
SELECT 'dwh.fact_operation (3 дня)' AS tbl, COUNT(*) AS cnt FROM dwh.fact_operation WITH (NOLOCK) WHERE date_key >= @cutoff_date;
SELECT 'dwh.fact_penalty' AS tbl, COUNT(*) AS cnt FROM dwh.fact_penalty WITH (NOLOCK);
SELECT 'dwh.fact_penalty (3 дня)' AS tbl, COUNT(*) AS cnt FROM dwh.fact_penalty WITH (NOLOCK) WHERE date_key >= @cutoff_date;

PRINT '';
PRINT '=== УСПЕШНОЕ ЗАВЕРШЕНИЕ ===';
GO
