-- ============================================================================
-- Добавление полей REJECTION_NOTE и ORDER_TYPE в таблицу отклоненных строк
-- ============================================================================

USE olap2_fixed;
GO

PRINT '=== Добавление полей REJECTION_NOTE и ORDER_TYPE ===';
PRINT 'Дата: ' + CAST(GETDATE() AS NVARCHAR(50));

-- ====== ШАГ 1: Добавление поля REJECTION_NOTE ======
PRINT 'Добавление поля REJECTION_NOTE в dwh.rejected_lines_detail...';

IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('dwh.rejected_lines_detail') 
    AND name = 'REJECTION_NOTE'
)
BEGIN
    ALTER TABLE dwh.rejected_lines_detail 
    ADD REJECTION_NOTE NVARCHAR(MAX) NULL;
    
    PRINT '  ✅ Поле REJECTION_NOTE добавлено в dwh.rejected_lines_detail';
END
ELSE
BEGIN
    PRINT '  ℹ️ Поле REJECTION_NOTE уже существует в dwh.rejected_lines_detail';
END

-- ====== ШАГ 2: Добавление поля ORDER_TYPE ======
PRINT 'Добавление поля ORDER_TYPE в dwh.rejected_lines_detail...';

IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('dwh.rejected_lines_detail') 
    AND name = 'ORDER_TYPE'
)
BEGIN
    ALTER TABLE dwh.rejected_lines_detail 
    ADD ORDER_TYPE NVARCHAR(50) NULL;
    
    PRINT '  ✅ Поле ORDER_TYPE добавлено в dwh.rejected_lines_detail';
END
ELSE
BEGIN
    PRINT '  ℹ️ Поле ORDER_TYPE уже существует в dwh.rejected_lines_detail';
END

-- ====== ШАГ 3: Обновление VIEW dm.v_rejected_lines_detail ======
PRINT 'Обновление VIEW dm.v_rejected_lines_detail...';
GO

CREATE OR ALTER VIEW dm.v_rejected_lines_detail
AS
SELECT
    SHIPMENT_ID,
    ORDER_TYPE,  -- Добавлено новое поле
    ITEM,
    ITEM_DESC,
    REQUESTED_QTY,
    QUANTITY_UM,
    PICK_LOC,
    PICK_ZONE,
    DATE_TIME_STAMP,
    REJECTION_NOTE  -- Добавлено новое поле
FROM dwh.rejected_lines_detail;
GO

PRINT '  ✅ VIEW dm.v_rejected_lines_detail обновлен';

-- ====== ШАГ 4: Проверка ======
PRINT 'Проверка...';

SELECT TOP 5 
    SHIPMENT_ID,
    ORDER_TYPE,
    ITEM,
    REJECTION_NOTE,
    DATE_TIME_STAMP
FROM dm.v_rejected_lines_detail
WHERE REJECTION_NOTE IS NOT NULL
ORDER BY DATE_TIME_STAMP DESC;

PRINT '=== ГОТОВО ===';
GO
