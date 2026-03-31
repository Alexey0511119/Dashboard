-- ============================================================================
-- СКРИПТ ВКЛЮЧЕНИЯ ИНДЕКСОВ ПОСЛЕ ВСТАВКИ
-- База данных: olap2_fixed
-- ============================================================================
USE olap2_fixed;
GO

PRINT '=== ВКЛЮЧЕНИЕ ИНДЕКСОВ ПОСЛЕ ВСТАВКИ ===';
PRINT 'Дата: ' + CAST(GETDATE() AS NVARCHAR(50));

-- ============================================================================
-- TRANSACTION_HISTORY (30M строк - самая большая таблица)
-- ============================================================================
PRINT '';
PRINT '=== TRANSACTION_HISTORY (30M строк) ===';

PRINT 'Включение индексов на raw_.TRANSACTION_HISTORY...';
PRINT 'Это может занять 2-5 минут...';

ALTER INDEX IX_TRANSACTION_HISTORY_DATE ON raw_.TRANSACTION_HISTORY REBUILD;
PRINT '  ✅ IX_TRANSACTION_HISTORY_DATE пересоздан';

ALTER INDEX IX_TRANS_HIST_TYPE_STAMP ON raw_.TRANSACTION_HISTORY REBUILD;
PRINT '  ✅ IX_TRANS_HIST_TYPE_STAMP пересоздан';

ALTER INDEX IX_TRANS_HIST_USER ON raw_.TRANSACTION_HISTORY REBUILD;
PRINT '  ✅ IX_TRANS_HIST_USER пересоздан';

PRINT '✅ Индексы TRANSACTION_HISTORY включены';

-- ============================================================================
-- WORK_INSTRUCTION_VIEW2 (8M строк)
-- ============================================================================
PRINT '';
PRINT '=== WORK_INSTRUCTION_VIEW2 (8M строк) ===';

PRINT 'Включение индексов на raw_.WORK_INSTRUCTION_VIEW2...';
PRINT 'Это может занять 1-2 минуты...';

ALTER INDEX IX_WIV_DATE ON raw_.WORK_INSTRUCTION_VIEW2 REBUILD;
PRINT '  ✅ IX_WIV_DATE пересоздан';

ALTER INDEX IX_WI_INTERNAL ON raw_.WORK_INSTRUCTION_VIEW2 REBUILD;
PRINT '  ✅ IX_WI_INTERNAL пересоздан';

ALTER INDEX IX_WI_REF_TYPE ON raw_.WORK_INSTRUCTION_VIEW2 REBUILD;
PRINT '  ✅ IX_WI_REF_TYPE пересоздан';

ALTER INDEX IX_WI_USER_STAMP ON raw_.WORK_INSTRUCTION_VIEW2 REBUILD;
PRINT '  ✅ IX_WI_USER_STAMP пересоздан';

PRINT '✅ Индексы WORK_INSTRUCTION_VIEW2 включены';

-- ============================================================================
-- ORDER_DETAIL
-- ============================================================================
PRINT '';
PRINT '=== ORDER_DETAIL ===';

ALTER INDEX IX_ORDER_DETAIL_DATE ON raw_.ORDER_DETAIL REBUILD;
PRINT '✅ Индексы ORDER_DETAIL включены';

-- ============================================================================
-- ORDER_HEADER
-- ============================================================================
PRINT '';
PRINT '=== ORDER_HEADER ===';

ALTER INDEX IX_ORDER_HEADER_ORDER_DATE ON raw_.ORDER_HEADER REBUILD;
PRINT '✅ Индексы ORDER_HEADER включены';

-- ============================================================================
-- RECEIPT_DETAIL
-- ============================================================================
PRINT '';
PRINT '=== RECEIPT_DETAIL ===';

ALTER INDEX IX_RECEIPT_DETAIL_DATE ON raw_.RECEIPT_DETAIL REBUILD;
PRINT '✅ Индексы RECEIPT_DETAIL включены';

-- ============================================================================
-- RECEIPT_HEADER
-- ============================================================================
PRINT '';
PRINT '=== RECEIPT_HEADER ===';

