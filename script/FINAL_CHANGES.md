# 🗑️ УДАЛЕНО ИЗ ВСЕХ СКРИПТОВ ОБНОВЛЕНИЯ

## ✅ ВСЕ ИЗМЕНЕНИЯ

Теперь **все** упоминания о `fact_location_snapshot` удалены из скриптов обновления!

---

## 📁 ИЗМЕНЁННЫЕ ФАЙЛЫ

### **1. `Full`** (ШАГ 17)
- **Удалено:** Создание и заполнение `fact_location_snapshot`
- **Заменено на:** Комментарий об отдельном обновлении

### **2. `create_indexes_3days.sql`**
- **Удалено:** Индексы для `fact_location_snapshot`

### **3. `diagnose_3days_cycle.sql`**
- **Удалено:** Проверка `fact_location_snapshot`

### **4. `update_dwh_3days_simple.sql`** (ШАГ 10)
- **Удалено:** Полная перезапись `fact_location_snapshot`
- **Заменено на:** Пропущено (обновляется отдельно)

### **5. `update_dwh_3days.sql`** (ШАГ 4)
- **Удалено:** Полная перезапись `fact_location_snapshot`
- **Заменено на:** Пропущено (обновляется отдельно)

### **6. `update_dwh_7days.sql`** (ШАГ 4)
- **Удалено:** Полная перезапись `fact_location_snapshot`
- **Заменено на:** Пропущено (обновляется отдельно)

### **7. `check_storage_data.sql`**
- **Перемещён в:** `script/old/`

---

## 🔄 НОВАЯ АРХИТЕКТУРА

```
┌────────────────────────────────────────────────────────────┐
│  pipeline_3days.py (каждые 10 минут)                      │
│  └─ reload_3days.py → raw_.таблицы (3 дня)               │
│  └─ run_update_dwh.py → DWH процедуры                     │
│     └─ update_dwh_3days_simple.sql (ШАГ 4 ПРОПУЩЕН)      │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  update_locations_all.py (каждую минуту) ⭐ ОТДЕЛЬНО      │
│  └─ ILS.LOCATION → raw_.LOCATION → DWH → Дашборд         │
│     └─ sp_update_location_snapshot                        │
└────────────────────────────────────────────────────────────┘
```

---

## 📦 ФАЙЛЫ ДЛЯ КОПИРОВАНИЯ НА СЕРВЕР

### **Обязательно:**

| Файл | Куда | Зачем |
|------|------|-------|
| `data/queries_mssql.py` | Где дашборд | Отключён кэш |
| `script/update_locations_all.py` | Где cron | Основной скрипт |
| `script/create_update_location_procedure.sql` | SQL Server | Процедура |
| `script/update_dwh_3days_simple.sql` | Где cron | Удалён ШАГ 10 |
| `script/update_dwh_3days.sql` | Где cron | Удалён ШАГ 4 |
| `script/update_dwh_7days.sql` | Где cron | Удалён ШАГ 4 |

### **Команда для копирования:**

```bash
# На Linux сервер
scp data/queries_mssql.py admin1@10.7.0.27:/home/admin1/data/
scp script/update_locations_all.py admin1@10.7.0.27:/home/admin1/script/
scp script/create_update_location_procedure.sql admin1@10.7.0.27:/home/admin1/script/
scp script/update_dwh_3days_simple.sql admin1@10.7.0.27:/home/admin1/script/
scp script/update_dwh_3days.sql admin1@10.7.0.27:/home/admin1/script/
scp script/update_dwh_7days.sql admin1@10.7.0.27:/home/admin1/script/
```

---

## 🚀 НАСТРОЙКА

### **1. Создать процедуру:**

```bash
sqlcmd -S localhost -U sa -P Rdflhfn600 -d olap2_fixed -i create_update_location_procedure.sql
```

### **2. Настроить cron:**

```bash
crontab -e

# Каждую минуту
* * * * * cd /home/admin1/script && python update_locations_all.py >> logs/cron.log 2>&1
```

### **3. Обновить данные (тест):**

```bash
python update_locations_all.py
```

### **4. Проверить:**

```bash
tail -f logs/update_locations_*.log
```

---

## ✅ ПРОВЕРКА

### **Теперь pipeline_3days.py НЕ затрагивает ячейки:**

```bash
# Запустить pipeline
python pipeline_3days.py

# Ячейки НЕ обновятся ✅
# Они обновляются только через update_locations_all.py
```

---

## 📊 МОНИТОРИНГ

```sql
-- Проверить последнее обновление ячеек
SELECT MAX(last_modified) FROM dwh.fact_location_snapshot;

-- Проверить последнее обновление DWH (pipeline)
SELECT MAX(date_key) FROM dwh.fact_operation;

-- Время должно быть разным!
```

---

## 🎯 ИТОГ

| Что было | Что стало |
|----------|-----------|
| Ячейки в 3-дневном цикле | **Отдельное обновление** |
| 4 файла с кодом ячеек | **Удалено из всех** |
| Кэш (задержка) | **Real-time (без кэша)** |
| Сложная логика | **Простая логика** |

---

**Дата:** 27 марта 2026 г.  
**Версия:** 4.0 (ФИНАЛЬНАЯ)  
**Статус:** ✅ ГОТОВО К ПРОДАКШЕНУ
