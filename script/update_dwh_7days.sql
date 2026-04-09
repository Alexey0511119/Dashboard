-- ============================================================================
-- ИНКРЕМЕНТАЛЬНОЕ ОБНОВЛЕНИЕ DWH ТАБЛИЦ ЗА 7 ДНЕЙ
-- Версия 1.0 - Безопасное обновление с использованием синонимов
-- ============================================================================
USE olap2_fixed;
GO

PRINT '=== НАЧАЛО СКРИПТА ОБНОВЛЕНИЯ ===';
PRINT 'Дата запуска: ' + CAST(GETDATE() AS NVARCHAR(50));

-- ====== ПЕРЕМЕННЫЕ ПЕРИОДА ======
DECLARE @period_days INT = 7;
DECLARE @start_date DATE;
DECLARE @end_date DATE;
DECLARE @cutoff_date DATE;
DECLARE @DDD DATETIME;
DECLARE @cnt INT;

-- Получаем динамический период из данных в raw_.WORK_INSTRUCTION_VIEW2
SELECT
    @start_date = MIN(CAST(date_time_stamp AS DATE)),
    @end_date = MAX(CAST(date_time_stamp AS DATE))
FROM raw_.WORK_INSTRUCTION_VIEW2
WHERE CONDITION = 'closed' AND INSTRUCTION_TYPE = 'Detail';

-- Устанавливаем дату отсечки (7 дней от максимальной даты)
SET @cutoff_date = DATEADD(DAY, -@period_days, @end_date);

-- Устанавливаем дату для грузчиков (6 месяцев назад от максимальной)
SET @DDD = DATEADD(MONTH, -6, @end_date);

PRINT 'Период обновления: ' + CONVERT(NVARCHAR(50), @cutoff_date, 104) + ' - ' + CONVERT(NVARCHAR(50), @end_date, 104);
PRINT 'Период для грузчиков: ' + CONVERT(NVARCHAR(50), @DDD, 104) + ' - ' + CONVERT(NVARCHAR(50), @end_date, 104);

-- ============================================================================
-- ШАГ 0: ПРОВЕРКА СУЩЕСТВОВАНИЯ ТАБЛИЦ
-- ============================================================================
PRINT '=== ШАГ 0: Проверка существования таблиц ===';

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'fact_operation' AND schema_id = SCHEMA_ID('dwh'))
BEGIN
    PRINT '❌ Таблица dwh.fact_operation не найдена! Запустите сначала Full.sql для инициализации.';
    THROW 50001, 'Таблица dwh.fact_operation не найдена', 1;
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'dim_employee' AND schema_id = SCHEMA_ID('dm'))
BEGIN
    PRINT '❌ Таблица dm.dim_employee не найдена! Запустите сначала Full.sql для инициализации.';
    THROW 50002, 'Таблица dm.dim_employee не найдена', 1;
END

PRINT '✅ Все необходимые таблицы найдены';

-- ============================================================================
-- ШАГ 1: ОБНОВЛЕНИЕ СПРАВОЧНИКОВ
-- ============================================================================
PRINT '=== ШАГ 1: Обновление справочников ===';

-- dim_date — не трогаем (создан один раз на 100 лет)
PRINT 'dim_date — пропущен (статический справочник)';

-- dim_employee — UPSERT (актуализация сотрудников)
PRINT 'Обновление dm.dim_employee...';

-- 1.1 Помечаем устаревших сотрудников как неактивных
UPDATE de
SET is_active = 0, valid_to = GETDATE()
FROM dm.dim_employee de
WHERE de.is_active = 1
AND NOT EXISTS (
    SELECT 1 
    FROM raw_.USER_CADR_EDIT u 
    WHERE LOWER(de.user_name) = LOWER(u.user_name) 
    AND u.deleted = 0
);

-- 1.2 Добавляем новых сотрудников
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
    SELECT 1 
    FROM dm.dim_employee de 
    WHERE LOWER(de.user_name) = LOWER(u.user_name) 
    AND de.is_active = 1
);

-- 1.3 Обновляем данные существующих сотрудников
UPDATE de
SET de.fio = u.fio,
    de.smena = u.smena,
    de.brigada = u.brigada,
    de.position = u.position
FROM dm.dim_employee de
JOIN raw_.USER_CADR_EDIT u 
    ON LOWER(de.user_name) = LOWER(u.user_name)
WHERE u.deleted = 0
AND de.is_active = 1;

SELECT @cnt = COUNT(*) FROM dm.dim_employee WHERE is_active = 1;
PRINT '  ✅ dim_employee обновлён. Активных сотрудников: ' + CAST(@cnt AS NVARCHAR);

-- dim_work_type — MERGE (обновление видов работ)
PRINT 'Обновление dm.dim_work_type...';

MERGE dm.dim_work_type AS target
USING (
    SELECT DISTINCT work_type
    FROM dwh.operations_enriched
    WHERE work_type IS NOT NULL
) AS source
ON (target.work_type_name = source.work_type)
WHEN NOT MATCHED THEN
    INSERT (work_type_name, work_category, complexity_level)
    VALUES (
        source.work_type,
        CASE 
            WHEN source.work_type LIKE '%Ревизия%' THEN 'Ревизия'
            WHEN source.work_type LIKE '%Размещение%' THEN 'Размещение'
            WHEN source.work_type LIKE '%Отбор%' THEN 'Отбор'
            WHEN source.work_type LIKE '%Прием%' THEN 'Приемка'
            WHEN source.work_type LIKE '%Перемещение%' THEN 'Перемещение'
            WHEN source.work_type LIKE '%Пополнение%' THEN 'Пополнение'
            WHEN source.work_type LIKE '%Погрузка%' THEN 'Погрузка'
            WHEN source.work_type LIKE '%Накопление%' THEN 'Накопление'
            WHEN source.work_type LIKE '%Трансферт%' THEN 'Трансферт'
            ELSE 'Прочее'
        END,
        CASE 
            WHEN source.work_type LIKE '%Ревизия%' THEN 3
            WHEN source.work_type LIKE '%Размещение%' THEN 2
            WHEN source.work_type LIKE '%Отбор%' THEN 2
            ELSE 1
        END
    );

-- Добавляем специальные виды работ, если их нет
IF NOT EXISTS (SELECT 1 FROM dm.dim_work_type WHERE work_type_name = N'Приемка')
    INSERT INTO dm.dim_work_type VALUES (N'Приемка', N'Приемка', 1);
IF NOT EXISTS (SELECT 1 FROM dm.dim_work_type WHERE work_type_name = N'Приемка WH2')
    INSERT INTO dm.dim_work_type VALUES (N'Приемка WH2', N'Приемка', 1);
IF NOT EXISTS (SELECT 1 FROM dm.dim_work_type WHERE work_type_name = N'Перемер ZX KPP')
    INSERT INTO dm.dim_work_type VALUES (N'Перемер ZX KPP', N'Перемер', 2);
IF NOT EXISTS (SELECT 1 FROM dm.dim_work_type WHERE work_type_name = N'Перемер с прихода')
    INSERT INTO dm.dim_work_type VALUES (N'Перемер с прихода', N'Перемер', 2);

SELECT @cnt = COUNT(*) FROM dm.dim_work_type;
PRINT '  ✅ dim_work_type обновлён. Всего видов работ: ' + CAST(@cnt AS NVARCHAR);

