-- ============================================================================
-- БЫСТРОЕ ОБНОВЛЕНИЕ DWH ЗА 3 ДНЯ (ОПТИМИЗИРОВАННАЯ ВЕРСИЯ)
-- Основано на скрипте Full.sql с поддержкой инкрементального обновления
-- Все таблицы обновляются только за последние 3 дня
-- Исключение: fact_location_snapshot — полная перезапись
-- ============================================================================
USE olap2_fixed;
GO

PRINT '=== НАЧАЛО ОБНОВЛЕНИЯ ЗА 3 ДНЯ ===';
PRINT 'Дата: ' + CAST(GETDATE() AS NVARCHAR(50));

-- ====== ПЕРЕМЕННЫЕ ======
DECLARE @period_days INT = 3;
DECLARE @cutoff_date DATE;
DECLARE @end_date DATE;
DECLARE @start_date DATE;
DECLARE @cnt INT;
DECLARE @rows_affected INT;

-- Получаем период из данных
SELECT
    @start_date = MIN(CAST(date_time_stamp AS DATE)),
    @end_date = MAX(CAST(date_time_stamp AS DATE))
FROM raw_.WORK_INSTRUCTION_VIEW2 WITH (NOLOCK)
WHERE CONDITION = 'closed' AND INSTRUCTION_TYPE = 'Detail';

SET @cutoff_date = DATEADD(DAY, -@period_days, @end_date);

-- ПРОВЕРКА: если @cutoff_date NULL, останавливаемся
IF @cutoff_date IS NULL
BEGIN
    PRINT '❌ ОШИБКА: @cutoff_date = NULL! Нет данных в raw_.WORK_INSTRUCTION_VIEW2';
    PRINT '❌ Обновление прервано.';
    RETURN;
END

PRINT 'Период обновления: ' + CONVERT(NVARCHAR(50), @cutoff_date, 104) + ' - ' + CONVERT(NVARCHAR(50), @end_date, 104);

-- ============================================================================
-- ШАГ 1: Справочники (dim_employee, dim_work_type)
-- ============================================================================
PRINT '';
PRINT '=== ШАГ 1: Обновление справочников ===';

-- dim_employee — UPSERT
PRINT 'Обновление dm.dim_employee...';

