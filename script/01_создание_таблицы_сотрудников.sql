-- ============================================================================
-- ЧАСТЬ 1: СОЗДАНИЕ ТАБЛИЦЫ dm.employees_on_shift_raw
-- Схема: dm (olap2_fixed)
-- Источник данных: TRANSACTION_HISTORY (DATE_TIME_STAMP, USER_NAME)
-- ============================================================================

USE olap2_fixed;

IF OBJECT_ID('dm.employees_on_shift_raw', 'U') IS NOT NULL
    DROP TABLE dm.employees_on_shift_raw;

CREATE TABLE dm.employees_on_shift_raw (
    id INT IDENTITY(1,1) PRIMARY KEY,
    date_key DATE NOT NULL,
    smena NVARCHAR(10) NOT NULL,
    user_name NVARCHAR(255),
    fio NVARCHAR(500),
    brigada NVARCHAR(100),
    position NVARCHAR(255),
    first_operation_time DATETIME,
    total_operations INT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE()
);

CREATE NONCLUSTERED INDEX IX_employees_on_shift_raw_date_smena
ON dm.employees_on_shift_raw(date_key, smena);

CREATE NONCLUSTERED INDEX IX_employees_on_shift_raw_fio
ON dm.employees_on_shift_raw(fio);

PRINT '✅ Таблица dm.employees_on_shift_raw создана.';
