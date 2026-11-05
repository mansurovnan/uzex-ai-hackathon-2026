"""
Master Upgrade Verification Suite for UZEX AI Hackathon:
Tests:
1. Human-like Conversational Intelligence (Zero SQL execution, Uzbek Latin/Cyrillic & Russian).
2. Traded Products Catalog & Product Intelligence.
3. Dimension-aware Top Products (Volume vs Turnover vs Deals).
4. Commodity-specific Sellers, Buyers, Brokers, Regions, and Price Ranges.
5. Multi-turn Conversational Context (Pronoun resolution 'uni', 'uning', implicit continuations).
6. Synthetic Data Disclaimer transparency.
"""

import sys
import os
import time

# Ensure backend is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.agent.query_engine import ExchangeQueryEngine

def run_tests():
    engine = ExchangeQueryEngine()
    print("=" * 80)
    print("STARTING UZEX AI CONVERSATIONAL & PRODUCT INTELLIGENCE TEST SUITE")
    print("=" * 80)

    test_cases = [
        # --- 1. Pure Conversational Small-talk (Zero SQL) ---
        {
            "id": 1,
            "cat": "Conversational Greeting (UZ Latin)",
            "q": "Salom, qandaysiz?",
            "check": lambda res: res["sql"] is None and "alaykum" in res["answer"].lower() and res["row_count"] == 0
        },
        {
            "id": 2,
            "cat": "Conversational Greeting (UZ Cyrillic)",
            "q": "Ассалому алайкум",
            "check": lambda res: res["sql"] is None and "алайкум" in res["answer"].lower() and res["row_count"] == 0
        },
        {
            "id": 3,
            "cat": "Conversational Greeting (Russian)",
            "q": "Здравствуйте! Как дела?",
            "check": lambda res: res["sql"] is None and "здравствуйте" in res["answer"].lower() and res["row_count"] == 0
        },
        {
            "id": 4,
            "cat": "Conversational Gratitude (UZ Latin)",
            "q": "Katta rahmat!",
            "check": lambda res: res["sql"] is None and "arzimaydi" in res["answer"].lower()
        },
        {
            "id": 5,
            "cat": "Conversational Gratitude (Russian)",
            "q": "Большое спасибо за помощь",
            "check": lambda res: res["sql"] is None and "пожалуйста" in res["answer"].lower()
        },
        {
            "id": 6,
            "cat": "Conversational Farewell (UZ Latin)",
            "q": "Xayr, salomat bo'ling!",
            "check": lambda res: res["sql"] is None and "xayr" in res["answer"].lower()
        },
        {
            "id": 7,
            "cat": "Conversational Farewell (Russian)",
            "q": "До свидания!",
            "check": lambda res: res["sql"] is None and "до свидания" in res["answer"].lower()
        },
        {
            "id": 8,
            "cat": "Conversational Identity (UZ Latin)",
            "q": "Sen kimsan va nima qila olasan?",
            "check": lambda res: res["sql"] is None and "uzex ai" in res["answer"].lower() and "500 000" in res["answer"]
        },
        {
            "id": 9,
            "cat": "Conversational Identity (Russian)",
            "q": "Кто ты и чем можешь помочь?",
            "check": lambda res: res["sql"] is None and "uzex ai" in res["answer"].lower() and "500 000" in res["answer"]
        },

        # --- 2. Synthetic Data Disclaimer ---
        {
            "id": 10,
            "cat": "Synthetic Disclaimer (UZ Latin)",
            "q": "Bu ma'lumotlar haqiqatdan olinganmi yoki sintetikmi?",
            "check": lambda res: res["sql"] is None and "sintetik" in res["answer"].lower() and "hackathon" in res["answer"].lower()
        },
        {
            "id": 11,
            "cat": "Synthetic Disclaimer (Russian)",
            "q": "Откуда эти данные? Они реальные или синтетические?",
            "check": lambda res: res["sql"] is None and "синтетическ" in res["answer"].lower() and "hackathon" in res["answer"].lower()
        },

        # --- 3. Product Catalog ---
        {
            "id": 12,
            "cat": "Product Catalog (UZ Latin)",
            "q": "Birjada qanday mahsulotlar savdosi o'tkaziladi?",
            "check": lambda res: "product_category" in res["sql"].lower() and "katalogi" in res["answer"].lower() and len(res["data"]) >= 5
        },
        {
            "id": 13,
            "cat": "Product Catalog (Russian)",
            "q": "Какие товары торгуются на бирже?",
            "check": lambda res: "product_category" in res["sql"].lower() and "каталог" in res["answer"].lower() and len(res["data"]) >= 5
        },

        # --- 4. Product Intelligence: Sellers, Buyers, Brokers, Regions, Prices ---
        {
            "id": 14,
            "cat": "Product Sellers (UZ Latin)",
            "q": "2024-yilda paxtani kim sotgan?",
            "check": lambda res: "seller_name" in res["sql"].lower() and "хлопок" in res["sql"].lower() and "sotuvchilar" in res["answer"].lower() and len(res["data"]) > 0
        },
        {
            "id": 15,
            "cat": "Product Buyers (Russian)",
            "q": "Кто покупал цемент в 2024 году?",
            "check": lambda res: "buyer_name" in res["sql"].lower() and "цемент" in res["sql"].lower() and "покупатели" in res["answer"].lower() and len(res["data"]) > 0
        },
        {
            "id": 16,
            "cat": "Product Brokers (UZ Latin)",
            "q": "Sement bo'yicha qaysi brokerlar ishlagan?",
            "check": lambda res: "broker_name" in res["sql"].lower() and "цемент" in res["sql"].lower() and "brokerlar" in res["answer"].lower() and len(res["data"]) > 0
        },
        {
            "id": 17,
            "cat": "Product Regions (Russian)",
            "q": "В каких регионах продавался хлопок в 2024 году?",
            "check": lambda res: "seller_region" in res["sql"].lower() and "хлопок" in res["sql"].lower() and "регион" in res["answer"].lower() and len(res["data"]) > 0
        },
        {
            "id": 18,
            "cat": "Product Price Range & Quotations",
            "q": "2024-yilda sement narxlari qanday bo'lgan?",
            "check": lambda res: "min_price" in res["sql"].lower() and "avg_price" in res["sql"].lower() and "diapazon" in res["answer"].lower() and len(res["data"]) > 0
        },

        # --- 5. Multi-turn Conversational Context & Pronoun Follow-up ---
        {
            "id": 19,
            "cat": "Multi-turn Step 1: Top Product",
            "session": "sess_multiturn_chain",
            "q": "2024-yilda eng ko'p sotilgan mahsulot qaysi?",
            "check": lambda res: "reyting" in res["answer"].lower() and len(res["data"]) > 0
        },
        {
            "id": 20,
            "cat": "Multi-turn Step 2: Pronoun 'Uni qaysi kompaniya sotgan?'",
            "session": "sess_multiturn_chain",
            "q": "Uni qaysi kompaniyalar sotgan?",
            "check": lambda res: "seller_name" in res["sql"].lower() and len(res["data"]) > 0
        },
        {
            "id": 21,
            "cat": "Multi-turn Step 3: Continuation with word-number 'Eng katta uchta kompaniyani ko'rsat'",
            "session": "sess_multiturn_chain",
            "q": "Eng katta uchta kompaniyani ko'rsat",
            "check": lambda res: "limit 3" in res["sql"].lower() and len(res["data"]) == 3
        },
        {
            "id": 22,
            "cat": "Multi-turn Step 4: Company's brokers 'Ushbu kompaniyaning brokerlari kim?'",
            "session": "sess_multiturn_chain",
            "q": "Ushbu kompaniyaning brokerlari kim?",
            "check": lambda res: "broker" in res["sql"].lower() and len(res["data"]) > 0
        }
    ]

    passed = 0
    failed = 0

    for tc in test_cases:
        t_id = tc["id"]
        cat = tc["cat"]
        q = tc["q"]
        sess = tc.get("session", f"sess_ci_{t_id}")

        start_t = time.time()
        res = engine.process_question(q, session_id=sess)
        elapsed_ms = (time.time() - start_t) * 1000

        try:
            is_ok = tc["check"](res)
        except Exception as e:
            is_ok = False

        if is_ok:
            passed += 1
            print(f"[PASS] #{t_id:02d} [{cat}] ({elapsed_ms:.1f}ms) '{q}'")
        else:
            failed += 1
            print(f"[FAIL] #{t_id:02d} [{cat}] ({elapsed_ms:.1f}ms) '{q}'")
            print(f"  SQL: {res.get('sql')}")
            print(f"  Answer Preview: {res.get('answer', '')[:200]}...")

    print("=" * 80)
    print(f"TEST SUITE COMPLETED: {passed}/{len(test_cases)} Passed ({passed/len(test_cases)*100:.1f}%)")
    print("=" * 80)

    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
