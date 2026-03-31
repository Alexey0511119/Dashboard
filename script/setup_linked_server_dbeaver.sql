-- ============================================================================
-- НАСТРОЙКА LINKED SERVER ДЛЯ ETL (ВЕРСИЯ ДЛЯ DBEAVER)
-- Сервер аналитики: 10.7.0.27 (olap2_fixed)
-- Сервер источник: 10.7.0.248 (ils, sk)
-- 
-- ЗАПУСК В DBEAVER: Откройте этот файл → Ctrl+Enter
-- ============================================================================

USE [master];
GO

PRINT '╔' + REPLICATE('=', 78) + '╗';
PRINT '║' + SPACE(15) + 'НАСТРОЙКА LINKED SERVER (DBEAVER VERSION)' + SPACE(20) + '║';
PRINT '╚' + REPLICATE('=', 78) + '╝';
PRINT '';
PRINT '📅 Время начала: ' + CAST(GETDATE() AS NVARCHAR(50));
PRINT '';

-- ============================================================================
-- 1. ПОДГОТОВКА
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '1. ПОДГОТОВКА (удаление старых Linked Server)';
PRINT '═' + REPLICATE('=', 78);

IF EXISTS (SELECT 1 FROM sys.linked_servers WHERE name = 'ILS_SOURCE')
BEGIN
    EXEC sp_droplinkedsrvlogin 'ILS_SOURCE', NULL;
    EXEC sp_dropserver 'ILS_SOURCE', 'droplogins';
    PRINT '✅ ILS_SOURCE удалён (старый)';
END
ELSE
BEGIN
    PRINT 'ℹ️ ILS_SOURCE не существовал';
END

IF EXISTS (SELECT 1 FROM sys.linked_servers WHERE name = 'SK_SOURCE')
BEGIN
    EXEC sp_droplinkedsrvlogin 'SK_SOURCE', NULL;
    EXEC sp_dropserver 'SK_SOURCE', 'droplogins';
    PRINT '✅ SK_SOURCE удалён (старый)';
END
ELSE
BEGIN
    PRINT 'ℹ️ SK_SOURCE не существовал';
END
GO

-- ============================================================================
-- 2. СОЗДАНИЕ ILS_SOURCE (с обработкой ошибок)
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '2. СОЗДАНИЕ ILS_SOURCE';
PRINT '═' + REPLICATE('=', 78);

BEGIN TRY
    -- Пробуем SQLNCLI11
    EXEC sp_addlinkedserver
        @server = N'ILS_SOURCE',
        @srvproduct = N'',
        @provider = N'SQLNCLI11',
        @datasrc = N'10.7.0.248',
        @catalog = N'ils';
    
    PRINT '✅ ILS_SOURCE создан (SQLNCLI11)';
END TRY
BEGIN CATCH
    PRINT '⚠️ SQLNCLI11 недоступен: ' + ERROR_MESSAGE();
    PRINT '   Пробуем SQLNCLI...';
    
    BEGIN TRY
        EXEC sp_addlinkedserver
            @server = N'ILS_SOURCE',
            @srvproduct = N'',
            @provider = N'SQLNCLI',
            @datasrc = N'10.7.0.248',
            @catalog = N'ils';
        
        PRINT '✅ ILS_SOURCE создан (SQLNCLI)';
    END TRY
    BEGIN CATCH
        PRINT '⚠️ SQLNCLI недоступен: ' + ERROR_MESSAGE();
        PRINT '   Пробуем MSDASQL...';
        
        EXEC sp_addlinkedserver
            @server = N'ILS_SOURCE',
            @srvproduct = N'SQL Server',
            @provider = N'MSDASQL',
            @provstr = 'DRIVER={SQL Server};SERVER=10.7.0.248;DATABASE=ils;UID=manhreader;PWD=August2021;';
        
        PRINT '✅ ILS_SOURCE создан (MSDASQL)';
    END CATCH
END CATCH

-- Настраиваем параметры
EXEC sp_serveroption 'ILS_SOURCE', 'data access', 'true';
EXEC sp_serveroption 'ILS_SOURCE', 'rpc', 'true';
EXEC sp_serveroption 'ILS_SOURCE', 'rpc out', 'true';
EXEC sp_serveroption 'ILS_SOURCE', 'remote proc transaction promotion', 'false';
EXEC sp_serveroption 'ILS_SOURCE', 'lazy schema validation', 'true';
EXEC sp_serveroption 'ILS_SOURCE', 'query timeout', '900';

PRINT '✅ ILS_SOURCE настроен';

-- Добавляем учётные данные
EXEC sp_addlinkedsrvlogin
    @rmtsrvname = 'ILS_SOURCE',
    @useself = 'false',
    @locallogin = NULL,
    @rmtuser = 'manhreader',
    @rmtpassword = 'August2021';

PRINT '✅ Учётные данные ILS_SOURCE добавлены';
GO

-- ============================================================================
-- 3. СОЗДАНИЕ SK_SOURCE (с обработкой ошибок)
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '3. СОЗДАНИЕ SK_SOURCE';
PRINT '═' + REPLICATE('=', 78);

BEGIN TRY
    EXEC sp_addlinkedserver
        @server = N'SK_SOURCE',
        @srvproduct = N'',
        @provider = N'SQLNCLI11',
        @datasrc = N'10.7.0.248',
        @catalog = N'sk';
    
    PRINT '✅ SK_SOURCE создан (SQLNCLI11)';
