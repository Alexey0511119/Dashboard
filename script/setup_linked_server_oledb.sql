-- ============================================================================
-- НАСТРОЙКА LINKED SERVER ЧЕРЕЗ OLE DB (БЕЗ SSL ПРОБЛЕМ)
-- Сервер аналитики: 10.7.0.27 (olap2_fixed)
-- Сервер источник: 10.7.0.248 (ils, sk)
-- ============================================================================

USE [master];
GO

PRINT '╔' + REPLICATE('=', 78) + '╗';
PRINT '║' + SPACE(20) + 'НАСТРОЙКА LINKED SERVER (OLE DB)' + SPACE(26) + '║';
PRINT '╚' + REPLICATE('=', 78) + '╝';
PRINT '';
PRINT '📅 Время начала: ' + CAST(GETDATE() AS NVARCHAR(50));
PRINT '';

-- ============================================================================
-- 1. ВКЛЮЧЕНИЕ OLE DB AUTOMATION
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '1. ВКЛЮЧЕНИЕ OLE DB AUTOMATION';
PRINT '═' + REPLICATE('=', 78);

EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;

EXEC sp_configure 'Ole Automation Procedures', 1;
RECONFIGURE;

PRINT '✅ Ole Automation Procedures включены';
GO

-- ============================================================================
-- 2. УДАЛЕНИЕ СТАРЫХ LINKED SERVER (если есть)
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '2. ПОДГОТОВКА (удаление старых)';
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
-- 3. СОЗДАНИЕ LINKED SERVER ЧЕРЕЗ SQLNCLI11 (с игнорированием SSL)
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '3. СОЗДАНИЕ LINKED SERVER';
PRINT '═' + REPLICATE('=', 78);

-- Пробуем создать с SQLNCLI11
BEGIN TRY
    EXEC sp_addlinkedserver
        @server = N'ILS_SOURCE',
        @srvproduct = N'',
        @provider = N'SQLNCLI11',
        @datasrc = N'10.7.0.248',
        @catalog = N'ils',
        @provstr = 'Provider=SQLNCLI11;Data Source=10.7.0.248;Initial Catalog=ils;';
    
    PRINT '✅ ILS_SOURCE создан (SQLNCLI11)';
END TRY
BEGIN CATCH
    PRINT '⚠️ SQLNCLI11 недоступен, пробуем SQLNCLI...';
    
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
        PRINT '⚠️ SQLNCLI недоступен, пробуем MSDASQL...';
        
        EXEC sp_addlinkedserver
            @server = N'ILS_SOURCE',
            @srvproduct = N'SQL Server',
            @provider = N'MSDASQL',
            @datasrc = N'SQL Server',
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
-- 4. СОЗДАНИЕ LINKED SERVER ДЛЯ SK
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '4. СОЗДАНИЕ LINKED SERVER ДЛЯ SK';
PRINT '═' + REPLICATE('=', 78);

BEGIN TRY
    EXEC sp_addlinkedserver
        @server = N'SK_SOURCE',
        @srvproduct = N'',
        @provider = N'SQLNCLI11',
        @datasrc = N'10.7.0.248',
        @catalog = N'sk',
        @provstr = 'Provider=SQLNCLI11;Data Source=10.7.0.248;Initial Catalog=sk;';
    
    PRINT '✅ SK_SOURCE создан (SQLNCLI11)';
END TRY
BEGIN CATCH
    PRINT '⚠️ SQLNCLI11 недоступен, пробуем альтернативы...';
    
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
        EXEC sp_addlinkedserver
            @server = N'SK_SOURCE',
            @srvproduct = N'SQL Server',
            @provider = N'MSDASQL',
            @datasrc = N'SQL Server',
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
-- 5. ПРОВЕРКА ПОДКЛЮЧЕНИЯ ЧЕРЕЗ OPENQUERY
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '5. ПРОВЕРКА ПОДКЛЮЧЕНИЯ';
PRINT '═' + REPLICATE('=', 78);

