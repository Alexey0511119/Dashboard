-- ============================================================================
-- ПОЛНЫЙ ПАКЕТ ПРОЦЕДУР ДЛЯ 3-ДНЕВНОГО ОБНОВЛЕНИЯ DWH
-- ОПТИМИЗИРОВАННАЯ ВЕРСИЯ: DELETE + WHERE вместо TRUNCATE
-- Все таблицы обновляются только за последние 3 дня
-- Исключение: fact_location_snapshot — полная перезапись (в главном скрипте)
-- ============================================================================
USE olap2_fixed;
GO

PRINT '=== СОЗДАНИЕ ПРОЦЕДУР 3-ДНЕВНОГО ОБНОВЛЕНИЯ ===';

-- ============================================================================
-- ПРОЦЕДУРА 1: Обновление dim_employee (UPSERT)
-- ============================================================================
IF OBJECT_ID('dm.usp_update_dim_employee_3days', 'P') IS NOT NULL
    DROP PROCEDURE dm.usp_update_dim_employee_3days;
GO

CREATE PROCEDURE dm.usp_update_dim_employee_3days
AS
BEGIN
    SET NOCOUNT ON;
    PRINT '  Обновление dm.dim_employee...';

    -- 1. Помечаем устаревших как неактивных
    UPDATE de
    SET is_active = 0, valid_to = GETDATE()
    FROM dm.dim_employee de
    WHERE de.is_active = 1
    AND NOT EXISTS (
        SELECT 1 FROM raw_.USER_CADR_EDIT u
        WHERE LOWER(de.user_name) = LOWER(u.user_name) AND u.deleted = 0
    );

    -- 2. Добавляем новых
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

    -- 3. Обновляем существующих
    UPDATE de
    SET de.fio = u.fio, de.smena = u.smena, de.brigada = u.brigada, de.position = u.position
    FROM dm.dim_employee de
    JOIN raw_.USER_CADR_EDIT u 
        ON LOWER(de.user_name) COLLATE DATABASE_DEFAULT = LOWER(u.user_name) COLLATE DATABASE_DEFAULT
    WHERE u.deleted = 0 AND de.is_active = 1;

    PRINT '  ✅ dim_employee обновлён';
END;
GO

-- ============================================================================
-- ПРОЦЕДУРА 2: Обновление dim_work_type (MERGE)
-- ============================================================================
IF OBJECT_ID('dm.usp_update_dim_work_type_3days', 'P') IS NOT NULL
    DROP PROCEDURE dm.usp_update_dim_work_type_3days;
GO

CREATE PROCEDURE dm.usp_update_dim_work_type_3days
AS
BEGIN
    SET NOCOUNT ON;
    PRINT '  Обновление dm.dim_work_type...';

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

    PRINT '  ✅ dim_work_type обновлён';
END;
GO

-- ============================================================================
-- ПРОЦЕДУРА 3: Обновление transaction_events (за 3 дня)
-- ============================================================================
IF OBJECT_ID('dwh.usp_update_transaction_events_3days', 'P') IS NOT NULL
    DROP PROCEDURE dwh.usp_update_transaction_events_3days;
GO

CREATE PROCEDURE dwh.usp_update_transaction_events_3days
    @cutoff_date DATE
AS
BEGIN
    SET NOCOUNT ON;
    PRINT '  Обновление dwh.transaction_events...';

    -- Удаляем только за 3 дня (не TRUNCATE!)
    DELETE FROM dwh.transaction_events WHERE date_key >= @cutoff_date;

    -- Вставляем новые данные
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

    PRINT '  ✅ transaction_events обновлён';
END;
GO

-- ============================================================================
-- ПРОЦЕДУРА 4: Обновление gruz_operations (за 3 дня)
-- ============================================================================
IF OBJECT_ID('dwh.usp_update_gruz_operations_3days', 'P') IS NOT NULL
    DROP PROCEDURE dwh.usp_update_gruz_operations_3days;
GO

CREATE PROCEDURE dwh.usp_update_gruz_operations_3days
    @cutoff_date DATE,
    @end_date DATE
