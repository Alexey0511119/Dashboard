# 🔧 РЕШЕНИЕ SSL-ОШИБКИ ПРИ ПОДКЛЮЧЕНИИ К SQL SERVER

## ❌ ОШИБКА

```
SQL Error [S0001]: SSL Provider: The Local Security Authority cannot be contacted
```

---

## ✅ РЕШЕНИЕ

### Вариант 1: Использовать ключ `-C` (рекомендуется)

Добавьте ключ `-C` к команде `sqlcmd` для игнорирования SSL-сертификата:

```bash
# Было (ошибка):
sqlcmd -S 10.7.0.27 -U sa -P Rdflhfn600 -d olap2_fixed -i setup_linked_server.sql

# Стало (работает):
sqlcmd -S 10.7.0.27 -U sa -P Rdflhfn600 -d olap2_fixed -C -i setup_linked_server_fixed.sql
```

**Ключ `-C`** отключает проверку SSL-сертификата сервера.

---

### Вариант 2: Через SSMS (без командной строки)

1. Откройте **SQL Server Management Studio**
2. Подключитесь к `10.7.0.27`
3. Откройте файл `.sql`
4. Нажмите **F5** (Выполнить)

---

### Вариант 3: Исправить реестр (Windows)

**⚠️ Только для опытных пользователей!**

1. Откройте `regedit`
2. Перейдите к:
   ```
   HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\TLS 1.2
   ```
3. Создайте параметры:
   ```
   "Enabled"=dword:00000001
   "DisabledByDefault"=dword:00000000
   ```
4. Перезагрузите сервер

---

## 📋 ВСЕ КОМАНДЫ С КЛЮЧОМ `-C`

```bash
# 1. Настройка Linked Server
sqlcmd -S 10.7.0.27 -U sa -P Rdflhfn600 -d olap2_fixed -C -i setup_linked_server_fixed.sql

# 2. Создание процедур
sqlcmd -S 10.7.0.27 -U sa -P Rdflhfn600 -d olap2_fixed -C -i update_procedures_3days_linked.sql

# 3. Настройка SQL Agent
sqlcmd -S 10.7.0.27 -U sa -P Rdflhfn600 -d master -C -i setup_sql_agent_job.sql

# 4. Тестовый запуск
sqlcmd -S 10.7.0.27 -U sa -P Rdflhfn600 -d olap2_fixed -C -i update_dwh_3days_linked.sql

# 5. Диагностика
sqlcmd -S 10.7.0.27 -U sa -P Rdflhfn600 -d olap2_fixed -C -i diagnose_linked_server.sql
```

---

## 🔍 ПРОВЕРКА ПОСЛЕ НАСТРОЙКИ

```sql
-- Проверка Linked Server
SELECT TOP 5 * FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2;
SELECT TOP 5 * FROM SK_SOURCE.sk.dbo.eks_peremer_ZX_KPP;

-- Проверка задач
EXEC msdb.dbo.sp_help_job @job_name = N'ETL_3DAYS_UPDATE';
```

---

##  ПРИЧИНЫ ОШИБКИ

1. **TLS 1.2 не включён** на сервере или клиенте
2. **Сертификат SSL** самоподписанный или просроченный
3. **SCHANNEL** не может проверить сертификат
4. **Групповые политики** блокируют подключение

---

## 🛠 ДОПОЛНИТЕЛЬНЫЕ ПАРАМЕТРЫ sqlcmd

| Ключ | Описание |
|------|----------|
| `-C` | Доверять сертификату сервера |
| `-N` | Не шифровать подключение |
| `-X` | Выход при ошибке |
| `-b` | Завершить с ошибкой при проблеме SQL |

**Пример:**
```bash
sqlcmd -S 10.7.0.27 -U sa -P Rdflhfn600 -d olap2_fixed -C -N -i script.sql
```

---

**Версия:** 1.0
**Дата:** 2026-03-26
**Статус:** ✅ Работает