-- ============================================================================
-- ШАГ 2: ПЕРЕСОЗДАНИЕ ПРОМЕЖУТОЧНЫХ ТАБЛИЦ
-- ============================================================================
PRINT '=== ШАГ 2: Пересоздание промежуточных таблиц ===';

-- placement_cache — полная перезапись
PRINT 'Пересоздание dwh.placement_cache...';
TRUNCATE TABLE dwh.placement_cache;

INSERT INTO dwh.placement_cache
SELECT
    REFERENCE_ID,
    REFERENCE_TYPE,
    WORK_TYPE,
    ITEM,
    TO_LOC,
    COMPLETED_BY_USER,
    START_DATE_TIME,
    END_DATE_TIME
FROM raw_.WORK_INSTRUCTION_VIEW2
WHERE
    INSTRUCTION_TYPE = 'Detail'
    AND CONDITION = 'closed'
    AND WORK_TYPE LIKE N'Размещение%'
    AND START_DATE_TIME IS NOT NULL
    AND END_DATE_TIME IS NOT NULL;

SELECT @cnt = COUNT(*) FROM dwh.placement_cache;
PRINT '  ✅ placement_cache: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- pick_cache — полная перезапись
PRINT 'Пересоздание dwh.pick_cache...';
TRUNCATE TABLE dwh.pick_cache;

INSERT INTO dwh.pick_cache
SELECT
    REFERENCE_ID,
    REFERENCE_TYPE,
    WORK_TYPE,
    PARENT_INSTR,
    ITEM,
    FROM_LOC,
    COMPLETED_BY_USER,
    START_DATE_TIME,
    END_DATE_TIME
FROM raw_.WORK_INSTRUCTION_VIEW2
WHERE
    INSTRUCTION_TYPE = 'Detail'
    AND CONDITION = 'closed'
    AND WORK_TYPE IN (
        N'Отбор ME', N'Отбор ZX 10-20', N'Отбор ZX 30-50', N'Отбор ZX 30-50 комп',
        N'Отбор ZX КПП', N'Отбор негабарит', N'Отбор транзит',
        N'Отбор WH2 ZX 10-20', N'Отбор WH2 ZX 30-50', N'Отбор WH2 ME', N'Отбор WH2 негабарит'
    )
    AND START_DATE_TIME IS NOT NULL
    AND END_DATE_TIME IS NOT NULL;

SELECT @cnt = COUNT(*) FROM dwh.pick_cache;
PRINT '  ✅ pick_cache: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- transaction_events — DELETE + INSERT за период
PRINT 'Обновление dwh.transaction_events...';

DELETE FROM dwh.transaction_events
WHERE date_key >= @cutoff_date;

INSERT INTO dwh.transaction_events
SELECT
    TRY_CAST(t.DATE_TIME_STAMP AS DATE) AS date_key,
    t.USER_STAMP AS user_name,
    u.fio,
    u.smena,
    u.brigada,
    u.position,
    TRY_CAST(t.DATE_TIME_STAMP AS DATETIME2(0)) AS event_time
FROM raw_.TRANSACTION_HISTORY t
JOIN raw_.USER_CADR_EDIT u
    ON t.USER_STAMP COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
    AND u.deleted = 0
WHERE
    t.TRANSACTION_TYPE = '20'
    AND t.DATE_TIME_STAMP IS NOT NULL
    AND u.smena IN ('1', '2')
    AND TRY_CAST(t.DATE_TIME_STAMP AS DATE) >= @cutoff_date;

SELECT @cnt = COUNT(*) FROM dwh.transaction_events WHERE date_key >= @cutoff_date;
PRINT '  ✅ transaction_events за период: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- operations_enriched — DELETE + INSERT за период
PRINT 'Обновление dwh.operations_enriched...';

DELETE FROM dwh.operations_enriched
WHERE date >= @cutoff_date;

-- Вставляем операции из WORK_INSTRUCTION_VIEW2
INSERT INTO dwh.operations_enriched
SELECT
    w.REFERENCE_ID,
    w.REFERENCE_TYPE,
    w.WORK_TYPE,
    w.ITEM,
    w.TO_LOC,
    w.COMPLETED_BY_USER AS user_name,
    w.START_DATE_TIME,
    w.END_DATE_TIME,
    DATEDIFF(SECOND, w.START_DATE_TIME, w.END_DATE_TIME) AS duration_sec,
    COALESCE(sp.price, 0) AS price_per_op,
    CAST(w.START_DATE_TIME AS DATE) AS date,
    u.fio,
    u.smena,
    u.position
FROM raw_.WORK_INSTRUCTION_VIEW2 w
LEFT JOIN raw_.USER_CADR_EDIT u
    ON w.COMPLETED_BY_USER COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
    AND u.deleted = 0
LEFT JOIN raw_.sdelka_price sp
    ON w.WORK_TYPE COLLATE DATABASE_DEFAULT = sp.work_type COLLATE DATABASE_DEFAULT
LEFT JOIN raw_.ITEM i
    ON w.ITEM COLLATE DATABASE_DEFAULT = i.ITEM COLLATE DATABASE_DEFAULT
WHERE
    w.INSTRUCTION_TYPE = 'Detail'
    AND w.CONDITION = 'closed'
    AND w.START_DATE_TIME IS NOT NULL
    AND w.END_DATE_TIME IS NOT NULL
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

-- Обновляем цену для KSP
UPDATE dwh.operations_enriched
SET price_per_op = CASE
    WHEN i.user_def1 = N'AABL' THEN 110.40
    ELSE 62.80
END
FROM dwh.operations_enriched o
JOIN raw_.ITEM i ON o.ITEM COLLATE DATABASE_DEFAULT = i.ITEM COLLATE DATABASE_DEFAULT
WHERE o.WORK_TYPE = N'Отбор KSP'
AND o.date >= @cutoff_date;

-- Приемка
INSERT INTO dwh.operations_enriched
SELECT
    NULL AS REFERENCE_ID,
    'Приемка' AS REFERENCE_TYPE,
    'Приемка' AS WORK_TYPE,
    NULL AS ITEM,
    NULL AS TO_LOC,
    th.USER_STAMP AS user_name,
    th.DATE_TIME_STAMP AS START_DATE_TIME,
    DATEADD(SECOND, 60, th.DATE_TIME_STAMP) AS END_DATE_TIME,
    60 AS duration_sec,
    18.70 AS price_per_op,
    CAST(th.DATE_TIME_STAMP AS DATE) AS date,
    u.fio,
    u.smena,
    u.position
FROM raw_.TRANSACTION_HISTORY th
JOIN raw_.USER_CADR_EDIT u
    ON th.USER_STAMP COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
    AND u.deleted = 0
WHERE
    th.TRANSACTION_TYPE = '20'
    AND th.DATE_TIME_STAMP IS NOT NULL
    AND u.smena IN ('1', '2')
    AND CAST(th.DATE_TIME_STAMP AS DATE) >= @cutoff_date;

-- Приемка WH2
INSERT INTO dwh.operations_enriched
SELECT
    NULL AS REFERENCE_ID,
    'Приемка WH2' AS REFERENCE_TYPE,
    'Приемка WH2' AS WORK_TYPE,
    NULL AS ITEM,
    NULL AS TO_LOC,
    th.USER_STAMP AS user_name,
    th.DATE_TIME_STAMP AS START_DATE_TIME,
    DATEADD(SECOND, 60, th.DATE_TIME_STAMP) AS END_DATE_TIME,
    60 AS duration_sec,
    8.50 AS price_per_op,
    CAST(th.DATE_TIME_STAMP AS DATE) AS date,
    u.fio,
    u.smena,
    u.position