-- 1.1 Помечаем устаревших как неактивных
UPDATE de
SET is_active = 0, valid_to = GETDATE()
FROM dm.dim_employee de
WHERE de.is_active = 1
AND NOT EXISTS (
    SELECT 1 FROM raw_.USER_CADR_EDIT u
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
FROM raw_.USER_CADR_EDIT u
WHERE u.deleted = 0
AND NOT EXISTS (
    SELECT 1 FROM dm.dim_employee de
    WHERE LOWER(de.user_name) = LOWER(u.user_name) AND de.is_active = 1
);

-- 1.3 Обновляем существующих
UPDATE de
SET de.fio = u.fio, de.smena = u.smena, de.brigada = u.brigada, de.position = u.position
FROM dm.dim_employee de
JOIN raw_.USER_CADR_EDIT u 
    ON LOWER(de.user_name) COLLATE DATABASE_DEFAULT = LOWER(u.user_name) COLLATE DATABASE_DEFAULT
WHERE u.deleted = 0 AND de.is_active = 1;

SELECT @cnt = COUNT(*) FROM dm.dim_employee WHERE is_active = 1;
PRINT '  ✅ dim_employee обновлён. Активных: ' + CAST(@cnt AS NVARCHAR);

-- dim_work_type — MERGE
PRINT 'Обновление dm.dim_work_type...';

MERGE dm.dim_work_type AS target
USING (
    SELECT DISTINCT work_type
    FROM dwh.operations_enriched WITH (NOLOCK)
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

-- ============================================================================
-- ШАГ 2: Промежуточные таблицы (кэши)
-- ============================================================================
PRINT '';
PRINT '=== ШАГ 2: Пересоздание кэшей ===';

-- placement_cache — полная перезапись (быстро)
PRINT 'Пересоздание dwh.placement_cache...';
TRUNCATE TABLE dwh.placement_cache;

INSERT INTO dwh.placement_cache WITH (TABLOCK)
SELECT
    REFERENCE_ID, REFERENCE_TYPE, WORK_TYPE, ITEM, TO_LOC,
    COMPLETED_BY_USER, START_DATE_TIME, END_DATE_TIME
FROM raw_.WORK_INSTRUCTION_VIEW2 WITH (NOLOCK)
WHERE
    INSTRUCTION_TYPE = 'Detail' AND CONDITION = 'closed'
    AND WORK_TYPE LIKE N'Размещение%'
    AND START_DATE_TIME IS NOT NULL AND END_DATE_TIME IS NOT NULL;

SELECT @cnt = COUNT(*) FROM dwh.placement_cache;
PRINT '  ✅ placement_cache: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- pick_cache — полная перезапись (быстро)
PRINT 'Пересоздание dwh.pick_cache...';
TRUNCATE TABLE dwh.pick_cache;

INSERT INTO dwh.pick_cache WITH (TABLOCK)
SELECT
    REFERENCE_ID, REFERENCE_TYPE, WORK_TYPE, PARENT_INSTR, ITEM, FROM_LOC,
    COMPLETED_BY_USER, START_DATE_TIME, END_DATE_TIME
FROM raw_.WORK_INSTRUCTION_VIEW2 WITH (NOLOCK)
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

-- ============================================================================
-- ШАГ 3: operations_enriched — ГЛАВНАЯ ТАБЛИЦА (ОПТИМИЗИРОВАНО)
-- ============================================================================
PRINT '';
PRINT '=== ШАГ 3: Обновление operations_enriched ===';

-- Проверка данных перед началом
SELECT @cnt = COUNT(*) FROM dwh.operations_enriched WITH (NOLOCK);
PRINT '  📊 operations_enriched до обновления: ' + CAST(@cnt AS NVARCHAR) + ' строк';

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
FROM raw_.WORK_INSTRUCTION_VIEW2 w WITH (NOLOCK)
LEFT JOIN raw_.USER_CADR_EDIT u WITH (NOLOCK)
    ON w.COMPLETED_BY_USER COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT AND u.deleted = 0
LEFT JOIN raw_.sdelka_price sp WITH (NOLOCK)
    ON w.WORK_TYPE COLLATE DATABASE_DEFAULT = sp.work_type COLLATE DATABASE_DEFAULT
LEFT JOIN raw_.ITEM i WITH (NOLOCK)
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
PRINT '  📊 Найдено операций из WIV2: ' + CAST(@cnt AS NVARCHAR) + ' строк';

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
JOIN raw_.ITEM i WITH (NOLOCK) ON o.ITEM COLLATE DATABASE_DEFAULT = i.ITEM COLLATE DATABASE_DEFAULT
WHERE o.WORK_TYPE = N'Отбор KSP' AND o.date >= @cutoff_date;

PRINT '  ✅ KSP цены обновлены';

-- ============================================================================
-- ДОПОЛНИТЕЛЬНЫЕ ИСТОЧНИКИ для operations_enriched
-- ============================================================================

-- Приемка из TRANSACTION_HISTORY
IF OBJECT_ID('tempdb..#priemka_temp', 'U') IS NOT NULL DROP TABLE #priemka_temp;

SELECT
    NULL AS REFERENCE_ID, 'Приемка' AS REFERENCE_TYPE, 'Приемка' AS WORK_TYPE,
    NULL AS ITEM, NULL AS TO_LOC,
    th.USER_STAMP AS user_name, th.DATE_TIME_STAMP AS START_DATE_TIME,
    DATEADD(SECOND, 60, th.DATE_TIME_STAMP) AS END_DATE_TIME,
    60 AS duration_sec, 18.70 AS price_per_op,
    CAST(th.DATE_TIME_STAMP AS DATE) AS date, u.fio, u.smena, u.position
INTO #priemka_temp
FROM raw_.TRANSACTION_HISTORY th WITH (NOLOCK)
INNER JOIN raw_.USER_CADR_EDIT u WITH (NOLOCK)
    ON th.USER_STAMP COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
    AND u.deleted = 0 AND u.smena IN ('1', '2')
WHERE
    th.TRANSACTION_TYPE = '20'
    AND th.DATE_TIME_STAMP IS NOT NULL
    AND CAST(th.DATE_TIME_STAMP AS DATE) >= @cutoff_date;

SELECT @cnt = COUNT(*) FROM #priemka_temp;
IF @cnt > 0
BEGIN
    INSERT INTO dwh.operations_enriched WITH (TABLOCK)
    SELECT * FROM #priemka_temp;
    PRINT '  ✅ Вставлено приемки: ' + CAST(@@ROWCOUNT AS NVARCHAR) + ' строк';
END
ELSE
    PRINT '  ℹ️ Приемка: нет данных';

-- Приемка WH2
IF OBJECT_ID('tempdb..#priemka_wh2_temp', 'U') IS NOT NULL DROP TABLE #priemka_wh2_temp;

SELECT
    NULL AS REFERENCE_ID, 'Приемка WH2' AS REFERENCE_TYPE, 'Приемка WH2' AS WORK_TYPE,
    NULL AS ITEM, NULL AS TO_LOC,
    th.USER_STAMP AS user_name, th.DATE_TIME_STAMP AS START_DATE_TIME,
    DATEADD(SECOND, 60, th.DATE_TIME_STAMP) AS END_DATE_TIME,
    60 AS duration_sec, 8.50 AS price_per_op,
    CAST(th.DATE_TIME_STAMP AS DATE) AS date, u.fio, u.smena, u.position
INTO #priemka_wh2_temp
FROM raw_.TRANSACTION_HISTORY th WITH (NOLOCK)
INNER JOIN raw_.USER_CADR_EDIT u WITH (NOLOCK)
    ON th.USER_STAMP COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
    AND u.deleted = 0 AND u.smena IN ('1', '2')
WHERE
    th.TRANSACTION_TYPE = '20'
    AND th.WAREHOUSE = 'WH2'
    AND th.DATE_TIME_STAMP IS NOT NULL
    AND CAST(th.DATE_TIME_STAMP AS DATE) >= @cutoff_date;

SELECT @cnt = COUNT(*) FROM #priemka_wh2_temp;
IF @cnt > 0
BEGIN
    INSERT INTO dwh.operations_enriched WITH (TABLOCK)
    SELECT * FROM #priemka_wh2_temp;
    PRINT '  ✅ Вставлено приемки WH2: ' + CAST(@@ROWCOUNT AS NVARCHAR) + ' строк';
END
ELSE
    PRINT '  ℹ️ Приемка WH2: нет данных';

-- Перемер ZX KPP
IF OBJECT_ID('tempdb..#kpp_temp', 'U') IS NOT NULL DROP TABLE #kpp_temp;

SELECT
    NULL AS REFERENCE_ID, 'Перемер ZX KPP' AS REFERENCE_TYPE, 'Перемер ZX KPP' AS WORK_TYPE,
    NULL AS ITEM, NULL AS TO_LOC,
    p.user_name, p.date_time_stamp AS START_DATE_TIME,
    DATEADD(SECOND, 60, p.date_time_stamp) AS END_DATE_TIME,
    60 AS duration_sec, 52.30 AS price_per_op,
    CAST(p.date_time_stamp AS DATE) AS date, u.fio, u.smena, u.position
INTO #kpp_temp
FROM raw_.eks_peremer_ZX_KPP p WITH (NOLOCK)
INNER JOIN raw_.USER_CADR_EDIT u WITH (NOLOCK)
    ON p.user_name COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
    AND u.deleted = 0 AND u.smena IN ('1', '2')
WHERE
    p.date_time_stamp IS NOT NULL
    AND CAST(p.date_time_stamp AS DATE) >= @cutoff_date;

SELECT @cnt = COUNT(*) FROM #kpp_temp;
IF @cnt > 0
BEGIN
    INSERT INTO dwh.operations_enriched WITH (TABLOCK)
    SELECT * FROM #kpp_temp;
    PRINT '  ✅ Вставлено перемера ZX KPP: ' + CAST(@@ROWCOUNT AS NVARCHAR) + ' строк';
END
ELSE
    PRINT '  ℹ️ Перемер ZX KPP: нет данных';

-- Перемер с прихода
IF OBJECT_ID('tempdb..#peremer_temp', 'U') IS NOT NULL DROP TABLE #peremer_temp;

WITH peremer_prihoda AS (
    SELECT
        UPPER(uc.USER_DEF6) AS user_name,
        urh.DATE_TIME_STAMP
    FROM raw_.UPLOAD_RECEIPT_HEADER urh WITH (NOLOCK)
    INNER JOIN raw_.UPLOAD_RECEIPT_CONTAINER uc WITH (NOLOCK)
        ON urh.INTERFACE_RECORD_ID = uc.INTERFACE_LINK_ID
    INNER JOIN raw_.ITEM i WITH (NOLOCK) 
        ON uc.ITEM COLLATE DATABASE_DEFAULT = i.ITEM COLLATE DATABASE_DEFAULT
    WHERE
        urh.INTERFACE_CONDITION = 'End'
        AND urh.DATE_TIME_STAMP IS NOT NULL
        AND i.ITEM_CATEGORY1 = '1'
        AND uc.USER_DEF6 IS NOT NULL
        AND uc.RECEIPT_ID NOT IN (
            SELECT uc2.CONTAINER_ID
            FROM raw_.UPLOAD_RECEIPT_HEADER urh2 WITH (NOLOCK)
            INNER JOIN raw_.UPLOAD_RECEIPT_CONTAINER uc2 WITH (NOLOCK)
                ON urh2.INTERFACE_RECORD_ID = uc2.INTERFACE_LINK_ID
            INNER JOIN raw_.UPLOAD_RECEIPT_CONTAINER uc1 WITH (NOLOCK)
                ON uc2.INTERNAL_REC_CONT_NUM = uc1.Parent
            WHERE urh2.INTERFACE_CONDITION = 'End'
            AND uc1.INTERFACE_CONDITION = 'End'
        )
        AND CAST(urh.DATE_TIME_STAMP AS DATE) >= @cutoff_date
)
SELECT
    NULL AS REFERENCE_ID, 'Перемер с прихода' AS REFERENCE_TYPE, 'Перемер с прихода' AS WORK_TYPE,
    NULL AS ITEM, NULL AS TO_LOC,
    p.user_name, p.DATE_TIME_STAMP AS START_DATE_TIME,
    DATEADD(SECOND, 60, p.DATE_TIME_STAMP) AS END_DATE_TIME,
    60 AS duration_sec, 17.00 AS price_per_op,
    CAST(p.DATE_TIME_STAMP AS DATE) AS date, u.fio, u.smena, u.position
INTO #peremer_temp
FROM peremer_prihoda p
INNER JOIN raw_.USER_CADR_EDIT u WITH (NOLOCK)
    ON p.user_name COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
    AND u.deleted = 0 AND u.smena IN ('1', '2')
WHERE
    CAST(p.DATE_TIME_STAMP AS DATE) >= @cutoff_date;

SELECT @cnt = COUNT(*) FROM #peremer_temp;
IF @cnt > 0
BEGIN
    INSERT INTO dwh.operations_enriched WITH (TABLOCK)
    SELECT * FROM #peremer_temp;
    PRINT '  ✅ Вставлено перемера с прихода: ' + CAST(@@ROWCOUNT AS NVARCHAR) + ' строк';
END
ELSE
    PRINT '  ℹ️ Перемер с прихода: нет данных';

-- Итоговая проверка
SELECT @cnt = COUNT(*) FROM dwh.operations_enriched WITH (NOLOCK);
PRINT '  📊 operations_enriched после обновления: ' + CAST(@cnt AS NVARCHAR) + ' строк';
SELECT @cnt = COUNT(*) FROM dwh.operations_enriched WITH (NOLOCK) WHERE date >= @cutoff_date;
PRINT '  📊 operations_enriched за 3 дня: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- ============================================================================
-- ШАГ 4: orders_enriched (обновление за 3 дня, не полное удаление!)
-- ============================================================================
PRINT '';
PRINT '=== ШАГ 4: Обновление orders_enriched ===';

-- Удаляем ТОЛЬКО за 3 дня
DELETE FROM dwh.orders_enriched WHERE date >= @cutoff_date;

INSERT INTO dwh.orders_enriched WITH (TABLOCK)
SELECT
    s.SHIPMENT_ID, s.ORDER_TYPE, s.STOP, s.ERP_ORDER, s.ROUTING_CODE,
    o.user_name, u.fio, u.smena,
    o.START_DATE_TIME, o.END_DATE_TIME, o.duration_sec,
    CASE
        WHEN o.END_DATE_TIME <= TRY_CAST(s.STOP AS DATETIME2(0)) THEN 'Вовремя'
        ELSE 'Просрочено'
    END AS timeliness_status,
    TRY_CAST(o.START_DATE_TIME AS DATE) AS date
FROM raw_.SHIPMENT_HEADER s WITH (NOLOCK)
JOIN dwh.operations_enriched o WITH (NOLOCK)
    ON s.SHIPMENT_ID COLLATE DATABASE_DEFAULT = o.REFERENCE_ID COLLATE DATABASE_DEFAULT
LEFT JOIN raw_.USER_CADR_EDIT u WITH (NOLOCK)
    ON o.user_name COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
WHERE
    s.STOP IS NOT NULL
    AND o.START_DATE_TIME IS NOT NULL
    AND o.END_DATE_TIME IS NOT NULL
    AND o.REFERENCE_TYPE IN ('Клиент', 'Филиал', 'Ювелс')
    AND TRY_CAST(o.START_DATE_TIME AS DATE) >= @cutoff_date;

SELECT @cnt = COUNT(*) FROM dwh.orders_enriched WITH (NOLOCK) WHERE date >= @cutoff_date;
PRINT '  ✅ orders_enriched за период: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- ============================================================================
-- ШАГ 5: fines_enriched (обновление за 3 дня, не полное удаление!)
-- ============================================================================
PRINT '';
PRINT '=== ШАГ 5: Обновление fines_enriched ===';

DELETE FROM dwh.fines_enriched WHERE date >= @cutoff_date;

INSERT INTO dwh.fines_enriched WITH (TABLOCK)
SELECT
    TRY_CAST(f.date_time_stamp AS DATETIME2(0)) AS date_time_stamp,
    f.[user] AS user_name, f.reference_id, f.name AS fine_category,
    CAST(f.price AS DECIMAL(18,2)) AS fine_amount,
    CAST(NULL AS NVARCHAR(500)) AS comment,
    u.fio, u.smena,
    TRY_CAST(f.date_time_stamp AS DATE) AS date
FROM raw_.Shtraf_Edit f WITH (NOLOCK)
LEFT JOIN raw_.USER_CADR_EDIT u WITH (NOLOCK)
    ON f.[user] COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT AND u.deleted = 0
WHERE
    f.date_time_stamp IS NOT NULL
    AND f.[user] IS NOT NULL
    AND u.smena IN ('1', '2')
    AND TRY_CAST(f.date_time_stamp AS DATE) >= @cutoff_date;

SELECT @cnt = COUNT(*) FROM dwh.fines_enriched WITH (NOLOCK) WHERE date >= @cutoff_date;
PRINT '  ✅ fines_enriched за период: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- ============================================================================
-- ШАГ 6: cube_shipment_detail (обновление за 3 дня)
-- ============================================================================
PRINT '';
PRINT '=== ШАГ 6: Обновление cube_shipment_detail ===';

DELETE FROM dwh.cube_shipment_detail WHERE CAST(DATE_TIME_STAMP AS DATE) >= @cutoff_date;

INSERT INTO dwh.cube_shipment_detail WITH (TABLOCK)
SELECT
    SHIPMENT_ID, ITEM, ITEM_DESC, REQUESTED_QTY, QUANTITY_UM, PICK_LOC, PICK_ZONE,
    TRY_CAST(DATE_TIME_STAMP AS DATETIME2(0)) AS DATE_TIME_STAMP
FROM raw_.SHIPMENT_DETAIL WITH (NOLOCK)
WHERE
    STATUS1 = '900'
    AND DATE_TIME_STAMP IS NOT NULL
    AND CAST(DATE_TIME_STAMP AS DATE) >= @cutoff_date;

SELECT @cnt = COUNT(*) FROM dwh.cube_shipment_detail WITH (NOLOCK) WHERE CAST(DATE_TIME_STAMP AS DATE) >= @cutoff_date;
PRINT '  ✅ cube_shipment_detail за период: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- ============================================================================
-- ШАГ 7: receipts_status (ПОЛНАЯ ПЕРЕЗАПИСЬ — так задумано)
-- ============================================================================
PRINT '';
PRINT '=== ШАГ 7: Полная перезапись receipts_status ===';

TRUNCATE TABLE dwh.receipts_status;

INSERT INTO dwh.receipts_status WITH (TABLOCK)
SELECT
    RECEIPT_ID,
    RECEIPT_TYPE AS receipt_type,
    CAST(CREATION_DATE_TIME_STAMP AS DATETIME2(0)) AS date_created,
    CAST(NULL AS DATETIME2(0)) AS date_started,
    CAST(CLOSE_DATE AS DATETIME2(0)) AS date_closed,
    DATEADD(HOUR, 24, CAST(CREATION_DATE_TIME_STAMP AS DATETIME2(0))) AS deadline,
    CAST(CREATION_DATE_TIME_STAMP AS DATE) AS date_key,
    0 AS items_total,
    0 AS items_completed,
    CASE
        WHEN CLOSE_DATE IS NOT NULL THEN
            CASE WHEN CAST(CLOSE_DATE AS DATETIME2(0)) <= DATEADD(HOUR, 24, CAST(CREATION_DATE_TIME_STAMP AS DATETIME2(0)))
                THEN '✅ Сделано вовремя'
                ELSE '❌ Просрочено'
            END
        ELSE '⏳ В процессе'
    END AS status
FROM raw_.UPLOAD_RECEIPT_HEADER WITH (NOLOCK)
WHERE CREATION_DATE_TIME_STAMP IS NOT NULL
  AND RECEIPT_TYPE IN ('Закупка', 'Кросс-докинг');

SELECT @cnt = COUNT(*) FROM dwh.receipts_status WITH (NOLOCK);
PRINT '  ✅ receipts_status: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- ============================================================================
-- ШАГ 8: transaction_events (обновление за 3 дня)
-- ============================================================================
PRINT '';
PRINT '=== ШАГ 8: Обновление transaction_events ===';

DELETE FROM dwh.transaction_events WHERE date_key >= @cutoff_date;

INSERT INTO dwh.transaction_events WITH (TABLOCK)
SELECT
    TRY_CAST(t.DATE_TIME_STAMP AS DATE) AS date_key,
    t.USER_STAMP AS user_name, u.fio, u.smena, u.brigada, u.position,
    TRY_CAST(t.DATE_TIME_STAMP AS DATETIME2(0)) AS event_time
FROM raw_.TRANSACTION_HISTORY t WITH (NOLOCK)
JOIN raw_.USER_CADR_EDIT u WITH (NOLOCK)
    ON t.USER_STAMP COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT AND u.deleted = 0
WHERE
    t.TRANSACTION_TYPE = '20'
    AND t.DATE_TIME_STAMP IS NOT NULL
    AND u.smena IN ('1', '2')
    AND TRY_CAST(t.DATE_TIME_STAMP AS DATE) >= @cutoff_date;

SELECT @cnt = COUNT(*) FROM dwh.transaction_events WITH (NOLOCK) WHERE date_key >= @cutoff_date;
PRINT '  ✅ transaction_events за период: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- ============================================================================
-- ШАГ 9: Вызов процедур для fact таблиц
-- ============================================================================
PRINT '';
PRINT '=== ШАГ 9: Обновление фактовых таблиц ===';

-- Проверка существования процедур
IF OBJECT_ID('dwh.usp_update_fact_operation_3days', 'P') IS NOT NULL
BEGIN
    EXEC dwh.usp_update_fact_operation_3days @cutoff_date;
    PRINT '  ✅ fact_operation обновлена';
END
ELSE
BEGIN
    PRINT '  ⚠️ Процедура dwh.usp_update_fact_operation_3days не найдена';
END

IF OBJECT_ID('dwh.usp_update_fact_penalty_3days', 'P') IS NOT NULL
BEGIN
    EXEC dwh.usp_update_fact_penalty_3days @cutoff_date;
    PRINT '  ✅ fact_penalty обновлена';
END
ELSE
BEGIN
    PRINT '  ⚠️ Процедура dwh.usp_update_fact_penalty_3days не найдена';
END

-- ============================================================================
-- ШАГ 10: Пропущено (fact_location_snapshot обновляется отдельно)
-- ============================================================================
PRINT '';
PRINT '=== ШАГ 10: Пропущено ===';
PRINT 'fact_location_snapshot обновляется через sp_update_location_snapshot (каждую минуту)';

-- ============================================================================
-- ШАГ 11: Дополнительные таблицы (обновление за 3 дня)
-- ============================================================================
PRINT '';
PRINT '=== ШАГ 11: Обновление дополнительных таблиц ===';

-- placement_operations
IF OBJECT_ID('dwh.usp_update_placement_operations_3days', 'P') IS NOT NULL
BEGIN
    EXEC dwh.usp_update_placement_operations_3days @cutoff_date;
    PRINT '  ✅ placement_operations обновлена';
END

-- order_accuracy_daily
IF OBJECT_ID('dwh.usp_update_order_accuracy_daily_3days', 'P') IS NOT NULL
BEGIN
    EXEC dwh.usp_update_order_accuracy_daily_3days @cutoff_date;
    PRINT '  ✅ order_accuracy_daily обновлена';
END

-- rejected_lines_detail (ПРОПУЩЕНО - обновляется отдельно)
-- Обновление dwh.rejected_lines_detail выполняется через:
-- - скрипт update_rejected_lines.py (каждые 5 минут)
-- - прямой запрос к ILS.dbo.SHIPMENT_DETAIL
-- PRINT '  ✅ rejected_lines_detail обновлена';

-- orders_timeliness
IF OBJECT_ID('dwh.usp_update_orders_timeliness_3days', 'P') IS NOT NULL
BEGIN
    EXEC dwh.usp_update_orders_timeliness_3days @cutoff_date;
    PRINT '  ✅ orders_timeliness обновлена';
END

-- fact_hourly_errors
IF OBJECT_ID('dwh.usp_update_fact_hourly_errors_3days', 'P') IS NOT NULL
BEGIN
    EXEC dwh.usp_update_fact_hourly_errors_3days @cutoff_date;
    PRINT '  ✅ fact_hourly_errors обновлена';
END

-- fact_hourly_delays
IF OBJECT_ID('dwh.usp_update_fact_hourly_delays_3days', 'P') IS NOT NULL
BEGIN
    EXEC dwh.usp_update_fact_hourly_delays_3days @cutoff_date;
    PRINT '  ✅ fact_hourly_delays обновлена';
END

-- employee_work_idle_summary
IF OBJECT_ID('dm.usp_update_employee_work_idle_summary_3days', 'P') IS NOT NULL
BEGIN
    EXEC dm.usp_update_employee_work_idle_summary_3days @cutoff_date;
    PRINT '  ✅ employee_work_idle_summary обновлена';
END

-- ============================================================================
-- ИТОГИ
-- ============================================================================
PRINT '';
PRINT '=== ОБНОВЛЕНИЕ ЗАВЕРШЕНО ===';
PRINT 'Дата: ' + CAST(GETDATE() AS NVARCHAR(50));
PRINT 'Период: ' + CONVERT(NVARCHAR(50), @cutoff_date, 104) + ' - ' + CONVERT(NVARCHAR(50), @end_date, 104);

-- Финальная статистика
PRINT '';
PRINT '=== ФИНАЛЬНАЯ СТАТИСТИКА ===';
SELECT 'dwh.operations_enriched' AS tbl, COUNT(*) AS cnt FROM dwh.operations_enriched WITH (NOLOCK);
SELECT 'dwh.operations_enriched (3 дня)' AS tbl, COUNT(*) AS cnt FROM dwh.operations_enriched WITH (NOLOCK) WHERE date >= @cutoff_date;
SELECT 'dwh.fact_operation' AS tbl, COUNT(*) AS cnt FROM dwh.fact_operation WITH (NOLOCK);
SELECT 'dwh.fact_operation (3 дня)' AS tbl, COUNT(*) AS cnt FROM dwh.fact_operation WITH (NOLOCK) WHERE date_key >= @cutoff_date;
SELECT 'dwh.fact_penalty' AS tbl, COUNT(*) AS cnt FROM dwh.fact_penalty WITH (NOLOCK);
SELECT 'dwh.fact_penalty (3 дня)' AS tbl, COUNT(*) AS cnt FROM dwh.fact_penalty WITH (NOLOCK) WHERE date_key >= @cutoff_date;
-- fact_location_snapshot обновляется отдельно
-- SELECT 'dwh.fact_location_snapshot' AS tbl, COUNT(*) AS cnt FROM dwh.fact_location_snapshot WITH (NOLOCK);

PRINT '';
PRINT '=== УСПЕШНОЕ ЗАВЕРШЕНИЕ ===';
