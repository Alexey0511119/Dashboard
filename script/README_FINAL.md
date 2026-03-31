# 🚀 ОБНОВЛЕНИЕ LOCATION - 2 СКРИПТА

## 📋 Архитектура

```
ILS.dbo.LOCATION ──(incremental_location_raw.py)──> raw_.LOCATION ──(update_location_snapshot.py)──> dwh.fact_location_snapshot
     (10.7.0.248)         (каждые 30-60 сек)        (10.7.0.27)          (каждые 30-60 сек)         (10.7.0.27)
```

---

## 📁 Файлы

| # | Файл | Назначение | Частота |
|---|------|-----------|---------|
| 1 | `incremental_location_raw.py` | Загрузка из ILS в raw_.LOCATION (инкрементально) | 30-60 сек |
| 2 | `run_incremental_location_raw.bat` | BAT-файл для Task Scheduler (raw) | 30-60 сек |
| 3 | `update_location_snapshot.py` | Вызов процедуры для dwh.fact_location_snapshot | 30-60 сек |
| 4 | `run_update_location.bat` | BAT-файл для Task Scheduler (DWH) | 30-60 сек |
| 5 | `create_update_location_procedure.sql` | Создание хранимой процедуры | 1 раз |

---

## ⚙️ НАСТРОЙКА

### ШАГ 1: Создать хранимую процедуру

```bash
# В SSMS: olap2_fixed
c:\Users\A.Gorbatenko\Documents\Dashboard\script\create_update_location_procedure.sql
```

---

### ШАГ 2: Настроить Task Scheduler (2 задачи)

#### Задача 1: RAW загрузка

1. **Task Scheduler** → **Create Basic Task**
2. **Name:** `Location RAW Load`
3. **Trigger:** Daily → **Advanced:**
   - ✅ Repeat every: **1 minute**
   - ✅ for duration: **Indefinitely**
4. **Action:** Start a program
   - **Program:** `c:\Users\A.Gorbatenko\Documents\Dashboard\script\run_incremental_location_raw.bat`
   - **Start in:** `c:\Users\A.Gorbatenko\Documents\Dashboard\script`
5. ✅ **Run with highest privileges**

#### Задача 2: DWH обновление

1. **Task Scheduler** → **Create Basic Task**
2. **Name:** `Location DWH Update`
3. **Trigger:** Daily → **Advanced:**
   - ✅ Repeat every: **1 minute**
   - ✅ for duration: **Indefinitely**
4. **Action:** Start a program
   - **Program:** `c:\Users\A.Gorbatenko\Documents\Dashboard\script\run_update_location.bat`
   - **Start in:** `c:\Users\A.Gorbatenko\Documents\Dashboard\script`
5. ✅ **Run with highest privileges**

---

### ШАГ 3: Тестовый запуск

```bash
# 1. Загрузка в raw
cd c:\Users\A.Gorbatenko\Documents\Dashboard
python script\incremental_location_raw.py

# 2. Обновление dwh
python script\update_location_snapshot.py
```

---

### ШАГ 4: Проверка

```sql
-- 1. Проверить raw_.LOCATION
SELECT COUNT(*) FROM raw_.LOCATION;
SELECT MAX(DATE_TIME_STAMP) FROM raw_.LOCATION;

-- 2. Проверить dwh.fact_location_snapshot
SELECT status, COUNT(*) FROM dwh.fact_location_snapshot GROUP BY status;

-- 3. Проверить VIEW
SELECT TOP 5 * FROM dm.v_storage_cells_current;
```

---

## 📊 Логи

```
script/logs/
├── incremental_location_raw_20260327_143000.log
└── update_location_snapshot_20260327_143000.log
```

---

## ✅ Готово!

Данные обновляются автоматически каждые 30-60 секунд! 🎉
