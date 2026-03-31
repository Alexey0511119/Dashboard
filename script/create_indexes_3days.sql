-- ============================================================================
-- ИНДЕКСЫ ДЛЯ ОПТИМИЗАЦИИ 3-ДНЕВНОГО ЦИКЛА ОБНОВЛЕНИЯ
-- Скрипт создаёт необходимые индексы для ускорения выполнения ETL
-- ============================================================================
USE olap2_fixed;
GO

PRINT '=== СОЗДАНИЕ ИНДЕКСОВ ДЛЯ ОПТИМИЗАЦИИ ===';
PRINT 'Дата: ' + CAST(GETDATE() AS NVARCHAR(50));

-- ============================================================================
-- ИНДЕКСЫ ДЛЯ raw_.ТАБЛИЦ (источники данных)
-- ============================================================================
PRINT '';
PRINT '=== Индексы для raw_.таблиц ===';

-- WORK_INSTRUCTION_VIEW2 - основная таблица операций
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_WIV2_CONDITION_TYPE_DATE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_WIV2_CONDITION_TYPE_DATE ON raw_.WORK_INSTRUCTION_VIEW2 (
        CONDITION, INSTRUCTION_TYPE, DATE_TIME_STAMP
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_WIV2_CONDITION_TYPE_DATE';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_WIV2_REFERENCE_ID')
BEGIN
    CREATE NONCLUSTERED INDEX IX_WIV2_REFERENCE_ID ON raw_.WORK_INSTRUCTION_VIEW2 (
        REFERENCE_ID
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_WIV2_REFERENCE_ID';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_WIV2_WORK_TYPE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_WIV2_WORK_TYPE ON raw_.WORK_INSTRUCTION_VIEW2 (
        WORK_TYPE
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_WIV2_WORK_TYPE';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_WIV2_USER_STAMP')
BEGIN
    CREATE NONCLUSTERED INDEX IX_WIV2_USER_STAMP ON raw_.WORK_INSTRUCTION_VIEW2 (
        USER_STAMP
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_WIV2_USER_STAMP';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_WIV2_INTERNAL_NUM')
BEGIN
    CREATE NONCLUSTERED INDEX IX_WIV2_INTERNAL_NUM ON raw_.WORK_INSTRUCTION_VIEW2 (
        INTERNAL_NUM
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_WIV2_INTERNAL_NUM';
END

-- TRANSACTION_HISTORY - для приемки и transaction_events
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_TRANSACTION_HISTORY_TYPE_DATE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_TRANSACTION_HISTORY_TYPE_DATE ON raw_.TRANSACTION_HISTORY (
        TRANSACTION_TYPE, DATE_TIME_STAMP
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_TRANSACTION_HISTORY_TYPE_DATE';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_TRANSACTION_HISTORY_USER')
BEGIN
    CREATE NONCLUSTERED INDEX IX_TRANSACTION_HISTORY_USER ON raw_.TRANSACTION_HISTORY (
        USER_STAMP
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_TRANSACTION_HISTORY_USER';
END

-- USER_CADR_EDIT - для JOIN с сотрудниками
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_USER_CADR_EDIT_USER_NAME')
BEGIN
    CREATE NONCLUSTERED INDEX IX_USER_CADR_EDIT_USER_NAME ON raw_.USER_CADR_EDIT (
        user_name
    ) INCLUDE (fio, smena, brigada, position, deleted)
    WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_USER_CADR_EDIT_USER_NAME';
END

-- sdelka_price - для определения цен операций
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_SDELKA_PRICE_WORK_TYPE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_SDELKA_PRICE_WORK_TYPE ON raw_.sdelka_price (
        work_type
    ) INCLUDE (price)
    WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_SDELKA_PRICE_WORK_TYPE';
END

-- ITEM - для JOIN с номенклатурой
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_ITEM_ITEM')
BEGIN
    CREATE NONCLUSTERED INDEX IX_ITEM_ITEM ON raw_.ITEM (
        ITEM
    ) INCLUDE (DESCRIPTION, ITEM_CATEGORY1, user_def1, ITEM_CATEGORY9)
    WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_ITEM_ITEM';
END

-- SHIPMENT_HEADER - для заказов
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_SHIPMENT_HEADER_ID')
BEGIN
    CREATE NONCLUSTERED INDEX IX_SHIPMENT_HEADER_ID ON raw_.SHIPMENT_HEADER (
        SHIPMENT_ID
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_SHIPMENT_HEADER_ID';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_SHIPMENT_INTERNAL_NUM')
BEGIN
    CREATE NONCLUSTERED INDEX IX_SHIPMENT_INTERNAL_NUM ON raw_.SHIPMENT_HEADER (
        INTERNAL_SHIPMENT_NUM
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_SHIPMENT_INTERNAL_NUM';
END

-- SHIPMENT_DETAIL - для отгрузочных позиций
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_SHIPMENT_DETAIL_STATUS')
BEGIN
    CREATE NONCLUSTERED INDEX IX_SHIPMENT_DETAIL_STATUS ON raw_.SHIPMENT_DETAIL (
        STATUS1, DATE_TIME_STAMP
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_SHIPMENT_DETAIL_STATUS';
END

-- UPLOAD_RECEIPT_HEADER - для приходов
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_UPLOAD_RECEIPT_HEADER_ID')
BEGIN
    CREATE NONCLUSTERED INDEX IX_UPLOAD_RECEIPT_HEADER_ID ON raw_.UPLOAD_RECEIPT_HEADER (
        RECEIPT_ID
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_UPLOAD_RECEIPT_HEADER_ID';
END

-- UPLOAD_RECEIPT_CONTAINER - для контейнеров приходов
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_UPLOAD_RECEIPT_CONTAINER_LINK')
BEGIN
    CREATE NONCLUSTERED INDEX IX_UPLOAD_RECEIPT_CONTAINER_LINK ON raw_.UPLOAD_RECEIPT_CONTAINER (
        INTERFACE_LINK_ID, Parent
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_UPLOAD_RECEIPT_CONTAINER_LINK';
END

-- Shtraf_Edit - для штрафов
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_SHTRAF_EDIT_USER_DATE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_SHTRAF_EDIT_USER_DATE ON raw_.Shtraf_Edit (
        [user], date_time_stamp
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_SHTRAF_EDIT_USER_DATE';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_SHTRAF_EDIT_REFERENCE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_SHTRAF_EDIT_REFERENCE ON raw_.Shtraf_Edit (
        reference_id
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_SHTRAF_EDIT_REFERENCE';
END

-- labor_management - для грузчиков
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_LABOR_MANAGEMENT_USER_DATE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_LABOR_MANAGEMENT_USER_DATE ON raw_.labor_management (
        USER_NAME, date_time_stamp
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_LABOR_MANAGEMENT_USER_DATE';
END

-- eks_peremer_ZX_KPP - для перемера
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_EKS_PEREMER_DATE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_EKS_PEREMER_DATE ON raw_.eks_peremer_ZX_KPP (
        date_time_stamp
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_EKS_PEREMER_DATE';
END

-- LOCATION - для локаций
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_LOCATION_LOC_DATE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_LOCATION_LOC_DATE ON raw_.LOCATION (
        LOCATION, DATE_TIME_STAMP
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_LOCATION_LOC_DATE';
END

-- LOCATION_INVENTORY - для занятых локаций
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_LOCATION_INVENTORY_LOC')
BEGIN
    CREATE NONCLUSTERED INDEX IX_LOCATION_INVENTORY_LOC ON raw_.LOCATION_INVENTORY (
        LOCATION
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_LOCATION_INVENTORY_LOC';
END

-- ============================================================================
-- ИНДЕКСЫ ДЛЯ dwh.ТАБЛИЦ (целевые таблицы)
-- ============================================================================
PRINT '';
PRINT '=== Индексы для dwh.таблиц ===';

-- operations_enriched - главная таблица операций
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_OPERATIONS_ENRICHED_DATE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_OPERATIONS_ENRICHED_DATE ON dwh.operations_enriched (
        date
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_OPERATIONS_ENRICHED_DATE';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_OPERATIONS_ENRICHED_REF_ID')
BEGIN
    CREATE NONCLUSTERED INDEX IX_OPERATIONS_ENRICHED_REF_ID ON dwh.operations_enriched (
        REFERENCE_ID
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_OPERATIONS_ENRICHED_REF_ID';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_OPERATIONS_ENRICHED_USER')
BEGIN
    CREATE NONCLUSTERED INDEX IX_OPERATIONS_ENRICHED_USER ON dwh.operations_enriched (
        user_name
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_OPERATIONS_ENRICHED_USER';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_OPERATIONS_ENRICHED_WORK_TYPE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_OPERATIONS_ENRICHED_WORK_TYPE ON dwh.operations_enriched (
        WORK_TYPE
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_OPERATIONS_ENRICHED_WORK_TYPE';
END

-- fact_operation - фактовая таблица операций
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_FACT_OPERATION_DATE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_FACT_OPERATION_DATE ON dwh.fact_operation (
        date_key
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_FACT_OPERATION_DATE';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_FACT_OPERATION_EMPLOYEE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_FACT_OPERATION_EMPLOYEE ON dwh.fact_operation (
        employee_id
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_FACT_OPERATION_EMPLOYEE';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_FACT_OPERATION_REF')
BEGIN
    CREATE NONCLUSTERED INDEX IX_FACT_OPERATION_REF ON dwh.fact_operation (
        reference_id
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_FACT_OPERATION_REF';
END

-- fact_penalty - фактовая таблица штрафов
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_FACT_PENALTY_DATE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_FACT_PENALTY_DATE ON dwh.fact_penalty (
        date_key
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_FACT_PENALTY_DATE';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_FACT_PENALTY_EMPLOYEE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_FACT_PENALTY_EMPLOYEE ON dwh.fact_penalty (
        employee_id
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_FACT_PENALTY_EMPLOYEE';
END

-- orders_enriched - заказы
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_ORDERS_ENRICHED_DATE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_ORDERS_ENRICHED_DATE ON dwh.orders_enriched (
        date
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_ORDERS_ENRICHED_DATE';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_ORDERS_ENRICHED_SHIPMENT')
BEGIN
    CREATE NONCLUSTERED INDEX IX_ORDERS_ENRICHED_SHIPMENT ON dwh.orders_enriched (
        SHIPMENT_ID
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_ORDERS_ENRICHED_SHIPMENT';
END

-- fines_enriched - штрафы
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_FINES_ENRICHED_DATE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_FINES_ENRICHED_DATE ON dwh.fines_enriched (
        date
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_FINES_ENRICHED_DATE';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_FINES_ENRICHED_USER')
BEGIN
    CREATE NONCLUSTERED INDEX IX_FINES_ENRICHED_USER ON dwh.fines_enriched (
        user_name
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_FINES_ENRICHED_USER';
END

-- transaction_events - события транзакций
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_TRANSACTION_EVENTS_DATE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_TRANSACTION_EVENTS_DATE ON dwh.transaction_events (
        date_key
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_TRANSACTION_EVENTS_DATE';
END

-- placement_cache - кэш размещений
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_PLACEMENT_CACHE_REF')
BEGIN
    CREATE NONCLUSTERED INDEX IX_PLACEMENT_CACHE_REF ON dwh.placement_cache (
        REFERENCE_ID
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_PLACEMENT_CACHE_REF';
END

-- pick_cache - кэш отборов
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_PICK_CACHE_PARENT')
BEGIN
    CREATE NONCLUSTERED INDEX IX_PICK_CACHE_PARENT ON dwh.pick_cache (
        PARENT_INSTR
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_PICK_CACHE_PARENT';
END

-- orders_timeliness - своевременность заказов
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_ORDERS_TIMELINESS_DATE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_ORDERS_TIMELINESS_DATE ON dwh.orders_timeliness (
        date
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_ORDERS_TIMELINESS_DATE';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_ORDERS_TIMELINESS_SHIPMENT')
BEGIN
    CREATE NONCLUSTERED INDEX IX_ORDERS_TIMELINESS_SHIPMENT ON dwh.orders_timeliness (
        SHIPMENT_ID
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_ORDERS_TIMELINESS_SHIPMENT';
END

-- cube_shipment_detail - детали отгрузки
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_CUBE_SHIPMENT_DETAIL_DATE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_CUBE_SHIPMENT_DETAIL_DATE ON dwh.cube_shipment_detail (
        DATE_TIME_STAMP
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_CUBE_SHIPMENT_DETAIL_DATE';
END

-- rejected_lines_detail - отклоненные позиции
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_REJECTED_LINES_DETAIL_DATE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_REJECTED_LINES_DETAIL_DATE ON dwh.rejected_lines_detail (
        DATE_TIME_STAMP
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_REJECTED_LINES_DETAIL_DATE';
END

-- ============================================================================
-- ИНДЕКСЫ ДЛЯ dm.ТАБЛИЦ (справочники)
-- ============================================================================
PRINT '';
PRINT '=== Индексы для dm.таблиц ===';

-- dim_employee - справочник сотрудников
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_DIM_EMPLOYEE_USER_NAME')
BEGIN
    CREATE NONCLUSTERED INDEX IX_DIM_EMPLOYEE_USER_NAME ON dm.dim_employee (
        user_name
    ) INCLUDE (fio, smena, brigada, position)
    WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_DIM_EMPLOYEE_USER_NAME';
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_DIM_EMPLOYEE_ACTIVE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_DIM_EMPLOYEE_ACTIVE ON dm.dim_employee (
        is_active
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_DIM_EMPLOYEE_ACTIVE';
END

-- dim_work_type - справочник видов работ
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_DIM_WORK_TYPE_NAME')
BEGIN
    CREATE NONCLUSTERED INDEX IX_DIM_WORK_TYPE_NAME ON dm.dim_work_type (
        work_type_name
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_DIM_WORK_TYPE_NAME';
END

-- employee_work_idle_summary - простой сотрудников
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_EMPLOYEE_WORK_IDLE_DATE')
BEGIN
    CREATE NONCLUSTERED INDEX IX_EMPLOYEE_WORK_IDLE_DATE ON dm.employee_work_idle_summary (
        date_key
    ) WITH (ONLINE = ON);
    PRINT '  ✅ Создан IX_EMPLOYEE_WORK_IDLE_DATE';
END

-- ============================================================================
-- СТАТИСТИКА
-- ============================================================================
PRINT '';
PRINT '=== ОБНОВЛЕНИЕ СТАТИСТИКИ ===';

-- Обновляем статистику для важных таблиц
UPDATE STATISTICS raw_.WORK_INSTRUCTION_VIEW2 WITH FULLSCAN;
PRINT '  ✅ Обновлена статистика raw_.WORK_INSTRUCTION_VIEW2';

UPDATE STATISTICS raw_.TRANSACTION_HISTORY WITH FULLSCAN;
PRINT '  ✅ Обновлена статистика raw_.TRANSACTION_HISTORY';

UPDATE STATISTICS dwh.operations_enriched WITH FULLSCAN;
PRINT '  ✅ Обновлена статистика dwh.operations_enriched';

UPDATE STATISTICS dwh.fact_operation WITH FULLSCAN;
PRINT '  ✅ Обновлена статистика dwh.fact_operation';

UPDATE STATISTICS dwh.fact_penalty WITH FULLSCAN;
PRINT '  ✅ Обновлена статистика dwh.fact_penalty';

-- ============================================================================
-- ИТОГИ
-- ============================================================================
PRINT '';
PRINT '=== СОЗДАНИЕ ИНДЕКСОВ ЗАВЕРШЕНО ===';
PRINT 'Дата: ' + CAST(GETDATE() AS NVARCHAR(50));
PRINT '';
PRINT '📊 Для применения изменений выполните:';
PRINT '   EXEC sp_updatestats;');
PRINT '';
PRINT '⚠️  Внимание: Создание индексов может занять несколько минут!';
PRINT '⚠️  Рекомендуется запускать в период низкой нагрузки.';