AS
BEGIN
    SET NOCOUNT ON;
    PRINT '  Обновление raw_.gruz_operations...';

    -- Удаляем только за 3 дня
    DELETE FROM raw_.gruz_operations WHERE date_key >= @cutoff_date;

    -- Создаём временную таблицу для результатов процедуры
    IF OBJECT_ID('tempdb..#gruz_temp', 'U') IS NOT NULL DROP TABLE #gruz_temp;

    CREATE TABLE #gruz_temp (
        [user] NVARCHAR(100) COLLATE DATABASE_DEFAULT NOT NULL,
        [Разгрузка_механизмами] DECIMAL(18,2) NOT NULL DEFAULT 0,
        [Разгрузка_ручная] DECIMAL(18,2) NOT NULL DEFAULT 0,
        [Загрузка механизмами] DECIMAL(18,2) NOT NULL DEFAULT 0,
        [Загрузка ручная] DECIMAL(18,2) NOT NULL DEFAULT 0,
        [Сортировка товаров приемка] DECIMAL(18,2) NOT NULL DEFAULT 0,
        [Сортировка товаров отгрузка] DECIMAL(18,2) NOT NULL DEFAULT 0
    );

    -- Вызываем процедуру для расчета грузчиков
    INSERT INTO #gruz_temp
    EXEC raw_.eks_sdelka_gruz @cutoff_date, @end_date;

    -- Вставляем данные по дням
    INSERT INTO raw_.gruz_operations WITH (TABLOCK)
    SELECT
        LOWER(g.[user]) AS user_name,
        CAST(lm.date_time_stamp AS DATE) AS date_key,
        g.[Разгрузка_механизмами] / NULLIF(COUNT(DISTINCT CAST(lm.date_time_stamp AS DATE)), 0) AS [Разгрузка_механизмами],
        g.[Разгрузка_ручная] / NULLIF(COUNT(DISTINCT CAST(lm.date_time_stamp AS DATE)), 0) AS [Разгрузка_ручная],
        g.[Загрузка механизмами] / NULLIF(COUNT(DISTINCT CAST(lm.date_time_stamp AS DATE)), 0) AS [Загрузка механизмами],
        g.[Загрузка ручная] / NULLIF(COUNT(DISTINCT CAST(lm.date_time_stamp AS DATE)), 0) AS [Загрузка ручная],
        g.[Сортировка товаров приемка] / NULLIF(COUNT(DISTINCT CAST(lm.date_time_stamp AS DATE)), 0) AS [Сортировка товаров приемка],
        g.[Сортировка товаров отгрузка] / NULLIF(COUNT(DISTINCT CAST(lm.date_time_stamp AS DATE)), 0) AS [Сортировка товаров отгрузка]
    FROM #gruz_temp g
    JOIN raw_.labor_management lm WITH (NOLOCK) 
        ON LOWER(g.[user]) COLLATE DATABASE_DEFAULT = lm.USER_NAME COLLATE DATABASE_DEFAULT
    WHERE lm.user_def1 IN ('Receipt_doc', 'Shipping_doc')
      AND CAST(lm.date_time_stamp AS DATE) >= @cutoff_date
    GROUP BY LOWER(g.[user]), CAST(lm.date_time_stamp AS DATE),
        g.[Разгрузка_механизмами], g.[Разгрузка_ручная],
        g.[Загрузка механизмами], g.[Загрузка ручная],
        g.[Сортировка товаров приемка], g.[Сортировка товаров отгрузка];

    PRINT '  ✅ gruz_operations обновлён';
END;
GO

-- ============================================================================
-- ПРОЦЕДУРА 5: Обновление fact_operation (за 3 дня, БЕЗ TRUNCATE!)
-- ============================================================================
IF OBJECT_ID('dwh.usp_update_fact_operation_3days', 'P') IS NOT NULL
    DROP PROCEDURE dwh.usp_update_fact_operation_3days;
GO

CREATE PROCEDURE dwh.usp_update_fact_operation_3days
    @cutoff_date DATE
