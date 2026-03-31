# 🚀 ОБНОВЛЕНИЕ ЯЧЕЕК (LOCATION) - ОДИН СКРИПТ

## 📋 Описание

Обновление `dwh.fact_location_snapshot` из `raw_.LOCATION` с помощью хранимой процедуры.

### Архитектура

```
ILS.dbo.LOCATION ──(reload_3days.py)──> raw_.LOCATION
                                            ↓
                              (sp_update_location_snapshot)
                                            ↓
                                   dwh.fact_location_snapshot
                                            ↓
                                           VIEW
                                            ↓
                                         Дашборд
```

---

## 📁 Файлы

| Файл | Назначение |
|------|-----------|
| `create_update_location_procedure.sql` | Создание хранимой процедуры |
| `update_location_snapshot.py` | Python-скрипт для вызова процедуры |
| `run_update_location.bat` | BAT-файл для Task Scheduler |

---

## ⚙️ НАСТРОЙКА

### ШАГ 1: Создать хранимую процедуру (1 минута)

```sql
-- Запустить в olap2_fixed
c:\Users\A.Gorbatenko\Documents\Dashboard\script\create_update_location_procedure.sql
```

**Или через SSMS:**
1. Откройте `olap2_fixed`
2. Выполните скрипт `create_update_location_procedure.sql`
3. Проверьте: `SELECT * FROM sys.procedures WHERE name = 'sp_update_location_snapshot';`

---

### ШАГ 2: Проверить, что raw_.LOCATION заполнена

```sql
-- Проверить количество записей
SELECT COUNT(*) FROM raw_.LOCATION;

-- Проверить последнее изменение
SELECT MAX(DATE_TIME_STAMP) FROM raw_.LOCATION;
```

**Если пусто** — запустите `reload_3days.py` для загрузки данных.

---

### ШАГ 3: Тестовый запуск (1 минута)

```bash
cd c:\Users\A.Gorbatenko\Documents\Dashboard
python script\update_location_snapshot.py
```

**Ожидаемый результат:**
```
✅ Найдено изменений: 15
🔄 Обновлено записей: 10
➕ Вставлено записей: 5
```

---

### ШАГ 4: Настроить Task Scheduler (3 минуты)

1. Откройте **Task Scheduler** → **Create Basic Task**
2. **Name:** `Location Snapshot Update`
3. **Trigger:** Daily
4. **Advanced settings:**
   - ✅ Repeat task every: **1 minute**
   - ✅ for a duration of: **Indefinitely**
5. **Action:** Start a program
   - **Program/script:**
     ```
     c:\Users\A.Gorbatenko\Documents\Dashboard\script\run_update_location.bat
     ```
   - **Start in:**
     ```
     c:\Users\A.Gorbatenko\Documents\Dashboard\script
     ```
6. ✅ **Run with highest privileges**
7. **Finish**

---

### ШАГ 5: Проверка

#### Проверить логи:

```
c:\Users\A.Gorbatenko\Documents\Dashboard\script\logs\
├── update_location_snapshot_20260327_120000.log
```

#### Проверить данные:

```sql
-- Проверить статусы
SELECT status, COUNT(*) AS количество
FROM dwh.fact_location_snapshot
GROUP BY status;

-- Проверить VIEW
SELECT TOP 5 * FROM dm.v_storage_cells_current;
```

#### Проверить дашборд:

Откройте модальное окно "Ячейки хранения" — данные должны обновляться каждые 30-60 секунд.

---

## 🔧 ПАРАМЕТРЫ

### В скрипте `update_location_snapshot.py`:

| Параметр | Значение | Описание |
|----------|----------|----------|
| `BUFFER_MINUTES` | 5 | Буфер времени (на случай задержек) |
| `DEBUG_MODE` | False | Режим отладки |

### В процедуре `sp_update_location_snapshot`:

```sql
-- Вызов с отладкой
EXEC dwh.sp_update_location_snapshot 
    @buffer_minutes = 5, 
    @debug = 1;  -- Показывать детали
```

---

## 📊 МОНИТОРИНГ

### Логи содержат:

```
2026-03-27 12:00:00 - INFO - ======================================================================
2026-03-27 12:00:00 - INFO - 🚀 Начало обновления dwh.fact_location_snapshot
2026-03-27 12:00:00 - INFO - ======================================================================
2026-03-27 12:00:01 - INFO - 📍 Последнее изменение: 2026-03-27 11:59:30
2026-03-27 12:00:01 - INFO - 📤 Запрос изменений с: 2026-03-27 11:54:30
2026-03-27 12:00:02 - INFO - ✅ Найдено изменений: 15
2026-03-27 12:00:03 - INFO - 🔄 Обновлено записей: 10
2026-03-27 12:00:03 - INFO - ➕ Вставлено записей: 5
2026-03-27 12:00:03 - INFO - ======================================================================
2026-03-27 12:00:03 - INFO - ✅ Обновление завершено успешно
```

### Метрики:

- **Время выполнения:** 1-3 секунды
- **Задержка данных:** 30-60 секунд
- **Нагрузка:** Минимальная (только изменения из raw_.LOCATION)

---

## ❗ УСТРАНЕНИЕ ПРОБЛЕМ

### Ошибка: "Процедура не существует"

**Решение:** Запустите `create_update_location_procedure.sql`

### Ошибка: "raw_.LOCATION пустая"

**Решение:** Запустите `reload_3days.py` для загрузки данных

### Ошибка: "Timeout expired"

**Решение:** Проверьте нагрузку на сервер или увеличьте timeout

### Дашборд показывает старые данные

**Решение:**
```sql
-- Проверить таблицу
SELECT COUNT(*) FROM dwh.fact_location_snapshot;

-- Проверить VIEW
SELECT COUNT(*) FROM dm.v_storage_cells_current;

-- Проверить последнее обновление
SELECT MAX(last_modified) FROM dwh.fact_location_snapshot;
```

---

## ✅ ЧЕК-ЛИСТ

- [ ] Хранимая процедура создана
- [ ] `raw_.LOCATION` заполнена
- [ ] Тестовый запуск успешен
- [ ] Task Scheduler настроен
- [ ] Логи пишутся
- [ ] Дашборд показывает актуальные данные

---

**Готово!** 🎉 Данные обновляются автоматически.
