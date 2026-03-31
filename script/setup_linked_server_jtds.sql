-- ============================================================================
-- НАСТРОЙКА LINKED SERVER ЧЕРЕЗ jTDS (БЕЗ SSL ПРОБЛЕМ)
-- Сервер аналитики: 10.7.0.27 (olap2_fixed)
-- Сервер источник: 10.7.0.248 (ils, sk)
-- 
-- ВАЖНО: Требуется jTDS драйвер в DBeaver
-- ============================================================================

USE [master];
GO

PRINT '╔' + REPLICATE('=', 78) + '╗';
PRINT '║' + SPACE(15) + 'НАСТРОЙКА LINKED SERVER (jTDS VERSION)' + SPACE(22) + '║';
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
    PRINT '✅ ILS_SOURCE удалён';
END
ELSE
BEGIN
    PRINT 'ℹ️ ILS_SOURCE не существовал';
END

IF EXISTS (SELECT 1 FROM sys.linked_servers WHERE name = 'SK_SOURCE')
BEGIN
    EXEC sp_droplinkedsrvlogin 'SK_SOURCE', NULL;
    EXEC sp_dropserver 'SK_SOURCE', 'droplogins';
    PRINT '✅ SK_SOURCE удалён';
END
ELSE
BEGIN
    PRINT 'ℹ️ SK_SOURCE не существовал';
END
GO

-- ============================================================================
-- 2. СОЗДАНИЕ ILS_SOURCE ЧЕРЕЗ SQLNCLI (без SSL)
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '2. СОЗДАНИЕ ILS_SOURCE';
PRINT '═' + REPLICATE('=', 78);

-- Пробуем создать с параметрами для отключения SSL
BEGIN TRY
    EXEC sp_addlinkedserver
        @server = N'ILS_SOURCE',
        @srvproduct = N'SQL Server',
        @provider = N'SQLNCLI11',
        @datasrc = N'10.7.0.248',
        @catalog = N'ils',
        @provstr = 'Provider=SQLNCLI11;Data Source=10.7.0.248;Initial Catalog=ils;Integrated Security=0;User ID=manhreader;Password=August2021;Encrypt=no;TrustServerCertificate=yes;';
    
    PRINT '✅ ILS_SOURCE создан';
END TRY
BEGIN CATCH
    PRINT '⚠️ Ошибка с SQLNCLI11: ' + ERROR_MESSAGE();
    PRINT '   Пробуем альтернативный метод...';
    
    -- Альтернатива: используем базовый SQLNCLI
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
        PRINT '❌ Не удалось создать ILS_SOURCE';
        PRINT '   Сообщение: ' + ERROR_MESSAGE();
        PRINT '   ';
        PRINT '   РЕШЕНИЕ: Используйте DBeaver с jTDS драйвером:';
        PRINT '   1. Database → Driver Manager';
        PRINT '   2. Создайте драйвер jTDS SQL Server';
        PRINT '   3. URL: jdbc:jtds:sqlserver://10.7.0.27:1433/olap2_fixed';
        PRINT '   4. Переподключитесь и попробуйте снова';
        THROW;
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
-- 3. СОЗДАНИЕ SK_SOURCE
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '3. СОЗДАНИЕ SK_SOURCE';
PRINT '═' + REPLICATE('=', 78);

BEGIN TRY
    EXEC sp_addlinkedserver
        @server = N'SK_SOURCE',
        @srvproduct = N'SQL Server',
        @provider = N'SQLNCLI11',
        @datasrc = N'10.7.0.248',
        @catalog = N'sk',
        @provstr = 'Provider=SQLNCLI11;Data Source=10.7.0.248;Initial Catalog=sk;Integrated Security=0;User ID=manhreader;Password=August2021;Encrypt=no;TrustServerCertificate=yes;';
    
    PRINT '✅ SK_SOURCE создан';
END TRY
BEGIN CATCH
    PRINT '⚠️ Ошибка с SQLNCLI11: ' + ERROR_MESSAGE();
    
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
        PRINT '❌ Не удалось создать SK_SOURCE';
        PRINT '   Используйте jTDS драйвер (см. инструкцию выше)';
        THROW;
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
    DECLARE @ils_count INT;
    SELECT @ils_count = COUNT(*) FROM ILS_SOURCE.ils.INFORMATION_SCHEMA.TABLES;
    PRINT '✅ ILS_SOURCE: подключение успешно (таблиц: ' + CAST(@ils_count AS NVARCHAR) + ')';
END TRY
BEGIN CATCH
    PRINT '❌ ILS_SOURCE: ошибка - ' + LEFT(ERROR_MESSAGE(), 200);
END CATCH

PRINT '';
PRINT 'Проверка SK_SOURCE...';

BEGIN TRY
    DECLARE @sk_count INT;
    SELECT @sk_count = COUNT(*) FROM SK_SOURCE.sk.INFORMATION_SCHEMA.TABLES;
    PRINT '✅ SK_SOURCE: подключение успешно (таблиц: ' + CAST(@sk_count AS NVARCHAR) + ')';
END TRY
BEGIN CATCH
    PRINT '❌ SK_SOURCE: ошибка - ' + LEFT(ERROR_MESSAGE(), 200);
END CATCH
GO

-- ============================================================================
-- 5. ФИНАЛЬНАЯ ИНФОРМАЦИЯ
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
    data_source
FROM sys.linked_servers
WHERE name IN ('ILS_SOURCE', 'SK_SOURCE');

PRINT '';
PRINT '✅ НАСТРОЙКА ЗАВЕРШЕНА';
GO
