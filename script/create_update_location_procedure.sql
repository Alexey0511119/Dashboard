-- ============================================================================
-- ХРАНИМАЯ ПРОЦЕДУРА ДЛЯ ОБНОВЛЕНИЯ dwh.fact_location_snapshot из raw_.LOCATION
-- Вызывается из Python-скрипта каждые 30-60 секунд
-- ============================================================================

USE olap2_fixed;
GO

PRINT 'Создание процедуры dwh.sp_update_location_snapshot...';
GO

-- Добавить поле last_modified, если нет
IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('dwh.fact_location_snapshot') 
    AND name = 'last_modified'
)
BEGIN
    PRINT 'Добавление поля last_modified...';
    ALTER TABLE dwh.fact_location_snapshot ADD last_modified DATETIME2 NULL;
END
GO

-- Создать индекс, если нет
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes 
    WHERE object_id = OBJECT_ID('dwh.fact_location_snapshot') 
    AND name = 'IX_location_snapshot_modified'
)
BEGIN
    PRINT 'Создание индекса IX_location_snapshot_modified...';
    CREATE INDEX IX_location_snapshot_modified 
    ON dwh.fact_location_snapshot (location, last_modified)
    INCLUDE (status, location_type, allocation_zone, work_zone, locating_zone);
END
GO