AS
BEGIN
    SET NOCOUNT ON;
    PRINT '  Обновление dwh.fact_operation...';

    -- Проверка таблицы
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'fact_operation' AND schema_id = SCHEMA_ID('dwh'))
    BEGIN
        PRINT '  ⚠️ Таблица dwh.fact_operation не найдена! Создаём...';
        
        CREATE TABLE dwh.fact_operation (
            date_key DATE NOT NULL,
            employee_id INT NOT NULL,
            work_type_id INT NOT NULL,
            reference_id NVARCHAR(25) NULL,
            reference_type NVARCHAR(25) NULL,
            start_time DATETIME2(0) NOT NULL,
            end_time DATETIME2(0) NOT NULL,
            duration_sec INT NOT NULL,
            price_per_op DECIMAL(18,2) NULL,
            is_order BIT NOT NULL,
            source_system NVARCHAR(20) NOT NULL
        );
        
        ALTER TABLE dwh.fact_operation 
            ADD CONSTRAINT FK_fact_operation_date FOREIGN KEY (date_key) REFERENCES dm.dim_date(date_key);
        ALTER TABLE dwh.fact_operation 
            ADD CONSTRAINT FK_fact_operation_employee FOREIGN KEY (employee_id) REFERENCES dm.dim_employee(employee_id);
        ALTER TABLE dwh.fact_operation 
            ADD CONSTRAINT FK_fact_operation_work_type FOREIGN KEY (work_type_id) REFERENCES dm.dim_work_type(work_type_id);
        
        PRINT '  ✅ Таблица создана';
    END

    -- ВАЖНО: Удаляем ТОЛЬКО за 3 дня (не TRUNCATE!)
    DELETE FROM dwh.fact_operation WHERE date_key >= @cutoff_date;

    -- 1. Простые операции из operations_enriched
    INSERT INTO dwh.fact_operation WITH (TABLOCK)
    SELECT
        CAST(o.START_DATE_TIME AS DATE) AS date_key,
        e.employee_id,
        wt.work_type_id,
        o.REFERENCE_ID,
        o.REFERENCE_TYPE,
        o.START_DATE_TIME,
        o.END_DATE_TIME,
        o.duration_sec,
        o.price_per_op,
        CASE WHEN o.REFERENCE_TYPE IN ('Клиент', 'Филиал', 'Ювелс') THEN 1 ELSE 0 END AS is_order,
        'WMS' AS source_system
    FROM dwh.operations_enriched o WITH (NOLOCK)
    JOIN dm.dim_employee e WITH (NOLOCK)
        ON o.user_name COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT AND e.is_active = 1
    JOIN dm.dim_work_type wt WITH (NOLOCK)
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

    PRINT '  ✅ Вставлено простых операций: ' + CAST(@@ROWCOUNT AS NVARCHAR);

    -- 2. Сложные отборы (pick_cache) с агрегацией
    IF OBJECT_ID('tempdb..#pick_groups', 'U') IS NOT NULL DROP TABLE #pick_groups;
    IF OBJECT_ID('tempdb..#pick_final', 'U') IS NOT NULL DROP TABLE #pick_final;

    SELECT
        PARENT_INSTR, ITEM, FROM_LOC, COMPLETED_BY_USER,
        MAX(END_DATE_TIME) AS max_end_time
    INTO #pick_groups
    FROM dwh.pick_cache WITH (NOLOCK)
    WHERE CAST(START_DATE_TIME AS DATE) >= @cutoff_date
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
        r.WORK_TYPE, r.REFERENCE_ID, r.REFERENCE_TYPE, r.PARENT_INSTR,
        r.ITEM, r.FROM_LOC, r.COMPLETED_BY_USER,
        MIN(r.START_DATE_TIME) AS start_time,
        g.max_end_time AS end_time,
        DATEDIFF(SECOND, MIN(r.START_DATE_TIME), g.max_end_time) AS duration_sec,
        COALESCE(sp.price, 0) AS price_per_op
    FROM #pick_groups g
    JOIN dwh.pick_cache r WITH (NOLOCK)
        ON g.PARENT_INSTR = r.PARENT_INSTR
        AND g.ITEM = r.ITEM
        AND g.FROM_LOC = r.FROM_LOC
        AND g.COMPLETED_BY_USER = r.COMPLETED_BY_USER
        AND g.max_end_time = r.END_DATE_TIME
    LEFT JOIN raw_.sdelka_price sp WITH (NOLOCK)
        ON r.WORK_TYPE COLLATE DATABASE_DEFAULT = sp.work_type COLLATE DATABASE_DEFAULT
    GROUP BY
        r.WORK_TYPE, r.REFERENCE_ID, r.REFERENCE_TYPE, r.PARENT_INSTR,
        r.ITEM, r.FROM_LOC, r.COMPLETED_BY_USER, g.max_end_time, sp.price;

    INSERT INTO dwh.fact_operation WITH (TABLOCK)
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
    JOIN dm.dim_employee e WITH (NOLOCK)
        ON p.COMPLETED_BY_USER COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT AND e.is_active = 1
    JOIN dm.dim_work_type wt WITH (NOLOCK)
        ON p.WORK_TYPE COLLATE DATABASE_DEFAULT = wt.work_type_name COLLATE DATABASE_DEFAULT;

    PRINT '  ✅ Вставлено сложных отборов: ' + CAST(@@ROWCOUNT AS NVARCHAR);

    -- 3. Размещения (placement_cache) с агрегацией
    IF OBJECT_ID('tempdb..#placement_groups', 'U') IS NOT NULL DROP TABLE #placement_groups;
    IF OBJECT_ID('tempdb..#placement_final', 'U') IS NOT NULL DROP TABLE #placement_final;

    SELECT REFERENCE_ID, REFERENCE_TYPE, ITEM, TO_LOC, MAX(END_DATE_TIME) AS max_end_time
    INTO #placement_groups
    FROM dwh.placement_cache WITH (NOLOCK)
    WHERE CAST(START_DATE_TIME AS DATE) >= @cutoff_date
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
        r.WORK_TYPE, g.REFERENCE_ID, g.REFERENCE_TYPE, g.ITEM, g.TO_LOC,
        r.COMPLETED_BY_USER,
        MIN(r.START_DATE_TIME) AS start_time,
        g.max_end_time AS end_time,
        DATEDIFF(SECOND, MIN(r.START_DATE_TIME), g.max_end_time) AS duration_sec,
        COALESCE(sp.price, 0) AS price_per_op
    FROM #placement_groups g
    JOIN dwh.placement_cache r WITH (NOLOCK)
        ON g.REFERENCE_ID = r.REFERENCE_ID
        AND g.ITEM = r.ITEM
        AND g.TO_LOC = r.TO_LOC
        AND g.max_end_time = r.END_DATE_TIME
    LEFT JOIN raw_.sdelka_price sp WITH (NOLOCK)
        ON r.WORK_TYPE COLLATE DATABASE_DEFAULT = sp.work_type COLLATE DATABASE_DEFAULT
    GROUP BY
        r.WORK_TYPE, g.REFERENCE_ID, g.REFERENCE_TYPE, g.ITEM, g.TO_LOC,
        r.COMPLETED_BY_USER, g.max_end_time, sp.price;

    INSERT INTO dwh.fact_operation WITH (TABLOCK)
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
    JOIN dm.dim_employee e WITH (NOLOCK)
        ON p.COMPLETED_BY_USER COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT AND e.is_active = 1
    JOIN dm.dim_work_type wt WITH (NOLOCK)
        ON p.WORK_TYPE COLLATE DATABASE_DEFAULT = wt.work_type_name COLLATE DATABASE_DEFAULT;

    PRINT '  ✅ Вставлено размещений: ' + CAST(@@ROWCOUNT AS NVARCHAR);

    -- 4. Приемка и перемер
    INSERT INTO dwh.fact_operation WITH (TABLOCK)
    SELECT
        fe.date AS date_key,
        e.employee_id,
        wt.work_type_id,
        NULL AS reference_id,
        'Приемка' AS reference_type,
        fe.START_DATE_TIME,
        fe.END_DATE_TIME,
        fe.duration_sec,
        fe.price_per_op,
        0 AS is_order,
        'WMS' AS source_system
    FROM dwh.operations_enriched fe WITH (NOLOCK)
    JOIN dm.dim_employee e WITH (NOLOCK)
        ON fe.user_name COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT AND e.is_active = 1
    JOIN dm.dim_work_type wt WITH (NOLOCK)
        ON fe.WORK_TYPE COLLATE DATABASE_DEFAULT = wt.work_type_name COLLATE DATABASE_DEFAULT
    WHERE fe.WORK_TYPE IN (N'Приемка', N'Приемка WH2', N'Перемер ZX KPP', N'Перемер с прихода')
      AND fe.date >= @cutoff_date;

    PRINT '  ✅ Вставлено приемки/перемера: ' + CAST(@@ROWCOUNT AS NVARCHAR);

    -- 5. Грузчики (из raw_.gruz_operations)
    -- Разгрузка механизмами
    INSERT INTO dwh.fact_operation WITH (TABLOCK)
    SELECT
        g.date_key,
        e.employee_id,
        wt.work_type_id,
        NULL, 'Разгрузка механизмами',
        MIN(lm.date_time_stamp), MAX(lm.date_time_stamp),
        DATEDIFF(SECOND, MIN(lm.date_time_stamp), MAX(lm.date_time_stamp)),
        g.[Разгрузка_механизмами] * 22.50,
        0, 'GRUZ'
    FROM raw_.gruz_operations g WITH (NOLOCK)
    JOIN dm.dim_employee e WITH (NOLOCK) 
        ON g.user_name COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT AND e.is_active = 1
    JOIN dm.dim_work_type wt WITH (NOLOCK) 
        ON wt.work_type_name = N'Разгрузка механизмами'
    JOIN raw_.labor_management lm WITH (NOLOCK) 
        ON g.user_name COLLATE DATABASE_DEFAULT = lm.USER_NAME COLLATE DATABASE_DEFAULT
        AND lm.user_def1 = 'Receipt_doc'
        AND lm.activity_type = N'Разгрузка механизмами'
        AND CAST(lm.date_time_stamp AS DATE) = g.date_key
    WHERE g.[Разгрузка_механизмами] > 0 AND g.date_key >= @cutoff_date
    GROUP BY g.date_key, e.employee_id, wt.work_type_id, g.[Разгрузка_механизмами], g.user_name;

    -- Разгрузка ручная
    INSERT INTO dwh.fact_operation WITH (TABLOCK)
    SELECT
        g.date_key, e.employee_id, wt.work_type_id,
        NULL, 'Разгрузка ручная',
        MIN(lm.date_time_stamp), MAX(lm.date_time_stamp),
        DATEDIFF(SECOND, MIN(lm.date_time_stamp), MAX(lm.date_time_stamp)),
        g.[Разгрузка_ручная] * 22.50, 0, 'GRUZ'
    FROM raw_.gruz_operations g WITH (NOLOCK)
    JOIN dm.dim_employee e WITH (NOLOCK) 
        ON g.user_name COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT AND e.is_active = 1
    JOIN dm.dim_work_type wt WITH (NOLOCK) 
        ON wt.work_type_name = N'Разгрузка ручная'
    JOIN raw_.labor_management lm WITH (NOLOCK) 
        ON g.user_name COLLATE DATABASE_DEFAULT = lm.USER_NAME COLLATE DATABASE_DEFAULT
        AND lm.user_def1 = 'Receipt_doc'
        AND lm.activity_type = N'Разгрузка ручная'
        AND CAST(lm.date_time_stamp AS DATE) = g.date_key
    WHERE g.[Разгрузка_ручная] > 0 AND g.date_key >= @cutoff_date
    GROUP BY g.date_key, e.employee_id, wt.work_type_id, g.[Разгрузка_ручная], g.user_name;

    -- Загрузка механизмами
    INSERT INTO dwh.fact_operation WITH (TABLOCK)
    SELECT
        g.date_key, e.employee_id, wt.work_type_id,
        NULL, 'Загрузка механизмами',
        MIN(lm.date_time_stamp), MAX(lm.date_time_stamp),
        DATEDIFF(SECOND, MIN(lm.date_time_stamp), MAX(lm.date_time_stamp)),
        g.[Загрузка механизмами] * 68.40, 0, 'GRUZ'
    FROM raw_.gruz_operations g WITH (NOLOCK)
    JOIN dm.dim_employee e WITH (NOLOCK) 
        ON g.user_name COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT AND e.is_active = 1
    JOIN dm.dim_work_type wt WITH (NOLOCK) 
        ON wt.work_type_name = N'Загрузка механизмами'
    JOIN raw_.labor_management lm WITH (NOLOCK) 
        ON g.user_name COLLATE DATABASE_DEFAULT = lm.USER_NAME COLLATE DATABASE_DEFAULT
        AND lm.user_def1 = 'Shipping_doc'
        AND lm.activity_type = N'Загрузка механизмами'
        AND CAST(lm.date_time_stamp AS DATE) = g.date_key
    WHERE g.[Загрузка механизмами] > 0 AND g.date_key >= @cutoff_date
    GROUP BY g.date_key, e.employee_id, wt.work_type_id, g.[Загрузка механизмами], g.user_name;

    -- Загрузка ручная
    INSERT INTO dwh.fact_operation WITH (TABLOCK)
    SELECT
        g.date_key, e.employee_id, wt.work_type_id,
        NULL, 'Загрузка ручная',
        MIN(lm.date_time_stamp), MAX(lm.date_time_stamp),
        DATEDIFF(SECOND, MIN(lm.date_time_stamp), MAX(lm.date_time_stamp)),
        g.[Загрузка ручная] * 68.40, 0, 'GRUZ'
    FROM raw_.gruz_operations g WITH (NOLOCK)
    JOIN dm.dim_employee e WITH (NOLOCK) 
        ON g.user_name COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT AND e.is_active = 1
    JOIN dm.dim_work_type wt WITH (NOLOCK) 
        ON wt.work_type_name = N'Загрузка ручная'
    JOIN raw_.labor_management lm WITH (NOLOCK) 
        ON g.user_name COLLATE DATABASE_DEFAULT = lm.USER_NAME COLLATE DATABASE_DEFAULT
        AND lm.user_def1 = 'Shipping_doc'
        AND lm.activity_type <> N'Загрузка механизмами'
        AND CAST(lm.date_time_stamp AS DATE) = g.date_key
    WHERE g.[Загрузка ручная] > 0 AND g.date_key >= @cutoff_date
    GROUP BY g.date_key, e.employee_id, wt.work_type_id, g.[Загрузка ручная], g.user_name;

    PRINT '  ✅ Вставлено грузчиков';
    PRINT '  ✅ fact_operation обновлена';
