"""
Independent Raw DuckDB Oracle Test Suite.
Verifies that the analytical engine produces identical numerical results
to hand-crafted, minimal, raw SQL queries executed directly against DuckDB.
"""

import pytest
import duckdb
from app.agent.query_engine import ExchangeQueryEngine
from app.database.connection import get_readonly_connection

@pytest.fixture(scope="module")
def engine():
    return ExchangeQueryEngine()

def test_oracle_overall_turnover_2024(engine):
    with get_readonly_connection() as conn:
        oracle = conn.execute("""
            SELECT 
                COUNT(*) AS total_deals,
                SUM(CASE WHEN status IN ('Исполнен', 'Исполнен(Частично)') THEN 1 ELSE 0 END) AS executed_deals,
                SUM(amount_uzs) AS total_turnover_uzs
            FROM v_deals_enriched
            WHERE EXTRACT(YEAR FROM deal_date) = 2024
        """).fetchone()

    res = engine.process_question("2024-yilda jami birja aylanmasi va bitimlar soni qancha bo'lgan?")
    assert res["verified"] is True
    # Verify deals count matches oracle
    assert str(oracle[0]) in res["answer"].replace(" ", "")

def test_oracle_top_broker_2023(engine):
    with get_readonly_connection() as conn:
        oracle = conn.execute("""
            SELECT seller_broker_code, SUM(executed_amount_uzs)
            FROM v_deals_enriched
            WHERE is_executed = TRUE
              AND EXTRACT(YEAR FROM deal_date) = 2023
            GROUP BY seller_broker_code
            ORDER BY SUM(executed_amount_uzs) DESC
            LIMIT 1
        """).fetchone()

    res = engine.process_question("2023 yilda eng faol broker qaysi bo'lgan?")
    assert res["verified"] is True
    assert oracle[0] in res["answer"]

def test_oracle_top_seller_2025(engine):
    with get_readonly_connection() as conn:
        oracle = conn.execute("""
            SELECT seller_inn, SUM(executed_amount_uzs)
            FROM v_deals_enriched
            WHERE is_executed = TRUE
              AND EXTRACT(YEAR FROM deal_date) = 2025
            GROUP BY seller_inn
            ORDER BY SUM(executed_amount_uzs) DESC
            LIMIT 1
        """).fetchone()

    res = engine.process_question("2025 yilda eng yirik sotuvchi kompaniya kim?")
    assert res["verified"] is True
    assert oracle[0] in res["answer"]

def test_oracle_cancelled_deals_count(engine):
    with get_readonly_connection() as conn:
        oracle_count = conn.execute("""
            SELECT COUNT(*) 
            FROM deals 
            WHERE status = 'Аннулирован(Не оплачен)'
        """).fetchone()[0]

    res = engine.process_question("Bekor qilingan bitimlar soni qancha?")
    assert res["verified"] is True
    assert str(oracle_count) in res["answer"].replace(" ", "")

def test_oracle_export_deals_count(engine):
    with get_readonly_connection() as conn:
        oracle_count = conn.execute("""
            SELECT COUNT(*) 
            FROM deals 
            WHERE contract_type = 'Экспортный'
        """).fetchone()[0]

    res = engine.process_question("Eksport bitimlari soni nechta?")
    assert res["verified"] is True
    assert str(oracle_count) in res["answer"].replace(" ", "")
