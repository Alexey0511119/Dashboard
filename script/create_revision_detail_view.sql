-- ============================================================================
-- Создание view для детализации ревизий по событию
-- dm.v_revision_detail
-- ============================================================================

USE olap2_fixed;
GO

-- Удаляем view если существует
IF OBJECT_ID('dm.v_revision_detail', 'V') IS NOT NULL
BEGIN
    PRINT 'Удаление существующего view dm.v_revision_detail...'
    DROP VIEW dm.v_revision_detail
END
GO

-- Создаем новое view
CREATE VIEW dm.v_revision_detail
AS
SELECT
    c.INTERNAL_COUNT_NUM AS internal_count_num,
    c.CONDITION AS condition,
    CASE 
        WHEN c.CONDITION = 'Open' THEN 'Открыто'
        WHEN c.CONDITION = 'Pending Review' THEN 'На согласовании'
        ELSE 'Прочее'
    END AS status_rus,
    c.ITEM AS item,
    c.LOT AS lot,
    c.LOCATION AS location,
    c.QUANTITY_COUNTED AS quantity_counted,
    c.SYSTEM_QUANTITY AS system_quantity,
    c.QUANTITY_COUNTED - c.SYSTEM_QUANTITY AS variance
FROM raw_.CYCLE_COUNT_REQUEST c
INNER JOIN raw_.WORK_INSTRUCTION_VIEW2 w 
    ON c.INTERNAL_COUNT_NUM = w.INTERNAL_COUNT_NUM
WHERE 
    w.WORK_TYPE = N'Ревизия по событию'
    AND c.CONDITION IN ('Open', 'Pending Review');
GO

-- Проверяем создание
PRINT '✅ View dm.v_revision_detail создано успешно'
GO

-- Тестовый запрос
SELECT TOP 10 * FROM dm.v_revision_detail
ORDER BY 
    CASE WHEN condition = 'Open' THEN 0 ELSE 1 END,
    internal_count_num;
GO
