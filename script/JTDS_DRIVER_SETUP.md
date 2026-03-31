# 🔧 НАСТРОЙКА jTDS ДРАЙВЕРА В DBEAVER (БЕЗ SSL)

## ❌ ПРОБЛЕМА

Драйвер **MSOLEDBSQL** и **Microsoft JDBC** требуют SSL, который не работает в вашей среде.

## ✅ РЕШЕНИЕ: Используем jTDS драйвер

**jTDS** — открытый драйвер для SQL Server, который **не требует SSL**.

---

## 📋 ПОШАГОВАЯ ИНСТРУКЦИЯ

### ШАГ 1: Откройте Driver Manager

1. В DBeaver: **Database** → **Driver Manager**
   (или главное меню → Database → Driver Manager)

---

### ШАГ 2: Создайте новый драйвер jTDS

1. Нажмите **Create** (Создать)
2. Заполните:
   ```
   Name: SQL Server (jTDS)
   Description: jTDS driver for SQL Server (no SSL)
   Class Name: net.sourceforge.jtds.jdbc.Driver
   ```

3. Нажмите **Download/Update** (Скачать)
4. В списке выберите **jTDS** → **OK**
5. Драйвер загрузится автоматически

---

### ШАГ 3: Настройте URL

1. В поле **URL Template** введите:
   ```
   jdbc:jtds:sqlserver://{host}:{port}/{database}
   ```

2. Вкладка **Driver Properties**:
   ```
   Parameter                      Value
   ─────────────────────────────────────────
   lcid                           1049
   prepareMethod                  Auto
   sendStringParametersAsUnicode  false
   socketTimeout                  30000
   loginTimeout                   30
   ```

---

### ШАГ 4: Создайте новое подключение с jTDS

1. **Database** → **New Database Connection**
2. Выберите **SQL Server (jTDS)** (который только что создали)
3. Заполните:
   ```
   Host: 10.7.0.27
   Port: 1433
   Database: olap2_fixed
   Username: sa
   Password: Rdflhfn600
   ```

4. Нажмите **Test Connection**
5. Если успешно → **Finish**

---

### ШАГ 5: Выполните скрипт

1. Подключитесь к новому подключению (jTDS)
2. Откройте файл: `setup_linked_server_jtds.sql`
3. Нажмите **Ctrl+Enter**

---

## 🔄 АЛЬТЕРНАТИВА: Изменить существующее подключение

Если не хотите создавать новое:

1. **ПКМ на подключении** → **Edit Connection** (F4)
2. Нажмите **Edit Driver Settings**
3. Измените **Driver** с `SQL Server` на `SQL Server (jTDS)`
4. Измените URL на:
   ```
   jdbc:jtds:sqlserver://10.7.0.27:1433/olap2_fixed
   ```
5. **OK** → переподключитесь

---

## 📊 СРАВНЕНИЕ ДРАЙВЕРОВ

| Драйвер | SSL | Скорость | Совместимость |
|---------|-----|----------|---------------|
| MSOLEDBSQL | ❌ Требуется | Высокая | SQL Server 2012+ |
| Microsoft JDBC | ❌ Требуется | Высокая | Все версии |
| **jTDS** | ✅ Не требует | Средняя | Все версии ✅ |

---

## 🔍 ПРОВЕРКА

После настройки выполните:

```sql
-- Проверка версии драйвера
SELECT @@VERSION;

-- Проверка подключения к источнику
SELECT TOP 5 * FROM ILS_SOURCE.ils.dbo.WORK_INSTRUCTION_VIEW2;
```

---

## 🛠 ЕСЛИ jTDS НЕ ЗАГРУЖАЕТСЯ

### Вариант 1: Скачайте вручную

1. Скачайте jTDS: https://sourceforge.net/projects/jtds/files/
2. Файл: `jtds-1.3.1.jar`
3. В Driver Manager:
   - **Add File** → выберите скачанный `.jar`
   - **Find Class** → выберите `net.sourceforge.jtds.jdbc.Driver`

### Вариант 2: Используйте Maven

1. В Driver Manager нажмите **Download/Update**
2. Введите Maven artifact:
   ```
   net.sourceforge.jtds:jtds:1.3.1
   ```
3. **OK**

---

## ✅ КОНТРОЛЬНЫЙ СПИСОК

- [ ] Driver Manager открыт
- [ ] Создан драйвер "SQL Server (jTDS)"
- [ ] Класс: `net.sourceforge.jtds.jdbc.Driver`
- [ ] Библиотека jTDS загружена
- [ ] URL: `jdbc:jtds:sqlserver://{host}:{port}/{database}`
- [ ] Новое подключение создано
- [ ] Тест подключения успешен
- [ ] `setup_linked_server_jtds.sql` выполнен

---

## 📞 ПОДДЕРЖКА

### Ошибка: "Driver class not found"

**Решение:**
1. Driver Manager → найдите jTDS
2. **Download/Update** → скачайте заново
3. Перезапустите DBeaver

### Ошибка: "Connection refused"

**Решение:**
1. Проверьте доступность сервера: `ping 10.7.0.27`
2. Проверьте порт: `telnet 10.7.0.27 1433`
3. Убедитесь, что SQL Server принимает подключения

### Ошибка: "Login failed"

**Решение:**
1. Проверьте логин/пароль
2. Убедитесь, что пользователь `sa` активен
3. Проверьте режим аутентификации на сервере (должен быть Mixed Mode)

---

**Версия:** 1.0
**Дата:** 2026-03-26
**Статус:** ✅ Работает без SSL
