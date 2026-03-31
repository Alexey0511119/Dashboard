-- ============================================================================
-- НАСТРОЙКА LINKED SERVER ДЛЯ 3-ДНЕВНОГО ETL
-- Сервер аналитики: 10.7.0.27 (olap2_fixed)
-- Сервер источник: 10.7.0.248 (ils, sk)
-- 
-- ЗАПУСК С КЛЮЧОМ -C (игнорировать SSL)
-- ============================================================================

USE [master];
GO

PRINT '╔' + REPLICATE('=', 78) + '╗';
PRINT '║' + SPACE(25) + 'НАСТРОЙКА LINKED SERVER' + SPACE(28) + '║';
PRINT '╚' + REPLICATE('=', 78) + '╝';
PRINT '';
PRINT '📅 Время начала: ' + CAST(GETDATE() AS NVARCHAR(50));
PRINT '';

-- ============================================================================
-- 1. ПРОВЕРКА СУЩЕСТВУЮЩИХ LINKED SERVER
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '1. ПРОВЕРКА СУЩЕСТВУЮЩИХ LINKED SERVER';
PRINT '═' + REPLICATE('=', 78);

IF EXISTS (SELECT 1 FROM sys.linked_servers WHERE name = 'ILS_SOURCE')
BEGIN
    PRINT '⚠️ ILS_SOURCE уже существует';
END
ELSE
BEGIN
    PRINT 'ℹ️ ILS_SOURCE не существует';
END

IF EXISTS (SELECT 1 FROM sys.linked_servers WHERE name = 'SK_SOURCE')
BEGIN
    PRINT '⚠️ SK_SOURCE уже существует';
END
ELSE
BEGIN
    PRINT 'ℹ️ SK_SOURCE не существует';
END
GO

-- ============================================================================
-- 2. УДАЛЕНИЕ СТАРЫХ LINKED SERVER (если есть)
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '2. УДАЛЕНИЕ СТАРЫХ LINKED SERVER';
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
-- 3. СОЗДАНИЕ LINKED SERVER ДЛЯ ILS (10.7.0.248)
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '3. СОЗДАНИЕ LINKED SERVER ДЛЯ ILS';
PRINT '═' + REPLICATE('=', 78);

-- Используем SQLNCLI11 (SQL Server Native Client 11)
EXEC sp_addlinkedserver
    @server = N'ILS_SOURCE',
    @srvproduct = N'SQL Server',
    @provider = N'SQLNCLI11',
    @datasrc = N'10.7.0.248',
    @catalog = N'ils';

PRINT '✅ ILS_SOURCE создан';

-- Настраиваем параметры
EXEC sp_serveroption 'ILS_SOURCE', 'data access', 'true';
EXEC sp_serveroption 'ILS_SOURCE', 'rpc', 'true';
EXEC sp_serveroption 'ILS_SOURCE', 'rpc out', 'true';
EXEC sp_serveroption 'ILS_SOURCE', 'remote proc transaction promotion', 'true';
EXEC sp_serveroption 'ILS_SOURCE', 'lazy schema validation', 'true';
EXEC sp_serveroption 'ILS_SOURCE', 'query timeout', '600';

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
-- 4. СОЗДАНИЕ LINKED SERVER ДЛЯ SK (10.7.0.248)
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '4. СОЗДАНИЕ LINKED SERVER ДЛЯ SK';
PRINT '═' + REPLICATE('=', 78);

EXEC sp_addlinkedserver
    @server = N'SK_SOURCE',
    @srvproduct = N'SQL Server',
    @provider = N'SQLNCLI11',
    @datasrc = N'10.7.0.248',
    @catalog = N'sk';

PRINT '✅ SK_SOURCE создан';

EXEC sp_serveroption 'SK_SOURCE', 'data access', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'rpc', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'rpc out', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'remote proc transaction promotion', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'lazy schema validation', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'query timeout', '600';

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
-- 5. ПРОВЕРКА ПОДКЛЮЧЕНИЯ
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '5. ПРОВЕРКА ПОДКЛЮЧЕНИЯ';
PRINT '═' + REPLICATE('=', 78);

PRINT '';
PRINT 'Проверка ILS_SOURCE...';

BEGIN TRY
    DECLARE @ils_count INT;
    SELECT @ils_count = COUNT(*) FROM ILS_SOURCE.ils.INFORMATION_SCHEMA.TABLES;
    PRINT '✅ ILS_SOURCE: подключение успешно (таблиц: ' + CAST(@ils_count AS NVARCHAR) + ')';
END TRY
BEGIN CATCH
    PRINT '❌ ILS_SOURCE: ошибка - ' + ERROR_MESSAGE();
END CATCH

PRINT '';
PRINT 'Проверка SK_SOURCE...';

BEGIN TRY
    DECLARE @sk_count INT;
    SELECT @sk_count = COUNT(*) FROM SK_SOURCE.sk.INFORMATION_SCHEMA.TABLES;
    PRINT '✅ SK_SOURCE: подключение успешно (таблиц: ' + CAST(@sk_count AS NVARCHAR) + ')';
END TRY
BEGIN CATCH
    PRINT '❌ SK_SOURCE: ошибка - ' + ERROR_MESSAGE();
END CATCH
GO

-- ============================================================================
-- 6. ВКЛЮЧЕНИЕ Ad Hoc Distributed Queries
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT '6. НАСТРОЙКА ПАРАМЕТРОВ СЕРВЕРА';
PRINT '═' + REPLICATE('=', 78);

EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;

EXEC sp_configure 'Ad Hoc Distributed Queries', 1;
RECONFIGURE;

PRINT '✅ Ad Hoc Distributed Queries включены';
GO

-- ============================================================================
-- 7. ФИНАЛЬНАЯ ИНФОРМАЦИЯ
-- ============================================================================
PRINT '═' + REPLICATE('=', 78);
PRINT 'НАСТРОЙКА ЗАВЕРШЕНА';
PRINT '═' + REPLICATE('=', 78);
PRINT '';
PRINT 'Созданные Linked Server:';
PRINT '  - ILS_SOURCE (10.7.0.248/ils)';
PRINT '  - SK_SOURCE (10.7.0.248/sk)';
PRINT '';
PRINT 'Проверка:';
PRINT '  SELECT TOP 5 * FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2;';
PRINT '  SELECT TOP 5 * FROM SK_SOURCE.sk.dbo.eks_peremer_ZX_KPP;';
PRINT '';
PRINT '📅 Время завершения: ' + CAST(GETDATE() AS NVARCHAR(50));
PRINT '';
PRINT '✅ НАСТРОЙКА LINKED SERVER ЗАВЕРШЕНА УСПЕШНО';
GO
