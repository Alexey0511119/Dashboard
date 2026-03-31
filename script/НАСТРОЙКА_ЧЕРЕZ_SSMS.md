# 🔧 НАСТРОЙКА LINKED SERVER ЧЕРЕЗ SSMS (БЕЗ SQLCMD)

## ❌ ПРОБЛЕМА

`sqlcmd` выдаёт ошибку SSL независимо от ключей:
```
SSL Provider: The Local Security Authority cannot be contacted
```

## ✅ РЕШЕНИЕ: Настройка через SSMS вручную

---

## 📋 ПОШАГОВАЯ ИНСТРУКЦИЯ

### ШАГ 1: Откройте SSMS

1. Запустите **SQL Server Management Studio**
2. Подключитесь к серверу аналитики:
   - **Server name:** `10.7.0.27`
   - **Authentication:** SQL Server Authentication
   - **Login:** `sa`
   - **Password:** `Rdflhfn600`

---

### ШАГ 2: Создание Linked Server для ILS

1. В обозревателе объектов перейдите к:
   ```
   Объекты сервера → Объекты сервера → Связанные серверы
   ```

2. **ПКМ** на "Связанные серверы" → **"Создать связанный сервер..."**

3. Заполните вкладку **"Общие"**:
   | Поле | Значение |
   |------|----------|
   | Имя связанного сервера | `ILS_SOURCE` |
   | Сервер | `10.7.0.248` |
   | Поставщик | `SQL Server Native Client 11.0` |
   | Имя продукта | *(оставьте пустым)* |
   | Каталог | `ils` |

4. Перейдите на вкладку **"Безопасность"**:
   
   Выберите: **"Будет создан с помощью этого входа:"**
   | Поле | Значение |
   |------|----------|
   | Логин | `manhreader` |
   | Пароль | `August2021` |
   | Подтверждение пароля | `August2021` |
   
   ✅ **Галочка:** "Не включать" (для остальных)

5. Перейдите на вкладку **"Параметры сервера"**:
   
   | Параметр | Значение |
   |----------|----------|
   | ✅ Доступ к данным | Включено |
   | ✅ RPC | Включено |
   | ✅ Исходящий RPC | Включено |
   | Исходящий уровень имитации | Без имитации |
   | ✅ Использовать самопроверку | Включено |
   | Таймаут запроса (сек) | `900` |
   | Таймаут подключения (сек) `60` |

6. Нажмите **OK**

---

### ШАГ 3: Создание Linked Server для SK

Повторите **ШАГ 2**, но с другими параметрами:

| Поле | Значение |
|------|----------|
| Имя связанного сервера | `SK_SOURCE` |
| Сервер | `10.7.0.248` |
| Поставщик | `SQL Server Native Client 11.0` |
| Каталог | `sk` |

**Безопасность:** те же учётные данные (`manhreader` / `August2021`)

---

### ШАГ 4: Проверка подключения

Выполните запрос в SSMS:

```sql
-- Проверка ILS_SOURCE
SELECT TOP 5 * FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2;

-- Проверка SK_SOURCE
SELECT TOP 5 * FROM SK_SOURCE.sk.dbo.eks_peremer_ZX_KPP;
```

**Если видите данные** ✅ — Linked Server работают!

---

### ШАГ 5: Создание процедур

Откройте файл в SSMS:
```
c:\Users\A.Gorbatenko\Documents\Dashboard\script\update_procedures_3days_linked.sql
```

Выполните (**F5**).

---

### ШАГ 6: Настройка SQL Agent Job

#### Вариант A: Автоматически через скрипт

Откройте в SSMS:
```
c:\Users\A.Gorbatenko\Documents\Dashboard\script\setup_sql_agent_job.sql
```

Выполните (**F5**).

#### Вариант B: Вручную через SSMS

1. Перейдите к:
   ```
   Объекты сервера → SQL Server Agent → Задания
   ```

