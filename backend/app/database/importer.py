import os
import sys
import csv
import glob
import time
from pathlib import Path
from datetime import datetime
import duckdb

# Support direct execution
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database.connection import get_writable_connection, get_db_path, SCHEMA_PATH

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ORIGINAL_DATA_DIR = PROJECT_ROOT / "dataset" / "original"

def parse_num(s):
    if not s or not s.strip():
        return None
    cleaned = s.replace(" ", "").replace("\xa0", "").replace("%", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None

def parse_date(s):
    if not s or not s.strip():
        return None
    try:
        return datetime.strptime(s.strip(), "%d.%m.%Y").date()
    except ValueError:
        return None

def import_all_data(db_path: str = None, data_dir: Path = None) -> dict:
    start_time = time.time()
    data_dir = data_dir or ORIGINAL_DATA_DIR
    target_db = get_db_path(db_path)
    
    print(f"Initializing database at: {target_db}")
    if target_db.exists():
        os.remove(target_db)
        
    conn = get_writable_connection(str(target_db))
    
    # 1. Apply Schema
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.execute(schema_sql)
    print("Schema applied successfully.")

    counts = {}

    # 2. Import Brokers
    brokers_file = data_dir / "brokers.csv"
    print(f"Importing {brokers_file}...")
    broker_rows = []
    with open(brokers_file, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            broker_rows.append((
                r["Код брокера"].strip(),
                r["Наименование"].strip(),
                r["ИНН"].strip(),
                r["Регион"].strip()
            ))
    conn.executemany("INSERT INTO brokers VALUES (?, ?, ?, ?)", broker_rows)
    counts["brokers"] = len(broker_rows)
    print(f"Loaded {counts['brokers']} brokers.")

    # 3. Import Participants
    part_file = data_dir / "participants.csv"
    print(f"Importing {part_file}...")
    part_rows = []
    with open(part_file, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            vat = True if r["Плательщик НДС"].strip().lower() in ["да", "yes", "true", "ha"] else False
            part_rows.append((
                r["ИНН"].strip(),
                r["Наименование"].strip(),
                r["Регион"].strip(),
                r["Вид деятельности"].strip(),
                r["Роль"].strip(),
                vat
            ))
    conn.executemany("INSERT INTO participants VALUES (?, ?, ?, ?, ?, ?)", part_rows)
    counts["participants"] = len(part_rows)
    print(f"Loaded {counts['participants']} participants.")

    # 4. Import USD Rates
    usd_file = data_dir / "usd_rates.csv"
    print(f"Importing {usd_file}...")
    usd_rows = []
    with open(usd_file, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            usd_rows.append((
                parse_date(r["Дата"]),
                parse_num(r["Курс"])
            ))
    conn.executemany("INSERT INTO usd_rates VALUES (?, ?)", usd_rows)
    counts["usd_rates"] = len(usd_rows)
    print(f"Loaded {counts['usd_rates']} USD rates.")

    # 5. Import Contracts
    contracts_file = data_dir / "contracts.csv"
    print(f"Importing {contracts_file}...")
    contract_rows = []
    with open(contracts_file, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            contract_rows.append((
                r["Номер контракта"].strip(),
                r["Наименование продукта"].strip(),
                r["Марка товара"].strip() or None,
                r["Размер товара"].strip() or None,
                r["Сорт товара"].strip() or None,
                r["Тип товара"].strip() or None,
                r["Класс товара"].strip() or None,
                r["Код ТН ВЭД"].strip() or None,
                r["Группа товара"].strip() or None,
                r["Категория товара"].strip() or None,
                r["Отрасль промышленности"].strip() or None,
                r["Единица измерения"].strip(),
                parse_num(r["Лот"]),
                r["Валюта"].strip(),
                parse_num(r["Базисная цена"]),
                parse_num(r["Сумма залога"]),
                r["Базис поставки"].strip(),
                r["Регион"].strip(),
                r["Адрес склада"].strip() or None,
                r["Тип торгов"].strip(),
                r["Тип контракта"].strip(),
                r["Форма контракта"].strip(),
                int(r["Срок оплаты"].strip() or 0),
                int(r["Срок поставки"].strip() or 0),
                r["Упаковка"].strip() or None,
                r["ИНН продавца"].strip(),
                parse_date(r["Дата регистрации"]),
                parse_date(r["Действует до"])
            ))
    conn.executemany("""
        INSERT INTO contracts VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """, contract_rows)
    counts["contracts"] = len(contract_rows)
    print(f"Loaded {counts['contracts']} contracts.")

    # 6. Import Deals (deals_2022.csv to deals_2026.csv)
    deal_files = sorted(glob.glob(str(data_dir / "deals_*.csv")))
    print(f"Found {len(deal_files)} deal files: {[os.path.basename(f) for f in deal_files]}")
    
    total_deals = 0
    deal_appender = conn.appender("deals")
    
    for df in deal_files:
        fname = os.path.basename(df)
        f_count = 0
        file_start = time.time()
        batch = []
        with open(df, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                f_count += 1
                total_deals += 1
                batch.append([
                    int(r["Номер сделки"].strip()),
                    parse_date(r["Дата сделки"]),
                    r["Время сделки"].strip(),
                    r["Тип торгов"].strip(),
                    parse_num(r["Количество"]),
                    parse_num(r["Сумма сделки"]),
                    parse_num(r["Стартовая цена"]),
                    r["Номер контракта"].strip(),
                    r["Наименование товара"].strip(),
                    parse_num(r["Лот"]),
                    r["Единица измерения"].strip(),
                    r["Регион"].strip(),
                    r["Тип контракта"].strip(),
                    r["Форма контракта"].strip(),
                    r["Состояние сделки"].strip(),
                    r["ИНН продавца"].strip(),
                    r["ИНН покупателя"].strip(),
                    r["Брокер продавца"].strip(),
                    r["Брокер покупателя"].strip(),
                    parse_date(r["Дата оплаты"]),
                    parse_date(r["Дата поставки"]),
                    parse_num(r["Поставлено"])
                ])
                if len(batch) >= 20000:
                    deal_appender.append_rows(batch)
                    batch = []
        if batch:
            deal_appender.append_rows(batch)
            batch = []
        deal_appender.flush()
        print(f"Imported {fname}: {f_count:,} deals in {time.time() - file_start:.2f}s")

    del deal_appender
    counts["deals"] = total_deals
    conn.close()
    
    duration = time.time() - start_time
    print(f"\nImport Complete! Total 500k deals + all master data imported in {duration:.2f}s.")
    return counts

if __name__ == "__main__":
    import_all_data()
