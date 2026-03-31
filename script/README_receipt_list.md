# Список приходов - Инструкция по развертыванию

## 📋 Обзор

Данный модуль реализует таблицу "Список прихода" на вкладке "Своевременность".
Данные загружаются из ILS.dbo.RECEIPT_HEADER → dwh.receipt_list и отображаются в дашборде.

---

## 🗂️ Файлы

### 1. SQL-скрипт создания таблицы
**Файл:** `script/create_receipt_list_table.sql`

Создает таблицу `dwh.receipt_list` с необходимыми индексами.

### 2. Python-скрипт обновления
**Файл:** `script/update_receipt_list.py`

Загружает данные из ILS и обновляет таблицу `dwh.receipt_list`.
Запускается каждые 5 минут через cron.

### 3. Функция получения данных
**Файл:** `data/queries_mssql.py`

Функция `get_receipt_list_data()` для получения данных из таблицы.

### 4. Обновление вкладки
**Файл:** `components/tabs/timeliness_tab.py`

Таблица переименована в "Список прихода" с новыми колонками.

### 5. Callback для заполнения таблицы
**Файл:** `callbacks/tab_callbacks.py`

Функция `update_receipt_list_table()` заполняет таблицу данными.

---

## 🚀 Установка

### Шаг 1: Создание таблицы в БД

Выполните SQL-скрипт на сервере `10.7.0.27` (база `olap2_fixed`):

```bash
# На сервере Ubuntu
cd /home/admin1/script
/opt/mssql-tools18/bin/sqlcmd -S 10.7.0.27 -U sa -P Rdflhfn600 -d olap2_fixed -i create_receipt_list_table.sql
```

Или через DBeaver/SSMS:
- Откройте `create_receipt_list_table.sql`
- Выполните на сервере `10.7.0.27`, база `olap2_fixed`

### Шаг 2: Копирование скрипта обновления на сервер

```bash
# Копируем скрипт на сервер
scp script/update_receipt_list.py admin1@olap-server:/home/admin1/script/

# Проверяем права
chmod +x /home/admin1/script/update_receipt_list.py
```

### Шаг 3: Тестовый запуск

```bash
# На сервере
cd /home/admin1/script
source venv/bin/activate
python update_receipt_list.py
```

**Ожидаемый результат:**
```
2026-03-31 10:00:00 - INFO - ======================================================================
2026-03-31 10:00:00 - INFO - 🚀 Обновление списка приходов (receipt_list)
2026-03-31 10:00:00 - INFO - ======================================================================
2026-03-31 10:00:00 - INFO - 📤 Запрос к ILS.dbo.RECEIPT_HEADER...
2026-03-31 10:00:01 - INFO - ✅ Найдено приходов: 55
2026-03-31 10:00:01 - INFO - 🗑️ Очистка dwh.receipt_list...
2026-03-31 10:00:01 - INFO -    ✅ Таблица очищена
2026-03-31 10:00:02 - INFO - ➕ Вставка 55 записей...
2026-03-31 10:00:02 - INFO -    Пакет 1/1: 55 записей
2026-03-31 10:00:02 - INFO - ✅ Вставлено записей: 55
2026-03-31 10:00:02 - INFO - 📊 В таблице: 55 записей
2026-03-31 10:00:02 - INFO - 📍 Последняя запись: RECEIPT123 (2026-03-31 09:55:00) - Ожидает приема
2026-03-31 10:00:02 - INFO - 📊 Распределение по статусам:
2026-03-31 10:00:02 - INFO -    Ожидает приема: 25
2026-03-31 10:00:02 - INFO -    Размещается: 20
2026-03-31 10:00:02 - INFO -    Принимается: 10
2026-03-31 10:00:02 - INFO - ======================================================================
2026-03-31 10:00:02 - INFO - ✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО
2026-03-31 10:00:02 - INFO - ======================================================================
```

### Шаг 4: Настройка автообновления (cron)

```bash
# Редактируем crontab
crontab -e

# Добавляем строку (запуск каждые 5 минут)
*/5 * * * * /home/admin1/script/venv/bin/python /home/admin1/script/update_receipt_list.py >> /home/admin1/script/logs/receipt_list.log 2>&1
```

**Проверка cron:**
```bash
# Просмотр заданий
crontab -l

# Просмотр логов
tail -f /home/admin1/script/logs/receipt_list.log
```

---

## 📊 Структура таблицы dwh.receipt_list