FROM raw_.TRANSACTION_HISTORY th
JOIN raw_.USER_CADR_EDIT u
    ON th.USER_STAMP COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
    AND u.deleted = 0
WHERE
    th.TRANSACTION_TYPE = '20'
    AND th.WAREHOUSE = 'WH2'
    AND th.DATE_TIME_STAMP IS NOT NULL
    AND u.smena IN ('1', '2')
    AND CAST(th.DATE_TIME_STAMP AS DATE) >= @cutoff_date;

-- Перемер ZX KPP
INSERT INTO dwh.operations_enriched
SELECT
    NULL AS REFERENCE_ID,
    'Перемер ZX KPP' AS REFERENCE_TYPE,
    'Перемер ZX KPP' AS WORK_TYPE,
    NULL AS ITEM,
    NULL AS TO_LOC,
    p.user_name,
    p.date_time_stamp AS START_DATE_TIME,
    DATEADD(SECOND, 60, p.date_time_stamp) AS END_DATE_TIME,
    60 AS duration_sec,
    52.30 AS price_per_op,
    CAST(p.date_time_stamp AS DATE) AS date,
    u.fio,
    u.smena,
    u.position
FROM raw_.eks_peremer_ZX_KPP p
JOIN raw_.USER_CADR_EDIT u
    ON p.user_name COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
    AND u.deleted = 0
WHERE u.smena IN ('1', '2')
    AND p.date_time_stamp IS NOT NULL
    AND CAST(p.date_time_stamp AS DATE) >= @cutoff_date;

-- Перемер с прихода
WITH peremer_prihoda AS (
    SELECT
        UPPER(uc.USER_DEF6) AS user_name,
        urh.DATE_TIME_STAMP
    FROM raw_.UPLOAD_RECEIPT_HEADER urh
    JOIN raw_.UPLOAD_RECEIPT_CONTAINER uc
        ON urh.INTERFACE_RECORD_ID = uc.INTERFACE_LINK_ID
    JOIN raw_.ITEM i ON uc.ITEM = i.ITEM
    WHERE
        urh.INTERFACE_CONDITION = 'End'
        AND urh.DATE_TIME_STAMP IS NOT NULL
        AND i.ITEM_CATEGORY1 = '1'
        AND uc.USER_DEF6 IS NOT NULL
        AND uc.RECEIPT_ID NOT IN (
            SELECT uc2.CONTAINER_ID
            FROM raw_.UPLOAD_RECEIPT_HEADER urh2
            JOIN raw_.UPLOAD_RECEIPT_CONTAINER uc2 ON urh2.INTERFACE_RECORD_ID = uc2.INTERFACE_LINK_ID
            JOIN raw_.UPLOAD_RECEIPT_CONTAINER uc1 ON uc2.INTERNAL_REC_CONT_NUM = uc1.Parent
            WHERE urh2.INTERFACE_CONDITION = 'End'
            AND uc1.INTERFACE_CONDITION = 'End'
        )
        AND CAST(urh.DATE_TIME_STAMP AS DATE) >= @cutoff_date
)
INSERT INTO dwh.operations_enriched
SELECT
    NULL AS REFERENCE_ID,
    'Перемер с прихода' AS REFERENCE_TYPE,
    'Перемер с прихода' AS WORK_TYPE,
    NULL AS ITEM,
    NULL AS TO_LOC,
    p.user_name,
    p.DATE_TIME_STAMP AS START_DATE_TIME,
    DATEADD(SECOND, 60, p.DATE_TIME_STAMP) AS END_DATE_TIME,
    60 AS duration_sec,
    17.00 AS price_per_op,
    CAST(p.DATE_TIME_STAMP AS DATE) AS date,
    u.fio,
    u.smena,
    u.position
FROM peremer_prihoda p
JOIN raw_.USER_CADR_EDIT u
    ON p.user_name COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
    AND u.deleted = 0
WHERE u.smena IN ('1', '2')
    AND CAST(p.DATE_TIME_STAMP AS DATE) >= @cutoff_date;

SELECT @cnt = COUNT(*) FROM dwh.operations_enriched WHERE date >= @cutoff_date;
PRINT '  ✅ operations_enriched за период: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- orders_enriched — DELETE + INSERT за период
PRINT 'Пересоздание dwh.orders_enriched...';
DELETE FROM dwh.orders_enriched WHERE date >= @cutoff_date;

INSERT INTO dwh.orders_enriched
SELECT
    s.SHIPMENT_ID,
    s.ORDER_TYPE,
    s.STOP,
    s.ERP_ORDER,
    s.ROUTING_CODE,
    o.user_name,
    u.fio,
    u.smena,
    o.START_DATE_TIME,
    o.END_DATE_TIME,
    o.duration_sec,
    CASE
        WHEN o.END_DATE_TIME <= TRY_CAST(s.STOP AS DATETIME2(0)) THEN 'Вовремя'
        ELSE 'Просрочено'
    END AS timeliness_status,
    TRY_CAST(o.START_DATE_TIME AS DATE) AS date
FROM raw_.SHIPMENT_HEADER s
JOIN dwh.operations_enriched o
    ON s.SHIPMENT_ID COLLATE DATABASE_DEFAULT = o.REFERENCE_ID COLLATE DATABASE_DEFAULT
LEFT JOIN raw_.USER_CADR_EDIT u
    ON o.user_name COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
WHERE
    s.STOP IS NOT NULL
    AND o.START_DATE_TIME IS NOT NULL
    AND o.END_DATE_TIME IS NOT NULL
    AND o.REFERENCE_TYPE IN ('Клиент', 'Филиал', 'Ювелс')
    AND TRY_CAST(o.START_DATE_TIME AS DATE) >= @cutoff_date;

SELECT @cnt = COUNT(*) FROM dwh.orders_enriched WHERE date >= @cutoff_date;
PRINT '  ✅ orders_enriched за период: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- fines_enriched — DELETE + INSERT за период
PRINT 'Пересоздание dwh.fines_enriched...';
DELETE FROM dwh.fines_enriched WHERE date >= @cutoff_date;

INSERT INTO dwh.fines_enriched
SELECT
    TRY_CAST(f.date_time_stamp AS DATETIME2(0)) AS date_time_stamp,
    f.[user] AS user_name,
    f.reference_id,
    f.name AS fine_category,
    CAST(f.price AS DECIMAL(18,2)) AS fine_amount,
    CAST(NULL AS NVARCHAR(500)) AS comment,
    u.fio,
    u.smena,
    TRY_CAST(f.date_time_stamp AS DATE) AS date
FROM raw_.Shtraf_Edit f
LEFT JOIN raw_.USER_CADR_EDIT u
    ON f.[user] COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
    AND u.deleted = 0
WHERE
    f.date_time_stamp IS NOT NULL
    AND f.[user] IS NOT NULL
    AND u.smena IN ('1', '2')
    AND TRY_CAST(f.date_time_stamp AS DATE) >= @cutoff_date;

