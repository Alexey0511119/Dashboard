-- ============================================================================
-- ПРОВЕРКА: Данные для диаграмм ячеек хранения
-- ============================================================================

USE olap2_fixed;

-- ====== 1. Проверяем данные в fact_location_snapshot ======
SELECT 
    'fact_location_snapshot' AS источник,
    status,
    COUNT(*) AS количество
FROM dwh.fact_location_snapshot
GROUP BY status;

-- ====== 2. Проверяем данные для диаграммы ======
SELECT
    COUNT(*) AS total_cells,
    SUM(CASE WHEN status = 'Available' THEN 1 ELSE 0 END) AS empty_cells,
    SUM(CASE WHEN status = 'Storage' THEN 1 ELSE 0 END) AS occupied_cells,
    CAST(SUM(CASE WHEN status = 'Available' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS DECIMAL(5,1)) AS empty_percent,
    CAST(SUM(CASE WHEN status = 'Storage' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS DECIMAL(5,1)) AS occupied_percent
FROM dwh.fact_location_snapshot
WHERE date_key = CAST(GETDATE() AS DATE);

-- ====== 3. Проверяем данные по типам ячеек ======
SELECT TOP 10
    location_type,
    COUNT(*) AS total_count,
    SUM(CASE WHEN status = 'Available' THEN 1 ELSE 0 END) AS empty_count
FROM dwh.fact_location_snapshot
WHERE date_key = CAST(GETDATE() AS DATE)
GROUP BY location_type
ORDER BY total_count DESC;
