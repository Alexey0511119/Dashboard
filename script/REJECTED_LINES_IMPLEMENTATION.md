# 🚀 ОБНОВЛЕНИЕ ОТКЛОНЁННЫХ СТРОК (REJECTED LINES)

## ✅ РЕАЛИЗАЦИЯ ЗАВЕРШЕНА

---

## 📋 АРХИТЕКТУРА

```
ILS.dbo.SHIPMENT_DETAIL (10.7.0.248)
    ↓ (прямой запрос, каждые 5 минут)
update_rejected_lines.py
    ↓ (TRUNCATE + INSERT)
dwh.rejected_lines_detail (10.7.0.27)
    ↓ (VIEW без кэша)
dm.v_rejected_lines_summary
dm.v_rejected_lines_detail
    ↓
Дашборд (карточка + модальное окно)
```

---

## 📁 СОЗДАННЫЕ/ИЗМЕНЁННЫЕ ФАЙЛЫ

### **1. НОВЫЙ ФАЙЛ:**

| Файл | Назначение |
|------|-----------|
| `script/update_rejected_lines.py` | Прямой запрос к ILS → полная перезапись dwh.rejected_lines_detail |

### **2. ИЗМЕНЁННЫЕ ФАЙЛЫ:**

| Файл | Что изменено |
|------|-------------|
| `data/queries_mssql.py` | Отключён кэш для `get_rejected_lines_summary()` и `get_rejected_lines_detail()` |
| `script/update_dwh_3days_simple.sql` | Удалено обновление rejected_lines_detail |
| `script/update_dwh_3days.sql` | Удалено обновление rejected_lines_detail |
| `script/update_dwh_7days.sql` | Удалено обновление rejected_lines_detail |
| `script/update_procedures_3days_full.sql` | Удалена процедура `usp_update_rejected_lines_detail_3days` |

---

## 🔧 НАСТРОЙКА НА СЕРВЕРЕ

### **1. Скопировать файлы на сервер:**

```bash
# Новый скрипт
scp script/update_rejected_lines.py admin1@10.7.0.27:/home/admin1/script/

# Обновлённый queries_mssql.py (где дашборд)
scp data/queries_mssql.py admin1@10.7.0.27:/home/admin1/data/

# Обновлённые SQL-файлы (если используются)
scp script/update_dwh_3days_simple.sql admin1@10.7.0.27:/home/admin1/script/
scp script/update_dwh_3days.sql admin1@10.7.0.27:/home/admin1/script/
scp script/update_dwh_7days.sql admin1@10.7.0.27:/home/admin1/script/
scp script/update_procedures_3days_full.sql admin1@10.7.0.27:/home/admin1/script/
```

---

### **2. Настроить cron (каждые 5 минут):**

```bash
crontab -e

# Добавить строку:
*/5 * * * * /home/admin1/script/update_rejected_lines.py
```

---

### **3. Тестовый запуск:**

```bash
cd /home/admin1/script
python update_rejected_lines.py
```

**Ожидаемый результат:**
```
2026-03-27 15:00:00 - INFO - ======================================================================
2026-03-27 15:00:00 - INFO - 🚀 Обновление отклонённых строк (rejected_lines)
2026-03-27 15:00:00 - INFO - ======================================================================
2026-03-27 15:00:01 - INFO - 📤 Запрос к ILS.dbo.SHIPMENT_DETAIL...
2026-03-27 15:00:02 - INFO - ✅ Найдено отклонённых строк: 150
2026-03-27 15:00:02 - INFO - 🗑️ Очистка dwh.rejected_lines_detail...
2026-03-27 15:00:02 - INFO -    ✅ Таблица очищена
2026-03-27 15:00:03 - INFO - ➕ Вставка 150 записей...
2026-03-27 15:00:03 - INFO -    Пакет 1/2: 100 записей
2026-03-27 15:00:03 - INFO -    Пакет 2/2: 50 записей
2026-03-27 15:00:03 - INFO - ✅ Вставлено записей: 150
2026-03-27 15:00:04 - INFO - 📊 В таблице: 150, записей
2026-03-27 15:00:04 - INFO - 📍 Последняя запись: O00000001594 (2026-03-27 14:08:06.717000)
2026-03-27 15:00:04 - INFO - ======================================================================
2026-03-27 15:00:04 - INFO - ✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО
2026-03-27 15:00:04 - INFO - ======================================================================
```

---

## 📊 ЛОГИКА ФИЛЬТРАЦИИ

**Критерии отбора:**
```sql
WHERE
    STATUS1 = '100'              -- Отклонённые строки в WMS
    AND PICK_LOC IS NOT NULL     -- Есть место отбора
    AND PICK_LOC <> N'ОТКАЗ'     -- Но НЕ "ОТКАЗ" (другие причины)
```

**Объяснение:**
- `STATUS1 = '100'` — строка отклонена в WMS ✅
- `PICK_LOC = N'ОТКАЗ'` — отклонено по причине "Отказ" ❌ (исключаем)
- `PICK_LOC = NULL` — нет места отбора ❌ (исключаем)
- `PICK_LOC = 'ME-123'` — любое другое место ✅ (включаем)

---

## 🎯 ОТЛИЧИЯ ОТ ПРЕДЫДУЩЕЙ ВЕРСИИ

| Параметр | Было | Стало |
|----------|------|-------|
| **Источник** | `raw_.SHIPMENT_DETAIL` | `ILS.dbo.SHIPMENT_DETAIL` (прямой запрос) |
| **Частота** | Раз в 10 минут | **Каждые 5 минут** |
| **Кэш** | Включён | **Отключён** (real-time) |
| **Логика** | DELETE + INSERT (за период) | **TRUNCATE + INSERT** (полная перезапись) |
| **Объём** | ~50-600 строк | ~50-600 строк |

---

## ✅ ПРОВЕРКА РАБОТЫ

### **1. Проверить данные в БД:**

```sql
-- Количество записей
SELECT COUNT(*) FROM dwh.rejected_lines_detail;

-- Последние данные
SELECT TOP 10 * FROM dwh.rejected_lines_detail 
ORDER BY DATE_TIME_STAMP DESC;

-- Проверить VIEW
SELECT * FROM dm.v_rejected_lines_summary;
```

### **2. Проверить дашборд:**

- Открыть карточку "Отклонённые строки"
- Открыть модальное окно
- Данные должны обновляться каждые 5 минут

---

## 📝 ФАЙЛЫ ДЛЯ КОПИРОВАНИЯ

**Обязательно:**
- `script/update_rejected_lines.py` → `/home/admin1/script/`
- `data/queries_mssql.py` → `/home/admin1/data/` (где дашборд)

**По желанию (если используются):**
- `script/update_dwh_3days_simple.sql`
- `script/update_dwh_3days.sql`
- `script/update_dwh_7days.sql`
- `script/update_procedures_3days_full.sql`

---

## 🎉 ГОТОВО!

Данные обновляются **каждые 5 минут** напрямую из основной базы! 🚀

---

**Дата:** 27 марта 2026 г.  
**Версия:** 1.0  
**Статус:** ✅ РЕАЛИЗОВАНО