| Поле | Тип | Описание |
|------|-----|----------|
| RECEIPT_ID | NVARCHAR(50) | Номер в WMS |
| ERP_ORDER_NUM | NVARCHAR(50) | Номер Веста |
| SOURCE_NAME | NVARCHAR(200) | Поставщик |
| RECEIPT_TYPE | NVARCHAR(50) | Тип прихода |
| CREATION_DATE_TIME_STAMP | DATETIME | Дата создания |
| TOTAL_LINES | INT | Строк прихода |
| TRAILING_STS | INT | Статус trailing |
| LEADING_STS | INT | Статус leading |
| STATUS | NVARCHAR(50) | Вычисленный статус |
| EXECUTION_TIME | NVARCHAR(50) | Время выполнения |
| OVERDUE_IN | NVARCHAR(50) | Просрочится через |
| LOADED_AT | DATETIME | Время загрузки |
| ROW_NUM | INT | Порядковый номер |

---

## 🎯 Логика работы

### Статусы

| TRAILING_STS | LEADING_STS | Результат |
|-------------|-------------|-----------|
| 100 | 100 | **Ожидает приема** (оранжевый) |
| 300 | Любое | **Размещается** (синий) |
| 100 или 200 | Не 100 | **Принимается** (зеленый) |
| Прошло > 24ч | - | **Просрочено** (красный) |

### Время выполнения
```
Время выполнения = Текущее время - CREATION_DATE_TIME_STAMP
Формат: "Xч Yм" (например: "2ч 15м")
```

### Просрочится через
```
Если прошло < 24 часов:
  Просрочится через = 24ч - (Текущее время - CREATION_DATE_TIME_STAMP)
  Формат: "Xч Yм" (например: "21ч 45м")

Если прошло ≥ 24 часов:
  Просрочится через = "Просрочено"
```

---

## 🔍 Проверка работы

### 1. Проверка данных в БД

```sql
-- Количество записей
SELECT COUNT(*) FROM dwh.receipt_list;

-- Последние записи
SELECT TOP 10 
    RECEIPT_ID,
    ERP_ORDER_NUM,
    SOURCE_NAME,
    STATUS,
    EXECUTION_TIME,
    OVERDUE_IN,
    LOADED_AT
FROM dwh.receipt_list
ORDER BY CREATION_DATE_TIME_STAMP DESC;

-- Распределение по статусам
SELECT STATUS, COUNT(*) as cnt
FROM dwh.receipt_list
GROUP BY STATUS
ORDER BY cnt DESC;
```

### 2. Проверка в дашборде

1. Откройте дашборд в браузере
2. Перейдите на вкладку **"Своевременность"**
3. Проверьте таблицу **"Список прихода"**
4. Убедитесь, что данные отображаются корректно

---

## 🛠️ Troubleshooting

### Ошибка: "Таблица не существует"
```bash
# Выполните SQL-скрипт создания таблицы
sqlcmd -S 10.7.0.27 -U sa -P Rdflhfn600 -d olap2_fixed -i create_receipt_list_table.sql
```

### Ошибка: "Нет данных"
```bash
# Проверьте подключение к ILS
# Проверьте наличие данных в RECEIPT_HEADER
sqlcmd -S 10.7.0.248 -U manhreader -P August2021 -d ils -Q "SELECT COUNT(*) FROM dbo.RECEIPT_HEADER"
```

### Ошибка: "Cron не работает"
```bash
# Проверьте статус cron
sudo systemctl status cron

# Проверьте логи cron
grep CRON /var/log/syslog | grep receipt_list

# Перезапустите cron
sudo systemctl restart cron
```

---

## 📝 Логи

**Расположение:** `/home/admin1/script/logs/receipt_list.log`

**Просмотр в реальном времени:**
```bash
tail -f /home/admin1/script/logs/receipt_list.log
```

**Последние 50 строк:**
```bash
tail -n 50 /home/admin1/script/logs/receipt_list.log
```

---

## ✅ Чек-лист после установки

- [ ] Таблица `dwh.receipt_list` создана
- [ ] Индексы созданы
- [ ] Скрипт `update_receipt_list.py` скопирован на сервер
- [ ] Тестовый запуск успешен
- [ ] Cron настроен (каждые 5 минут)
- [ ] Данные отображаются в дашборде
- [ ] Логи пишутся

---

## 📞 Контакты

По вопросам обращайтесь к разработчику.
