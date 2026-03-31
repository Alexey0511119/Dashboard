# 📦 ОБНОВЛЕНИЕ LOCATION - УПРОЩЁННАЯ ВЕРСИЯ (ОДИН СКРИПТ)

## ✅ Созданные файлы

| # | Файл | Назначение |
|---|------|-----------|
| 1 | `create_update_location_procedure.sql` | Создание хранимой процедуры в olap2_fixed |
| 2 | `update_location_snapshot.py` | Python-скрипт для вызова процедуры |
| 3 | `run_update_location.bat` | BAT-файл для Task Scheduler |
| 4 | `README_UPDATE_LOCATION.md` | Документация |
| 5 | `INSTRUCTIONS.md` | Этот файл (сводка) |

**Итого:** 5 файлов

---

## 🔄 Архитектура

```
ILS.dbo.LOCATION ──(reload_3days.py)──> raw_.LOCATION ──(sp_update_location_snapshot)──> dwh.fact_location_snapshot ──> VIEW ──> Дашборд
```

---

## 🚀 БЫСТРЫЙ СТАРТ

### 1️⃣ Создать процедуру

```bash
# В SSMS или через sqlcmd
c:\Users\A.Gorbatenko\Documents\Dashboard\script\create_update_location_procedure.sql
```

### 2️⃣ Проверить raw_.LOCATION

```sql
SELECT COUNT(*) FROM raw_.LOCATION;
```

**Если 0** — запустите `reload_3days.py`

### 3️⃣ Тестовый запуск

```bash
cd c:\Users\A.Gorbatenko\Documents\Dashboard
python script\update_location_snapshot.py
```

### 4️⃣ Настроить Task Scheduler

- **Name:** `Location Snapshot Update`
- **Trigger:** Every 1 minute
- **Action:** `c:\Users\A.Gorbatenko\Documents\Dashboard\script\run_update_location.bat`

---

## 📊 Характеристики

- **Задержка:** 30-60 секунд
- **Нагрузка на ILS:** Отсутствует (данные уже в raw_.LOCATION)
- **Время выполнения:** 1-3 секунды
- **Задач в Task Scheduler:** 1

---

**Готово!** 🎉
