"""
Entity Resolver and Semantic Search for UZEX AI Hackathon.
Verifies candidate entities (companies, brokers, commodities, regions)
against actual DuckDB database records before SQL generation.
"""

import re
from typing import Optional, Dict, Any, List, Tuple
from app.database.connection import get_readonly_connection
from .dictionary import COMMODITY_MAP, REGION_MAP, STATUS_MAP

class EntityResolver:
    def __init__(self):
        self._brokers: Dict[str, str] = {}  # code -> name
        self._broker_names: Dict[str, str] = {} # cleaned name -> code
        self._companies: Dict[str, str] = {} # inn -> name
        self._company_names: List[Tuple[str, str]] = [] # (cleaned_name, inn)
        self._categories: List[str] = []
        self._industries: List[str] = []
        self._initialized = False

    def initialize(self):
        """Loads reference catalog from DuckDB for ultra-fast in-memory entity resolution."""
        if self._initialized:
            return

        try:
            with get_readonly_connection() as conn:
                # Load brokers
                brokers_data = conn.execute("SELECT broker_code, name FROM brokers").fetchall()
                for code, name in brokers_data:
                    self._brokers[code.upper()] = name
                    clean_bname = self._clean_text(name)
                    self._broker_names[clean_bname] = code.upper()

                # Load participants (top sellers/buyers and common names)
                comp_data = conn.execute("SELECT inn, name FROM participants").fetchall()
                for inn, name in comp_data:
                    self._companies[inn] = name
                    self._company_names.append((self._clean_text(name), inn))

                # Load categories and industries
                cats = conn.execute("SELECT DISTINCT product_category FROM contracts WHERE product_category IS NOT NULL").fetchall()
                self._categories = [c[0] for c in cats]

                inds = conn.execute("SELECT DISTINCT industry FROM contracts WHERE industry IS NOT NULL").fetchall()
                self._industries = [i[0] for i in inds]

            self._initialized = True
        except Exception as e:
            # Will retry on next request if DB was not ready
            pass

    def _clean_text(self, text: str) -> str:
        """Normalizes quotes, punctuation, and case for fuzzy comparison."""
        t = text.lower()
        t = re.sub(r'[\'\"«»`‘’“”]', '', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    def resolve_broker(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Extracts and verifies broker code or broker company name.
        Returns (broker_code, broker_name) or None.
        """
        self.initialize()
        # Direct regex match for BK###
        m = re.search(r'\b(BK\d{3})\b', text, re.IGNORECASE)
        if m:
            code = m.group(1).upper()
            if code in self._brokers:
                return (code, self._brokers[code])

        clean_q = self._clean_text(text)
        # Match broker company name
        for bname_clean, code in self._broker_names.items():
            if len(bname_clean) > 4 and bname_clean in clean_q:
                return (code, self._brokers[code])
        return None

    def resolve_company(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Extracts and verifies company INN or company name.
        Returns (inn, company_name) or None.
        """
        self.initialize()
        # Direct 9-digit INN
        m = re.search(r'\b(\d{9})\b', text)
        if m:
            inn = m.group(1)
            if inn in self._companies:
                return (inn, self._companies[inn])

        clean_q = self._clean_text(text)
        # Search against verified companies (prioritize longer name matches)
        candidates = []
        for cname_clean, inn in self._company_names:
            if len(cname_clean) >= 5 and cname_clean in clean_q:
                candidates.append((len(cname_clean), inn, self._companies[inn]))
        
        if candidates:
            candidates.sort(reverse=True, key=lambda x: x[0])
            _, best_inn, best_name = candidates[0]
            return (best_inn, best_name)

        return None

    def resolve_commodity(self, text: str) -> Optional[str]:
        """
        Resolves commodity terms across Uzbek Latin, Uzbek Cyrillic, and Russian.
        """
        t = self._clean_text(text)
        for uz_term, ru_term in COMMODITY_MAP.items():
            if self._clean_text(uz_term) in t:
                return ru_term

        # Check Russian standard commodities
        common_ru_map = {
            "катод": "катод",
            "медный": "катод",
            "медь": "катод",
            "цемент": "цемент",
            "портландцемент": "портландцемент",
            "пшеница": "пшеница",
            "хлопок": "хлопок",
            "сахар": "сахар",
            "масло": "масло",
            "селитра": "селитра",
            "уголь": "уголь",
            "автобензин": "автобензин",
            "бензин": "автобензин",
            "полиэтилен": "полиэтилен",
            "шрот": "шрот",
            "битум": "битум",
            "прокат": "прокат",
            "стекло": "стекло",
            "мука": "мука",
            "рис": "рис"
        }
        for cr, mapped_val in common_ru_map.items():
            if cr in t:
                return mapped_val
        return None

    def resolve_category(self, text: str) -> Optional[str]:
        self.initialize()
        clean_q = self._clean_text(text)
        for cat in self._categories:
            if self._clean_text(cat) in clean_q:
                return cat
        return None

    def resolve_region(self, text: str) -> Optional[str]:
        t = self._clean_text(text)
        for alias, reg in REGION_MAP.items():
            if self._clean_text(alias) in t:
                return reg
        return None

    def resolve_status(self, text: str) -> Optional[str]:
        t = self._clean_text(text)
        for term, st in STATUS_MAP.items():
            if self._clean_text(term) in t:
                return st
        return None
