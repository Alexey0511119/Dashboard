@echo off
REM Обновление dwh.fact_location_snapshot из raw_.LOCATION
REM Запускается каждые 30-60 секунд

cd /d "c:\Users\A.Gorbatenko\Documents\Dashboard"
python script\update_location_snapshot.py
