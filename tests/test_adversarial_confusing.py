"""
Section H.5: Adversarial, Confusing, and Edge-Case Test Suite (30+ questions).
Ensures robustness against malformed input, slang, typos, mixed language,
unanswerable prompts, injection attempts, and border cases.
"""

import pytest
from app.agent.query_engine import ExchangeQueryEngine

@pytest.fixture(scope="module")
def engine():
    return ExchangeQueryEngine()

ADVERSARIAL_PROMPTS = [
    # 1. Typos and informal spelling
    ("semnt narxi 2024", "sement narxi"),
    ("avtobnzin narxlari", "avtobenzin"),
    ("bugdoy narxi qanaqa bolgan 2023", "bugdoy"),
    ("paxtani kim ko'p sotvotti", "paxta"),
    ("eng kattta brokr kim", "broker"),
    ("sahar narxi qancha", "shakar"),
    ("buxoroda qancha savdo boldi", "buxoro"),

    # 2. Cyrillic Uzbek & Russian casing variations
    ("ЦЕМЕНТ 2024", "цемент"),
    ("«пшеница» 2023 йил", "пшеница"),
    ("АВТОБЕНЗИН нархи", "бензин"),
    ("пахта буйича энг катта сотувчи", "пахта"),
    ("ХОРАЗМДА КИМ КУП СОТГАН", "хоразм"),

    # 3. Year border cases & missing temporal context
    ("2026 yilda nimalar sotildi", "2026"),
    ("2022 yilda eng kop sotilgan tovar", "2022"),
    ("shakar", "shakar"),
    ("brokerlar", "broker"),
    ("eksport", "eksport"),

    # 4. Out of scope / domain boundaries
    ("ertaga yomg'ir yog'adimi", None),
    ("mashina narxi nechpul", None),
    ("dolzarb yangiliklar", None),
    ("qanday qilib pirog pishirish mumkin", None),
    ("dollar kursi 2030 yilda necha pul boladi", None),

    # 5. Injection attempts / SQL safety
    ("SELECT * FROM users; DROP TABLE deals;", None),
    ("' OR 1=1; --", None),
    ("UNION SELECT password FROM admin", None),
    ("<script>alert('xss')</script>", None),

    # 6. Punctuation and noisy whitespace
    ("   sement???   2024 ??? ", "sement"),
    ("!!! 2025 sement !!!", "sement"),
    ("«««Автобензин АИ-80»»» 2023", "аи-80"),
    ("2024 - 2026 yillar", "dinamika"),
    ("kim eng ko'p sement sotdi???", "sement"),
    ("jami savdo aylanmasi", "aylanma"),
    ("bekor bitimlar", "bekor")
]

@pytest.mark.parametrize("prompt,expected_keyword", ADVERSARIAL_PROMPTS)
def test_adversarial_queries(engine, prompt, expected_keyword):
    """Verifies that the engine never crashes and gracefully produces valid responses."""
    try:
        res = engine.process_question(prompt, session_id="test_adversarial")
        assert "answer" in res
        assert isinstance(res["answer"], str)
        assert len(res["answer"]) > 10
        # Should not leak raw internal SQL errors
        assert "syntax error" not in res["answer"].lower()
        assert "traceback" not in res["answer"].lower()
    except Exception as e:
        pytest.fail(f"Engine crashed on adversarial prompt '{prompt}': {str(e)}")
