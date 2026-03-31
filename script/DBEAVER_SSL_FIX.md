# 🔧 НАСТРОЙКА ПОДКЛЮЧЕНИЯ DBEAVER К SQL SERVER (БЕЗ SSL)

## ❌ ПРОБЛЕМА

```
SQL Error [S0001]: SSL Provider: The Local Security Authority cannot be contacted
```

Это ошибка **драйвера DBeaver**, а не SQL-скрипта!

---

## ✅ РЕШЕНИЕ: Изменить настройки подключения

### ШАГ 1: Откройте настройки подключения

1. В DBeaver: **ПКМ на подключении** к `10.7.0.27` → **Редактировать соединение**
   (или F4)

---

### ШАГ 2: Измените настройки драйвера

1. Перейдите на вкладку **"Настройки драйвера"** (Driver Properties)
2. Найдите параметр **`encrypt`**
3. Установите значение: **`false`**

Или добавьте следующие параметры:

| Параметр | Значение |
|----------|----------|
| `encrypt` | `false` |
| `trustServerCertificate` | `true` |
| `hostNameInCertificate` | *(оставьте пустым)* |

---

### ШАГ 3: Альтернативный способ (через JDBC URL)

1. В окне подключения нажмите **"Edit Driver Settings"**
2. Найдите поле **JDBC URL**
3. Измените с:
   ```
   jdbc:sqlserver://10.7.0.27:1433;databaseName=olap2_fixed
   ```
   
   На:
   ```
   jdbc:sqlserver://10.7.0.27:1433;databaseName=olap2_fixed;encrypt=false;trustServerCertificate=true
   ```

---

### ШАГ 4: Сохраните и переподключитесь

1. Нажмите **OK**
2. **Переподключитесь** к серверу (Disconnect → Connect)
3. Проверьте подключение

---

## 📋 ПОЛНАЯ ИНСТРУКЦИЯ ПО НАСТРОЙКЕ

### Для Windows (Microsoft JDBC Driver)

1. **ПКМ на подключении** → **Редактировать соединение**
2. Вкладка **"Главное"**:
   - Host: `10.7.0.27`
   - Port: `1433`
   - Database: `olap2_fixed`
   - Username: `sa`
   - Password: `Rdflhfn600`

3. Вкладка **"Настройки драйвера"**:
   ```
   encrypt                          = false
   trustServerCertificate           = true
   integratedSecurity               = false
   loginTimeout                     = 30
   queryTimeout                     = 0
   ```

4. Вкладка **"SSH"** (если нужно):
   - Не используйте SSH для локальной сети

5. Нажмите **"Тест подключения"**
6. Если успешно → **OK**

---

### Для Linux (jTDS Driver)

Если используете jTDS вместо Microsoft JDBC:

```
jdbc:jtds:sqlserver://10.7.0.27:1433/olap2_fixed;user=sa;password=Rdflhfn600;
```

Параметры:
```
ssl                              = false
trustServerCertificate           = true
```

---

## 🔍 ПРОВЕРКА ПОСЛЕ НАСТРОЙКИ

После изменения настроек выполните простой запрос:

```sql
SELECT @@VERSION;
```

Если видите версию SQL Server — **подключение работает!** ✅

---

## 🛠 ЕСЛИ НЕ ПОМОГЛО

### Вариант 1: Переустановите драйвер

1. В DBeaver: **Database** → **Driver Manager**
2. Найдите **SQL Server**
3. **Download/Update**
4. Выберите **Microsoft JDBC Driver for SQL Server**
5. Перезапустите DBeaver

### Вариант 2: Используйте jTDS драйвер

1. **Database** → **Driver Manager**
2. Создайте новый драйвер:
   - Name: `SQL Server (jTDS)`
   - Class Name: `net.sourceforge.jtds.jdbc.Driver`
   - URL Template: `jdbc:jtds:sqlserver://{host}:{port}/{database}`
3. Добавьте библиотеку jTDS (скачивается автоматически)

### Вариант 3: Отключите SSL на уровне Windows

**⚠️ Только если есть доступ к серверу!**

На сервере 10.7.0.27:
```powershell
# Отключить принудительное шифрование
reg add "HKLM\SOFTWARE\Microsoft\MSSQLServer\MSSQLServer\SuperSocketNetLib" /v ForceEncryption /t REG_DWORD /d 0 /f

# Перезапустить службу SQL Server
Restart-Service MSSQLSERVER -Force
```

---

## 📊 СРАВНЕНИЕ ДРАЙВЕРОВ

| Драйвер | SSL по умолчанию | Решение |
|---------|-----------------|---------|
| Microsoft JDBC 7.x | `true` | Добавить `encrypt=false` |
| Microsoft JDBC 8.x+ | `true` | Добавить `encrypt=false;trustServerCertificate=true` |
| jTDS | `false` | Работает без изменений |

---

## ✅ КОНТРОЛЬНЫЙ СПИСОК

- [ ] Открываем настройки подключения (F4)
- [ ] Находим параметр `encrypt`
- [ ] Устанавливаем `false`
- [ ] Находим параметр `trustServerCertificate`
- [ ] Устанавливаем `true`
- [ ] Сохраняем (OK)
- [ ] Переподключаемся
- [ ] Выполняем `SELECT @@VERSION;`
- [ ] Если работает → запускаем `setup_linked_server_dbeaver.sql`

---

**Версия:** 1.0
**Дата:** 2026-03-26
**Статус:** ✅ Работает
