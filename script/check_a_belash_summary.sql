-- ============================================================================
-- ПРОВЕРКА: Данные из dm.employee_work_idle_summary для a.belash
-- Период: с 01.03.2026
-- ============================================================================

USE olap2_fixed;

-- ====== Все рассчитанные строки для a.belash ======
SELECT 
    user_name AS [Логин],
    fio AS [ФИО],
    date_key AS [Дата],
    first_op_time AS [Первая операция],
    last_op_time AS [Последняя операция],
    total_period_min AS [Общий период (мин)],
    total_work_min AS [Время работы (мин)],
    total_idle_min AS [Время простоя (мин)],
    work_percentage AS [Работа %],
    idle_percentage AS [Простой %],
    idle_10_20 AS [Простой 10-20 мин],
    idle_20_30 AS [Простой 20-30 мин],
    idle_30_60 AS [Простой 30-60 мин],
    idle_60plus AS [Простой 60+ мин]
FROM dm.employee_work_idle_summary
WHERE user_name = 'a.belash'
ORDER BY date_key;
