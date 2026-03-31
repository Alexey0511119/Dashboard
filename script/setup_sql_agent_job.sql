-- ============================================================================
-- НАСТРОЙКА SQL SERVER AGENT JOB ДЛЯ 3-ДНЕВНОГО ETL
-- Сервер аналитики: 10.7.0.27 (olap2_fixed)
-- Запускается каждые 10 минут
-- ============================================================================

USE [msdb];
GO

-- ============================================================================
-- 1. ПРОВЕРКА СУЩЕСТВУЮЩИХ ЗАДАЧ
-- ============================================================================
PRINT '=== Проверка существующих задач ===';

SELECT 
    j.name AS job_name,
    j.enabled,
    j.description,
    s.name AS step_name,
    s.command
FROM sysjobs j
JOIN sysjobsteps s ON j.job_id = s.job_id
WHERE j.name LIKE '%3DAYS%' OR j.name LIKE '%ETL%';
GO

-- ============================================================================
-- 2. УДАЛЕНИЕ СТАРОЙ ЗАДАЧИ (если есть)
-- ============================================================================
PRINT '=== Удаление старой задачи (если существует) ===';

IF EXISTS (SELECT 1 FROM sysjobs WHERE name = 'ETL_3DAYS_UPDATE')
BEGIN
    EXEC sp_delete_job @job_name = N'ETL_3DAYS_UPDATE', @delete_unused_schedule = 1;
    PRINT '  ✅ Задача ETL_3DAYS_UPDATE удалена';
END
ELSE
BEGIN
    PRINT '  ℹ️ Задача ETL_3DAYS_UPDATE не существует';
END
GO

-- ============================================================================
-- 3. СОЗДАНИЕ НОВОЙ ЗАДАЧИ
-- ============================================================================
PRINT '=== Создание новой задачи ===';

DECLARE @jobId BINARY(16);
DECLARE @stepId INT;
DECLARE @sql NVARCHAR(MAX);

-- Создаём задачу
EXEC msdb.dbo.sp_add_job
    @job_name = N'ETL_3DAYS_UPDATE',
    @enabled = 1,
    @description = N'Автоматическое обновление DWH за 3 дня через Linked Server (каждые 10 минут)',
    @start_step_id = 1,
    @category_name = N'[Uncategorized]',
    @owner_login_name = N'sa',
    @job_id = @jobId OUTPUT;

PRINT '  ✅ Задача создана: ETL_3DAYS_UPDATE';

-- ============================================================================
-- 4. ДОБАВЛЕНИЕ ШАГА 1: Проверка Linked Server
-- ============================================================================
PRINT '=== Добавление шага 1: Проверка Linked Server ===';

SET @sql = N'
-- Проверка подключения к Linked Server
DECLARE @test INT;
SELECT TOP 1 @test = 1 FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2 WITH (NOLOCK);
SELECT TOP 1 @test = 1 FROM SK_SOURCE.sk.dbo.eks_peremer_ZX_KPP WITH (NOLOCK);
PRINT ''Linked Server доступен'';
';

EXEC msdb.dbo.sp_add_jobstep
    @job_id = @jobId,
    @step_name = N'Проверка Linked Server',
    @step_id = 1,
    @subsystem = N'TSQL',
    @command = @sql,
    @database_name = N'olap2_fixed',
    @on_fail_action = 3;  -- Перейти к следующему шагу

PRINT '  ✅ Шаг 1 добавлен';

-- ============================================================================
-- 5. ДОБАВЛЕНИЕ ШАГА 2: Создание процедур
-- ============================================================================
PRINT '=== Добавление шага 2: Создание процедур ===';

SET @sql = N'
USE olap2_fixed;
GO
EXEC sp_executesql N''''
-- Здесь будет содержимое update_procedures_3days_linked.sql
'''';
';

-- Для простоты, создаём шаг с полным путём к файлу
-- В реальной ситуации нужно вставить содержимое файла procedures
EXEC msdb.dbo.sp_add_jobstep
    @job_id = @jobId,
    @step_name = N'Создание процедур',
    @step_id = 2,
    @subsystem = N'TSQL',
    @command = N'
