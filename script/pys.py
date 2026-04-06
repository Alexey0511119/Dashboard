import pyodbc
import pandas as pd
import os
import glob
import re
from datetime import datetime, date
import logging
import time
from pathlib import Path

# ============= КОНФИГУРАЦИЯ =============
MSSQL_CONFIG = {
    'server': '10.7.0.27',
    'port': 1433,
    'database': 'DefectMonitoring',
    'user': 'sa',
    'password': 'Rdflhfn600'
}

CSV_FOLDER = r'C:\Users\A.Gorbatenko\Desktop\Выгрузка брака и боя'
ARCHIVE_FOLDER = r'C:\Users\A.Gorbatenko\Desktop\Выгрузка брака и боя\Архив'
ERROR_FOLDER = r'C:\Users\A.Gorbatenko\Desktop\Выгрузка брака и боя\Ошибки'
LOG_FOLDER = r'C:\Users\A.Gorbatenko\Desktop\Выгрузка брака и боя\Логи'

for folder in [ARCHIVE_FOLDER, ERROR_FOLDER, LOG_FOLDER]:
    Path(folder).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_FOLDER, f'loader_{datetime.now().strftime("%Y%m%d")}.log'), 
                           encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class MSSQLClient:
    def __init__(self):
        self.server = MSSQL_CONFIG['server']
        self.port = MSSQL_CONFIG['port']
        self.database = MSSQL_CONFIG['database']
        self.user = MSSQL_CONFIG['user']
        self.password = MSSQL_CONFIG['password']
        self.connection_string = (
            f"DRIVER={{SQL Server}};"
            f"SERVER={self.server},{self.port};"
            f"DATABASE={self.database};"
            f"UID={self.user};"
            f"PWD={self.password};"
            f"TrustServerCertificate=yes;"
        )
        
    def execute(self, query):
        try:
            conn = pyodbc.connect(self.connection_string, timeout=30)
            cursor = conn.cursor()
            cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
                conn.close()
                return result
            else:
                conn.commit()
                result = cursor.rowcount
                conn.close()
                return result
        except Exception as e:
            logging.error(f"SQL Error: {e}")
            return []

def parse_number(val):
    """Преобразование строки с запятой в число"""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(' ', '').replace(',', '.')
    try:
        return float(s)
    except:
        return 0.0

def load_csv_to_sql(file_path, client):
    start_time = time.time()
    file_name = os.path.basename(file_path)
    logging.info(f"Обработка файла: {file_name}")
    
    # ИЗВЛЕКАЕМ ДАТУ ИЗ ИМЕНИ ФАЙЛА
    date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', file_name)
    if not date_match:
        return 0, f"Не удалось извлечь дату из имени файла: {file_name}"
    
    report_date = date(int(date_match.group(3)), int(date_match.group(2)), int(date_match.group(1)))
    report_date_str = report_date.strftime('%Y-%m-%d')
    logging.info(f"Дата из имени файла: {report_date_str}")
    
    try:
        # Читаем CSV с разделителем TAB и кодировкой UTF-16
        df = pd.read_csv(file_path, sep='\t', encoding='utf-16')
        logging.info(f"Строк: {len(df)}, колонок: {len(df.columns)}")
        logging.info(f"Колонки: {list(df.columns)}")
        
        # Выводим первые 3 строки для проверки
        logging.info("Пример данных (первые 3 строки):")
        for i in range(min(3, len(df))):
            row = df.iloc[i]
            row_str = {}
            for col in df.columns:
                val = row[col]
                if pd.notna(val):
                    row_str[col] = str(val)[:80]
            logging.info(f"  Строка {i+1}: {row_str}")
        
        # ========== ИСПРАВЛЕНИЕ: Удаляем ТОЛЬКО за текущую дату ==========
        delete_query = f"DELETE FROM monitoring.Fact_DefectInventory WHERE ReportDate = '{report_date_str}'"
        client.execute(delete_query)
        logging.info(f"Удалены старые данные за {report_date_str}")
        
        rows_inserted = 0
        
        for idx, row in df.iterrows():
            try:
                # Берем данные ПО ИМЕНИ КОЛОНКИ
                division = str(row['Подразделение']) if pd.notna(row['Подразделение']) else ''
                warehouse_name = str(row['Название склада']) if pd.notna(row['Название склада']) else ''
                warehouse_type = str(row['Тип склада']) if 'Тип склада' in df.columns and pd.notna(row['Тип склада']) else 'Хранение'
                
                # Пропускаем пустые строки
                if not division or not warehouse_name:
                    continue
                
                # Суммы
                aging30 = parse_number(row['Не больше 30']) if 'Не больше 30' in df.columns else 0
                aging60 = parse_number(row['Не больше 60']) if 'Не больше 60' in df.columns else 0
                aging90 = parse_number(row['Не больше 90']) if 'Не больше 90' in df.columns else 0
                aging135 = parse_number(row['Не больше 135']) if 'Не больше 135' in df.columns else 0
                aging180 = parse_number(row['Не больше 180']) if 'Не больше 180' in df.columns else 0
                aging_over180 = parse_number(row['Свыше 180']) if 'Свыше 180' in df.columns else 0
                total_amount = parse_number(row['Всего ТМЗ']) if 'Всего ТМЗ' in df.columns else 0
                
                if idx == 0:
                    logging.info(f"ПЕРВАЯ СТРОКА:")
                    logging.info(f"  Division: {division}")
                    logging.info(f"  WarehouseName: {warehouse_name}")
                    logging.info(f"  WarehouseType: {warehouse_type}")
                    logging.info(f"  TotalAmount: {total_amount}")
                
                # Экранируем кавычки
                division_escaped = division.replace("'", "''")
                warehouse_name_escaped = warehouse_name.replace("'", "''")
                warehouse_type_escaped = warehouse_type.replace("'", "''")
                
                # Вставка (обновление не нужно, так как мы удалили старые данные за эту дату)
                insert_query = f"""
                    INSERT INTO monitoring.Fact_DefectInventory 
                    (ReportDate, Division, WarehouseName, WarehouseType,
                     AgingDays30, AgingDays60, AgingDays90, AgingDays135, AgingDays180, AgingDaysOver180, TotalAmount)
                    VALUES (
                        '{report_date_str}',
                        N'{division_escaped}',
                        N'{warehouse_name_escaped}',
                        N'{warehouse_type_escaped}',
                        {aging30}, {aging60}, {aging90}, {aging135}, {aging180}, {aging_over180}, {total_amount}
                    )
                """
                client.execute(insert_query)
                
                rows_inserted += 1
                
                if (idx + 1) % 50 == 0:
                    logging.info(f"Обработано {idx + 1} строк...")
                    
            except Exception as e:
                logging.error(f"Ошибка в строке {idx + 1}: {e}")
                continue
        
        duration = int(time.time() - start_time)
        
        # Логирование
        log_query = f"""
            INSERT INTO monitoring.Load_Log 
            (SourceFile, ReportDate, RowsProcessed, RowsInserted, Status, DurationSeconds)
            VALUES (
                N'{file_name}',
                '{report_date_str}',
                {len(df)},
                {rows_inserted},
                'SUCCESS',
                {duration}
            )
        """
        client.execute(log_query)
        
        logging.info(f"Загружено: {rows_inserted} записей для даты {report_date_str}")
        return rows_inserted, None
        
    except Exception as e:
        duration = int(time.time() - start_time)
        error_msg = str(e)
        logging.error(f"Ошибка: {error_msg}")
        
        try:
            log_query = f"""
                INSERT INTO monitoring.Load_Log 
                (SourceFile, ReportDate, Status, ErrorMessage, DurationSeconds)
                VALUES (
                    N'{file_name}',
                    '{report_date_str}',
                    'FAILED',
                    N'{error_msg[:500].replace("'", "''")}',
                    {duration}
                )
            """
            client.execute(log_query)
        except:
            pass
        
        return 0, error_msg

