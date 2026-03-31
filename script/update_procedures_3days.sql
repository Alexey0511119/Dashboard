-- ============================================================================
-- УПРОЩЁННЫЕ ПРОЦЕДУРЫ ДЛЯ 3-ДНЕВНОГО ОБНОВЛЕНИЯ
-- Без подзапросов, которые вызывают ошибки в pymssql
-- ============================================================================
USE olap2_fixed;
GO

-- ============================================================================
-- ПРОЦЕДУРА 1: Обновление dim_employee (UPSERT)
-- ============================================================================
IF OBJECT_ID('dm.usp_update_dim_employee_3days') IS NOT NULL
    DROP PROCEDURE dm.usp_update_dim_employee_3days;
GO

CREATE PROCEDURE dm.usp_update_dim_employee_3days
AS
BEGIN
    SET NOCOUNT ON;
    
    PRINT 'Обновление dm.dim_employee...';
    
    -- 1. Помечаем устаревших как неактивных
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
        SELECT 1 
        FROM dm.dim_employee de 
        WHERE LOWER(de.user_name) = LOWER(u.user_name) 
        AND de.is_active = 1
    );
    
    -- 3. Обновляем существующих
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
    
    PRINT '✅ dim_employee обновлён';
END;
GO

-- ============================================================================
-- ПРОЦЕДУРА 2: Обновление dim_work_type (MERGE)
-- ============================================================================
IF OBJECT_ID('dm.usp_update_dim_work_type_3days') IS NOT NULL
    DROP PROCEDURE dm.usp_update_dim_work_type_3days;
GO

CREATE PROCEDURE dm.usp_update_dim_work_type_3days
AS
BEGIN
    SET NOCOUNT ON;
    
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
                ELSE 'Прочее'
            END,
            CASE 
                WHEN source.work_type LIKE '%Ревизия%' THEN 3
                WHEN source.work_type LIKE '%Размещение%' THEN 2
                WHEN source.work_type LIKE '%Отбор%' THEN 2
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
    
    PRINT '✅ dim_work_type обновлён';
END;
GO

-- ============================================================================
-- ПРОЦЕДУРА 3: Обновление fact_operation (через временные таблицы)
-- ============================================================================
IF OBJECT_ID('dwh.usp_update_fact_operation_3days') IS NOT NULL
    DROP PROCEDURE dwh.usp_update_fact_operation_3days;
GO

CREATE PROCEDURE dwh.usp_update_fact_operation_3days
    @cutoff_date DATE
AS
BEGIN
    SET NOCOUNT ON;
    
    PRINT 'Обновление dwh.fact_operation...';
    
    -- Проверяем, существует ли таблица
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
        
        PRINT '  ✅ Таблица создана';
    END
    
    -- Очищаем старые таблицы если остались
    DROP TABLE IF EXISTS dwh.fact_operation_old;
    DROP TABLE IF EXISTS dwh.fact_operation_tmp;
    
    -- Сохраняем старые данные (за пределами 3 дней)
    SELECT * INTO dwh.fact_operation_tmp
    FROM dwh.fact_operation
    WHERE date_key < @cutoff_date;
    
    -- Вставляем новые данные (здесь будет ваша логика из update_dwh_3days.sql)
    -- ... (добавите INSERT из основного скрипта)
    
    -- SWAP
    EXEC sp_rename 'dwh.fact_operation', 'fact_operation_old';
    EXEC sp_rename 'dwh.fact_operation_tmp', 'fact_operation';
    
    -- Удаляем старую
    DROP TABLE IF EXISTS dwh.fact_operation_old;
    
    PRINT '✅ fact_operation обновлена';
END;
GO

PRINT '=== ПРОЦЕДУРЫ СОЗДАНЫ ===';
PRINT 'Вызывайте через: EXEC dm.usp_update_dim_employee_3days()';
PRINT '                  EXEC dm.usp_update_dim_work_type_3days()';
PRINT '                  EXEC dwh.usp_update_fact_operation_3days(@cutoff_date)';