-- ============================================================================
-- ПРОЦЕДУРА ОБНОВЛЕНИЯ
-- ============================================================================
CREATE OR ALTER PROCEDURE dwh.sp_update_location_snapshot
    @buffer_minutes INT = 5,  -- Буфер времени на случай задержек
    @debug BIT = 0            -- Режим отладки (показывать детали)
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @last_timestamp DATETIME2;
    DECLARE @buffer_timestamp DATETIME2;
    DECLARE @rows_inserted INT = 0;
    DECLARE @rows_updated INT = 0;
    DECLARE @start_time DATETIME2 = GETDATE();
    
    PRINT '============================================================';
    PRINT '🚀 Начало обновления dwh.fact_location_snapshot';
    PRINT '============================================================';
    
    -- 1. Получить последнее время изменения из dwh
    SELECT @last_timestamp = MAX(last_modified)
    FROM dwh.fact_location_snapshot
    WHERE last_modified IS NOT NULL;
    
    -- Если нет данных, используем дату 30 дней назад
    IF @last_timestamp IS NULL
    BEGIN
        SET @last_timestamp = DATEADD(DAY, -30, GETDATE());
        PRINT '📍 Нет данных в таблице, загружаем за 30 дней';
    END
    ELSE
    BEGIN
        PRINT '📍 Последнее изменение: ' + CONVERT(NVARCHAR(50), @last_timestamp, 121);
    END
    
    -- 2. Добавить буфер
    SET @buffer_timestamp = DATEADD(MINUTE, -@buffer_minutes, @last_timestamp);
    PRINT '📤 Запрос изменений с: ' + CONVERT(NVARCHAR(50), @buffer_timestamp, 121);
    
    -- 3. Создать временную таблицу с изменениями из raw_.LOCATION
    IF OBJECT_ID('tempdb..#location_changes') IS NOT NULL
        DROP TABLE #location_changes;
    
    SELECT
        r.LOCATION AS location_id,
        r.LOCATION_TYPE AS location_type,
        r.ALLOCATION_ZONE AS allocation_zone,
        r.WORK_ZONE AS work_zone,
        r.LOCATING_ZONE AS locating_zone,
        r.LOCATION_STS AS location_status,
        CASE
            WHEN r.LOCATION_STS = 'Empty' THEN 'Empty'
            WHEN r.LOCATION_STS IN ('Picking', 'Storage') THEN 'Occupied'
            ELSE 'Available'
        END AS status,
        r.DATE_TIME_STAMP AS last_modified
    INTO #location_changes
    FROM raw_.LOCATION r
    WHERE
        r.DATE_TIME_STAMP > @buffer_timestamp
        AND r.LOCATION_STS IS NOT NULL
        AND r.LOCATION_STS != 'Frozen'
        AND (r.LOCATION_CLASS = 'Inventory' OR r.LOCATION_CLASS IS NULL)
        AND r.LOCATION_TYPE NOT IN ('Брак/бой DMG', 'Напольная', 'Улица KC', 'Ячейки KSP');
    
    DECLARE @total_changes INT = (SELECT COUNT(*) FROM #location_changes);
    PRINT '✅ Найдено изменений: ' + CAST(@total_changes AS NVARCHAR);
    
    IF @total_changes = 0
    BEGIN
        PRINT 'ℹ️ Нет изменений для загрузки';
        PRINT '============================================================';
        RETURN;
    END
    
    -- 4. Обновить существующие записи
    UPDATE dwh
    SET 
        dwh.status = src.status,
        dwh.location_type = src.location_type,
        dwh.allocation_zone = src.allocation_zone,
        dwh.work_zone = src.work_zone,
        dwh.locating_zone = src.locating_zone,
        dwh.last_modified = src.last_modified,
        dwh.date_key = CAST(GETDATE() AS DATE)
    FROM dwh.fact_location_snapshot dwh
    INNER JOIN #location_changes src ON dwh.location = src.location_id;
    
    SET @rows_updated = @@ROWCOUNT;
    PRINT '🔄 Обновлено записей: ' + CAST(@rows_updated AS NVARCHAR);
    
    -- 5. Вставить новые записи
    INSERT INTO dwh.fact_location_snapshot 
    (date_key, location, status, location_type, locating_zone, allocation_zone, work_zone, source_system, last_modified)
    SELECT
        CAST(GETDATE() AS DATE),
        src.location_id,
        src.status,
        src.location_type,
        src.locating_zone,
        src.allocation_zone,
        src.work_zone,
        'WMS',
        src.last_modified
    FROM #location_changes src
    LEFT JOIN dwh.fact_location_snapshot dwh ON src.location_id = dwh.location
    WHERE dwh.location IS NULL;
    
    SET @rows_inserted = @@ROWCOUNT;
    PRINT '➕ Вставлено записей: ' + CAST(@rows_inserted AS NVARCHAR);
    
    -- 6. Вывести статистику
    DECLARE @duration_ms INT = DATEDIFF(MILLISECOND, @start_time, GETDATE());
    
    PRINT '============================================================';
    PRINT '✅ Обновление завершено';
    PRINT '   Всего обработано: ' + CAST(@rows_inserted + @rows_updated AS NVARCHAR);
    PRINT '   Вставлено: ' + CAST(@rows_inserted AS NVARCHAR);
    PRINT '   Обновлено: ' + CAST(@rows_updated AS NVARCHAR);
    PRINT '   Время выполнения: ' + CAST(@duration_ms AS NVARCHAR) + ' мс';
    PRINT '============================================================';
    
    -- 7. Режим отладки - показать детали
    IF @debug = 1
    BEGIN
        PRINT '';
        PRINT '📊 Детализация по статусам (изменения):';
        SELECT 
            status, 
            COUNT(*) AS количество
        FROM #location_changes
        GROUP BY status;
        
        PRINT '';
        PRINT '📊 Итоговое состояние таблицы:';
        SELECT 
            status, 
            COUNT(*) AS количество
        FROM dwh.fact_location_snapshot
        GROUP BY status;
    END
    
    -- Очистка
    DROP TABLE #location_changes;
END
GO

PRINT '✅ Процедура dwh.sp_update_location_snapshot создана';
GO

-- ============================================================================
-- ТЕСТИРОВАНИЕ ПРОЦЕДУРЫ
-- ============================================================================
PRINT '';
PRINT 'Тестирование процедуры...';
PRINT '';

-- Запустить с отладкой
EXEC dwh.sp_update_location_snapshot @buffer_minutes = 5, @debug = 1;
GO

PRINT '';
PRINT '✅ Готово!';
PRINT '';
PRINT 'Теперь можно запускать процедуру из Python-скрипта:';
PRINT '  EXEC dwh.sp_update_location_snapshot;';
PRINT '';
