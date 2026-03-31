-- ============================================================================
-- ПРОВЕРКА: dm.v_revision_by_event
-- ============================================================================

USE olap2_fixed;

-- ====== 1. Проверяем существование view ======
SELECT 
    'Существование' AS проверка,
    CASE WHEN OBJECT_ID('dm.v_revision_by_event', 'V') IS NOT NULL 
         THEN '✅ View существует' 
         ELSE '❌ View не существует' 
    END AS результат;

-- ====== 2. Если view существует, проверяем структуру ======
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'dm'
  AND TABLE_NAME = 'v_revision_by_event'
ORDER BY ORDINAL_POSITION;

-- ====== 3. Проверяем данные ======
SELECT TOP 10 *
FROM dm.v_revision_by_event;

-- ====== 4. Проверяем определение view ======
SELECT 
    OBJECT_DEFINITION(OBJECT_ID('dm.v_revision_by_event')) AS view_definition;
