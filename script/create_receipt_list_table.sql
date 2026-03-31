-- ============================================================================
-- Создание таблицы dwh.receipt_list для списка приходов
-- ============================================================================

USE olap2_fixed;
GO

-- Удаляем таблицу если существует (для пересоздания)
IF OBJECT_ID('dwh.receipt_list', 'U') IS NOT NULL
BEGIN
    PRINT 'Удаление существующей таблицы dwh.receipt_list...'
    DROP TABLE dwh.receipt_list
END
GO

-- Создаем новую таблицу
CREATE TABLE dwh.receipt_list (
    -- Основные поля из RECEIPT_HEADER
    RECEIPT_ID NVARCHAR(50) NOT NULL,           -- Номер в WMS
    ERP_ORDER_NUM NVARCHAR(50),                 -- Номер Веста
    SOURCE_NAME NVARCHAR(200),                  -- Поставщик
    RECEIPT_TYPE NVARCHAR(50),                  -- Тип прихода
    CREATION_DATE_TIME_STAMP DATETIME,          -- Дата создания
    TOTAL_LINES INT,                            -- Строк прихода
    TRAILING_STS INT,                           -- Для логики статусов
    LEADING_STS INT,                            -- Для логики статусов
    
    -- Вычисляемые поля
    STATUS NVARCHAR(50),                        -- Статус прихода
    EXECUTION_TIME NVARCHAR(50),                -- Время выполнения
    OVERDUE_IN NVARCHAR(50),                    -- Просрочится через
    
    -- Служебные поля
    LOADED_AT DATETIME DEFAULT GETDATE(),       -- Время загрузки
    ROW_NUM INT IDENTITY(1,1)                   -- Порядковый номер
)
GO

-- Создаем индексы для ускорения выборки
CREATE INDEX IX_receipt_list_status 
ON dwh.receipt_list (TRAILING_STS, LEADING_STS)
GO

CREATE INDEX IX_receipt_list_creation_date 
ON dwh.receipt_list (CREATION_DATE_TIME_STAMP DESC)
GO

CREATE INDEX IX_receipt_list_loaded_at 
ON dwh.receipt_list (LOADED_AT DESC)
GO

-- Проверяем создание
PRINT '✅ Таблица dwh.receipt_list создана успешно'
PRINT 'Созданные индексы:'
PRINT '  - IX_receipt_list_status (TRAILING_STS, LEADING_STS)'
PRINT '  - IX_receipt_list_creation_date (CREATION_DATE_TIME_STAMP DESC)'
PRINT '  - IX_receipt_list_loaded_at (LOADED_AT DESC)'
GO

-- Показываем информацию о таблице
EXEC sp_help 'dwh.receipt_list'
GO
