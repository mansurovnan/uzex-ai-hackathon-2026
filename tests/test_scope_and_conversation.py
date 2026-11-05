"""
Section I & Scope Router Test Suite.
Verifies that pure small talk, out-of-scope commodity questions, and unrelated
prompts are appropriately routed without issuing database SQL queries,
and that responses are delivered respectfully and fluently in the user's language.
"""

import pytest
from app.agent.query_engine import ExchangeQueryEngine
from app.agent.conversational import ConversationalAgent

@pytest.fixture(scope="module")
def engine():
    return ExchangeQueryEngine()

def test_small_talk_greetings_uzbek(engine):
    res = engine.process_question("Salom, qandaysiz?")
    assert res["sql"] is None
    assert res["row_count"] == 0
    assert any(w in res["answer"].lower() for w in ["assalomu", "salom", "yordam", "birja"])

def test_small_talk_greetings_russian(engine):
    res = engine.process_question("Привет! Как твои дела?")
    assert res["sql"] is None
    assert res["row_count"] == 0
    assert any(w in res["answer"].lower() for w in ["здравствуйте", "привет", "чем могу", "бирж"])

def test_small_talk_identity_uzbek(engine):
    res = engine.process_question("Siz kimsiz?")
    assert res["sql"] is None
    assert any(w in res["answer"].lower() for w in ["uzex", "ai", "agent", "yordamchi"])

def test_small_talk_thanks(engine):
    res_uz = engine.process_question("Katta rahmat!")
    assert res_uz["sql"] is None
    assert "arzimaydi" in res_uz["answer"].lower() or "xursandman" in res_uz["answer"].lower()

    res_ru = engine.process_question("Большое спасибо за помощь!")
    assert res_ru["sql"] is None
    assert "пожалуйста" in res_ru["answer"].lower() or "рад" in res_ru["answer"].lower()

def test_out_of_scope_weather(engine):
    res = engine.process_question("Ertaga Toshkentda ob-havo qanday bo'ladi?")
    assert res["sql"] is None
    assert "ob-havo" in res["answer"].lower() or "tegishli emas" in res["answer"].lower()

def test_out_of_scope_football(engine):
    res = engine.process_question("Real Madrid futbol o'yini necha-necha bo'ldi?")
    assert res["sql"] is None
    assert "futbol" in res["answer"].lower() or "tegishli emas" in res["answer"].lower()

def test_out_of_scope_crypto(engine):
    res = engine.process_question("Bitcoin narxi bugun qancha?")
    assert res["sql"] is None
    assert "kripto" in res["answer"].lower() or "bitcoin" in res["answer"].lower() or "tegishli emas" in res["answer"].lower()

def test_synthetic_data_authenticity_explanation(engine):
    res_uz = engine.process_question("Bu ma'lumotlar haqiqiymi yoki sintetikmi?")
    assert "sintetik" in res_uz["answer"].lower()
    assert "hackathon" in res_uz["answer"].lower()

    res_ru = engine.process_question("Откуда эти данные и настоящие ли они?")
    assert "синтетическ" in res_ru["answer"].lower()
    assert "hackathon" in res_ru["answer"].lower()