SELECT @cnt = COUNT(*) FROM dwh.fines_enriched WHERE date >= @cutoff_date;
PRINT '  ✅ fines_enriched за период: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- cube_shipment_detail — DELETE + INSERT за период
PRINT 'Пересоздание dwh.cube_shipment_detail...';
DELETE FROM dwh.cube_shipment_detail WHERE CAST(DATE_TIME_STAMP AS DATE) >= @cutoff_date;

INSERT INTO dwh.cube_shipment_detail
SELECT
    SHIPMENT_ID,
    ITEM,
    ITEM_DESC,
    REQUESTED_QTY,
    QUANTITY_UM,
    PICK_LOC,
    PICK_ZONE,
    TRY_CAST(DATE_TIME_STAMP AS DATETIME2(0)) AS DATE_TIME_STAMP
FROM raw_.SHIPMENT_DETAIL
WHERE
    STATUS1 = '900'
    AND DATE_TIME_STAMP IS NOT NULL
    AND CAST(DATE_TIME_STAMP AS DATE) >= @cutoff_date;

SELECT @cnt = COUNT(*) FROM dwh.cube_shipment_detail WHERE CAST(DATE_TIME_STAMP AS DATE) >= @cutoff_date;
PRINT '  ✅ cube_shipment_detail за период: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- receipts_status — полная перезапись (быстро)
PRINT 'Пересоздание dwh.receipts_status...';
TRUNCATE TABLE dwh.receipts_status;

WITH headers AS (
    SELECT
        RECEIPT_ID,
        MIN(CAST(CREATION_DATE_TIME_STAMP AS DATETIME2(0))) AS date_created,
        MAX(CAST(CLOSE_DATE AS DATETIME2(0))) AS date_closed,
        MAX(RECEIPT_TYPE) AS receipt_type,
        CAST(MIN(CAST(CREATION_DATE_TIME_STAMP AS DATETIME2(0))) AS DATE) AS date_key
    FROM raw_.UPLOAD_RECEIPT_HEADER
    WHERE CREATION_DATE_TIME_STAMP IS NOT NULL
    GROUP BY RECEIPT_ID
),
details AS (
    SELECT
        RECEIPT_ID,
        MIN(CASE WHEN INTERFACE_CONDITION = 'End' THEN CAST(DATE_TIME_STAMP AS DATETIME2(0)) END) AS date_started,
        COUNT(*) AS items_total,
        COUNT(CASE WHEN INTERFACE_CONDITION = 'End' THEN 1 END) AS items_completed
    FROM raw_.UPLOAD_RECEIPT_DETAIL
    WHERE RECEIPT_ID IS NOT NULL AND DATE_TIME_STAMP IS NOT NULL
    GROUP BY RECEIPT_ID
)
INSERT INTO dwh.receipts_status
SELECT
    h.RECEIPT_ID,
    h.receipt_type,
    h.date_created,
    d.date_started,
    h.date_closed,
    DATEADD(HOUR, 24, h.date_created) AS deadline,
    h.date_key,
    COALESCE(d.items_total, 0) AS items_total,
    COALESCE(d.items_completed, 0) AS items_completed,
    CASE
        WHEN h.date_closed IS NOT NULL THEN
            CASE WHEN h.date_closed <= DATEADD(HOUR, 24, h.date_created) THEN '✅ Сделано вовремя' ELSE '❌ Просрочено' END
        WHEN d.items_completed > 0 THEN '🛠 В работе'
        WHEN d.items_completed = 0 OR d.items_completed IS NULL THEN
            CASE
                WHEN GETDATE() >= DATEADD(HOUR, 24, h.date_created) THEN '🔴 Просрочена (не начата)'
                WHEN GETDATE() >= DATEADD(HOUR, 22, h.date_created) THEN '⚠️ Просрочится через ≤2 часа'
                ELSE '⏳ Ожидает приёма'
            END
        ELSE 'Неизвестно'
    END AS status
FROM headers h
LEFT JOIN details d ON h.RECEIPT_ID = d.RECEIPT_ID
WHERE h.date_created IS NOT NULL;

SELECT @cnt = COUNT(*) FROM dwh.receipts_status;
PRINT '  ✅ receipts_status: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- ============================================================================
-- ШАГ 3: ОБНОВЛЕНИЕ ФАКТОВЫХ ТАБЛИЦ (SWAP через временные таблицы)
-- ============================================================================
PRINT '=== ШАГ 3: Обновление фактовых таблиц (SWAP) ===';

-- ============================================================================
-- 3.1 fact_operation — основная таблица операций
-- ============================================================================
PRINT 'Обновление dwh.fact_operation...';

-- Сохраняем старые данные (до cutoff_date) во временную таблицу
SELECT * INTO dwh.fact_operation_tmp
FROM dwh.fact_operation
WHERE date_key < @cutoff_date;

PRINT '  Сохранено старых данных: ' + CAST((SELECT COUNT(*) FROM dwh.fact_operation_tmp) AS NVARCHAR) + ' строк';

-- Вставляем новые данные за период
-- Простые операции
INSERT INTO dwh.fact_operation_tmp
SELECT
    CAST(o.START_DATE_TIME AS DATE),
    e.employee_id,
    wt.work_type_id,
    o.REFERENCE_ID,
    o.REFERENCE_TYPE,
    o.START_DATE_TIME,
    o.END_DATE_TIME,
    o.duration_sec,
    o.price_per_op,
    CASE WHEN o.REFERENCE_TYPE IN ('Клиент', 'Филиал', 'Ювелс') THEN 1 ELSE 0 END,
    'WMS'
FROM dwh.operations_enriched o
JOIN dm.dim_employee e
    ON o.user_name COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT
    AND e.is_active = 1
JOIN dm.dim_work_type wt
    ON o.WORK_TYPE COLLATE DATABASE_DEFAULT = wt.work_type_name COLLATE DATABASE_DEFAULT
WHERE o.WORK_TYPE NOT IN (
    N'Отбор ME', N'Отбор ZX 10-20', N'Отбор ZX 30-50', N'Отбор ZX 30-50 комп',
    N'Отбор ZX КПП', N'Отбор негабарит', N'Отбор транзит',
    N'Отбор WH2 ZX 10-20', N'Отбор WH2 ZX 30-50', N'Отбор WH2 ME', N'Отбор WH2 негабарит',
    N'Размещение ME', N'Размещение ZX 10-15', N'Размещение ZX 20-50', N'Размещение КС',
    N'Размещение NG', N'Размещение WH2', N'Размещение брака/боя', N'Размещение транзит',
    N'Размещение ZX КПП',
    N'Приемка', N'Приемка WH2', N'Перемер ZX KPP', N'Перемер с прихода'
)
AND CAST(o.START_DATE_TIME AS DATE) >= @cutoff_date;

-- Сложные отборы (pick_cache)
SELECT
    PARENT_INSTR,
    ITEM,
    FROM_LOC,
    COMPLETED_BY_USER,
    MAX(END_DATE_TIME) AS max_end_time
INTO #pick_groups
FROM dwh.pick_cache
GROUP BY PARENT_INSTR, ITEM, FROM_LOC, COMPLETED_BY_USER;

