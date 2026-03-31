@echo off
REM Инкрементальная загрузка LOCATION (raw таблица)
REM Запускается каждые 30-60 секунд

cd /d "c:\Users\A.Gorbatenko\Documents\Dashboard"
python script\incremental_locations_raw.py
