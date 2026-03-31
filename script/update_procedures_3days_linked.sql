-- ============================================================================
-- ПРОЦЕДУРЫ ДЛЯ 3-ДНЕВНОГО ОБНОВЛЕНИЯ ЧЕРЕЗ LINKED SERVER
-- Сервер аналитики: 10.7.0.27 (olap2_fixed)
-- Сервер источник: 10.7.0.248 (ils, sk)
-- ============================================================================

USE olap2_fixed;
GO

PRINT '=== СОЗДАНИЕ ПРОЦЕДУР 3-ДНЕВНОГО ОБНОВЛЕНИЯ (LINKED SERVER) ===';

-- ============================================================================
-- ПРОЦЕДУРА 1: Обновление fact_operation (за 3 дня, через Linked Server)
-- ============================================================================
IF OBJECT_ID('dwh.usp_update_fact_operation_3days_linked', 'P') IS NOT NULL
    DROP PROCEDURE dwh.usp_update_fact_operation_3days_linked;
GO

CREATE PROCEDURE dwh.usp_update_fact_operation_3days_linked
    @cutoff_date DATE
AS
BEGIN
    SET NOCOUNT ON;
    PRINT '  🔄 Обновление dwh.fact_operation...';

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
    LEFT JOIN ILS_SOURCE.ils.dbo.sdelka_price sp WITH (NOLOCK)
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
    LEFT JOIN ILS_SOURCE.ils.dbo.sdelka_price sp WITH (NOLOCK)
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
    PRINT '  ✅ fact_operation обновлена';
END;
GO

-- ============================================================================
-- ПРОЦЕДУРА 2: Обновление fact_penalty (за 3 дня, через Linked Server)
-- ============================================================================
IF OBJECT_ID('dwh.usp_update_fact_penalty_3days_linked', 'P') IS NOT NULL
    DROP PROCEDURE dwh.usp_update_fact_penalty_3days_linked;
GO

CREATE PROCEDURE dwh.usp_update_fact_penalty_3days_linked
    @cutoff_date DATE
AS
BEGIN
    SET NOCOUNT ON;
    PRINT '  🔄 Обновление dwh.fact_penalty...';

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

    -- Вставляем новые данные из Shtraf_Edit
    INSERT INTO dwh.fact_penalty WITH (TABLOCK)
    SELECT
        TRY_CAST(f.date_time_stamp AS DATE) AS date_key,
        e.employee_id,
        f.reference_id,
        f.name AS fine_category,
        CAST(f.price AS DECIMAL(18,2)) AS fine_amount,
        CAST(NULL AS NVARCHAR(500)) AS comment,
        'SHTRAF' AS source_system
    FROM SK_SOURCE.sk.dbo.Shtraf_Edit f WITH (NOLOCK)
    JOIN dm.dim_employee e WITH (NOLOCK)
        ON f.[user] COLLATE DATABASE_DEFAULT = e.user_name COLLATE DATABASE_DEFAULT AND e.is_active = 1
    WHERE
        f.date_time_stamp IS NOT NULL
        AND f.[user] IS NOT NULL
        AND TRY_CAST(f.date_time_stamp AS DATE) >= @cutoff_date;

    PRINT '  ✅ Вставлено штрафов: ' + CAST(@@ROWCOUNT AS NVARCHAR);
    PRINT '  ✅ fact_penalty обновлена';
END;
GO

PRINT '=== ПРОЦЕДУРЫ СОЗДАНЫ ===';
GO