END;
GO

-- ============================================================================
-- ПРОЦЕДУРА 6: Обновление fact_penalty (за 3 дня, БЕЗ TRUNCATE!)
-- ============================================================================
IF OBJECT_ID('dwh.usp_update_fact_penalty_3days', 'P') IS NOT NULL
    DROP PROCEDURE dwh.usp_update_fact_penalty_3days;
GO

CREATE PROCEDURE dwh.usp_update_fact_penalty_3days
    @cutoff_date DATE
AS
BEGIN
    SET NOCOUNT ON;
    PRINT '  Обновление dwh.fact_penalty...';

    -- Проверка таблицы
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'fact_penalty' AND schema_id = SCHEMA_ID('dwh'))
    BEGIN
        PRINT '  ⚠️ Таблица dwh.fact_penalty не найдена! Создаём...';
        
        CREATE TABLE dwh.fact_penalty (
            date_key DATE NOT NULL,
            employee_id INT NOT NULL,
            penalty_id INT IDENTITY(1,1) PRIMARY KEY,
            reference_id NVARCHAR(50) NULL,
            fine_category NVARCHAR(100) NOT NULL,
            fine_amount DECIMAL(18,2) NOT NULL,
            comment NVARCHAR(500) NULL,
            source_system NVARCHAR(20) NOT NULL DEFAULT 'SHTRAF'
        );
        
        ALTER TABLE dwh.fact_penalty 
            ADD CONSTRAINT FK_fact_penalty_date FOREIGN KEY (date_key) REFERENCES dm.dim_date(date_key);
        ALTER TABLE dwh.fact_penalty 
            ADD CONSTRAINT FK_fact_penalty_employee FOREIGN KEY (employee_id) REFERENCES dm.dim_employee(employee_id);
        
        PRINT '  ✅ Таблица создана';
    END

    -- ВАЖНО: Удаляем ТОЛЬКО за 3 дня (не TRUNCATE!)
    DELETE FROM dwh.fact_penalty WHERE date_key >= @cutoff_date;

    -- Вставляем новые данные из fines_enriched
    INSERT INTO dwh.fact_penalty WITH (TABLOCK)
    SELECT
        fe.date AS date_key,
        e.employee_id,
        fe.reference_id,
        fe.fine_category,
        fe.fine_amount,
        fe.comment,
        'SHTRAF' AS source_system
    FROM dwh.fines_enriched fe WITH (NOLOCK)
    JOIN dm.dim_employee e WITH (NOLOCK)
        ON fe.user_name COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT AND e.is_active = 1
    WHERE fe.date >= @cutoff_date;

    PRINT '  ✅ fact_penalty обновлена. Вставлено: ' + CAST(@@ROWCOUNT AS NVARCHAR);
