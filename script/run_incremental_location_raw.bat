@echo off
REM Инкрементальная загрузка LOCATION из ILS в raw_.LOCATION
REM Запускается каждые 30-60 секунд

cd /d "c:\Users\A.Gorbatenko\Documents\Dashboard"
python script\incremental_location_raw.py