PRINT '';
PRINT 'Проверка ILS_SOURCE через OPENQUERY...';

BEGIN TRY
    DECLARE @ils_test TABLE (table_name NVARCHAR(255));
    INSERT INTO @ils_test
    EXEC('SELECT TOP 1 TABLE_NAME FROM INFORMATION_SCHEMA.TABLES') AT ILS_SOURCE;
    
    PRINT '✅ ILS_SOURCE: подключение успешно';
END TRY
BEGIN CATCH
    PRINT '❌ ILS_SOURCE: ошибка - ' + ERROR_MESSAGE();
    PRINT '   Попробуйте использовать SSMS для настройки';
END CATCH

PRINT '';
PRINT 'Проверка SK_SOURCE через OPENQUERY...';

BEGIN TRY
    DECLARE @sk_test TABLE (table_name NVARCHAR(255));
    INSERT INTO @sk_test
    EXEC('SELECT TOP 1 TABLE_NAME FROM INFORMATION_SCHEMA.TABLES') AT SK_SOURCE;
    
    PRINT '✅ SK_SOURCE: подключение успешно';
END TRY
BEGIN CATCH
    PRINT '❌ SK_SOURCE: ошибка - ' + ERROR_MESSAGE();
    PRINT '   Попробуйте использовать SSMS для настройки';
END CATCH
GO

-- ============================================================================
-- 6. АЛЬТЕРНАТИВА: НАСТРОЙКА ЧЕРЕЗ SSMS (если скрипт не работает)
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '6. ИНСТРУКЦИЯ ДЛЯ SSMS (если скрипт не сработал)';
PRINT '═' + REPLICATE('=', 78);

PRINT '';
PRINT 'Если скрипт выше не сработал, выполните вручную через SSMS:';
PRINT '';
PRINT '1. Откройте SSMS, подключитесь к 10.7.0.27';
PRINT '2. Объекты сервера -> Объекты сервера -> Связанные серверы';
PRINT '3. ПКМ -> Создать связанный сервер...';
PRINT '4. Заполните:';
PRINT '   - Имя связанного сервера: ILS_SOURCE';
PRINT '   - Сервер: 10.7.0.248';
PRINT '   - Поставщик: SQL Server Native Client 11.0';
PRINT '   - Каталог: ils';
PRINT '5. Страница "Безопасность":';
PRINT '   - Не включен: Выберите "Будет создан с помощью этого входа"';
PRINT '   - Логин: manhreader';
PRINT '   - Пароль: August2021';
PRINT '6. Страница "Параметры сервера":';
PRINT '   - ✅ Доступ к данным';
PRINT '   - ✅ RPC';
PRINT '   - ✅ Исходящий RPC';
PRINT '   - Таймаут запроса: 900';
PRINT '7. Нажмите OK';
PRINT '';
PRINT 'Повторите для SK_SOURCE (каталог: sk)';
PRINT '';
GO

-- ============================================================================
-- 7. ФИНАЛЬНАЯ ИНФОРМАЦИЯ
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT 'НАСТРОЙКА ЗАВЕРШЕНА';
PRINT '═' + REPLICATE('=', 78);
PRINT '';
PRINT '📅 Время завершения: ' + CAST(GETDATE() AS NVARCHAR(50));
PRINT '';
PRINT 'Проверка:';
PRINT '  SELECT TOP 5 * FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2;';
PRINT '  SELECT TOP 5 * FROM SK_SOURCE.sk.dbo.eks_peremer_ZX_KPP;';
PRINT '';

-- Вывод списка Linked Server
PRINT 'Созданные Linked Server:';
SELECT 
    name AS linked_server,
    provider,
    data_source,
    is_data_access_enabled AS data_access
FROM sys.linked_servers
WHERE name IN ('ILS_SOURCE', 'SK_SOURCE');

PRINT '';
PRINT '✅ НАСТРОЙКА ЗАВЕРШЕНА';
GO