END;
GO

-- ============================================================================
-- ПРОЦЕДУРА 7: Обновление placement_operations (за 3 дня)
-- ============================================================================
IF OBJECT_ID('dwh.usp_update_placement_operations_3days', 'P') IS NOT NULL
    DROP PROCEDURE dwh.usp_update_placement_operations_3days;
GO

CREATE PROCEDURE dwh.usp_update_placement_operations_3days
    @cutoff_date DATE
AS
BEGIN
    SET NOCOUNT ON;
    PRINT '  Обновление dwh.placement_operations...';

    DELETE FROM dwh.placement_operations WHERE date >= @cutoff_date;

    INSERT INTO dwh.placement_operations WITH (TABLOCK)
    SELECT
        w.REFERENCE_ID, w.REFERENCE_TYPE, w.WORK_TYPE,
        w.USER_STAMP AS user_name,
        w.START_DATE_TIME, w.END_DATE_TIME, w.LOCATING_ZONE,
        CAST(w.START_DATE_TIME AS DATE) AS date,
        i.ITEM_CATEGORY9,
        u.fio, u.smena, u.position
    FROM raw_.WORK_INSTRUCTION_VIEW2 w WITH (NOLOCK)
    LEFT JOIN raw_.ITEM i WITH (NOLOCK)
        ON w.ITEM COLLATE DATABASE_DEFAULT = i.ITEM COLLATE DATABASE_DEFAULT
    LEFT JOIN raw_.USER_CADR_EDIT u WITH (NOLOCK)
        ON w.USER_STAMP COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT AND u.deleted = 0
    WHERE
        w.WORK_TYPE = N'Размещение КС'
        AND w.INSTRUCTION_TYPE = 'Detail'
        AND w.START_DATE_TIME IS NOT NULL
        AND w.END_DATE_TIME IS NOT NULL
        AND CAST(w.START_DATE_TIME AS DATE) >= @cutoff_date;

    PRINT '  ✅ placement_operations обновлена';
