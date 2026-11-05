"""
Mandatory Section G Acceptance Test Suite for UZEX AI.
Tests 1–5 covering:
1. Specific product, specific year (Пшеница продовольственная, 2024).
2. Multi-year trend with 2026 caveat (2022–2026).
3. Product sellers with top 3 ranking & market shares («Автобензин АИ-80», 2023).
4. 4-turn follow-up chain (Cement 2025 -> cancelled -> top seller -> region/INN).
5. Three distinct ranking metrics for top products (deals, turnover, volume).
"""

import pytest
import duckdb
from app.agent.query_engine import ExchangeQueryEngine

@pytest.fixture(scope="module")
def engine():
    return ExchangeQueryEngine()

def test_section_g_test_1_specific_product_year(engine):
    """
    Test 1: Specific product, specific year.
    Uzbek Latin: 2024 yilda «Пшеница продовольственная» bo'yicha qancha bitim tuzilgan va o'rtacha narx qancha bo'lgan?
    Russian: Сколько сделок заключено по «Пшенице продовольственной» в 2024 году и какова средняя цена?
    """
    q_uz = "2024 yilda «Пшеница продовольственная» bo'yicha qancha bitim tuzilgan va o'rtacha narx qancha bo'lgan?"
    res_uz = engine.process_question(q_uz, session_id="test_g1_uz")
    
    assert res_uz["verified"] is True
    assert res_uz["row_count"] > 0
    ans_uz = res_uz["answer"]
    # Check that canonical product is selected
    assert "Пшеница продовольственная" in ans_uz
    assert "3-класс" not in ans_uz and "4-класс" not in ans_uz
    # Check deal count (5 961 deals in 2024)
    assert "5 961" in ans_uz or "5961" in ans_uz
    # Check weighted avg price (~3 894 243)
    assert "3 894 243" in ans_uz or "3894243" in ans_uz

    # Russian version
    q_ru = "Сколько сделок заключено по «Пшенице продовольственной» в 2024 году и какова средняя цена?"
    res_ru = engine.process_question(q_ru, session_id="test_g1_ru")
    assert res_ru["verified"] is True
    assert "5 961" in res_ru["answer"] or "5961" in res_ru["answer"]

def test_section_g_test_2_multi_year_trend_with_2026_caveat(engine):
    """
    Test 2: Multi-year trend with 2026 caveat.
    Uzbek: 2022 yildan 2026 yilgacha birjada o'rtacha narxlar qanday o'zgardi?
    Russian: Как изменились средние цены на бирже с 2022 по 2026 год?
    """
    q_uz = "2022 yildan 2026 yilgacha birjada o'rtacha narxlar qanday o'zgardi?"
    res_uz = engine.process_question(q_uz, session_id="test_g2_uz")
    
    assert res_uz["verified"] is True
    ans_uz = res_uz["answer"]
    # All 5 years must be in the table
    for yr in ["2022", "2023", "2024", "2025", "2026"]:
        assert yr in ans_uz
    # Explicit 2026 caveat must be present
    assert "2026" in ans_uz and ("10 oy" in ans_uz or "noto'liq" in ans_uz or "qamrovi" in ans_uz)

    q_ru = "Как изменились средние цены на бирже с 2022 по 2026 год?"
    res_ru = engine.process_question(q_ru, session_id="test_g2_ru")
    assert res_ru["verified"] is True
    ans_ru = res_ru["answer"]
    for yr in ["2022", "2023", "2024", "2025", "2026"]:
        assert yr in ans_ru
    assert "2026" in ans_ru and ("10 месяцев" in ans_ru or "неполный" in ans_ru)