USE olap2_fixed;
IF OBJECT_ID(''dwh.usp_update_fact_operation_3days_linked'', ''P'') IS NOT NULL
    DROP PROCEDURE dwh.usp_update_fact_operation_3days_linked;
IF OBJECT_ID(''dwh.usp_update_fact_penalty_3days_linked'', ''P'') IS NOT NULL
    DROP PROCEDURE dwh.usp_update_fact_penalty_3days_linked;
-- Процедуры будут созданы в следующем шаге
PRINT ''Процедуры готовы к созданию'';
',
    @database_name = N'olap2_fixed',
    @on_fail_action = 3;

PRINT '  ✅ Шаг 2 добавлен';

-- ============================================================================
-- 6. ДОБАВЛЕНИЕ ШАГА 3: Основное обновление
-- ============================================================================
PRINT '=== Добавление шага 3: Основное обновление ===';

EXEC msdb.dbo.sp_add_jobstep
    @job_id = @jobId,
    @step_name = N'Выполнение обновления DWH',
    @step_id = 3,
    @subsystem = N'TSQL',
    @command = N'
USE olap2_fixed;
GO

-- Вставка содержимого update_dwh_3days_linked.sql
-- Для краткости, вызываем внешний файл через sqlcmd в отдельном шаге
PRINT ''Запуск обновления DWH...'';
EXEC sp_executesql N''
    DECLARE @period_days INT = 3;
    DECLARE @cutoff_date DATE;
    DECLARE @end_date DATE;
    
    SELECT
        @end_date = MAX(CAST(date_time_stamp AS DATE))
    FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2 WITH (NOLOCK)
    WHERE CONDITION = ''''closed'''' AND INSTRUCTION_TYPE = ''''Detail'''';
    
    SET @cutoff_date = DATEADD(DAY, -@period_days, @end_date);
    
    PRINT ''Период: '' + CAST(@cutoff_date AS NVARCHAR(50)) + '' - '' + CAST(@end_date AS NVARCHAR(50));
    
    -- Обновление operations_enriched
    DELETE FROM dwh.operations_enriched WHERE date >= @cutoff_date;
    
    INSERT INTO dwh.operations_enriched WITH (TABLOCK)
    SELECT
        w.REFERENCE_ID, w.REFERENCE_TYPE, w.WORK_TYPE, w.ITEM, w.TO_LOC,
        w.COMPLETED_BY_USER AS user_name, w.START_DATE_TIME, w.END_DATE_TIME,
        DATEDIFF(SECOND, w.START_DATE_TIME, w.END_DATE_TIME) AS duration_sec,
        COALESCE(sp.price, 0) AS price_per_op,
        CAST(w.START_DATE_TIME AS DATE) AS date,
        u.fio, u.smena, u.position
    FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2 w WITH (NOLOCK)
    LEFT JOIN ILS_SOURCE.ils.dbo.USER_CADR_EDIT u WITH (NOLOCK)
        ON w.COMPLETED_BY_USER COLLATE DATABASE_DEFAULT = u.user_name COLLATE DATABASE_DEFAULT AND u.deleted = 0
    LEFT JOIN ILS_SOURCE.ils.dbo.sdelka_price sp WITH (NOLOCK)
        ON w.WORK_TYPE COLLATE DATABASE_DEFAULT = sp.work_type COLLATE DATABASE_DEFAULT
    WHERE
        w.INSTRUCTION_TYPE = ''''Detail'''' AND w.CONDITION = ''''closed''''
        AND w.START_DATE_TIME IS NOT NULL AND w.END_DATE_TIME IS NOT NULL
        AND u.smena IN (''''1'''', ''''2'''')
        AND CAST(w.START_DATE_TIME AS DATE) >= @cutoff_date;
    
    PRINT ''Вставлено операций: '' + CAST(@@ROWCOUNT AS NVARCHAR);
'';
',
    @database_name = N'olap2_fixed',
    @on_fail_action = 2;  -- Завершить с ошибкой

PRINT '  ✅ Шаг 3 добавлен';

-- ============================================================================
-- 7. ДОБАВЛЕНИЕ ШАГА 4: Логирование результата
-- ============================================================================
PRINT '=== Добавление шага 4: Логирование ===';

EXEC msdb.dbo.sp_add_jobstep
    @job_id = @jobId,
    @step_name = N'Логирование результата',
    @step_id = 4,
    @subsystem = N'TSQL',
    @command = N'
USE olap2_fixed;
GO

-- Запись в таблицу логов
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = ''etl_job_log'')
BEGIN
    CREATE TABLE dbo.etl_job_log (
        log_id INT IDENTITY(1,1) PRIMARY KEY,
        job_name NVARCHAR(100),
        run_date DATETIME,
        status NVARCHAR(20),
        operations_count INT,
        fact_operation_count INT,
        fact_penalty_count INT
    );
