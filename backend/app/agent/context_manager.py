"""
Multi-turn Conversation Context Manager for UZEX AI Hackathon.
Preserves session state and resolves anaphoric follow-up references
('uning', 'uning aylanmasi', 'его', 'их', 'shu yilda', etc.).
"""

from typing import Dict, Any, Optional

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
        Inspects whether the prompt contains follow-up pronouns referencing
        previous entities. Returns inherited entities from session context.
        """
        s = self.get_session(session_id)
        t = text.lower()
        
        # Follow-up pronoun markers
        uz_pronouns = ["uning", "ularning", "shu", "ushbu", "buning", "u haqida", "o'sha"]
        ru_pronouns = ["его", "ее", "её", "их", "у него", "у них", "этого", "данного", "этой"]
        
        has_reference = any(p in t for p in uz_pronouns + ru_pronouns) or len(t.split()) <= 4
        
        inherited = {
            "broker": None,
            "company": None,
            "commodity": None,
            "year": None,
            "region": None
        }

        if has_reference:
            # If the user asks about turnover, volume, deals, or details without naming the entity
            inherited["broker"] = s.get("last_broker")
            inherited["company"] = s.get("last_company")
            inherited["commodity"] = s.get("last_commodity")
            inherited["year"] = s.get("last_year")
            inherited["region"] = s.get("last_region")
            
        return inherited