2. **ПКМ** на "Задания" → **"Создать задание..."**

3. Вкладка **"Общие"**:
   - Имя: `ETL_3DAYS_UPDATE`
   - Владелец: `sa`
   - ✅ Включено

4. Вкладка **"Шаги"** → **Создать**:
   - Имя: `Update DWH`
   - Тип: `Транзакция Transact-SQL (T-SQL)`
   - База данных: `olap2_fixed`
   - Команда: *(скопируйте содержимое `update_dwh_3days_linked.sql`)*

5. Вкладка **"Расписания"** → **Создать**:
   - Имя: `Every 10 minutes`
   - Тип: `Периодическое`
   - Повторять каждые: `10` минут
   - Длительность: ежедневно, с текущей даты

6. Нажмите **OK**

---

### ШАГ 7: Тестовый запуск

1. В SSMS:
   ```
   Объекты сервера → SQL Server Agent → Задания
   ```

2. **ПКМ** на `ETL_3DAYS_UPDATE` → **"Запустить задание в начале..."**

3. Проверьте статус:
   ```sql
   SELECT TOP 5 * FROM msdb.dbo.sysjobhistory 
   WHERE job_id = (SELECT job_id FROM msdb.dbo.sysjobs WHERE name = 'ETL_3DAYS_UPDATE')
   ORDER BY run_date DESC;
   ```

---

### ШАГ 8: Проверка результата

```sql
-- Количество записей
SELECT 'operations_enriched' AS tbl, COUNT(*) AS cnt FROM dwh.operations_enriched;
SELECT 'fact_operation' AS tbl, COUNT(*) AS cnt FROM dwh.fact_operation;
SELECT 'fact_penalty' AS tbl, COUNT(*) AS cnt FROM dwh.fact_penalty;

-- Логи
SELECT TOP 10 * FROM dbo.etl_job_log ORDER BY run_date DESC;
```

---

## 🔍 ДИАГНОСТИКА

### Проверка Linked Server

```sql
-- Список Linked Server
SELECT 
    name,
    provider,
    data_source,
    is_data_access_enabled
FROM sys.linked_servers;

-- Тест подключения
EXEC sp_testlinkedserver N'ILS_SOURCE';
EXEC sp_testlinkedserver N'SK_SOURCE';
```

### Если Linked Server не работает

1. Проверьте доступность сервера 10.7.0.248:
   ```bash
   ping 10.7.0.248
   ```

2. Проверьте порты (1433):
   ```bash
   telnet 10.7.0.248 1433
   ```

3. Пересоздайте Linked Server:
   - Удалить: ПКМ на `ILS_SOURCE` → Удалить
   - Создать заново по инструкции выше

---

## 📊 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ

После успешной настройки:

| Параметр | Значение |
|----------|----------|
| Linked Server | `ILS_SOURCE`, `SK_SOURCE` ✅ |
| Тест подключения | Успешно ✅ |
| SQL Agent Job | Создан, включён ✅ |
| Время выполнения | 1-2 минуты ✅ |
| Записей в operations_enriched | ~500K - 1M |

---

## 🛠 ЕСЛИ НИЧЕГО НЕ ПОМОГАЕТ

### Альтернатива: Используйте PowerShell

```powershell
# Подключение к серверу
$server = New-Object Microsoft.SqlServer.Management.Smo.Server("10.7.0.27")

# Создание Linked Server
$linkedServer = New-Object Microsoft.SqlServer.Management.Smo.LinkedServer($server, "ILS_SOURCE")
$linkedServer.ProviderName = "SQLNCLI11"
$linkedServer.DataSource = "10.7.0.248"
$linkedServer.Catalog = "ils"
$linkedServer.Create()

# Добавление учётных данных
$linkedServer.AddRemoteLogon("manhreader", "August2021", $null)
```

---

**Версия:** 1.0
**Дата:** 2026-03-26
**Статус:** ✅ Работает без sqlcmd
