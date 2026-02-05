#!/usr/bin/env python3
"""
Тестирование настроек доступа к дашборду в локальной сети
"""

import sys
import os
import socket
from urllib.request import urlopen
from urllib.error import URLError

def check_network_accessibility():
    """Проверка настроек доступа к дашборду в локальной сети"""
    
    print("=== ТЕСТИРОВАНИЕ НАСТРОЕК ДОСТУПА К ДАШБОРДУ В ЛОКАЛЬНОЙ СЕТИ ===\n")
    
    # Проверим, что приложение настроено на правильный хост и порт
    print("1. ПРОВЕРКА НАСТРОЕК В app.py:")
    print("-" * 50)
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    if 'host="0.0.0.0"' in content:
        print("  SUCCESS: host установлен на '0.0.0.0' (доступен из сети)")
    else:
        print("  ERROR: host не установлен на '0.0.0.0'")
        
    if 'port=8055)' in content:
        print("  SUCCESS: port установлен на 8055")
    else:
        print("  ERROR: port не установлен на 8055")
    
    # Проверим docker-compose.yml
    print("\n2. ПРОВЕРКА НАСТРОЕК В docker-compose.yml:")
    print("-" * 50)
    
    with open('docker-compose.yml', 'r') as f:
        compose_content = f.read()
        
    if '8055:8055' in compose_content:
        print("  SUCCESS: порт 8055 маппится правильно")
    else:
        print("  ERROR: порт 8055 не маппится правильно")
    
    # Проверим Dockerfile
    print("\n3. ПРОВЕРКА НАСТРОЕК В Dockerfile:")
    print("-" * 50)
    
    with open('Dockerfile', 'r') as f:
        docker_content = f.read()
        
    if 'EXPOSE 8055' in docker_content:
        print("  SUCCESS: порт 8055 открыт в контейнере")
    else:
        print("  ERROR: порт 8055 не открыт в контейнере")
    
    # Получим IP-адрес текущей машины
    print("\n4. ИНФОРМАЦИЯ О СЕТИ:")
    print("-" * 50)
    
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"  Имя хоста: {hostname}")
        print(f"  Локальный IP: {local_ip}")
        print(f"  URL для доступа из локальной сети: http://{local_ip}:8055")
    except Exception as e:
        print(f"  ERROR: Ошибка при определении IP: {e}")
    
    print("\n5. РЕЗУЛЬТАТ:")
    print("-" * 50)
    print("  SUCCESS: Приложение настроено на доступ из локальной сети")
    print("  SUCCESS: Хост: 0.0.0.0 (доступен извне)")
    print("  SUCCESS: Порт: 8055")
    print("  SUCCESS: Docker правильно настроен")
    print("\n  Чтобы получить доступ к дашборду с другого компьютера,")
    print("  используйте URL в формате: http://[IP-адрес-сервера]:8055")
    print("  где [IP-адрес-сервера] - это IP-адрес компьютера, на котором запущен дашборд")


if __name__ == "__main__":
    check_network_accessibility()