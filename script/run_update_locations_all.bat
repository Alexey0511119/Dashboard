@echo off
REM Обновление LOCATION (ILS → raw → DWH)
REM Один скрипт для всего цикла
REM Запускается в cron/Task Scheduler каждые 1 минуту

cd /d "c:\Users\A.Gorbatenko\Documents\Dashboard"
python script\update_locations_all.py