SELECT
    CAST(NULL AS NVARCHAR(100)) AS WORK_TYPE,
    CAST(NULL AS NVARCHAR(50)) AS REFERENCE_ID,
    CAST(NULL AS NVARCHAR(50)) AS REFERENCE_TYPE,
    CAST(NULL AS NVARCHAR(50)) AS PARENT_INSTR,
    CAST(NULL AS NVARCHAR(50)) AS ITEM,
    CAST(NULL AS NVARCHAR(50)) AS FROM_LOC,
    CAST(NULL AS NVARCHAR(100)) AS COMPLETED_BY_USER,
    CAST(NULL AS DATETIME2) AS start_time,
    CAST(NULL AS DATETIME2) AS end_time,
    CAST(0 AS INT) AS duration_sec,
    CAST(0.0 AS DECIMAL(18,2)) AS price_per_op
INTO #pick_final
WHERE 1 = 0;

INSERT INTO #pick_final
SELECT
    r.WORK_TYPE,
    r.REFERENCE_ID,
    r.REFERENCE_TYPE,
    r.PARENT_INSTR,
    r.ITEM,
    r.FROM_LOC,
    r.COMPLETED_BY_USER,
    MIN(r.START_DATE_TIME) AS start_time,
    g.max_end_time AS end_time,
    DATEDIFF(SECOND, MIN(r.START_DATE_TIME), g.max_end_time) AS duration_sec,
    COALESCE(sp.price, 0) AS price_per_op
FROM #pick_groups g
JOIN dwh.pick_cache r
    ON g.PARENT_INSTR = r.PARENT_INSTR
    AND g.ITEM = r.ITEM
    AND g.FROM_LOC = r.FROM_LOC
    AND g.COMPLETED_BY_USER = r.COMPLETED_BY_USER
    AND g.max_end_time = r.END_DATE_TIME
LEFT JOIN raw_.sdelka_price sp
    ON r.WORK_TYPE COLLATE DATABASE_DEFAULT = sp.work_type COLLATE DATABASE_DEFAULT
GROUP BY
    r.WORK_TYPE,
    r.REFERENCE_ID,
    r.REFERENCE_TYPE,
    r.PARENT_INSTR,
    r.ITEM,
    r.FROM_LOC,
    r.COMPLETED_BY_USER,
    g.max_end_time,
    sp.price;

INSERT INTO dwh.fact_operation_tmp
SELECT
    CAST(p.start_time AS DATE),
    e.employee_id,
    wt.work_type_id,
    p.REFERENCE_ID,
    p.REFERENCE_TYPE,
    p.start_time,
    p.end_time,
    p.duration_sec,
    p.price_per_op,
    CASE WHEN p.REFERENCE_TYPE IN ('Клиент', 'Филиал', 'Ювелс') THEN 1 ELSE 0 END,
    'WMS'
FROM #pick_final p
JOIN dm.dim_employee e
    ON p.COMPLETED_BY_USER COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT
    AND e.is_active = 1
JOIN dm.dim_work_type wt
    ON p.WORK_TYPE COLLATE DATABASE_DEFAULT = wt.work_type_name COLLATE DATABASE_DEFAULT;

-- Размещения (placement_cache)
SELECT
    REFERENCE_ID,
    REFERENCE_TYPE,
    ITEM,
    TO_LOC,
    MAX(END_DATE_TIME) AS max_end_time
INTO #placement_groups
FROM dwh.placement_cache
GROUP BY REFERENCE_ID, REFERENCE_TYPE, ITEM, TO_LOC;

SELECT
    CAST(NULL AS NVARCHAR(100)) AS WORK_TYPE,
    CAST(NULL AS NVARCHAR(50)) AS REFERENCE_ID,
    CAST(NULL AS NVARCHAR(50)) AS REFERENCE_TYPE,
    CAST(NULL AS NVARCHAR(50)) AS ITEM,
    CAST(NULL AS NVARCHAR(50)) AS TO_LOC,
    CAST(NULL AS NVARCHAR(100)) AS COMPLETED_BY_USER,
    CAST(NULL AS DATETIME2) AS start_time,
    CAST(NULL AS DATETIME2) AS end_time,
    CAST(0 AS INT) AS duration_sec,
    CAST(0.0 AS DECIMAL(18,2)) AS price_per_op
INTO #placement_final
WHERE 1 = 0;

INSERT INTO #placement_final
SELECT
    r.WORK_TYPE,
    g.REFERENCE_ID,
    g.REFERENCE_TYPE,
    g.ITEM,
    g.TO_LOC,
    r.COMPLETED_BY_USER,
    MIN(r.START_DATE_TIME) AS start_time,
    g.max_end_time AS end_time,
    DATEDIFF(SECOND, MIN(r.START_DATE_TIME), g.max_end_time) AS duration_sec,
    COALESCE(sp.price, 0) AS price_per_op
FROM #placement_groups g
JOIN dwh.placement_cache r
    ON g.REFERENCE_ID = r.REFERENCE_ID
    AND g.ITEM = r.ITEM
    AND g.TO_LOC = r.TO_LOC
    AND g.max_end_time = r.END_DATE_TIME
LEFT JOIN raw_.sdelka_price sp
    ON r.WORK_TYPE COLLATE DATABASE_DEFAULT = sp.work_type COLLATE DATABASE_DEFAULT
GROUP BY
    r.WORK_TYPE,
    g.REFERENCE_ID,
    g.REFERENCE_TYPE,
    g.ITEM,
    g.TO_LOC,
    r.COMPLETED_BY_USER,
    g.max_end_time,
    sp.price;

INSERT INTO dwh.fact_operation_tmp
SELECT
    CAST(p.start_time AS DATE),
    e.employee_id,
    wt.work_type_id,
    p.REFERENCE_ID,
    p.REFERENCE_TYPE,
    p.start_time,
    p.end_time,
    p.duration_sec,
    p.price_per_op,
    CASE WHEN p.REFERENCE_TYPE IN ('Клиент', 'Филиал', 'Ювелс') THEN 1 ELSE 0 END,
    'WMS'
FROM #placement_final p
JOIN dm.dim_employee e
    ON p.COMPLETED_BY_USER COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT
    AND e.is_active = 1
JOIN dm.dim_work_type wt
    ON p.WORK_TYPE COLLATE DATABASE_DEFAULT = wt.work_type_name COLLATE DATABASE_DEFAULT;

-- Приемка и Перемер
INSERT INTO dwh.fact_operation_tmp
SELECT
    fe.date,
    e.employee_id,
    wt.work_type_id,
    NULL,
    'Приемка',
    fe.START_DATE_TIME,
    fe.END_DATE_TIME,
    fe.duration_sec,
    fe.price_per_op,
    0,
    'WMS'
FROM dwh.operations_enriched fe
JOIN dm.dim_employee e
    ON fe.user_name COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT
    AND e.is_active = 1
JOIN dm.dim_work_type wt
    ON fe.WORK_TYPE COLLATE DATABASE_DEFAULT = wt.work_type_name COLLATE DATABASE_DEFAULT
WHERE fe.WORK_TYPE IN (N'Приемка', N'Приемка WH2', N'Перемер ZX KPP', N'Перемер с прихода')
AND fe.date >= @cutoff_date;

-- Грузчики (через процедуру)
PRINT '  Расчет грузчиков...';
DROP TABLE IF EXISTS #gruz_temp;

