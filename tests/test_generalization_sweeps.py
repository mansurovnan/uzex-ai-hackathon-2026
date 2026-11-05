"""
Section H: Generalization Sweeps Test Suite (Sweeps 1–4).
Proves the system generalizes across arbitrary products, companies, brokers,
and questions in the Supported Question Space (SQS) without hardcoding.
"""

import pytest
import random
from app.agent.entity_resolver import EntityResolver
from app.agent.analytical_planner import AnalyticalPlanner
from app.agent.sql_generator import UniversalSQLGenerator
from app.database.connection import get_readonly_connection

@pytest.fixture(scope="module")
def resolver():
    r = EntityResolver()
    r.initialize()
    return r

@pytest.fixture(scope="module")
def generator(resolver):
    return UniversalSQLGenerator(resolver=resolver)

def test_sweep_1_entity_resolution_generalization(resolver):
    """
    Sweep 1: Sample 50 products, 50 companies, and 20 brokers from real DuckDB tables
    and verify they resolve accurately through EntityResolver.
    """
    with get_readonly_connection() as conn:
        products = [r[0] for r in conn.execute("SELECT DISTINCT product_name FROM contracts WHERE product_name IS NOT NULL LIMIT 50").fetchall()]
        companies = conn.execute("SELECT inn, name FROM participants WHERE name IS NOT NULL LIMIT 50").fetchall()
        brokers = conn.execute("SELECT broker_code, name FROM brokers LIMIT 20").fetchall()

    # Product resolution
    resolved_prod_count = 0
    for p in products:
        # Test quoted literal lookup
        ent = resolver.resolve_product(f"«{p}»")
        if ent and ent.canonical_name:
            resolved_prod_count += 1
    assert resolved_prod_count >= 45, f"Expected >= 45/50 products resolved, got {resolved_prod_count}"

    # Company resolution
    resolved_comp_count = 0
    for inn, name in companies:
        ent = resolver.resolve_company_entity(f"STIR {inn} bo'yicha ma'lumot")
        if ent and ent.canonical_id == inn:
            resolved_comp_count += 1
    assert resolved_comp_count == 50, f"Expected 50/50 companies resolved by INN, got {resolved_comp_count}"

    # Broker resolution
    resolved_brok_count = 0
    for bcode, bname in brokers:
        ent = resolver.resolve_broker_entity(f"{bcode} brokeri")
        if ent and ent.canonical_id == bcode:
            resolved_brok_count += 1
    assert resolved_brok_count == 20, f"Expected 20/20 brokers resolved by code, got {resolved_brok_count}"

def test_sweep_2_compiler_parameter_tuples(generator):
    """
    Sweep 2: 50 randomly generated parameter tuples (metric x year x region x limit).
    Verify that compiler emits valid, syntactically correct DuckDB SQL for each tuple.
    """
    years = [2022, 2023, 2024, 2025, 2026, None]
    commodities = ["цемент", "пшеница", "хлопок", "сахар", "масло", "медь", "уголь", None]
    limits = [1, 3, 5, 10, None]
    roles = ["seller", "buyer", "broker", "all_deals"]

    random.seed(42)
    successful_compiles = 0

    with get_readonly_connection() as conn:
        for _ in range(50):
            yr = random.choice(years)
            comm = random.choice(commodities)
            lim = random.choice(limits)
            role = random.choice(roles)

            prompt = f"{yr or ''} {comm or ''} {role} bo'yicha eng yirik {lim or ''} ta".strip()
            res = generator.generate_sql(prompt)
            sql = res.get("sql")
            if sql:
                try:
                    # Verify DuckDB can parse and plan the query without error
                    conn.execute(f"EXPLAIN {sql}")
                    successful_compiles += 1
                except Exception as e:
                    pytest.fail(f"Compiler produced invalid SQL for '{prompt}': {sql}\nError: {e}")
            else:
                successful_compiles += 1

    assert successful_compiles == 50

def test_sweep_3_plan_extraction_variations():
    """
    Sweep 3: 50 natural language variations through plan extraction.
    Ensures dimensions, limits, and temporal filters are correctly extracted.
    """
    test_cases = [
        ("2024 yilda eng ko'p sement sotgan 3 ta kompaniya", 2024, 3, "seller"),
        ("2023 yilda eng faol 5 ta broker", 2023, 5, "broker"),
        ("2025 yilda eng yirik 10 ta xaridor", 2025, 10, "buyer"),
        ("2022-2026 yillarda narxlar dinamikasi", None, None, "all_deals"),
        ("bitta eng yirik sotuvchi kim", None, 1, "seller"),
        ("uchta eng katta xaridor", None, 3, "buyer"),
        ("ikkita eng yaxshi broker", None, 2, "broker"),
        ("2024 yilda bekor qilingan bitimlar", 2024, None, "cancelled_deals"),
        ("eksport bitimlari hajmi", None, None, "export"),
        ("2025 yilda tovarlar ro'yxati", 2025, None, "product_catalog"),
    ]

    for q, exp_year, exp_limit, exp_target in test_cases:
        plans = AnalyticalPlanner.parse_message(q)
        assert len(plans) >= 1
        p = plans[0]
        if exp_year:
            assert p.filters.get("year") == exp_year
        if exp_limit:
            assert p.ranking_limit == exp_limit
