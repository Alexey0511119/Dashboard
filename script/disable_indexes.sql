-- ============================================================================
-- СКРИПТ ОТКЛЮЧЕНИЯ ИНДЕКСОВ ПЕРЕД ВСТАВКОЙ
-- База данных: olap2_fixed
-- ============================================================================
USE olap2_fixed;
GO

PRINT '=== ОТКЛЮЧЕНИЕ ИНДЕКСОВ ПЕРЕД ВСТАВКОЙ ===';
PRINT 'Дата: ' + CAST(GETDATE() AS NVARCHAR(50));

-- ============================================================================
-- TRANSACTION_HISTORY (30M строк - самая большая таблица)
-- ============================================================================
PRINT '';
PRINT '=== TRANSACTION_HISTORY (30M строк) ===';

-- Отключаем некластеризованные индексы (кроме PK)
PRINT 'Отключение индексов на raw_.TRANSACTION_HISTORY...';

ALTER INDEX IX_TRANSACTION_HISTORY_DATE ON raw_.TRANSACTION_HISTORY DISABLE;
ALTER INDEX IX_TRANS_HIST_TYPE_STAMP ON raw_.TRANSACTION_HISTORY DISABLE;
ALTER INDEX IX_TRANS_HIST_USER ON raw_.TRANSACTION_HISTORY DISABLE;

PRINT '✅ Индексы отключены';

-- ============================================================================
-- WORK_INSTRUCTION_VIEW2 (8M строк)
-- ============================================================================
PRINT '';
PRINT '=== WORK_INSTRUCTION_VIEW2 (8M строк) ===';

PRINT 'Отключение индексов на raw_.WORK_INSTRUCTION_VIEW2...';

ALTER INDEX IX_WIV_DATE ON raw_.WORK_INSTRUCTION_VIEW2 DISABLE;
ALTER INDEX IX_WI_INTERNAL ON raw_.WORK_INSTRUCTION_VIEW2 DISABLE;
ALTER INDEX IX_WI_REF_TYPE ON raw_.WORK_INSTRUCTION_VIEW2 DISABLE;
ALTER INDEX IX_WI_USER_STAMP ON raw_.WORK_INSTRUCTION_VIEW2 DISABLE;

PRINT '✅ Индексы отключены';

-- ============================================================================
-- ORDER_DETAIL (пустая, но для консистентности)
-- ============================================================================
PRINT '';
PRINT '=== ORDER_DETAIL ===';

PRINT 'Отключение индексов на raw_.ORDER_DETAIL...';

ALTER INDEX IX_ORDER_DETAIL_DATE ON raw_.ORDER_DETAIL DISABLE;

PRINT '✅ Индексы отключены';

-- ============================================================================
-- ORDER_HEADER (пустая, но для консистентности)
-- ============================================================================
PRINT '';
PRINT '=== ORDER_HEADER ===';

PRINT 'Отключение индексов на raw_.ORDER_HEADER...';

ALTER INDEX IX_ORDER_HEADER_ORDER_DATE ON raw_.ORDER_HEADER DISABLE;

PRINT '✅ Индексы отключены';

-- ============================================================================
-- RECEIPT_DETAIL
-- ============================================================================
PRINT '';
PRINT '=== RECEIPT_DETAIL ===';

PRINT 'Отключение индексов на raw_.RECEIPT_DETAIL...';

ALTER INDEX IX_RECEIPT_DETAIL_DATE ON raw_.RECEIPT_DETAIL DISABLE;

PRINT '✅ Индексы отключены';

-- ============================================================================
-- RECEIPT_HEADER
-- ============================================================================
PRINT '';
PRINT '=== RECEIPT_HEADER ===';

PRINT 'Отключение индексов на raw_.RECEIPT_HEADER...';

ALTER INDEX IX_RECEIPT_HEADER_RECEIPT_DATE ON raw_.RECEIPT_HEADER DISABLE;

PRINT '✅ Индексы отключены';

-- ============================================================================
-- SHIPMENT_DETAIL
-- ============================================================================
PRINT '';
PRINT '=== SHIPMENT_DETAIL ===';

PRINT 'Отключение индексов на raw_.SHIPMENT_DETAIL...';

ALTER INDEX IX_SHIPMENT_DETAIL_DATE ON raw_.SHIPMENT_DETAIL DISABLE;

PRINT '✅ Индексы отключены';

-- ============================================================================
-- SHIPMENT_HEADER
-- ============================================================================
PRINT '';
PRINT '=== SHIPMENT_HEADER ===';

PRINT 'Отключение индексов на raw_.SHIPMENT_HEADER...';

ALTER INDEX IX_SHIPMENT_HEADER_SHIP_DATE ON raw_.SHIPMENT_HEADER DISABLE;

PRINT '✅ Индексы отключены';

-- ============================================================================
-- ОСТАЛЬНЫЕ ТАБЛИЦЫ
-- ============================================================================
PRINT '';
PRINT '=== ОСТАЛЬНЫЕ ТАБЛИЦЫ ===';

-- DOWNLOAD_ORDER_DETAIL
ALTER INDEX IX_DOWNLOAD_OD_DATE ON raw_.DOWNLOAD_ORDER_DETAIL DISABLE;

-- DOWNLOAD_ORDER_HEADER
ALTER INDEX IX_DOWNLOAD_OH_DATE ON raw_.DOWNLOAD_ORDER_HEADER DISABLE;

-- DOWNLOAD_RECEIPT_DETAIL
ALTER INDEX IX_DOWNLOAD_RD_DATE ON raw_.DOWNLOAD_RECEIPT_DETAIL DISABLE;

-- DOWNLOAD_RECEIPT_HEADER
ALTER INDEX IX_DOWNLOAD_RH_DATE ON raw_.DOWNLOAD_RECEIPT_HEADER DISABLE;

-- UPLOAD_ORDER_DETAIL
ALTER INDEX IX_UPLOAD_OD_DATE ON raw_.UPLOAD_ORDER_DETAIL DISABLE;

-- UPLOAD_ORDER_HEADER
ALTER INDEX IX_UPLOAD_OH_DATE ON raw_.UPLOAD_ORDER_HEADER DISABLE;

-- UPLOAD_RECEIPT_DETAIL
ALTER INDEX IX_UPLOAD_RD_DATE ON raw_.UPLOAD_RECEIPT_DETAIL DISABLE;

-- UPLOAD_RECEIPT_HEADER
ALTER INDEX IX_UPLOAD_RH_DATE ON raw_.UPLOAD_RECEIPT_HEADER DISABLE;

-- CYCLE_COUNT_REQUEST
ALTER INDEX IX_CYCLE_COUNT_DATE ON raw_.CYCLE_COUNT_REQUEST DISABLE;

-- labor_management
ALTER INDEX IX_LABOR_DATE ON raw_.labor_management DISABLE;

-- UPLOAD_RECEIPT_CONTAINER
ALTER INDEX IX_URC_DATE ON raw_.UPLOAD_RECEIPT_CONTAINER DISABLE;

-- eks_peremer_ZX_KPP
ALTER INDEX IX_EKS_DATE ON raw_.eks_peremer_ZX_KPP DISABLE;

-- Shtraf_Edit
ALTER INDEX IX_SHTRAF_DATE ON raw_.Shtraf_Edit DISABLE;
ALTER INDEX IX_SHTRAF_REF_USER ON raw_.Shtraf_Edit DISABLE;

PRINT '✅ Все индексы отключены';

PRINT '';
PRINT '=== ГОТОВО ===';
PRINT 'Теперь можно выполнять вставку данных';
PRINT 'После вставки выполните: enable_indexes.sql';
