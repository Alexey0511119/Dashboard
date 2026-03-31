-- ============================================================================
-- НАСТРОЙКА LINKED SERVER ДЛЯ 3-ДНЕВНОГО ETL
-- Сервер аналитики: 10.7.0.27 (olap2_fixed)
-- Сервер источник: 10.7.0.248 (ils, sk)
-- ============================================================================

USE [master];
GO

-- ============================================================================
-- 1. ПРОВЕРКА СУЩЕСТВУЮЩИХ LINKED SERVER
-- ============================================================================
PRINT '=== Проверка существующих Linked Server ===';

SELECT 
    name AS linked_server_name,
    product,
    provider,
    data_source,
    is_remote_login_enabled,
    is_rpc_out_enabled,
    is_data_access_enabled
FROM sys.linked_servers
WHERE name IN ('ILS_SOURCE', 'SK_SOURCE');
GO

-- ============================================================================
-- 2. УДАЛЕНИЕ СТАРЫХ LINKED SERVER (если есть)
-- ============================================================================
PRINT '=== Удаление старых Linked Server (если существуют) ===';

IF EXISTS (SELECT 1 FROM sys.linked_servers WHERE name = 'ILS_SOURCE')
BEGIN
    -- Удаляем логины
    EXEC sp_droplinkedsrvlogin 'ILS_SOURCE', NULL;
    -- Удаляем Linked Server
    EXEC sp_dropserver 'ILS_SOURCE', 'droplogins';
    PRINT '  ✅ ILS_SOURCE удалён';
END
ELSE
BEGIN
    PRINT '  ℹ️ ILS_SOURCE не существует';
END

IF EXISTS (SELECT 1 FROM sys.linked_servers WHERE name = 'SK_SOURCE')
BEGIN
    EXEC sp_droplinkedsrvlogin 'SK_SOURCE', NULL;
    EXEC sp_dropserver 'SK_SOURCE', 'droplogins';
    PRINT '  ✅ SK_SOURCE удалён';
END
ELSE
BEGIN
    PRINT '  ℹ️ SK_SOURCE не существует';
END
GO

-- ============================================================================
-- 3. СОЗДАНИЕ LINKED SERVER ДЛЯ ILS (10.7.0.248)
-- ============================================================================
PRINT '=== Создание Linked Server для ILS (10.7.0.248) ===';

EXEC sp_addlinkedserver
    @server = N'ILS_SOURCE',           -- Имя Linked Server
    @srvproduct = N'SQL Server',        -- Продукт
    @provider = N'SQLNCLI',             -- Провайдер (SQL Server Native Client)
    @datasrc = N'10.7.0.248',           -- Адрес сервера
    @catalog = N'ils';                  -- База данных по умолчанию

PRINT '  ✅ ILS_SOURCE создан';

-- Настраиваем параметры Linked Server
EXEC sp_serveroption 'ILS_SOURCE', 'data access', 'true';       -- Разрешить доступ к данным
EXEC sp_serveroption 'ILS_SOURCE', 'rpc', 'true';               -- Разрешить RPC
EXEC sp_serveroption 'ILS_SOURCE', 'rpc out', 'true';           -- Разрешить исходящий RPC
EXEC sp_serveroption 'ILS_SOURCE', 'remote proc transaction promotion', 'true';
EXEC sp_serveroption 'ILS_SOURCE', 'lazy schema validation', 'true';
EXEC sp_serveroption 'ILS_SOURCE', 'query timeout', '600';      -- Таймаут 10 минут

PRINT '  ✅ ILS_SOURCE настроен';

-- Добавляем учётные данные для подключения
EXEC sp_addlinkedsrvlogin
    @rmtsrvname = 'ILS_SOURCE',
    @useself = 'false',
    @locallogin = NULL,              -- Для всех локальных логинов
    @rmtuser = 'manhreader',         -- Логин на удалённом сервере
    @rmtpassword = 'August2021';     -- Пароль

PRINT '  ✅ Учётные данные ILS_SOURCE добавлены';
GO

-- ============================================================================
-- 4. СОЗДАНИЕ LINKED SERVER ДЛЯ SK (10.7.0.248)
-- ============================================================================
PRINT '=== Создание Linked Server для SK (10.7.0.248) ===';

EXEC sp_addlinkedserver
    @server = N'SK_SOURCE',
    @srvproduct = N'SQL Server',
    @provider = N'SQLNCLI',
    @datasrc = N'10.7.0.248',
    @catalog = N'sk';

PRINT '  ✅ SK_SOURCE создан';

EXEC sp_serveroption 'SK_SOURCE', 'data access', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'rpc', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'rpc out', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'remote proc transaction promotion', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'lazy schema validation', 'true';
EXEC sp_serveroption 'SK_SOURCE', 'query timeout', '600';

PRINT '  ✅ SK_SOURCE настроен';

EXEC sp_addlinkedsrvlogin
    @rmtsrvname = 'SK_SOURCE',
    @useself = 'false',
    @locallogin = NULL,
    @rmtuser = 'manhreader',
    @rmtpassword = 'August2021';

PRINT '  ✅ Учётные данные SK_SOURCE добавлены';
GO

-- ============================================================================
-- 5. ПРОВЕРКА ПОДКЛЮЧЕНИЯ
-- ============================================================================
PRINT '=== Проверка подключения к Linked Server ===';

-- Проверка ILS_SOURCE
BEGIN TRY
    SELECT TOP 1 
        'ILS_SOURCE: подключение успешно' AS status,
        COUNT(*) OVER () AS total_tables
    FROM ILS_SOURCE.ils.INFORMATION_SCHEMA.TABLES;
    PRINT '  ✅ ILS_SOURCE: подключение успешно';
END TRY
BEGIN CATCH
    PRINT '  ❌ ILS_SOURCE: ошибка подключения - ' + ERROR_MESSAGE();
END CATCH

-- Проверка SK_SOURCE
BEGIN TRY
    SELECT TOP 1 
        'SK_SOURCE: подключение успешно' AS status,
        COUNT(*) OVER () AS total_tables
    FROM SK_SOURCE.sk.INFORMATION_SCHEMA.TABLES;
    PRINT '  ✅ SK_SOURCE: подключение успешно';
END TRY
BEGIN CATCH
    PRINT '  ❌ SK_SOURCE: ошибка подключения - ' + ERROR_MESSAGE();
END CATCH
GO

-- ============================================================================
-- 6. ВКЛЮЧЕНИЕ OPENDATASOURCE (если отключён)
-- ============================================================================
PRINT '=== Включение Ad Hoc Distributed Queries ===';

EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;

EXEC sp_configure 'Ad Hoc Distributed Queries', 1;
RECONFIGURE;

PRINT '  ✅ Ad Hoc Distributed Queries включены';
GO

-- ============================================================================
-- 7. ФИНАЛЬНАЯ ИНФОРМАЦИЯ
-- ============================================================================
PRINT '=== Настройка Linked Server завершена ===';
PRINT '';
PRINT 'Теперь доступны следующие Linked Server:';
PRINT '  - ILS_SOURCE (10.7.0.248/ils)';
PRINT '  - SK_SOURCE (10.7.0.248/sk)';
PRINT '';
PRINT 'Пример использования:';
PRINT '  SELECT TOP 10 * FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2;';
PRINT '  SELECT TOP 10 * FROM SK_SOURCE.sk.dbo.eks_peremer_ZX_KPP;';
GO
