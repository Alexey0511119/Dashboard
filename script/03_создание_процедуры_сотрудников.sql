-- ============================================================================
-- ЧАСТЬ 3: СОЗДАНИЕ ПРОЦЕДУРЫ dm.usp_update_employees_on_shift_raw
-- Схема: dm (olap2_fixed)
-- Источник: TRANSACTION_HISTORY (DATE_TIME_STAMP, USER_NAME)
-- ============================================================================

IF OBJECT_ID('dm.usp_update_employees_on_shift_raw', 'P') IS NOT NULL
    DROP PROCEDURE dm.usp_update_employees_on_shift_raw;

CREATE PROCEDURE dm.usp_update_employees_on_shift_raw
    @target_date DATE,
    @target_smena NVARCHAR(10)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @source_data TABLE (
        date_key DATE,
        smena NVARCHAR(10),
        user_name NVARCHAR(255),
        fio NVARCHAR(500),
        brigada NVARCHAR(100),
        position NVARCHAR(255),
        first_operation_time DATETIME,
        total_operations INT
    );

    INSERT INTO @source_data
    SELECT
        @target_date,
        @target_smena,
        th.USER_NAME,
        uce.fio,
        uce.brigada,
        uce.position,
        MIN(th.DATE_TIME_STAMP),
        COUNT(*)
    FROM TRANSACTION_HISTORY th
    INNER JOIN USER_CADR_EDIT uce
        ON th.USER_NAME = uce.user_name
    WHERE
        CAST(th.DATE_TIME_STAMP AS DATE) = @target_date
        AND uce.smena = @target_smena
        AND uce.deleted = 'False'
        AND uce.brigada IS NOT NULL 
        AND uce.brigada != ''
        AND uce.position IS NOT NULL
        AND uce.position != ''
    GROUP BY
        th.USER_NAME,
        uce.fio,
        uce.brigada,
        uce.position;

    MERGE dm.employees_on_shift_raw AS target
    USING @source_data AS source
    ON (target.user_name = source.user_name
        AND target.date_key = source.date_key
        AND target.smena = source.smena)
    WHEN MATCHED THEN
        UPDATE SET
            target.fio = source.fio,
            target.brigada = source.brigada,
            target.position = source.position,
            target.first_operation_time = source.first_operation_time,
            target.total_operations = source.total_operations,
            target.updated_at = GETDATE()
    WHEN NOT MATCHED THEN
        INSERT (date_key, smena, user_name, fio, brigada, position, first_operation_time, total_operations)
        VALUES (source.date_key, source.smena, source.user_name, source.fio, source.brigada, source.position, source.first_operation_time, source.total_operations)
    WHEN NOT MATCHED BY SOURCE AND target.date_key = @target_date AND target.smena = @target_smena THEN
        DELETE;

END;

PRINT '✅ Процедура dm.usp_update_employees_on_shift_raw создана.';
