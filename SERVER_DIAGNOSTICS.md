# Диагностика проблем с данными на сервере

## Быстрая диагностика

### 1. Запустите диагностический скрипт на сервере:
```bash
python diagnose_server.py
```

Этот скрипт проверит:
- ✅ Импорт всех библиотек
- ✅ Подключение к БД
- ✅ Доступность VIEW
- ✅ Наличие данных
- ✅ Сетевое подключение

### 2. Проверьте логи дашборда:
```bash
# Если дашборд запущен в фоне
tail -f logs/dashboard.log

# Или посмотрите последние ошибки
tail -100 logs/dashboard.log
```

### 3. Проверьте подключение к БД вручную:
```bash
# Linux
tsql -S 10.7.0.27 -U sa -P Rdflhfn600 -D olap2_fixed

# Windows (PowerShell)
python -c "import pyodbc; conn = pyodbc.connect('DRIVER={SQL Server};SERVER=10.7.0.27,1433;DATABASE=olap2_fixed;UID=sa;PWD=Rdflhfn600'); print('OK')"
```

## Частые проблемы и решения

### ❌ Проблема: Нет подключения к БД
**Причина:** Сервер БД недоступен с сервера дашборда

**Решение:**
1. Проверьте firewall: `telnet 10.7.0.27 1433`
2. Проверьте что SQL Server разрешает удаленные подключения
3. Проверьте credentials

### ❌ Проблема: Ошибка импорта pyodbc
**Причина:** Не установлен драйвер ODBC

**Решение:**
```bash
# Ubuntu/Debian
sudo apt-get install unixodbc unixodbc-dev
pip install pyodbc

# CentOS/RHEL
sudo yum install unixODBC unixODBC-devel
pip install pyodbc

# Windows
pip install pyodbc
```

### ❌ Проблема: VIEW не существуют
**Причина:** База данных не настроена на сервере

**Решение:**
1. Проверьте что база `olap2_fixed` существует
2. Проверьте что схема `dm` существует
3. Выполните скрипты создания VIEW из папки `script/`

### ❌ Проблема: Данные есть но не отображаются
**Причина:** Пустой кэш или проблемы с callback

**Решение:**
1. Откройте браузер консоль (F12)
2. Посмотрите ошибки в консоли
3. Очистите кэш: в коде вызовите `clear_cache()`
4. Перезапустите дашборд

### ❌ Проблема: Данные за другой период
**Причина:** На сервере другое системное время

**Решение:**
```bash
# Проверьте время на сервере
date

# Если время неверое - синхронизируйте
sudo ntpdate -s time.nist.gov
```

## Проверка работы дашборда

### 1. Запустите дашборд с отладкой:
```bash
# Временно включите debug
python -c "
import dash
from app import app
app.run(debug=True, host='0.0.0.0', port=8051)
"
```

### 2. Проверьте доступность:
```bash
# С сервера
curl http://localhost:8051

# С другого компьютера
curl http://IP_СЕРВЕРА:8051
```

### 3. Проверьте что порт слушается:
```bash
# Linux
netstat -tlnp | grep 8051
# или
ss -tlnp | grep 8051

# Windows
netstat -an | findstr 8051
```

## Логи для анализа

### Логи дашборда:
- `logs/dashboard.log` - основные логи
- Консоль вывода при запуске

### Логи БД (если есть доступ):
- SQL Server Error Log
- Проверка запросов через SQL Profiler

## Если ничего не помогает

Включите подробное логирование в `app.py`:
```python
# Временно измените уровень логирования
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

И посмотрите все запросы к БД в `data/mssql_client.py`:
```python
# Добавьте в execute() перед выполнением запроса
print(f"EXECUTING: {query}")
print(f"PARAMS: {params}")
```