CREATE TABLE #gruz_temp (
    [user] NVARCHAR(100) COLLATE DATABASE_DEFAULT NOT NULL,
    [Разгрузка_механизмами] DECIMAL(18,2) NOT NULL DEFAULT 0,
    [Разгрузка_ручная] DECIMAL(18,2) NOT NULL DEFAULT 0,
    [Загрузка механизмами] DECIMAL(18,2) NOT NULL DEFAULT 0,
    [Загрузка ручная] DECIMAL(18,2) NOT NULL DEFAULT 0,
    [Сортировка товаров приемка] DECIMAL(18,2) NOT NULL DEFAULT 0,
    [Сортировка товаров отгрузка] DECIMAL(18,2) NOT NULL DEFAULT 0
);

-- Вызываем процедуру за период
INSERT INTO #gruz_temp
EXEC raw_.eks_sdelka_gruz @cutoff_date, @end_date;

-- Вставляем данные грузчиков по дням
INSERT INTO dwh.fact_operation_tmp
SELECT
    CAST(lm.date_time_stamp AS DATE),
    e.employee_id,
    wt.work_type_id,
    NULL,
    'Разгрузка механизмами',
    MIN(lm.date_time_stamp),
    MAX(lm.date_time_stamp),
    DATEDIFF(SECOND, MIN(lm.date_time_stamp), MAX(lm.date_time_stamp)),
    g.[Разгрузка_механизмами] * 22.50,
    0,
    'GRUZ'
FROM #gruz_temp g
JOIN dm.dim_employee e ON LOWER(g.[user]) = e.user_name COLLATE DATABASE_DEFAULT
JOIN dm.dim_work_type wt ON wt.work_type_name = N'Разгрузка механизмами'
JOIN raw_.labor_management lm ON LOWER(g.[user]) = lm.USER_NAME COLLATE DATABASE_DEFAULT
    AND lm.user_def1 = 'Receipt_doc'
    AND lm.activity_type = N'Разгрузка механизмами'
    AND CAST(lm.date_time_stamp AS DATE) = CAST(lm.date_time_stamp AS DATE)
WHERE g.[Разгрузка_механизмами] > 0
GROUP BY CAST(lm.date_time_stamp AS DATE), e.employee_id, wt.work_type_id, g.[Разгрузка_механизмами];

INSERT INTO dwh.fact_operation_tmp
SELECT
    CAST(lm.date_time_stamp AS DATE),
    e.employee_id,
    wt.work_type_id,
    NULL,
    'Разгрузка ручная',
    MIN(lm.date_time_stamp),
    MAX(lm.date_time_stamp),
    DATEDIFF(SECOND, MIN(lm.date_time_stamp), MAX(lm.date_time_stamp)),
    g.[Разгрузка_ручная] * 22.50,
    0,
    'GRUZ'
FROM #gruz_temp g
JOIN dm.dim_employee e ON LOWER(g.[user]) = e.user_name COLLATE DATABASE_DEFAULT
JOIN dm.dim_work_type wt ON wt.work_type_name = N'Разгрузка ручная'
JOIN raw_.labor_management lm ON LOWER(g.[user]) = lm.USER_NAME COLLATE DATABASE_DEFAULT
    AND lm.user_def1 = 'Receipt_doc'
    AND lm.activity_type = N'Разгрузка ручная'
    AND CAST(lm.date_time_stamp AS DATE) = CAST(lm.date_time_stamp AS DATE)
WHERE g.[Разгрузка_ручная] > 0
GROUP BY CAST(lm.date_time_stamp AS DATE), e.employee_id, wt.work_type_id, g.[Разгрузка_ручная];

INSERT INTO dwh.fact_operation_tmp
SELECT
    CAST(lm.date_time_stamp AS DATE),
    e.employee_id,
    wt.work_type_id,
    NULL,
    'Загрузка механизмами',
    MIN(lm.date_time_stamp),
    MAX(lm.date_time_stamp),
    DATEDIFF(SECOND, MIN(lm.date_time_stamp), MAX(lm.date_time_stamp)),
    g.[Загрузка механизмами] * 68.40,
    0,
    'GRUZ'
FROM #gruz_temp g
JOIN dm.dim_employee e ON LOWER(g.[user]) = e.user_name COLLATE DATABASE_DEFAULT
JOIN dm.dim_work_type wt ON wt.work_type_name = N'Загрузка механизмами'
JOIN raw_.labor_management lm ON LOWER(g.[user]) = lm.USER_NAME COLLATE DATABASE_DEFAULT
    AND lm.user_def1 = 'Shipping_doc'
    AND lm.activity_type = N'Загрузка механизмами'
    AND CAST(lm.date_time_stamp AS DATE) = CAST(lm.date_time_stamp AS DATE)
WHERE g.[Загрузка механизмами] > 0
GROUP BY CAST(lm.date_time_stamp AS DATE), e.employee_id, wt.work_type_id, g.[Загрузка механизмами];

INSERT INTO dwh.fact_operation_tmp
SELECT
    CAST(lm.date_time_stamp AS DATE),
    e.employee_id,
    wt.work_type_id,
    NULL,
    'Загрузка ручная',
    MIN(lm.date_time_stamp),
    MAX(lm.date_time_stamp),
    DATEDIFF(SECOND, MIN(lm.date_time_stamp), MAX(lm.date_time_stamp)),
    g.[Загрузка ручная] * 68.40,
    0,
    'GRUZ'
FROM #gruz_temp g
JOIN dm.dim_employee e ON LOWER(g.[user]) = e.user_name COLLATE DATABASE_DEFAULT
JOIN dm.dim_work_type wt ON wt.work_type_name = N'Загрузка ручная'
JOIN raw_.labor_management lm ON LOWER(g.[user]) = lm.USER_NAME COLLATE DATABASE_DEFAULT
    AND lm.user_def1 = 'Shipping_doc'
    AND lm.activity_type <> N'Загрузка механизмами'
    AND CAST(lm.date_time_stamp AS DATE) = CAST(lm.date_time_stamp AS DATE)
WHERE g.[Загрузка ручная] > 0
GROUP BY CAST(lm.date_time_stamp AS DATE), e.employee_id, wt.work_type_id, g.[Загрузка ручная];

PRINT '  ✅ fact_operation_tmp за период: ' + CAST((SELECT COUNT(*) FROM dwh.fact_operation_tmp WHERE date_key >= @cutoff_date) AS NVARCHAR) + ' строк';

-- АТОМАРНОЕ ПЕРЕКЛЮЧЕНИЕ (SWAP)
PRINT '  Выполнение SWAP таблиц...';

-- Отключаем внешние ключи
ALTER TABLE dwh.fact_operation NOCHECK CONSTRAINT FK_fact_operation_date;
ALTER TABLE dwh.fact_operation NOCHECK CONSTRAINT FK_fact_operation_employee;
ALTER TABLE dwh.fact_operation NOCHECK CONSTRAINT FK_fact_operation_work_type;

-- Переименовываем таблицы
EXEC sp_rename 'dwh.fact_operation', 'fact_operation_old';
EXEC sp_rename 'dwh.fact_operation_tmp', 'fact_operation';

-- Включаем внешние ключи обратно
ALTER TABLE dwh.fact_operation CHECK CONSTRAINT FK_fact_operation_date;
ALTER TABLE dwh.fact_operation CHECK CONSTRAINT FK_fact_operation_employee;
ALTER TABLE dwh.fact_operation CHECK CONSTRAINT FK_fact_operation_work_type;