ALTER INDEX IX_RECEIPT_HEADER_RECEIPT_DATE ON raw_.RECEIPT_HEADER REBUILD;
PRINT '✅ Индексы RECEIPT_HEADER включены';

-- ============================================================================
-- SHIPMENT_DETAIL
-- ============================================================================
PRINT '';
PRINT '=== SHIPMENT_DETAIL ===';

ALTER INDEX IX_SHIPMENT_DETAIL_DATE ON raw_.SHIPMENT_DETAIL REBUILD;
PRINT '✅ Индексы SHIPMENT_DETAIL включены';

-- ============================================================================
-- SHIPMENT_HEADER
-- ============================================================================
PRINT '';
PRINT '=== SHIPMENT_HEADER ===';

ALTER INDEX IX_SHIPMENT_HEADER_SHIP_DATE ON raw_.SHIPMENT_HEADER REBUILD;
PRINT '✅ Индексы SHIPMENT_HEADER включены';

-- ============================================================================
-- ОСТАЛЬНЫЕ ТАБЛИЦЫ
-- ============================================================================
PRINT '';
PRINT '=== ОСТАЛЬНЫЕ ТАБЛИЦЫ ===';

-- DOWNLOAD_ORDER_DETAIL
ALTER INDEX IX_DOWNLOAD_OD_DATE ON raw_.DOWNLOAD_ORDER_DETAIL REBUILD;

-- DOWNLOAD_ORDER_HEADER
ALTER INDEX IX_DOWNLOAD_OH_DATE ON raw_.DOWNLOAD_ORDER_HEADER REBUILD;

-- DOWNLOAD_RECEIPT_DETAIL
ALTER INDEX IX_DOWNLOAD_RD_DATE ON raw_.DOWNLOAD_RECEIPT_DETAIL REBUILD;

-- DOWNLOAD_RECEIPT_HEADER
ALTER INDEX IX_DOWNLOAD_RH_DATE ON raw_.DOWNLOAD_RECEIPT_HEADER REBUILD;

-- UPLOAD_ORDER_DETAIL
ALTER INDEX IX_UPLOAD_OD_DATE ON raw_.UPLOAD_ORDER_DETAIL REBUILD;

-- UPLOAD_ORDER_HEADER
ALTER INDEX IX_UPLOAD_OH_DATE ON raw_.UPLOAD_ORDER_HEADER REBUILD;

-- UPLOAD_RECEIPT_DETAIL
ALTER INDEX IX_UPLOAD_RD_DATE ON raw_.UPLOAD_RECEIPT_DETAIL REBUILD;

-- UPLOAD_RECEIPT_HEADER
ALTER INDEX IX_UPLOAD_RH_DATE ON raw_.UPLOAD_RECEIPT_HEADER REBUILD;

-- CYCLE_COUNT_REQUEST
ALTER INDEX IX_CYCLE_COUNT_DATE ON raw_.CYCLE_COUNT_REQUEST REBUILD;

-- labor_management
ALTER INDEX IX_LABOR_DATE ON raw_.labor_management REBUILD;

-- UPLOAD_RECEIPT_CONTAINER
ALTER INDEX IX_URC_DATE ON raw_.UPLOAD_RECEIPT_CONTAINER REBUILD;

-- eks_peremer_ZX_KPP
ALTER INDEX IX_EKS_DATE ON raw_.eks_peremer_ZX_KPP REBUILD;

-- Shtraf_Edit
ALTER INDEX IX_SHTRAF_DATE ON raw_.Shtraf_Edit REBUILD;
ALTER INDEX IX_SHTRAF_REF_USER ON raw_.Shtraf_Edit REBUILD;

PRINT '✅ Все индексы включены';

-- ============================================================================
-- ОБНОВЛЕНИЕ СТАТИСТИКИ
-- ============================================================================
PRINT '';
PRINT '=== ОБНОВЛЕНИЕ СТАТИСТИКИ ===';
PRINT 'Это может занять 1-2 минуты...';

EXEC sp_updatestats;

PRINT '✅ Статистика обновлена';

PRINT '';
PRINT '=== ГОТОВО ===';
PRINT 'Все индексы пересозданы и статистика обновлена';
