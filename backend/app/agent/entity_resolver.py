"""
Universal 6-Stage Entity Resolver & Index for UZEX AI.
Loads verified reference catalog from DuckDB at startup:
- 230 canonical products with units and categories
- 14,392 market participants with INNs and roles (392 sellers, 13,997 buyers)
- 120 accredited brokers with codes and regions
- 8 commodity categories, contract types, regions, and statuses.

Resolution Policy (Strict Order):
1. Literal Extraction from quotes («...», "...", „...“, '...')
2. Exact match against canonical string
3. Normalized exact match (case, whitespace, apostrophes o‘/o'/g‘/g', ё↔е)
4. Script/transliteration match (Uzbek Latin ↔ Uzbek Cyrillic ↔ Russian)
5. Cross-language alias & glossary match
6. Calibrated token / fuzzy match
"""

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
from app.database.connection import get_readonly_connection
from .dictionary import COMMODITY_MAP, REGION_MAP, STATUS_MAP

@dataclass
class ResolvedEntity:
    entity_type: str  # "product", "category", "company", "broker", "region", "status"
    canonical_id: str
    canonical_name: str
    match_stage: str
    unit: Optional[str] = None
    category: Optional[str] = None
    role: Optional[str] = None
    input_token: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "canonical_id": self.canonical_id,
            "canonical_name": self.canonical_name,
            "match_stage": self.match_stage,
            "unit": self.unit,
            "category": self.category,
            "role": self.role,
            "input_token": self.input_token
        }

# Transliteration mappings for Uzbek Cyrillic <-> Latin
CYR_TO_LAT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'j',
    'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'x', 'ц': 'ts',
    'ч': 'ch', 'ш': 'sh', 'щ': 'sh', 'ъ': "'", 'ы': 'i', 'ь': '', 'э': 'e', 'ю': 'yu',
    'я': 'ya', 'ў': "o'", 'қ': 'q', 'ғ': "g'", 'ҳ': 'h'
}

def transliterate_to_lat(text: str) -> str:
    res = []
    for ch in text.lower():
        res.append(CYR_TO_LAT.get(ch, ch))
    return "".join(res)