-- Пересоздаём индексы
CREATE INDEX IX_fact_operation_date_key ON dwh.fact_operation(date_key);
CREATE INDEX IX_fact_operation_employee ON dwh.fact_operation(employee_id);
CREATE INDEX IX_fact_operation_work_type ON dwh.fact_operation(work_type_id);

-- Удаляем старую таблицу
DROP TABLE IF EXISTS dwh.fact_operation_old;

SELECT @cnt = COUNT(*) FROM dwh.fact_operation;
PRINT '  ✅ fact_operation обновлена. Всего записей: ' + CAST(@cnt AS NVARCHAR);

-- ============================================================================
-- 3.2 fact_penalty — штрафы
-- ============================================================================
PRINT 'Обновление dwh.fact_penalty...';

-- Сохраняем старые данные
SELECT * INTO dwh.fact_penalty_tmp
FROM dwh.fact_penalty
WHERE date_key < @cutoff_date;

-- Вставляем новые данные
INSERT INTO dwh.fact_penalty_tmp
SELECT
    fe.date,
    e.employee_id,
    fe.reference_id,
    fe.fine_category,
    fe.fine_amount,
    'SHTRAF'
FROM dwh.fines_enriched fe
JOIN dm.dim_employee e
    ON fe.user_name COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT
    AND e.is_active = 1
WHERE fe.date >= @cutoff_date;

-- SWAP
EXEC sp_rename 'dwh.fact_penalty', 'fact_penalty_old';
EXEC sp_rename 'dwh.fact_penalty_tmp', 'fact_penalty';

DROP TABLE IF EXISTS dwh.fact_penalty_old;

-- Пересоздаём индексы
CREATE INDEX IX_fact_penalty_date ON dwh.fact_penalty(date_key);
CREATE INDEX IX_fact_penalty_employee ON dwh.fact_penalty(employee_id);

SELECT @cnt = COUNT(*) FROM dwh.fact_penalty;
PRINT '  ✅ fact_penalty обновлена. Всего записей: ' + CAST(@cnt AS NVARCHAR);

-- ============================================================================
-- 3.3 fact_rejection — брак (если существует)
-- ============================================================================
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'fact_rejection' AND schema_id = SCHEMA_ID('dwh'))
BEGIN
    PRINT 'Обновление dwh.fact_rejection...';
    
    SELECT * INTO dwh.fact_rejection_tmp
    FROM dwh.fact_rejection
    WHERE date_key < @cutoff_date;
    
    -- Вставить новые данные (логика зависит от структуры таблицы)
    -- ...
    
    EXEC sp_rename 'dwh.fact_rejection', 'fact_rejection_old';
    EXEC sp_rename 'dwh.fact_rejection_tmp', 'fact_rejection';
    
    DROP TABLE IF EXISTS dwh.fact_rejection_old;
    
    PRINT '  ✅ fact_rejection обновлена';
END
ELSE
BEGIN
    PRINT '  ℹ️ fact_rejection не существует, пропущено';
END

-- ============================================================================
-- ШАГ 4: ЛОКАЦИИ (ПРОПУЩЕНО)
-- ============================================================================
PRINT '=== ШАГ 4: Пропущено ===';
PRINT 'fact_location_snapshot обновляется через sp_update_location_snapshot (каждую минуту)';

-- ============================================================================
-- ШАГ 5: ДОПОЛНИТЕЛЬНЫЕ ТАБЛИЦЫ
-- ============================================================================
PRINT '=== ШАГ 5: Дополнительные таблицы ===';

-- employee_work_idle_summary — полная перезапись за период
PRINT 'Обновление dm.employee_work_idle_summary...';

DELETE FROM dm.employee_work_idle_summary
WHERE date_key >= @cutoff_date;

