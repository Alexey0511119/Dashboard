# 🚀 БЫСТРЫЙ СТАРТ - ИНКРЕМЕНТАЛЬНАЯ ЗАГРУЗКА ЯЧЕЕК

## ⏱️ Время настройки: 10 минут

---

## ШАГ 1: Проверка (2 минуты)

```bash
cd c:\Users\A.Gorbatenko\Documents\Dashboard
python script\test_incremental_locations.py
```

**Ожидаемый результат:**
```
✅ ILS подключение
✅ Analytics подключение
✅ raw_.LOCATION
✅ dwh.fact_location_snapshot
✅ VIEW для дашборда
✅ Инкрементальная загрузка

Итого: 6/6 проверок пройдено
```

**Если есть ошибки** — устраните их перед продолжением.

---

## ШАГ 2: Первичная загрузка данных (3 минуты)

Если таблица `dwh.fact_location_snapshot` пустая, выполните SQL:

```sql
USE olap2_fixed;
GO

-- Загрузить все данные
INSERT INTO dwh.fact_location_snapshot 
(date_key, location, status, location_type, locating_zone, allocation_zone, work_zone, source_system)
SELECT
    CAST(GETDATE() AS DATE),
    l.LOCATION,
    CASE
        WHEN l.LOCATION_STS = 'Empty' THEN 'Empty'
        WHEN l.LOCATION_STS IN ('Picking', 'Storage') THEN 'Occupied'
        ELSE 'Available'
    END,
    l.LOCATION_TYPE,
    l.LOCATING_ZONE,
    l.ALLOCATION_ZONE,
    l.WORK_ZONE,
    'WMS'
FROM ILS.dbo.LOCATION l WITH (NOLOCK)
WHERE
    l.LOCATION_STS IS NOT NULL
    AND l.LOCATION_STS != 'Frozen'
    AND (l.LOCATION_CLASS = 'Inventory' OR l.LOCATION_CLASS IS NULL)
    AND l.LOCATION_TYPE NOT IN ('Брак/бой DMG', 'Напольная', 'Улица KC', 'Ячейки KSP');
GO

-- Проверить
SELECT status, COUNT(*) FROM dwh.fact_location_snapshot GROUP BY status;
```

---

## ШАГ 3: Настройка Task Scheduler (5 минут)

### Задача 1: RAW загрузка

1. **Пуск** → введите "Task Scheduler" → откройте
2. **Create Basic Task...**
3. **Name:** `Location Incremental RAW`
4. **Trigger:** Daily → **Next**
5. **Advanced settings:**
   - ✅ **Repeat task every:** `1 minute`
   - ✅ **for a duration of:** `Indefinitely`
6. **Action:** Start a program → **Next**
7. **Program/script:**
   ```
   c:\Users\A.Gorbatenko\Documents\Dashboard\script\run_incremental_raw.bat
   ```
8. **Start in:**
   ```
   c:\Users\A.Gorbatenko\Documents\Dashboard\script
   ```
9. ✅ **Open Properties** → ✅ **Run with highest privileges**
10. **Finish**

### Задача 2: DWH загрузка

Повторите шаги выше, но:
- **Name:** `Location Incremental DWH`
- **Program/script:**
  ```
  c:\Users\A.Gorbatenko\Documents\Dashboard\script\run_incremental_dwh.bat
  ```

---

## ШАГ 4: Проверка работы (1 минута)

### Запустите вручную:

```bash
cd c:\Users\A.Gorbatenko\Documents\Dashboard
python script\incremental_locations_raw.py
python script\incremental_locations_dwh.py
```

### Проверьте логи:

```
c:\Users\A.Gorbatenko\Documents\Dashboard\script\logs\
```

**Должно быть:**
```
✅ Найдено изменений: 15
✅ Загружено: 10 новых, 5 обновлённых
```

### Проверьте в SQL:

```sql
-- Проверить данные
SELECT status, COUNT(*) FROM dwh.fact_location_snapshot GROUP BY status;

-- Проверить VIEW
SELECT TOP 5 * FROM dm.v_storage_cells_current;
```

---

## ШАГ 5: Проверка дашборда

1. Откройте дашборд в браузере
2. Откройте модальное окно "Ячейки хранения"
3. Данные должны обновляться каждые 30-60 секунд

---

## ✅ ГОТОВО!

Теперь данные обновляются автоматически! 🎉

---

## 🔧 Если что-то пошло не так

### Проблема: "Таблица не существует"

**Решение:** Запустите `reload_3days.py` для создания таблиц.

### Проблема: "Нет данных"

**Решение:** Выполните первичную загрузку (ШАГ 2).

### Проблема: Задачи не запускаются

**Решение:**
1. Проверьте логи в `script/logs/`
2. Запустите вручную: `python script\incremental_locations_raw.py`
3. Проверьте права доступа в Task Scheduler

### Проблема: Дашборд показывает старые данные

**Решение:**
```sql
-- Проверить VIEW
SELECT COUNT(*) FROM dm.v_storage_cells_current;

-- Если 0, проверьте таблицу
SELECT COUNT(*) FROM dwh.fact_location_snapshot;
```

---

## 📊 Мониторинг

### Логи:

```
script/logs/incremental_locations_raw_*.log
script/logs/incremental_locations_dwh_*.log
```

### Быстрая проверка:

```bash
# Последние 10 строк лога
Get-Content script\logs\incremental_locations_raw_*.log -Tail 10
```

---

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи
2. Запустите `test_incremental_locations.py`
3. Проверьте Task Scheduler

---

**Удачи!** 🚀