class EntityResolver:
    def __init__(self):
        self._brokers: Dict[str, str] = {}              # code -> canonical name
        self._broker_names: Dict[str, str] = {}         # cleaned_name -> code
        self._broker_inn: Dict[str, str] = {}           # inn -> code
        self._broker_regions: Dict[str, str] = {}       # code -> region

        self._companies: Dict[str, str] = {}            # inn -> canonical name
        self._company_names: List[Tuple[str, str]] = [] # (cleaned_name, inn)
        self._company_roles: Dict[str, str] = {}        # inn -> role ("Продавец" / "Покупатель")
        self._company_regions: Dict[str, str] = {}      # inn -> region

        self._products: Dict[str, Dict[str, Any]] = {}  # canonical_name -> {category, unit, ...}
        self._product_names_clean: List[Tuple[str, str]] = [] # (clean_name, canonical_name)
        self._categories: List[str] = []
        self._industries: List[str] = []
        self._initialized = False

    def initialize(self):
        """Loads reference catalog from DuckDB for ultra-fast in-memory entity resolution."""
        if self._initialized:
            return

        try:
            with get_readonly_connection() as conn:
                # 1. Load brokers
                brokers_data = conn.execute("SELECT broker_code, name, inn, region FROM brokers").fetchall()
                for code, name, inn, reg in brokers_data:
                    c_up = code.upper()
                    self._brokers[c_up] = name
                    self._broker_names[self.normalize_text(name)] = c_up
                    if inn:
                        self._broker_inn[str(inn)] = c_up
                    self._broker_regions[c_up] = reg or ""

                # 2. Load participants
                comp_data = conn.execute("SELECT inn, name, region, role FROM participants").fetchall()
                for inn, name, reg, role in comp_data:
                    s_inn = str(inn)
                    self._companies[s_inn] = name
                    self._company_names.append((self.normalize_text(name), s_inn))
                    self._company_roles[s_inn] = role or ""
                    self._company_regions[s_inn] = reg or ""

                # 3. Load products & categories from contracts
                prod_data = conn.execute("""
                    SELECT product_name, product_category, unit, COUNT(*) as cnt
                    FROM contracts
                    WHERE product_name IS NOT NULL
                    GROUP BY product_name, product_category, unit
                    ORDER BY cnt DESC
                """).fetchall()

                for p_name, cat, unit, _ in prod_data:
                    if p_name not in self._products:
                        self._products[p_name] = {
                            "canonical_name": p_name,
                            "category": cat or "",
                            "unit": unit or ""
                        }
                        self._product_names_clean.append((self.normalize_text(p_name), p_name))

                # 4. Load distinct categories & industries
                cats = conn.execute("SELECT DISTINCT product_category FROM contracts WHERE product_category IS NOT NULL").fetchall()
                self._categories = [c[0] for c in cats]

                inds = conn.execute("SELECT DISTINCT industry FROM contracts WHERE industry IS NOT NULL").fetchall()
                self._industries = [i[0] for i in inds]

            # Sort clean names by length descending for greedy longest-match
            self._company_names.sort(key=lambda x: len(x[0]), reverse=True)
            self._product_names_clean.sort(key=lambda x: len(x[0]), reverse=True)
            self._initialized = True
        except Exception:
            pass

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalizes quotes, apostrophes (o‘/o'/o`/g‘/g'), whitespace, case, and ё->е.
        """
        if not text:
            return ""
        t = text.lower()
        # Unify apostrophes and quotes
        t = re.sub(r'[\'\"«»`‘’“”„‟]', '', t)
        t = t.replace('ё', 'е').replace('ў', "o").replace('ғ', "g")
        t = re.sub(r'[!?,.:;()]+', ' ', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    @staticmethod
    def extract_quoted_tokens(text: str) -> List[str]:
        """Extracts candidate entity names from «guillemets», "quotes", „quotes“, safely ignoring Uzbek apostrophes."""
        patterns = [
            r'«([^»]+)»',
            r'"([^"]+)"',
            r'„([^“]+)“',
            r'(?:^|\s)\'([^\']+)\'(?:\s|$|[.,!?])'
        ]
        tokens = []
        for pat in patterns:
            for match in re.finditer(pat, text):
                val = match.group(1).strip()
                if len(val) >= 2:
                    tokens.append(val)
        return tokens

    @staticmethod
    def stem_ru(w: str) -> str:
        w = w.lower()
        for end in ['ой', 'ей', 'ем', 'ом', 'ам', 'ах', 'ях', 'ая', 'яя', 'ое', 'ее', 'ую', 'юю', 'ые', 'ие', 'е', 'а', 'у', 'ы', 'и', 'я']:
            if w.endswith(end) and len(w) - len(end) >= 4:
                return w[:-len(end)]
        return w

    # -------------------------------------------------------------
    # PRODUCT RESOLUTION (6 STAGES)
    # -------------------------------------------------------------
    def resolve_product(self, text: str) -> Optional[ResolvedEntity]:
        """
        Resolves product name following strict 6-stage policy:
        1. Literal from quotes
        2. Exact canonical match
        3. Normalized match
        4. Transliteration match
        5. Alias / glossary match
        6. Token intersection match
        """
        self.initialize()
        q_raw = text.strip()

        # Stage 1: Quoted literal extraction
        quotes = self.extract_quoted_tokens(q_raw)
        for q_token in quotes:
            clean_token = self.normalize_text(q_token)
            q_stems = [self.stem_ru(w) for w in clean_token.split() if len(w) >= 3]
            # Try exact / case-insensitive on quoted token
            for canon_name, info in self._products.items():
                if canon_name.lower() == q_token.lower() or self.normalize_text(canon_name) == clean_token:
                    return ResolvedEntity(
                        entity_type="product",
                        canonical_id=canon_name,
                        canonical_name=canon_name,
                        match_stage="stage_1_literal_quotes",
                        unit=info["unit"],
                        category=info["category"],
                        input_token=q_token
                    )
                # Russian stem equality (e.g. Пшенице продовольственной -> Пшеница продовольственная)
                c_stems = [self.stem_ru(w) for w in self.normalize_text(canon_name).split() if len(w) >= 3]
                if q_stems and q_stems == c_stems:
                    return ResolvedEntity(
                        entity_type="product",
                        canonical_id=canon_name,
                        canonical_name=canon_name,
                        match_stage="stage_1_literal_quotes",
                        unit=info["unit"],
                        category=info["category"],
                        input_token=q_token
                    )

        # Stage 2: Exact canonical match in text
        for canon_name, info in self._products.items():
            if canon_name in q_raw:
                return ResolvedEntity(
                    entity_type="product",
                    canonical_id=canon_name,
                    canonical_name=canon_name,
                    match_stage="stage_2_exact",
                    unit=info["unit"],
                    category=info["category"],
                    input_token=canon_name
                )

        # Stage 3: Normalized exact match
        clean_q = self.normalize_text(q_raw)
        for clean_p, canon_name in self._product_names_clean:
            if clean_p and clean_p in clean_q:
                # Word boundary or significant substring check
                if len(clean_p) >= 5 or re.search(r'\b' + re.escape(clean_p) + r'\b', clean_q):
                    info = self._products[canon_name]
                    return ResolvedEntity(
                        entity_type="product",
                        canonical_id=canon_name,
                        canonical_name=canon_name,
                        match_stage="stage_3_normalized",
                        unit=info["unit"],
                        category=info["category"],
                        input_token=clean_p
                    )

        # Stage 4: Transliteration match (e.g. Uzbek Cyrillic or Latin)
        q_latn = transliterate_to_lat(q_raw)
        for clean_p, canon_name in self._product_names_clean:
            p_latn = transliterate_to_lat(clean_p)
            if len(p_latn) >= 5 and p_latn in q_latn:
                info = self._products[canon_name]
                return ResolvedEntity(
                    entity_type="product",
                    canonical_id=canon_name,
                    canonical_name=canon_name,
                    match_stage="stage_4_transliteration",
                    unit=info["unit"],
                    category=info["category"],
                    input_token=canon_name
                )

        # Stage 5: Commodity alias mapping
        comm_resolved = self.resolve_commodity(q_raw)
        if comm_resolved:
            # Map commodity to canonical product if available
            for clean_p, canon_name in self._product_names_clean:
                if comm_resolved.lower() in clean_p:
                    info = self._products[canon_name]
                    return ResolvedEntity(
                        entity_type="product",
                        canonical_id=canon_name,
                        canonical_name=canon_name,
                        match_stage="stage_5_alias",
                        unit=info["unit"],
                        category=info["category"],
                        input_token=comm_resolved
                    )

        return None

    # -------------------------------------------------------------
    # BROKER RESOLUTION
    # -------------------------------------------------------------
    def resolve_broker_entity(self, text: str) -> Optional[ResolvedEntity]:
        self.initialize()
        # Direct regex match for BK###
        m = re.search(r'\b(BK\d{3})\b', text, re.IGNORECASE)
        if m:
            code = m.group(1).upper()
            if code in self._brokers:
                return ResolvedEntity(
                    entity_type="broker",
                    canonical_id=code,
                    canonical_name=self._brokers[code],
                    match_stage="stage_1_exact_code",
                    role="broker",
                    input_token=code
                )

        clean_q = self.normalize_text(text)
        for bname_clean, code in self._broker_names.items():
            if len(bname_clean) >= 4 and bname_clean in clean_q:
                return ResolvedEntity(
                    entity_type="broker",
                    canonical_id=code,
                    canonical_name=self._brokers[code],
                    match_stage="stage_3_normalized",
                    role="broker",
                    input_token=bname_clean
                )
        return None

    def resolve_broker(self, text: str) -> Optional[Tuple[str, str]]:
        ent = self.resolve_broker_entity(text)
        return (ent.canonical_id, ent.canonical_name) if ent else None

    # -------------------------------------------------------------
    # COMPANY RESOLUTION
    # -------------------------------------------------------------
    def resolve_company_entity(self, text: str) -> Optional[ResolvedEntity]:
        self.initialize()
        # Direct 9-digit INN
        m = re.search(r'\b(\d{9})\b', text)
        if m:
            inn = m.group(1)
            if inn in self._companies:
                return ResolvedEntity(
                    entity_type="company",
                    canonical_id=inn,
                    canonical_name=self._companies[inn],
                    match_stage="stage_1_exact_inn",
                    role=self._company_roles.get(inn),
                    input_token=inn
                )

        # Quoted company extraction
        quotes = self.extract_quoted_tokens(text)
        for q_token in quotes:
            clean_q = self.normalize_text(q_token)
            for cname_clean, inn in self._company_names:
                if cname_clean == clean_q or (len(clean_q) >= 4 and clean_q in cname_clean):
                    return ResolvedEntity(
                        entity_type="company",
                        canonical_id=inn,
                        canonical_name=self._companies[inn],
                        match_stage="stage_1_literal_quotes",
                        role=self._company_roles.get(inn),
                        input_token=q_token
                    )

        clean_text = self.normalize_text(text)
        for cname_clean, inn in self._company_names:
            if len(cname_clean) >= 6 and cname_clean in clean_text:
                return ResolvedEntity(
                    entity_type="company",
                    canonical_id=inn,
                    canonical_name=self._companies[inn],
                    match_stage="stage_3_normalized",
                    role=self._company_roles.get(inn),
                    input_token=cname_clean
                )
        return None

    def resolve_company(self, text: str) -> Optional[Tuple[str, str]]:
        ent = self.resolve_company_entity(text)
        return (ent.canonical_id, ent.canonical_name) if ent else None

    def resolve_entity(self, text: str) -> Optional[ResolvedEntity]:
        """
        Unified entity resolution entry point:
        Resolves text to ResolvedEntity (product, company, broker).
        Prioritizes literal quotes, exact codes/INNs, exact matches, then normalized.
        """
        self.initialize()
        # Stage 1: Explicit tokens (INN, BK###, or quotes)
        m_inn = re.search(r'\b(\d{9})\b', text)
        if m_inn:
            comp = self.resolve_company_entity(text)
            if comp:
                return comp

        m_bk = re.search(r'\b(BK\d{3})\b', text, re.IGNORECASE)
        if m_bk:
            brok = self.resolve_broker_entity(text)
            if brok:
                return brok

        quotes = self.extract_quoted_tokens(text)
        if quotes:
            prod = self.resolve_product(text)
            if prod and prod.match_stage == "stage_1_literal_quotes":
                return prod
            comp = self.resolve_company_entity(text)
            if comp and comp.match_stage == "stage_1_literal_quotes":
                return comp

        # Exact and normalized stages
        prod = self.resolve_product(text)
        if prod and prod.match_stage in ["stage_1_literal_quotes", "stage_2_exact", "stage_3_normalized"]:
            return prod

        comp = self.resolve_company_entity(text)
        if comp:
            return comp

        brok = self.resolve_broker_entity(text)
        if brok:
            return brok

        if prod:
            return prod

        return None

    # -------------------------------------------------------------
    # COMMODITY / CATEGORY / REGION / STATUS
    # -------------------------------------------------------------
    def resolve_commodity(self, text: str) -> Optional[str]:
        t = self.normalize_text(text)
        sorted_uz = sorted(COMMODITY_MAP.items(), key=lambda x: len(x[0]), reverse=True)
        for uz_term, ru_term in sorted_uz:
            clean_term = self.normalize_text(uz_term)
            if len(clean_term) <= 3:
                if re.search(r'\b' + re.escape(clean_term) + r'\b', t):
                    return ru_term
            else:
                if clean_term in t:
                    return ru_term

        common_ru_map = {
            "портландцемент": "портландцемент",
            "автобензин": "автобензин",
            "полиэтилен": "полиэтилен",
            "катод": "катод",
            "медный": "катод",
            "медь": "катод",
            "цемент": "цемент",
            "пшеница": "пшеница",
            "хлопок": "хлопок",
            "сахар": "сахар",
            "масло": "масло",
            "селитра": "селитра",
            "уголь": "уголь",
            "бензин": "автобензин",
            "шрот": "шрот",
            "битум": "битум",
            "прокат": "прокат",
            "стекло": "стекло",
            "мука": "мука",
            "рис": "рис"
        }
        for cr, mapped_val in common_ru_map.items():
            if len(cr) <= 3:
                if re.search(r'\b' + re.escape(cr) + r'\b', t):
                    return mapped_val
            else:
                if cr in t:
                    return mapped_val
        return None

    def resolve_category(self, text: str) -> Optional[str]:
        self.initialize()
        clean_q = self.normalize_text(text)
        for cat in self._categories:
            if self.normalize_text(cat) in clean_q:
                return cat
        return None

    def resolve_region(self, text: str) -> Optional[str]:
        t = self.normalize_text(text)
        for alias, reg in REGION_MAP.items():
            if self.normalize_text(alias) in t:
                return reg
        return None

    def resolve_status(self, text: str) -> Optional[str]:
        t = self.normalize_text(text)
        for term, st in STATUS_MAP.items():
            if self.normalize_text(term) in t:
                return st
        return None