def main():
    logging.info("=" * 50)
    logging.info("Запуск загрузчика данных")
    
    if not os.path.exists(CSV_FOLDER):
        logging.error(f"Папка не найдена: {CSV_FOLDER}")
        return
    
    try:
        client = MSSQLClient()
        
        # Проверка подключения
        test_result = client.execute("SELECT 1 AS Test")
        if test_result:
            logging.info("Подключение к SQL Server успешно")
        else:
            logging.error("Не удалось подключиться")
            return
        
        # ========== ИСПРАВЛЕНИЕ: Убрали полную очистку таблицы ==========
        # Больше не удаляем все данные!
        logging.info("Загрузка данных (без удаления исторических данных)")
        
        csv_files = glob.glob(os.path.join(CSV_FOLDER, '*.csv'))
        
        if not csv_files:
            logging.info("Нет CSV файлов")
            return
        
        total_inserted = 0
        
        for file_path in sorted(csv_files):
            inserted, error = load_csv_to_sql(file_path, client)
            file_name = os.path.basename(file_path)
            
            if error:
                error_path = os.path.join(ERROR_FOLDER, file_name)
                os.rename(file_path, error_path)
                logging.info(f"Файл перемещен в ошибки: {error_path}")
            else:
                total_inserted += inserted
                archive_path = os.path.join(ARCHIVE_FOLDER, file_name)
                os.rename(file_path, archive_path)
                logging.info(f"Файл перемещен в архив: {archive_path}")
        
        logging.info(f"Загрузка завершена. Итого: {total_inserted} записей")
        
        # Выводим статистику по датам
        stats = client.execute("""
            SELECT ReportDate, COUNT(*) as Cnt 
            FROM monitoring.Fact_DefectInventory 
            GROUP BY ReportDate 
            ORDER BY ReportDate DESC
        """)
        if stats:
            logging.info("Статистика по датам в базе:")
            for row in stats:
                logging.info(f"  {row[0]}: {row[1]} записей")
        
        # Проверяем, что название склада заполнилось
        sample = client.execute("""
            SELECT TOP 5 ReportDate, Division, WarehouseName, TotalAmount 
            FROM monitoring.Fact_DefectInventory 
            ORDER BY ID DESC
        """)
        if sample:
            logging.info("Пример последних записей:")
            for row in sample:
                logging.info(f"  {row[0]} | {row[1][:50]} | {row[2][:50]} | {row[3]}")
        
        logging.info("=" * 50)
        
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        raise

if __name__ == "__main__":
    main()