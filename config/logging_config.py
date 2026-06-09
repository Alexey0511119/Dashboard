"""
Конфигурация логирования для production
Все логи уровня WARNING и выше записываются в файл
"""
import logging
import os
from logging.handlers import RotatingFileHandler

# Создаем директорию для логов если не существует
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, 'dashboard.log')

# Настраиваем формат логов
log_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Создаем handler для файла с ротацией (10 файлов по 5MB)
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=5*1024*1024,  # 5MB
    backupCount=10,
    encoding='utf-8'
)
file_handler.setFormatter(log_format)
file_handler.setLevel(logging.WARNING)

# Создаем handler для консоли (только ошибки)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
console_handler.setLevel(logging.ERROR)

# Настраиваем корневой логгер
root_logger = logging.getLogger()
root_logger.setLevel(logging.WARNING)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Отключаем лишние логи от Dash и других библиотек
logging.getLogger('dash').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('plotly').setLevel(logging.WARNING)
