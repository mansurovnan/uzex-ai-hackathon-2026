"""
Analytical Planner and Multi-Question Requirement Extractor.
Deconstructs complex user prompts into discrete sub-questions,
extracts analytical requirements (entities, metrics, dimensions, filters),
and defines a coverage checklist for completeness validation.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

@dataclass
class SubQuestionPlan:
    index: int
    raw_question: str
    target_entity: str            # 'seller', 'buyer', 'broker', 'commodity', 'category', 'market', 'all_deals', 'contract', 'unknown'
    metrics: List[str]            # ['total_amount', 'executed_amount', 'deals_count', 'volume', 'avg_price', etc.]
    dimensions: List[str]         # ['by_broker', 'by_product', 'by_year', 'by_region', 'by_status', etc.]
    filters: Dict[str, Any]       # {'year': 2024, 'region': 'Samarqand', 'status': '...', 'currency': '...'}
    ranking_limit: Optional[int]  # 1, 5, 10, None
    ranking_order: str            # 'DESC' or 'ASC'
    is_compound: bool             # True if asks for entity + its breakdown (e.g. brokers + products)
    compound_breakdowns: List[str]# ['brokers', 'products', 'deals', 'amounts']
    required_components: List[str]# Checklist for completeness validation

def split_user_message(text: str) -> List[str]:
    """
    Intelligently splits a user message into distinct sub-questions or tasks.
    Handles '?', numbered lists (1., 2.), and sentence boundaries with question words.
    """
    text = text.strip()
    if not text:
        return []

    # 1. Check for numbered questions like "1. ... 2. ..."
    numbered_parts = re.split(r'\b\d+[\.\)]\s+', text)
    if len(numbered_parts) > 1 and len(numbered_parts[1].strip()) > 3:
        return [p.strip() for p in numbered_parts if p.strip()]

    # 2. Check for multiple '?'
    if text.count('?') > 1:
        raw_chunks = text.split('?')
        questions = [q.strip() + '?' for q in raw_chunks if q.strip()]
        return questions

    # 3. Check for semicolon or newline separation with question words
    newline_parts = [p.strip() for p in re.split(r'[\n;]+', text) if len(p.strip()) > 5]
    if len(newline_parts) > 1:
        # Verify if parts look like distinct tasks
        q_markers = ["kim", "qaysi", "qancha", "nechta", "top", "kimlar", "кто", "какой", "какова", "каков", "сколько", "сравни"]
        is_all_questions = any(any(m in p.lower() for m in q_markers) for p in newline_parts)
        if is_all_questions:
            return newline_parts

    return [text]

class AnalyticalPlanner:
    @staticmethod
    def parse_message(text: str) -> List[SubQuestionPlan]:
        sub_questions = split_user_message(text)
        plans = []

        for idx, sub_q in enumerate(sub_questions, 1):
            plan = AnalyticalPlanner._plan_single_question(idx, sub_q)
            plans.append(plan)

        return plans

    @staticmethod
    def _plan_single_question(index: int, q: str) -> SubQuestionPlan:
        q_lower = q.lower()
        
        # 1. Year filter
        year = None
        m_year = re.search(r'\b(202[2-6])\b', q_lower)
        if m_year:
            year = int(m_year.group(1))

        # 2. Ranking limit
        limit = None
        m_limit = re.search(r'\b(\d+)\s*(ta|nafar|tasi|самых|топ|top)\b', q_lower)
        if m_limit:
            try:
                limit = int(m_limit.group(1))
            except ValueError:
                limit = None
        elif any(w in q_lower for w in ["eng ko'p", "eng yirik", "eng katta", "eng faol", "кто крупнейший", "самый", "топ", "лидер"]):
            limit = 1 if any(w in q_lower for w in ["kompaniya kim", "kompaniyani", "broker kim", "qaysi kompaniya", "qaysi broker", "кто"]) else 5

        # 3. Target Entity & Dimension Detection
        target_entity = "all_deals"
        metrics = []
        dimensions = []
        is_compound = False
        compound_breakdowns = []
        required_components = []

        # Check for direct 9-digit INN lookup
        m_inn = re.search(r'\b(\d{9})\b', q_lower)
        if m_inn and not any(w in q_lower for w in ["sotgan", "olgan", "xarid"]):
            target_entity = "company_card"
            required_components = ["company_name", "inn", "region"]
            return SubQuestionPlan(
                index=index,
                raw_question=q,
                target_entity=target_entity,
                metrics=[],
                dimensions=[],
                filters={"inn": m_inn.group(1)},
                ranking_limit=1,
                ranking_order="DESC",
                is_compound=False,
                compound_breakdowns=[],
                required_components=required_components
            )

        # Sellers
        if any(w in q_lower for w in ["sotuvchi", "sotgan", "kim sotgan", "продавец", "продавц", "продал", "поставщик"]):
            target_entity = "seller"
            required_components.append("seller_entity")
            if "summa" in q_lower or "savdo" in q_lower or "aylanma" in q_lower or "объем" in q_lower:
                metrics.append("total_sales_amount")
                required_components.append("sales_amount")
            if "bitim" in q_lower or "soni" in q_lower or "сделок" in q_lower or "сделки" in q_lower:
                metrics.append("deals_count")
                required_components.append("deals_count")
            if "broker" in q_lower or "брокер" in q_lower:
                dimensions.append("by_broker")
                compound_breakdowns.append("brokers")
                required_components.append("brokers_used")
            if "mahsulot" in q_lower or "tovar" in q_lower or "товар" in q_lower:
                dimensions.append("by_product")
                compound_breakdowns.append("products")
                required_components.append("products_sold")
            if len(compound_breakdowns) > 0:
                is_compound = True

        # Buyers
        elif any(w in q_lower for w in ["xaridor", "olgan", "sotib olgan", "xarid qilgan", "покупател", "купил", "закуп"]):
            target_entity = "buyer"
            required_components.append("buyer_entity")
            if "summa" in q_lower or "xarid" in q_lower or "aylanma" in q_lower:
                metrics.append("total_purchase_amount")
                required_components.append("purchase_amount")
            if "bitim" in q_lower or "soni" in q_lower:
                metrics.append("deals_count")
                required_components.append("deals_count")
            if "broker" in q_lower or "брокер" in q_lower:
                dimensions.append("by_broker")
                compound_breakdowns.append("brokers")
                required_components.append("brokers_used")
            if len(compound_breakdowns) > 0:
                is_compound = True

        # Brokers
        elif any(w in q_lower for w in ["broker", "брокер"]):
            target_entity = "broker"
            required_components.append("broker_entity")
            if "aylanma" in q_lower or "summa" in q_lower or "оборот" in q_lower:
                metrics.append("broker_turnover")
                required_components.append("turnover")
            if "bitim" in q_lower or "soni" in q_lower or "сделок" in q_lower:
                metrics.append("deals_count")
                required_components.append("deals_count")

        # Market Comparison (Export vs Domestic)
        elif any(w in q_lower for w in ["solishtir", "taqqosla", "сравни", "разница"]) and any(w in q_lower for w in ["eksport", "ichki", "экспорт", "внутренн"]):
            target_entity = "market_comparison"
            metrics.extend(["deals_count", "turnover_uzs", "currency_breakdown"])
            required_components.extend(["export_market", "domestic_market", "comparison_table"])

        # Export Specific
        elif any(w in q_lower for w in ["eksport", "export", "dollar", "usd", "экспорт"]):
            target_entity = "export"
            metrics.extend(["export_deals_count", "export_volume", "export_usd", "export_uzs_eq"])
            required_components.extend(["export_usd", "export_uzs", "deals_count"])

        # Cancelled Deals
        elif any(w in q_lower for w in ["bekor", "annulir", "to'lanmagan", "аннулирован", "отменен"]):
            target_entity = "cancelled_deals"
            metrics.extend(["cancelled_count", "cancelled_amount_uzs", "cancellation_percentage"])
            required_components.extend(["cancelled_count", "cancelled_amount", "percentage"])

        # Commodities
        elif any(w in q_lower for w in ["sement", "bug'doy", "bugdoy", "paxta", "shakar", "yog'", "yog", "mis", "katod", "benzin", "ko'mir", "цемент", "пшеница", "хлопок", "сахар", "масло", "медь", "катод", "уголь"]):
            target_entity = "commodity"
            metrics.extend(["volume", "turnover", "deals_count", "avg_price"])
            required_components.extend(["commodity_metrics", "unit_price"])
            if any(w in q_lower for w in ["dinamika", "o'zgarish", "trend", "yillar bo'yicha", "по годам"]):
                dimensions.append("by_year")
                required_components.append("yearly_trend")

        # Regional sales
        elif any(w in q_lower for w in ["viloyat", "shahar", "hudud", "область", "город", "регион"]):
            target_entity = "region"
            metrics.extend(["deals_count", "sales_volume", "turnover"])
            required_components.extend(["regional_deals", "regional_sales"])

        # General annual/total
        else:
            target_entity = "general_turnover"
            metrics.extend(["total_deals", "executed_deals", "total_turnover_uzs", "executed_turnover_uzs"])
            required_components.extend(["total_deals", "turnover"])

        filters = {}
        if year:
            filters["year"] = year

        # Default required components fallback
        if not required_components:
            required_components.append("general_answer")

        return SubQuestionPlan(
            index=index,
            raw_question=q,
            target_entity=target_entity,
            metrics=metrics,
            dimensions=dimensions,
            filters=filters,
            ranking_limit=limit,
            ranking_order="DESC",
            is_compound=is_compound,
            compound_breakdowns=compound_breakdowns,
            required_components=required_components
        )