END TRY
BEGIN CATCH
    PRINT '⚠️ SQLNCLI11 недоступен: ' + ERROR_MESSAGE();
    PRINT '   Пробуем SQLNCLI...';
    
    BEGIN TRY
        EXEC sp_addlinkedserver
            @server = N'SK_SOURCE',
            @srvproduct = N'',
            @provider = N'SQLNCLI',
            @datasrc = N'10.7.0.248',
            @catalog = N'sk';
        
        PRINT '✅ SK_SOURCE создан (SQLNCLI)';
    END TRY
    BEGIN CATCH
        PRINT '⚠️ SQLNCLI недоступен: ' + ERROR_MESSAGE();
        PRINT '   Пробуем MSDASQL...';
        
        EXEC sp_addlinkedserver
            @server = N'SK_SOURCE',
            @srvproduct = N'SQL Server',
            @provider = N'MSDASQL',
            @provstr = 'DRIVER={SQL Server};SERVER=10.7.0.248;DATABASE=sk;UID=manhreader;PWD=August2021;';
        
        PRINT '✅ SK_SOURCE создан (MSDASQL)';
    END CATCH
END CATCH

EXEC sp_serveroption 'SK_SOURCE', 'data access', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'rpc', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'rpc out', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'remote proc transaction promotion', 'false';
EXEC sp_serveroption 'SK_SOURCE', 'lazy schema validation', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'query timeout', '900';

PRINT '✅ SK_SOURCE настроен';

EXEC sp_addlinkedsrvlogin
    @rmtsrvname = 'SK_SOURCE',
    @useself = 'false',
    @locallogin = NULL,
    @rmtuser = 'manhreader',
    @rmtpassword = 'August2021';

PRINT '✅ Учётные данные SK_SOURCE добавлены';
GO

-- ============================================================================
-- 4. ПРОВЕРКА ПОДКЛЮЧЕНИЯ
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '4. ПРОВЕРКА ПОДКЛЮЧЕНИЯ';
PRINT '═' + REPLICATE('=', 78);

PRINT '';
PRINT 'Проверка ILS_SOURCE...';

BEGIN TRY
    DECLARE @ils_check INT;
    SELECT @ils_check = COUNT(*) FROM ILS_SOURCE.ils.INFORMATION_SCHEMA.TABLES;
    PRINT '✅ ILS_SOURCE: подключение успешно (таблиц: ' + CAST(@ils_check AS NVARCHAR) + ')';
END TRY
BEGIN CATCH
    PRINT '❌ ILS_SOURCE: ошибка подключения';
    PRINT '   Сообщение: ' + ERROR_MESSAGE();
    PRINT '   Решение: Проверьте доступность 10.7.0.248 и права manhreader';
END CATCH

PRINT '';
PRINT 'Проверка SK_SOURCE...';

BEGIN TRY
    DECLARE @sk_check INT;
    SELECT @sk_check = COUNT(*) FROM SK_SOURCE.sk.INFORMATION_SCHEMA.TABLES;
    PRINT '✅ SK_SOURCE: подключение успешно (таблиц: ' + CAST(@sk_check AS NVARCHAR) + ')';
END TRY
BEGIN CATCH
    PRINT '❌ SK_SOURCE: ошибка подключения';
    PRINT '   Сообщение: ' + ERROR_MESSAGE();
    PRINT '   Решение: Проверьте доступность 10.7.0.248 и права manhreader';
END CATCH
GO

-- ============================================================================
-- 5. БЫСТРЫЙ ТЕСТ ДАННЫХ
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '5. БЫСТРЫЙ ТЕСТ ДАННЫХ';
PRINT '═' + REPLICATE('=', 78);

PRINT '';
PRINT 'WORK_INSTRUCTION_VIEW2 (ILS):';
SELECT TOP 3 
    'ILS' AS source,
    REFERENCE_ID,
    WORK_TYPE,
    START_DATE_TIME
FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2
WHERE CONDITION = 'closed' AND INSTRUCTION_TYPE = 'Detail'
ORDER BY START_DATE_TIME DESC;

PRINT '';
PRINT 'eks_peremer_ZX_KPP (SK):';
SELECT TOP 3
    'SK' AS source,
    user_name,
    date_time_stamp
FROM SK_SOURCE.sk.dbo.eks_peremer_ZX_KPP
ORDER BY date_time_stamp DESC;
GO

-- ============================================================================
-- 6. ФИНАЛЬНАЯ ИНФОРМАЦИЯ
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT 'НАСТРОЙКА ЗАВЕРШЕНА';
PRINT '═' + REPLICATE('=', 78);
PRINT '';
PRINT '📅 Время завершения: ' + CAST(GETDATE() AS NVARCHAR(50));
PRINT '';
PRINT 'Созданные Linked Server:';

SELECT 
    name AS linked_server,
    provider,
    data_source,
    CASE is_data_access_enabled 
        WHEN 1 THEN '✅' 
        ELSE '❌' 
    END AS data_access
FROM sys.linked_servers
WHERE name IN ('ILS_SOURCE', 'SK_SOURCE');

PRINT '';
PRINT 'Следующие шаги:';
PRINT '  1. Выполните: update_procedures_3days_linked.sql';
PRINT '  2. Выполните: setup_sql_agent_job.sql';
PRINT '  3. Тест: update_dwh_3days_linked.sql';
PRINT '';
PRINT '✅ НАСТРОЙКА LINKED SERVER ЗАВЕРШЕНА УСПЕШНО';
GO