WITH unique_ops AS (
    SELECT DISTINCT
        LOWER(th.USER_STAMP) COLLATE DATABASE_DEFAULT AS user_name,
        CAST(th.DATE_TIME_STAMP AS DATE) AS date_key,
        th.DATE_TIME_STAMP AS op_time
    FROM raw_.TRANSACTION_HISTORY th
    WHERE
        th.DATE_TIME_STAMP IS NOT NULL
        AND th.USER_STAMP IS NOT NULL
        AND CAST(th.DATE_TIME_STAMP AS DATE) >= @cutoff_date
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
INSERT INTO dm.employee_work_idle_summary
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

SELECT @cnt = COUNT(*) FROM dm.employee_work_idle_summary WHERE date_key >= @cutoff_date;
PRINT '  ✅ employee_work_idle_summary за период: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- placement_operations — DELETE + INSERT за период
PRINT 'Обновление dwh.placement_operations...';
DELETE FROM dwh.placement_operations WHERE date >= @cutoff_date;

INSERT INTO dwh.placement_operations
SELECT
    w.REFERENCE_ID,
    w.REFERENCE_TYPE,
    w.WORK_TYPE,
    w.USER_STAMP AS user_name,
    w.START_DATE_TIME,
    w.END_DATE_TIME,
    w.LOCATING_ZONE,
    CAST(w.START_DATE_TIME AS DATE) AS date,
    i.ITEM_CATEGORY9,
    u.fio,
    u.smena,
    u.position
INTO dwh.placement_operations
FROM raw_.WORK_INSTRUCTION_VIEW2 w
LEFT JOIN raw_.ITEM i
    ON w.ITEM = i.ITEM COLLATE Cyrillic_General_100_CI_AS
LEFT JOIN raw_.USER_CADR_EDIT u
    ON w.USER_STAMP = u.user_name COLLATE Cyrillic_General_100_CI_AS
   AND u.deleted = 0
WHERE
    w.WORK_TYPE = N'Размещение KC'
    AND w.INSTRUCTION_TYPE = 'Detail'
    AND w.START_DATE_TIME IS NOT NULL
    AND w.END_DATE_TIME IS NOT NULL
    AND CAST(w.START_DATE_TIME AS DATE) >= @cutoff_date;

SELECT @cnt = COUNT(*) FROM dwh.placement_operations WHERE date >= @cutoff_date;
PRINT '  ✅ placement_operations за период: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- order_accuracy_daily — DELETE + INSERT за период
PRINT 'Обновление dwh.order_accuracy_daily...';
DELETE FROM dwh.order_accuracy_daily WHERE date >= @cutoff_date;

WITH deduped AS (
    SELECT
        REFERENCE_ID,
        ITEM,
        MAX(DATE_TIME_STAMP) AS DATE_TIME_STAMP,
        MAX(CASE WHEN TRANSACTION_TYPE = 240 THEN 1 ELSE 0 END) AS has_error
    FROM raw_.TRANSACTION_HISTORY WITH (NOLOCK)
    WHERE REFERENCE_ID IS NOT NULL
      AND ITEM IS NOT NULL
      AND CAST(DATE_TIME_STAMP AS DATE) >= @cutoff_date
    GROUP BY REFERENCE_ID, ITEM
)
INSERT INTO dwh.order_accuracy_daily
SELECT
    CAST(DATE_TIME_STAMP AS DATE) AS date,
    COUNT(*) AS total_assembled,
    SUM(has_error) AS error_count,
    COUNT(*) - SUM(has_error) AS correct_count,
    CAST(
        (COUNT(*) - SUM(has_error)) * 100.0 / COUNT(*)
        AS DECIMAL(5,2)
    ) AS accuracy_pct
FROM deduped
WHERE CAST(DATE_TIME_STAMP AS DATE) >= @cutoff_date
GROUP BY CAST(DATE_TIME_STAMP AS DATE);

SELECT @cnt = COUNT(*) FROM dwh.order_accuracy_daily WHERE date >= @cutoff_date;
PRINT '  ✅ order_accuracy_daily за период: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- rejected_lines_detail (ПРОПУЩЕНО - обновляется отдельно)
PRINT 'Пропущено: dwh.rejected_lines_detail обновляется через update_rejected_lines.py (каждые 5 минут)';

-- orders_timeliness — SWAP за период
PRINT 'Обновление dwh.orders_timeliness...';

SELECT * INTO dwh.orders_timeliness_tmp
FROM dwh.orders_timeliness
WHERE date < @cutoff_date;

WITH filtered_ops AS (
    SELECT
        INTERNAL_NUM,
        REFERENCE_ID,
        REFERENCE_TYPE,
        START_DATE_TIME,
        END_DATE_TIME,
        DATEDIFF(SECOND, START_DATE_TIME, END_DATE_TIME) AS duration_sec,
        COMPLETED_BY_USER,
        ROW_NUMBER() OVER (
            PARTITION BY INTERNAL_NUM
            ORDER BY END_DATE_TIME DESC
        ) AS rn
    FROM raw_.WORK_INSTRUCTION_VIEW2
    WHERE
        INSTRUCTION_TYPE = 'Detail'
        AND REFERENCE_TYPE IN ('Клиент', 'Филиал', 'Ювелс')
        AND START_DATE_TIME IS NOT NULL
        AND END_DATE_TIME IS NOT NULL
        AND INTERNAL_NUM IS NOT NULL
        AND CAST(START_DATE_TIME AS DATE) >= @cutoff_date
),
latest_ops AS (
    SELECT *
    FROM filtered_ops
    WHERE rn = 1
)
INSERT INTO dwh.orders_timeliness_tmp
SELECT
    s.SHIPMENT_ID,
    s.ORDER_TYPE,
    s.STOP,
    s.ERP_ORDER,
    s.ROUTING_CODE,
    s.SHIP_TO_CITY,
    o.COMPLETED_BY_USER,
    u.fio,
    u.smena,
    o.START_DATE_TIME,
    o.END_DATE_TIME,
    o.duration_sec,
    CASE
        WHEN o.END_DATE_TIME <= TRY_CAST(s.STOP AS DATETIME2(0)) THEN 'Вовремя'
        ELSE 'Просрочено'
    END AS timeliness_status,
    CAST(o.START_DATE_TIME AS DATE) AS date,
    s.INTERNAL_SHIPMENT_NUM
FROM raw_.SHIPMENT_HEADER s
JOIN latest_ops o
  ON s.INTERNAL_SHIPMENT_NUM = o.INTERNAL_NUM
LEFT JOIN raw_.USER_CADR_EDIT u
  ON o.COMPLETED_BY_USER COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT
  AND u.deleted = 0
WHERE
    s.STOP IS NOT NULL;

EXEC sp_rename 'dwh.orders_timeliness', 'orders_timeliness_old';
EXEC sp_rename 'dwh.orders_timeliness_tmp', 'orders_timeliness';
DROP TABLE IF EXISTS dwh.orders_timeliness_old;

SELECT @cnt = COUNT(*) FROM dwh.orders_timeliness;
PRINT '  ✅ orders_timeliness обновлена. Всего записей: ' + CAST(@cnt AS NVARCHAR);

-- fact_hourly_errors — полная перезапись за период
PRINT 'Обновление dwh.fact_hourly_errors...';

WITH deduped AS (
    SELECT
        REFERENCE_ID,
        ITEM,
        MAX(DATE_TIME_STAMP) AS DATE_TIME_STAMP,
        MAX(CASE WHEN TRANSACTION_TYPE = 240 THEN 1 ELSE 0 END) AS has_error
    FROM raw_.TRANSACTION_HISTORY WITH (NOLOCK)
    WHERE REFERENCE_ID IS NOT NULL
      AND ITEM IS NOT NULL
      AND CAST(DATE_TIME_STAMP AS DATE) >= @cutoff_date
    GROUP BY REFERENCE_ID, ITEM
),
error_orders AS (
    SELECT
        DATEPART(HOUR, DATE_TIME_STAMP) AS hour,
        COUNT(DISTINCT REFERENCE_ID) AS error_orders
    FROM deduped
    WHERE has_error = 1
    GROUP BY DATEPART(HOUR, DATE_TIME_STAMP)
),
all_orders_by_hour AS (
    SELECT
        DATEPART(HOUR, DATE_TIME_STAMP) AS hour,
        COUNT(*) AS total_orders
    FROM deduped
    GROUP BY DATEPART(HOUR, DATE_TIME_STAMP)
)
DELETE FROM dwh.fact_hourly_errors;

INSERT INTO dwh.fact_hourly_errors
SELECT
    t.hour,
    t.total_orders,
    COALESCE(e.error_orders, 0) AS error_orders,
    CAST(COALESCE(e.error_orders, 0) * 100.0 / NULLIF(t.total_orders, 0) AS DECIMAL(5,2)) AS pct_errors
FROM all_orders_by_hour t
LEFT JOIN error_orders e ON t.hour = e.hour
WHERE COALESCE(e.error_orders, 0) > 0;

SELECT @cnt = COUNT(*) FROM dwh.fact_hourly_errors;
PRINT '  ✅ fact_hourly_errors: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- fact_hourly_delays — полная перезапись за период
PRINT 'Обновление dwh.fact_hourly_delays...';
DELETE FROM dwh.fact_hourly_delays WHERE hour IN (
    SELECT DISTINCT DATEPART(HOUR, START_DATE_TIME) 
    FROM dwh.orders_timeliness 
    WHERE date >= @cutoff_date
);

WITH hourly_stats AS (
    SELECT
        DATEPART(HOUR, START_DATE_TIME) AS hour,
        COUNT(*) AS total_orders,
        SUM(CASE WHEN timeliness_status = 'Просрочено' THEN 1 ELSE 0 END) AS delayed_orders
    FROM dwh.orders_timeliness
    WHERE ORDER_TYPE = 'Клиент'
    AND date >= @cutoff_date
    GROUP BY DATEPART(HOUR, START_DATE_TIME)
)
INSERT INTO dwh.fact_hourly_delays
SELECT
    hour,
    total_orders,
    delayed_orders,
    CAST(delayed_orders * 100.0 / NULLIF(total_orders, 0) AS DECIMAL(5,2)) AS pct_delayed
FROM hourly_stats;

SELECT @cnt = COUNT(*) FROM dwh.fact_hourly_delays;
PRINT '  ✅ fact_hourly_delays: ' + CAST(@cnt AS NVARCHAR) + ' строк';

-- ============================================================================
-- ИТОГИ
-- ============================================================================
PRINT '=== ОБНОВЛЕНИЕ ЗАВЕРШЕНО ===';
PRINT 'Дата завершения: ' + CAST(GETDATE() AS NVARCHAR(50));
PRINT 'Период обновления: ' + CONVERT(NVARCHAR(50), @cutoff_date, 104) + ' - ' + CONVERT(NVARCHAR(50), @end_date, 104);
PRINT '✅ Все таблицы успешно обновлены!';