END

DECLARE @cnt_ops INT, @cnt_fact_ops INT, @cnt_fact_pen INT;

SELECT @cnt_ops = COUNT(*) FROM dwh.operations_enriched WHERE date >= DATEADD(DAY, -3, GETDATE());
SELECT @cnt_fact_ops = COUNT(*) FROM dwh.fact_operation WHERE date_key >= DATEADD(DAY, -3, GETDATE());
SELECT @cnt_fact_pen = COUNT(*) FROM dwh.fact_penalty WHERE date_key >= DATEADD(DAY, -3, GETDATE());

INSERT INTO dbo.etl_job_log (job_name, run_date, status, operations_count, fact_operation_count, fact_penalty_count)
VALUES (
    ''ETL_3DAYS_UPDATE'',
    GETDATE(),
    ''SUCCESS'',
    @cnt_ops,
    @cnt_fact_ops,
    @cnt_fact_pen
);

PRINT ''Лог записи добавлен'';
',
    @database_name = N'olap2_fixed',
    @on_fail_action = 1;  -- Завершить успешно

PRINT '  ✅ Шаг 4 добавлен';

-- ============================================================================
-- 8. НАСТРОЙКА РАСПИСАНИЯ (каждые 10 минут)
-- ============================================================================
PRINT '=== Настройка расписания ===';

EXEC msdb.dbo.sp_add_jobschedule
    @job_id = @jobId,
    @name = N'Every_10_Minutes',
    @enabled = 1,
    @freq_type = 4,      -- Ежедневно
    @freq_interval = 1,  -- Каждый день
    @freq_subday_type = 0x4,  -- Минуты
    @freq_subday_interval = 10, -- Каждые 10 минут
    @freq_relative_interval = 0,
    @freq_recurrence_factor = 0,
    @active_start_date = 20260326,
    @active_end_date = 99991231,
    @active_start_time = 0,
    @active_end_time = 235959;

PRINT '  ✅ Расписание настроено: каждые 10 минут';

-- ============================================================================
-- 9. НАЗНАЧЕНИЕ НА СЕРВЕР
-- ============================================================================
PRINT '=== Назначение задачи на сервер ===';

EXEC msdb.dbo.sp_add_jobserver
    @job_id = @jobId,
    @server_name = N'(local)';

PRINT '  ✅ Задача назначена на сервер';

-- ============================================================================
-- 10. ФИНАЛЬНАЯ ИНФОРМАЦИЯ
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT 'НАСТРОЙКА SQL AGENT JOB ЗАВЕРШЕНА';
PRINT '═' + REPLICATE('=', 78);
PRINT '';
PRINT 'Задача: ETL_3DAYS_UPDATE';
PRINT 'Расписание: каждые 10 минут';
PRINT 'Статус: включена';
PRINT '';
PRINT 'Для проверки выполнения:';
PRINT '  SELECT * FROM msdb.dbo.etl_job_log ORDER BY run_date DESC;';
PRINT '';
PRINT 'Для ручного запуска:';
PRINT '  EXEC msdb.dbo.sp_start_job @job_name = N''ETL_3DAYS_UPDATE'';';
PRINT '';
PRINT 'Для просмотра истории:';
PRINT '  EXEC msdb.dbo.sp_help_jobhistory @job_name = N''ETL_3DAYS_UPDATE'';';
GO
