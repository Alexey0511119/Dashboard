#!/usr/bin/env python3
"""
ЭКСТРЕННОЕ ВОССТАНОВЛЕНИЕ TRANSACTION_HISTORY
Только февраль и март 2026 года
Остальные данные НЕ ТРОГАЕМ
"""
import pymssql
from datetime import datetime

# Параметры подключения
SRC_SERVER = '10.7.0.248'
SRC_PORT = 1433
SRC_DATABASE = 'ils'
SRC_USER = 'manhreader'
SRC_PASSWORD = 'August2021'

DST_SERVER = '10.7.0.27'
DST_DATABASE = 'olap2_fixed'
DST_USER = 'sa'
DST_PASSWORD = 'Rdflhfn600'

PERIODS = [
    ('2026-02-01', '2026-02-28', 'Февраль 2026'),
    ('2026-03-01', '2026-03-24', 'Март 2026')
]

def get_src_conn():
    return pymssql.connect(
        server=SRC_SERVER,
        port=SRC_PORT,
        user=SRC_USER,
        password=SRC_PASSWORD,
        database=SRC_DATABASE,
        tds_version='7.0'
    )

def get_dst_conn():
    return pymssql.connect(
        server=DST_SERVER,
        user=DST_USER,
        password=DST_PASSWORD,
        database=DST_DATABASE,
        charset='UTF-8'
    )

def restore_period(start_date, end_date, period_name):
    print(f"\n{'='*60}")
    print(f"🔄 ВОССТАНОВЛЕНИЕ: {period_name}")
    print(f"{'='*60}")
    
    src = get_src_conn()
    dst = get_dst_conn()
    
    try:
        src_cursor = src.cursor()
        dst_cursor = dst.cursor()
        
        # 1. Считаем, сколько было в источнике
        src_cursor.execute("""
            SELECT COUNT(*)
            FROM TRANSACTION_HISTORY
            WHERE DATE_TIME_STAMP >= %s AND DATE_TIME_STAMP <= %s
        """, (start_date, end_date))
        source_count = src_cursor.fetchone()[0]
        print(f"📊 В источнике за период: {source_count:,} строк")
        
        # 2. Считаем, сколько сейчас в цели
        dst_cursor.execute("""
            SELECT COUNT(*)
            FROM raw_.TRANSACTION_HISTORY
            WHERE DATE_TIME_STAMP >= %s AND DATE_TIME_STAMP <= %s
        """, (start_date, end_date))
        current_count = dst_cursor.fetchone()[0]
        print(f"📊 Сейчас в цели (испорчено): {current_count:,} строк")
        
        # 3. Получаем список колонок из ЦЕЛЕВОЙ таблицы
        dst_cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'raw_' AND TABLE_NAME = 'TRANSACTION_HISTORY'
            ORDER BY ORDINAL_POSITION
        """)
        target_columns = [row[0] for row in dst_cursor.fetchall()]
        print(f"📋 В целевой таблице: {len(target_columns)} колонок")
        
        # 4. Получаем список колонок из ИСХОДНОЙ таблицы
        src_cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'TRANSACTION_HISTORY'
            ORDER BY ORDINAL_POSITION
        """)
        source_columns = [row[0] for row in src_cursor.fetchall()]
        print(f"📋 В исходной таблице: {len(source_columns)} колонок")
        
        # 5. Находим ОБЩИЕ колонки (которые есть в обеих таблицах)
        common_columns = [col for col in target_columns if col in source_columns]
        
        # Исключаем IDENTITY-колонки
        dst_cursor.execute("""
            SELECT c.name
            FROM sys.columns c
            INNER JOIN sys.tables t ON c.object_id = t.object_id
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = 'raw_' AND t.name = 'TRANSACTION_HISTORY' AND c.is_identity = 1
        """)
        identity_columns = [row[0] for row in dst_cursor.fetchall()]
        insert_columns = [col for col in common_columns if col not in identity_columns]
        
        print(f"📋 Колонок для вставки: {len(insert_columns)} (исключено IDENTITY: {len(identity_columns)})")
        
        if not insert_columns:
            print("❌ Нет колонок для вставки!")
            return
        
        # 6. Читаем данные из источника (ТОЛЬКО ОБЩИЕ КОЛОНКИ)
        print(f"⏳ Чтение данных из источника...")
        column_list = ", ".join(insert_columns)
        src_cursor.execute(f"""
            SELECT {column_list}
            FROM TRANSACTION_HISTORY
            WHERE DATE_TIME_STAMP >= %s AND DATE_TIME_STAMP <= %s
        """, (start_date, end_date))
        
        rows = src_cursor.fetchall()
        print(f"✅ Прочитано: {len(rows):,} строк")
        
        if not rows:
            print("⚠️ Нет данных для восстановления!")
            return
        
        # 7. Удаляем ТОЛЬКО данные за этот период
        print(f"🗑️ Удаление данных за {period_name} из цели...")
        dst_cursor.execute("""
            DELETE FROM raw_.TRANSACTION_HISTORY
            WHERE DATE_TIME_STAMP >= %s AND DATE_TIME_STAMP <= %s
        """, (start_date, end_date))
        deleted = dst_cursor.rowcount
        dst.commit()
        print(f"   Удалено: {deleted:,} строк")
        
        # 8. Вставляем данные пакетами
        print(f"📥 Вставка данных...")
        placeholders = ",".join(["%s"] * len(insert_columns))
        insert_sql = f"INSERT INTO raw_.TRANSACTION_HISTORY ({', '.join(insert_columns)}) VALUES ({placeholders})"
        
        batch_size = 5000
        inserted = 0
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            dst_cursor.executemany(insert_sql, batch)
            dst.commit()
            inserted += len(batch)
            
            if inserted % 100000 == 0:
                print(f"   → Вставлено: {inserted:,} строк...")
        
        print(f"✅ Вставлено: {inserted:,} строк")
        
        # 9. Проверка результата
        dst_cursor.execute("""
            SELECT COUNT(*)
            FROM raw_.TRANSACTION_HISTORY
            WHERE DATE_TIME_STAMP >= %s AND DATE_TIME_STAMP <= %s
        """, (start_date, end_date))
        final_count = dst_cursor.fetchone()[0]
        print(f"🔍 Проверка: в цели {final_count:,} строк")
        
        if final_count == source_count:
            print(f"✅ ВОССТАНОВЛЕНО КОРЕКТНО!")
        else:
            print(f"⚠️ РАСХОЖДЕНИЕ: источник={source_count:,}, цель={final_count:,}")
            print(f"   Разница: {abs(source_count - final_count):,} строк")
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
    finally:
        src.close()
        dst.close()

def main():
    print("="*60)
    print("🚨 ЭКСТРЕННОЕ ВОССТАНОВЛЕНИЕ TRANSACTION_HISTORY")
    print("   Только февраль и март 2026")
    print("   Остальные данные НЕ ТРОГАЕМ")
    print("="*60)
    print(f"📅 Дата запуска: {datetime.now()}")
    print(f"📁 Источник: {SRC_SERVER}/{SRC_DATABASE}")
    print(f"📁 Цель: {DST_SERVER}/{DST_DATABASE}")
    
    for start_date, end_date, period_name in PERIODS:
        restore_period(start_date, end_date, period_name)
    
    print("\n" + "="*60)
    print("🏁 ВОССТАНОВЛЕНИЕ ЗАВЕРШЕНО")
    print("="*60)

if __name__ == "__main__":
    main()