END;
GO

-- ============================================================================
-- ПРОЦЕДУРА 8: Обновление order_accuracy_daily (за 3 дня)
-- ============================================================================
IF OBJECT_ID('dwh.usp_update_order_accuracy_daily_3days', 'P') IS NOT NULL
    DROP PROCEDURE dwh.usp_update_order_accuracy_daily_3days;
GO

CREATE PROCEDURE dwh.usp_update_order_accuracy_daily_3days
    @cutoff_date DATE
AS
BEGIN
    SET NOCOUNT ON;
    PRINT '  Обновление dwh.order_accuracy_daily...';

    DELETE FROM dwh.order_accuracy_daily WHERE date >= @cutoff_date;

    INSERT INTO dwh.order_accuracy_daily WITH (TABLOCK)
    SELECT
        CAST(w.DATE_TIME_STAMP AS DATE) AS date,
        COUNT(*) AS total_assembled,
        SUM(CASE WHEN s.reference_id IS NOT NULL THEN 1 ELSE 0 END) AS error_count,
        COUNT(*) - SUM(CASE WHEN s.reference_id IS NOT NULL THEN 1 ELSE 0 END) AS correct_count,
        CAST(
            (COUNT(*) - SUM(CASE WHEN s.reference_id IS NOT NULL THEN 1 ELSE 0 END)) * 100.0 / COUNT(*)
            AS DECIMAL(5,2)
        ) AS accuracy_pct
    FROM raw_.WORK_INSTRUCTION_VIEW2 w WITH (NOLOCK)
    LEFT JOIN raw_.Shtraf_Edit s WITH (NOLOCK)
        ON w.REFERENCE_ID = s.reference_id COLLATE DATABASE_DEFAULT
        AND s.name IN (N'Штраф по претензии', N'Недобор', N'Излишки', N'Некомплект')
    WHERE 
        w.INSTRUCTION_TYPE = 'Detail'
        AND CAST(w.DATE_TIME_STAMP AS DATE) >= @cutoff_date
    GROUP BY CAST(w.DATE_TIME_STAMP AS DATE);

    PRINT '  ✅ order_accuracy_daily обновлена';
END;
GO

-- ============================================================================
-- ПРОЦЕДУРА 9: Пропущено (rejected_lines_detail обновляется отдельно)
-- ============================================================================
-- dwh.usp_update_rejected_lines_detail_3days - УДАЛЕНА
-- Обновление dwh.rejected_lines_detail выполняется через:
-- - скрипт update_rejected_lines.py (каждые 5 минут)
-- - прямой запрос к ILS.dbo.SHIPMENT_DETAIL
-- ============================================================================

-- ============================================================================
-- ПРОЦЕДУРА 10: Обновление orders_timeliness (за 3 дня)
-- ============================================================================
IF OBJECT_ID('dwh.usp_update_orders_timeliness_3days', 'P') IS NOT NULL
    DROP PROCEDURE dwh.usp_update_orders_timeliness_3days;
GO

CREATE PROCEDURE dwh.usp_update_orders_timeliness_3days
    @cutoff_date DATE
