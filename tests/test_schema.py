import os
import sys
import tempfile
from pathlib import Path

# Add backend to python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.database.connection import (
    get_writable_connection,
    get_readonly_connection,
    init_database,
    SCHEMA_PATH
)

def test_schema_creation_and_tables():
    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=True) as tmp:
        tmp_db_path = tmp.name

    if os.path.exists(tmp_db_path):
        os.remove(tmp_db_path)

    try:
        # 1. Initialize schema via writable connection
        init_database(db_path=tmp_db_path)

        # 2. Insert sample records using writable connection
        with get_writable_connection(tmp_db_path) as wconn:
            wconn.execute("INSERT INTO brokers VALUES ('BK001', 'Test Broker', '123456789', 'Toshkent shahri')")
            wconn.execute("INSERT INTO participants VALUES ('111111111', 'Seller LLC', 'Toshkent shahri', 'Manufacturer', 'Продавец', TRUE)")
            wconn.execute("INSERT INTO participants VALUES ('222222222', 'Buyer LLC', 'Samarqand viloyati', 'Trader', 'Покупатель', FALSE)")
            wconn.execute("INSERT INTO usd_rates VALUES ('2024-01-15', 12450.5000)")
            wconn.execute("""
                INSERT INTO contracts VALUES (
                    'C1001', 'Test Cement', 'M500', NULL, '1 sort', NULL, NULL, '2523290000',
                    'Высоколиквидные товары', 'Строительные материалы', 'Строительная индустрия',
                    'тонна', 1.0000, 'Узбекский сум', 650000.0000, 10.0000, 'EXW', 'Toshkent shahri',
                    'Main Depot', 'Английский аукцион', 'Внутренний', 'Спот', 5, 10, 'Bagged',
                    '111111111', '2024-01-01', '2024-12-31'
                )
            """)
            # Deal 1: Executed (10 lots, 6,500,000 UZS)
            wconn.execute("""
                INSERT INTO deals VALUES (
                    1, '2024-01-15', '10:00:00', 'Английский аукцион', 10.0000, 6500000.0000, 650000.0000,
                    'C1001', 'Test Cement M500 1 sort', 1.0000, 'тонна', 'Toshkent shahri',
                    'Внутренний', 'Спот', 'Исполнен', '111111111', '222222222', 'BK001', 'BK001',
                    '2024-01-16', '2024-01-18', 10.0000
                )
            """)
            # Deal 2: Cancelled (5 lots, 3,250,000 UZS)
            wconn.execute("""
                INSERT INTO deals VALUES (
                    2, '2024-01-15', '11:00:00', 'Английский аукцион', 5.0000, 3250000.0000, 650000.0000,
                    'C1001', 'Test Cement M500 1 sort', 1.0000, 'тонна', 'Toshkent shahri',
                    'Внутренний', 'Спот', 'Аннулирован(Не оплачен)', '111111111', '222222222', 'BK001', 'BK001',
                    NULL, NULL, NULL
                )
            """)
        
        # 3. Open READ-ONLY connection for all verification & agent queries
        with get_readonly_connection(tmp_db_path) as conn:
            tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]
            assert "brokers" in tables, "Table 'brokers' missing"
            assert "participants" in tables, "Table 'participants' missing"
            assert "contracts" in tables, "Table 'contracts' missing"
            assert "usd_rates" in tables, "Table 'usd_rates' missing"
            assert "deals" in tables, "Table 'deals' missing"
            assert "v_deals_enriched" in tables, "View 'v_deals_enriched' missing"

            # 4. Verify column data types in deals
            cols = conn.execute("DESCRIBE deals").fetchall()
            col_types = {col[0]: col[1].replace(" ", "") for col in cols}
            assert "DECIMAL(24,4)" in col_types["deal_amount"], f"Unexpected type for deal_amount: {col_types['deal_amount']}"
            assert "DECIMAL(18,4)" in col_types["quantity_lots"], f"Unexpected type for quantity_lots: {col_types['quantity_lots']}"
            assert "DECIMAL(18,4)" in col_types["start_price"], f"Unexpected type for start_price: {col_types['start_price']}"
            assert "DATE" in col_types["deal_date"], f"Unexpected type for deal_date: {col_types['deal_date']}"
            assert "BIGINT" in col_types["deal_id"], f"Unexpected type for deal_id: {col_types['deal_id']}"

            # 5. Verify read-only enforcement
            read_only_blocked = False
            try:
                conn.execute("CREATE TABLE evil_table (id INT)")
            except Exception:
                read_only_blocked = True
            assert read_only_blocked, "Read-only connection failed to block table creation!"

            # 6. Verify indexes exist
            indexes = [row[0] for row in conn.execute("SELECT index_name FROM duckdb_indexes()").fetchall()]
            print("Created indexes:", indexes)
            assert len(indexes) >= 8, f"Expected at least 8 secondary indexes, got {len(indexes)}"

            # 7. Query enriched view to verify calculations and transaction status rules
            res = conn.execute("""
                SELECT 
                    deal_id, status_category, is_executed, is_cancelled, 
                    contracted_volume_units, executed_volume_units,
                    amount_uzs, executed_amount_uzs
                FROM v_deals_enriched
                ORDER BY deal_id
            """).fetchall()

            # Deal 1 assertions (Executed deal)
            assert res[0][0] == 1
            assert res[0][1] == 'EXECUTED'
            assert res[0][2] is True
            assert res[0][3] is False
            assert float(res[0][4]) == 10.0
            assert float(res[0][5]) == 10.0
            assert float(res[0][6]) == 6500000.0
            assert float(res[0][7]) == 6500000.0

            # Deal 2 assertions (Cancelled deal: executed volume and amount MUST BE ZERO)
            assert res[1][0] == 2
            assert res[1][1] == 'CANCELLED'
            assert res[1][2] is False
            assert res[1][3] is True
            assert float(res[1][4]) == 5.0
            assert float(res[1][5]) == 0.0
            assert float(res[1][6]) == 3250000.0
            assert float(res[1][7]) == 0.0

            print("Enriched view status and volume business rules verified successfully!")
            print("All schema verification assertions passed successfully!")
    finally:
        if os.path.exists(tmp_db_path):
            os.remove(tmp_db_path)

if __name__ == "__main__":
    test_schema_creation_and_tables()