def test_section_g_test_3_product_sellers(engine):
    """
    Test 3: Top sellers for a product.
    Uzbek: «Автобензин АИ-80» mahsulotini 2023 yilda eng ko'p sotgan 3 ta kompaniya
    Russian: 3 крупнейших продавца «Автобензин АИ-80» в 2023 году
    """
    q_uz = "«Автобензин АИ-80» mahsulotini 2023 yilda eng ko'p sotgan 3 ta kompaniya"
    res_uz = engine.process_question(q_uz, session_id="test_g3_uz")
    
    assert res_uz["verified"] is True
    ans_uz = res_uz["answer"]
    # Check top sellers: Linom Energo and Suzem Energo
    assert "Linom Energo" in ans_uz or "948428016" in ans_uz
    assert "Suzem Energo" in ans_uz or "957989836" in ans_uz
    assert "Vejut Neft" in ans_uz or "903587288" in ans_uz
    # Check that market share percentage is computed
    assert "%" in ans_uz

    q_ru = "3 крупнейших продавца «Автобензин АИ-80» в 2023 году"
    res_ru = engine.process_question(q_ru, session_id="test_g3_ru")
    assert res_ru["verified"] is True
    assert "Linom Energo" in res_ru["answer"] or "948428016" in res_ru["answer"]

def test_section_g_test_4_followup_chain(engine):
    """
    Test 4: Follow-up chain (4 turns).
    Turn 1: 2025 yilda sement bo'yicha jami bitimlar hajmi qancha?
    Turn 2: Ularning qanchasi bekor qilingan?
    Turn 3: Eng katta sotuvchi kim bo'lgan?
    Turn 4: Bu kompaniya qaysi hududda joylashgan va STIR raqami nima?
    """
    sess = "test_g4_chain"
    # Turn 1
    t1 = engine.process_question("2025 yilda sement bo'yicha jami bitimlar hajmi qancha?", session_id=sess)
    assert t1["verified"] is True
    assert "1 426 805" in t1["answer"] or "8 837" in t1["answer"] or "8837" in t1["answer"]

    # Turn 2: Inherits cement & 2025
    t2 = engine.process_question("Ularning qanchasi bekor qilingan?", session_id=sess)
    assert t2["verified"] is True
    assert "622" in t2["answer"] or "bekor" in t2["answer"].lower()

    # Turn 3: Top seller for cement in 2025
    t3 = engine.process_question("Eng katta sotuvchi kim bo'lgan?", session_id=sess)
    assert t3["verified"] is True
    assert "FICHO‘R STROY" in t3["answer"] or "984713635" in t3["answer"]

    # Turn 4: Region and INN of this company
    t4 = engine.process_question("Bu kompaniya qaysi hududda joylashgan va STIR raqami nima?", session_id=sess)
    assert t4["verified"] is True
    assert "984713635" in t4["answer"]
    assert "Toshkent" in t4["answer"]

def test_section_g_test_5_three_ranking_metrics(engine):
    """
    Test 5: Three distinct ranking metrics for 2024 top products.
    Metric A: Turnover (UZS)
    Metric B: Physical volume (tons)
    Metric C: Deals count
    """
    # Metric A: Pul aylanmasi
    res_turnover = engine.process_question("2024 yilda pul aylanmasi bo'yicha eng yuqori 5 ta tovar", session_id="test_g5_turnover")
    assert res_turnover["verified"] is True
    # #1 turnover is Пшеница продовольственная
    assert "Пшеница продовольственная" in res_turnover["answer"]

    # Metric B: Hajm (tonna)
    res_vol = engine.process_question("2024 yilda hajm (tonna) bo'yicha eng yuqori 5 ta tovar", session_id="test_g5_vol")
    assert res_vol["verified"] is True
    assert "ПОРТЛАНДЦЕМЕНТ" in res_vol["answer"] or "Пшеница" in res_vol["answer"]

    # Metric C: Bitimlar soni
    res_deals = engine.process_question("2024 yilda bitimlar soni bo'yicha eng yuqori 5 ta tovar", session_id="test_g5_deals")
    assert res_deals["verified"] is True
    # #1 deals count is Хлопок-сырец (спот)
    assert "Хлопок" in res_deals["answer"]