AS
BEGIN
    SET NOCOUNT ON;
    PRINT '  Обновление dwh.orders_timeliness...';

    DELETE FROM dwh.orders_timeliness WHERE date >= @cutoff_date;

    WITH filtered_ops AS (
        SELECT
            INTERNAL_NUM, REFERENCE_ID, REFERENCE_TYPE,
            START_DATE_TIME, END_DATE_TIME,
            DATEDIFF(SECOND, START_DATE_TIME, END_DATE_TIME) AS duration_sec,
            COMPLETED_BY_USER,
            ROW_NUMBER() OVER (PARTITION BY INTERNAL_NUM ORDER BY END_DATE_TIME DESC) AS rn
        FROM raw_.WORK_INSTRUCTION_VIEW2 WITH (NOLOCK)
        WHERE
            INSTRUCTION_TYPE = 'Detail'
            AND REFERENCE_TYPE IN ('Клиент', 'Филиал', 'Ювелс')
            AND START_DATE_TIME IS NOT NULL
            AND END_DATE_TIME IS NOT NULL
            AND INTERNAL_NUM IS NOT NULL
            AND CAST(START_DATE_TIME AS DATE) >= @cutoff_date
    ),
    latest_ops AS (
        SELECT * FROM filtered_ops WHERE rn = 1
    )
    INSERT INTO dwh.orders_timeliness WITH (TABLOCK)
    SELECT
        s.SHIPMENT_ID, s.ORDER_TYPE, s.STOP, s.ERP_ORDER, s.ROUTING_CODE,
        s.SHIP_TO_CITY, o.COMPLETED_BY_USER, u.fio, u.smena,
        o.START_DATE_TIME, o.END_DATE_TIME, o.duration_sec,
        CASE
            WHEN o.END_DATE_TIME <= TRY_CAST(s.STOP AS DATETIME2(0)) THEN 'Вовремя'
            ELSE 'Просрочено'
        END AS timeliness_status,
        CAST(o.START_DATE_TIME AS DATE) AS date,
        s.INTERNAL_SHIPMENT_NUM
    FROM raw_.SHIPMENT_HEADER s WITH (NOLOCK)
    JOIN latest_ops o ON s.INTERNAL_SHIPMENT_NUM = o.INTERNAL_NUM
    LEFT JOIN raw_.USER_CADR_EDIT u WITH (NOLOCK)
        ON o.COMPLETED_BY_USER COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT AND u.deleted = 0
    WHERE s.STOP IS NOT NULL;

    PRINT '  ✅ orders_timeliness обновлена';
END;
GO

-- ============================================================================
-- ПРОЦЕДУРА 11: Обновление fact_hourly_errors (за 3 дня)
-- ============================================================================
IF OBJECT_ID('dwh.usp_update_fact_hourly_errors_3days', 'P') IS NOT NULL
    DROP PROCEDURE dwh.usp_update_fact_hourly_errors_3days;
GO

CREATE PROCEDURE dwh.usp_update_fact_hourly_errors_3days
    @cutoff_date DATE
AS
BEGIN
    SET NOCOUNT ON;
    PRINT '  Обновление dwh.fact_hourly_errors...';

    DELETE FROM dwh.fact_hourly_errors;

    WITH error_orders AS (
        SELECT
            DATEPART(HOUR, o.START_DATE_TIME) AS hour,
            COUNT(DISTINCT se.reference_id) AS error_orders
        FROM dwh.orders_timeliness o WITH (NOLOCK)
        JOIN raw_.Shtraf_Edit se WITH (NOLOCK)
            ON o.SHIPMENT_ID = se.reference_id COLLATE DATABASE_DEFAULT
            AND se.name IN (N'Штраф по претензии', N'Недобор', N'Излишки', N'Недокомплект')
        WHERE o.date >= @cutoff_date
        GROUP BY DATEPART(HOUR, o.START_DATE_TIME)
    ),
    all_orders_by_hour AS (
        SELECT
            DATEPART(HOUR, START_DATE_TIME) AS hour,
            COUNT(DISTINCT SHIPMENT_ID) AS total_orders
        FROM dwh.orders_timeliness WITH (NOLOCK)
        WHERE date >= @cutoff_date
        GROUP BY DATEPART(HOUR, START_DATE_TIME)
    )
    INSERT INTO dwh.fact_hourly_errors WITH (TABLOCK)
    SELECT
        t.hour, t.total_orders,
        COALESCE(e.error_orders, 0) AS error_orders,
        CAST(COALESCE(e.error_orders, 0) * 100.0 / NULLIF(t.total_orders, 0) AS DECIMAL(5,2)) AS pct_errors
    FROM all_orders_by_hour t
    LEFT JOIN error_orders e ON t.hour = e.hour
    WHERE COALESCE(e.error_orders, 0) > 0;

    PRINT '  ✅ fact_hourly_errors обновлена';
END;
GO

-- ============================================================================
-- ПРОЦЕДУРА 12: Обновление fact_hourly_delays (за 3 дня)
-- ============================================================================
IF OBJECT_ID('dwh.usp_update_fact_hourly_delays_3days', 'P') IS NOT NULL
    DROP PROCEDURE dwh.usp_update_fact_hourly_delays_3days;
GO

CREATE PROCEDURE dwh.usp_update_fact_hourly_delays_3days
    @cutoff_date DATE
AS
BEGIN
    SET NOCOUNT ON;
    PRINT '  Обновление dwh.fact_hourly_delays...';

    DELETE FROM dwh.fact_hourly_delays;

    WITH hourly_stats AS (
        SELECT
            DATEPART(HOUR, START_DATE_TIME) AS hour,
            COUNT(*) AS total_orders,
            SUM(CASE WHEN timeliness_status = 'Просрочено' THEN 1 ELSE 0 END) AS delayed_orders
        FROM dwh.orders_timeliness WITH (NOLOCK)
        WHERE ORDER_TYPE = 'Клиент' AND date >= @cutoff_date
        GROUP BY DATEPART(HOUR, START_DATE_TIME)
    )
    INSERT INTO dwh.fact_hourly_delays WITH (TABLOCK)
    SELECT
        hour, total_orders, delayed_orders,
        CAST(delayed_orders * 100.0 / NULLIF(total_orders, 0) AS DECIMAL(5,2)) AS pct_delayed
    FROM hourly_stats;

    PRINT '  ✅ fact_hourly_delays обновлена';
