"""
Multi-turn Conversation Context Manager for UZEX AI Hackathon.
Preserves session state and resolves anaphoric follow-up references
('uning', 'uni', 'ushbu mahsulotni', 'его', 'их', 'shu yilda', 'eng katta 3 ta kompaniyani ko'rsat', etc.).
"""

from typing import Dict, Any, Optional, List

class ConversationContext:
    def __init__(self):
        # Maps session_id -> state dict
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def get_session(self, session_id: str = "default") -> Dict[str, Any]:
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "last_broker": None,       # (code, name)
                "last_company": None,      # (inn, name)
                "last_commodity": None,    # str
                "last_product_name": None, # str
                "last_year": None,         # int
                "last_region": None,       # str
                "last_intent": None,       # str
                "last_sql": None,          # str
                "history": []              # list of {q, a, sql}
            }
        return self._sessions[session_id]

    def update_context(
        self,
        session_id: str = "default",
        broker: Optional[tuple] = None,
        company: Optional[tuple] = None,
        commodity: Optional[str] = None,
        product_name: Optional[str] = None,
        year: Optional[int] = None,
        region: Optional[str] = None,
        intent: Optional[str] = None,
        sql: Optional[str] = None,
        question: Optional[str] = None,
        answer: Optional[str] = None
    ):
        s = self.get_session(session_id)
        if broker:
            s["last_broker"] = broker
        if company:
            s["last_company"] = company
        if commodity:
            s["last_commodity"] = commodity
        if product_name:
            s["last_product_name"] = product_name
        if year:
            s["last_year"] = year
        if region:
            s["last_region"] = region
        if intent:
            s["last_intent"] = intent
        if sql:
            s["last_sql"] = sql
            
        if question and answer:
            s["history"].append({"question": question, "answer": answer, "sql": sql})
            if len(s["history"]) > 10:
                s["history"].pop(0)

    def resolve_references(self, text: str, session_id: str = "default") -> Dict[str, Any]:
        """
        Inspects whether the prompt contains follow-up pronouns or context references
        to previous entities. Returns inherited entities from session context.
        """
        s = self.get_session(session_id)
        t = text.lower().strip()
        
        # Follow-up pronoun markers across Uzbek (Latin/Cyrillic) and Russian
        uz_pronouns = [
            "uning", "uni", "ularning", "ularni", "shu", "ushbu", "buning", "buni", 
            "u haqida", "o'sha", "ushbu mahsulot", "shu mahsulot", "ushbu tovar", 
            "shu tovar", "ushbu kompaniya", "shu kompaniya", "bu kompaniya", "bu tovar",
            "bu korxona", "bu broker", "unga", "undan", "bunda", "bu"
        ]
        uz_cyr_pronouns = [
            "унинг", "уни", "уларнинг", "уларни", "шу", "ушбу", "бунинг", "буни",
            "у ҳақида", "ўша", "унга", "ундан"
        ]
        ru_pronouns = [
            "его", "ее", "её", "их", "у него", "у них", "этого", "данного", "этой",
            "данный", "этот товар", "эту компанию", "этот брокер", "данного товара",
            "кто его", "кто её", "кто их", "кто этот", "у данного", "для этого"
        ]
        
        # Continuation questions that implicitly inherit entity if one is active:
        # e.g., "Eng katta uchta kompaniyani ko'rsat", "Qaysi kompaniyalar sotgan?", "Kimlar sotib olgan?"
        continuation_phrases = [
            "qaysi kompaniya", "qaysi kompaniyalar", "kimlar sotgan", "kim sotgan",
            "kimlar sotib olgan", "kim sotib olgan", "xaridorlari kim", "sotuvchilari kim",
            "qaysi brokerlar", "qaysi hududlarda",
            "кто продал", "кто купил", "какие компании", "какие брокеры", "в каких регионах",
            "eng katta", "самый крупный", "топ 3", "топ 5", "uchta kompaniya", "3 ta kompaniya"
        ]

        # Check if the question is an explicit exchange-wide aggregation (should NOT inherit specific entities)
        is_exchange_wide = any(w in t for w in ["jami", "umumiy", "birja", "barcha", "всего", "общий", "бирж"])

        has_reference = (
            any(p in t for p in uz_pronouns + uz_cyr_pronouns + ru_pronouns)
            or any(cp in t for cp in continuation_phrases)
            or (len(t.split()) <= 3 and ("chi" in t or "чи" in t or len(t.split()) == 1))
        ) and not is_exchange_wide
        
        inherited = {
            "broker": None,
            "company": None,
            "commodity": None,
            "product_name": None,
            "year": None,
            "region": None
        }

        if has_reference:
            # If the user asks about turnover, volume, deals, sellers, buyers, brokers without re-naming the entity
            inherited["broker"] = s.get("last_broker")
            inherited["company"] = s.get("last_company")
            inherited["commodity"] = s.get("last_commodity")
            inherited["product_name"] = s.get("last_product_name")
            inherited["year"] = s.get("last_year")
            inherited["region"] = s.get("last_region")
            
        return inherited
