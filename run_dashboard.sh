#!/bin/bash

# Скрипт автозапуска дашборда с автоматическим перезапуском при падении

cd /home/admin1/Dashboard

# Активируем виртуальное окружение
source /home/admin1/script/venv/bin/activate

# Создаем папку для логов если её нет
mkdir -p logs

# Функция логирования
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a logs/runner.log
}

log_message "======= DASHBOARD RUNNER STARTED ======="

restart_count=0
max_restarts=50

while [ $restart_count -lt $max_restarts ]; do
    log_message "Starting Dashboard (attempt $((restart_count + 1))/$max_restarts)"
    
    # Запускаем дашборд
    python3 app.py 2>&1 | tee -a logs/dashboard_output.log
    
    EXIT_CODE=$?
    
    log_message "Dashboard exited with code $EXIT_CODE"
    
    # Если завершился нормально (Ctrl+C) - выходим
    if [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 130 ]; then
        log_message "Normal shutdown"
        break
    fi
    
    restart_count=$((restart_count + 1))
    
    if [ $restart_count -lt $max_restarts ]; then
        wait_time=$((5 + restart_count * 2))
        if [ $wait_time -gt 30 ]; then
            wait_time=30
        fi
        log_message "Crash detected. Restarting in $wait_time seconds..."
        sleep $wait_time
    else
        log_message "Max restart attempts reached. Exiting."
        exit 1
    fi
done

log_message "======= DASHBOARD RUNNER STOPPED ======="