END;
GO

-- ============================================================================
-- ПРОЦЕДУРА 13: Обновление employee_work_idle_summary (за 3 дня)
-- ============================================================================
IF OBJECT_ID('dm.usp_update_employee_work_idle_summary_3days', 'P') IS NOT NULL
    DROP PROCEDURE dm.usp_update_employee_work_idle_summary_3days;
GO

CREATE PROCEDURE dm.usp_update_employee_work_idle_summary_3days
    @cutoff_date DATE
AS
BEGIN
    SET NOCOUNT ON;
    PRINT '  Обновление dm.employee_work_idle_summary...';

    -- Проверяем существование таблицы
    IF OBJECT_ID('dm.employee_work_idle_summary', 'U') IS NULL
    BEGIN
        PRINT '  ⚠️ Таблица dm.employee_work_idle_summary не найдена! Создаём...';
        
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
        
        PRINT '  ✅ Таблица создана';
    END

    -- Удаляем только за 3 дня
    DELETE FROM dm.employee_work_idle_summary WHERE date_key >= @cutoff_date;

    -- Вставляем новые данные
    WITH unique_ops AS (
        SELECT DISTINCT
            LOWER(th.USER_STAMP) COLLATE DATABASE_DEFAULT AS user_name,
            CAST(th.DATE_TIME_STAMP AS DATE) AS date_key,
            th.DATE_TIME_STAMP AS op_time
        FROM raw_.TRANSACTION_HISTORY th WITH (NOLOCK)
        WHERE
            th.DATE_TIME_STAMP IS NOT NULL
            AND th.USER_STAMP IS NOT NULL
            AND CAST(th.DATE_TIME_STAMP AS DATE) >= @cutoff_date
    ),
    numbered_ops AS (
        SELECT
            user_name, date_key, op_time,
            ROW_NUMBER() OVER (PARTITION BY user_name, date_key ORDER BY op_time) AS rn
        FROM unique_ops
    ),
    daily_bounds AS (
        SELECT
            user_name, date_key,
            MIN(op_time) AS first_op_time,
            MAX(op_time) AS last_op_time
        FROM unique_ops
        GROUP BY user_name, date_key
    ),
    idle_gaps AS (
        SELECT
            curr.user_name, curr.date_key,
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
            user_name, date_key,
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
            db.user_name, db.date_key,
            db.first_op_time, db.last_op_time,
            DATEDIFF(MINUTE, db.first_op_time, db.last_op_time) AS total_period_min,
            COALESCE(idle.total_idle_min, 0) AS total_idle_min,
            COALESCE(idle.idle_10_20, 0) AS idle_10_20,
            COALESCE(idle.idle_20_30, 0) AS idle_20_30,
            COALESCE(idle.idle_30_60, 0) AS idle_30_60,
            COALESCE(idle.idle_60plus, 0) AS idle_60plus,
            uce.fio
        FROM daily_bounds db
        LEFT JOIN idle_summary idle
            ON db.user_name = idle.user_name AND db.date_key = idle.date_key
        LEFT JOIN (
            SELECT DISTINCT
                LOWER(user_name) COLLATE DATABASE_DEFAULT AS user_name,
                FIRST_VALUE(fio) OVER (PARTITION BY LOWER(user_name) ORDER BY deleted, user_name) AS fio
            FROM raw_.USER_CADR_EDIT WITH (NOLOCK)
            WHERE user_name IS NOT NULL
        ) uce ON db.user_name COLLATE DATABASE_DEFAULT = uce.user_name COLLATE DATABASE_DEFAULT
    )
    INSERT INTO dm.employee_work_idle_summary WITH (TABLOCK)
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
        idle_10_20, idle_20_30, idle_30_60, idle_60plus
    FROM employee_data;

    PRINT '  ✅ employee_work_idle_summary обновлена';
END;
GO

PRINT '';
PRINT '=== ВСЕ ПРОЦЕДУРЫ СОЗДАНЫ ===';
PRINT 'Список процедур:';
PRINT '  dm.usp_update_dim_employee_3days';
PRINT '  dm.usp_update_dim_work_type_3days';
PRINT '  dwh.usp_update_transaction_events_3days';
PRINT '  dwh.usp_update_gruz_operations_3days';
PRINT '  dwh.usp_update_fact_operation_3days';
PRINT '  dwh.usp_update_fact_penalty_3days';
PRINT '  dwh.usp_update_placement_operations_3days';
PRINT '  dwh.usp_update_order_accuracy_daily_3days';
PRINT '  dwh.usp_update_rejected_lines_detail_3days - УДАЛЕНА (обновляется отдельно)';
PRINT '  dwh.usp_update_orders_timeliness_3days';
PRINT '  dwh.usp_update_fact_hourly_errors_3days';
PRINT '  dwh.usp_update_fact_hourly_delays_3days';
PRINT '  dm.usp_update_employee_work_idle_summary_3days';
