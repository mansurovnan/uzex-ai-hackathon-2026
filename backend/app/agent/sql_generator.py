"""
Universal Schema-Aware SQL Generator for UZEX AI Hackathon.
Dynamically constructs analytical SQL queries over DuckDB across all 6 source data categories.
Supports arbitrary questions, cross-table JOINs, aggregations, rankings, comparisons,
temporal trends, multi-turn follow-ups, and unanswerable intent detection.
"""

import os
import re
from typing import Tuple, Dict, Any, Optional, List
from .schema_registry import SCHEMA_METADATA, get_schema_summary_text
from .entity_resolver import EntityResolver
from .context_manager import ConversationContext

class UniversalSQLGenerator:
    def __init__(self, resolver: Optional[EntityResolver] = None, context: Optional[ConversationContext] = None):
        self.resolver = resolver or EntityResolver()
        self.context = context or ConversationContext()

    def generate_sql(self, question: str, session_id: str = "default") -> Dict[str, Any]:
        """
        Main entry point for generating SQL from arbitrary natural language questions.
        Returns a dictionary containing:
        - sql: generated SQL string
        - intent: analytical intent category
        - metadata: extracted entities and filters
        - is_unanswerable: bool flag if question is outside dataset scope
        """
        from .analytical_planner import AnalyticalPlanner
        plans = AnalyticalPlanner.parse_message(question)
        plan = plans[0] if plans else None
        return self.generate_sql_for_plan(plan or question, session_id=session_id)

    def generate_sql_for_plan(self, plan_or_q: Any, session_id: str = "default") -> Dict[str, Any]:
        """
        Generates dynamic SQL given an AnalyticalPlan (or raw question string).
        """
        from .analytical_planner import SubQuestionPlan
        if isinstance(plan_or_q, SubQuestionPlan):
            plan = plan_or_q
            q_raw = plan.raw_question
        else:
            from .analytical_planner import AnalyticalPlanner
            plans = AnalyticalPlanner.parse_message(str(plan_or_q))
            plan = plans[0]
            q_raw = str(plan_or_q)

        q_lower = q_raw.lower().strip()

        # 1. Check for completely out-of-scope / unanswerable questions
        if self._is_out_of_scope(q_lower):
            return {
                "sql": None,
                "intent": "unanswerable",
                "metadata": {},
                "is_unanswerable": True,
                "reason": "out_of_scope"
            }

        # 2. Multi-turn reference resolution
        inherited = self.context.resolve_references(q_raw, session_id)

        # 3. Extract temporal filters from plan or prompt
        year = plan.filters.get("year") or self._extract_year(q_lower) or inherited.get("year")
        year_range = plan.filters.get("year_range")
        if not year_range:
            all_years = [int(y) for y in re.findall(r'\b(202[2-6])\b', q_lower)]
            if len(all_years) >= 2:
                year_range = (min(all_years), max(all_years))

        is_trend = any(w in q_lower for w in ["o'zgarish", "dinamika", "yillar", "trend", "динамик", "изменени", "по годам", "yillar bo'yicha"]) or "by_year" in plan.dimensions or (year_range is not None)
        is_comparison = any(w in q_lower for w in ["solishtir", "taqqosla", "farqi", "сравни", "разница", "сопостав"]) or plan.target_entity == "market_comparison"

        # 4. Resolve entities against actual database records
        broker = self.resolver.resolve_broker(q_raw) or inherited.get("broker")
        company = self.resolver.resolve_company(q_raw) or inherited.get("company")
        commodity = self.resolver.resolve_commodity(q_raw) or inherited.get("commodity")
        product_entity = self.resolver.resolve_product(q_raw) or inherited.get("product_entity")
        quoted_entity = plan.filters.get("quoted_entity")
        category = self.resolver.resolve_category(q_raw)
        region = self.resolver.resolve_region(q_raw) or inherited.get("region")
        status = self.resolver.resolve_status(q_raw)

        # Check for LLM generation if API key is provided
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                llm_res = self._try_gemini_generation(q_raw, gemini_key, {
                    "broker": broker, "company": company, "commodity": commodity,
                    "year": year, "region": region
                })
                if llm_res and llm_res.get("sql"):
                    return llm_res
            except Exception:
                pass  # Fallback to dynamic deterministic engine

        # 5. Dynamic Semantic Query Synthesis
        res = self._synthesize_dynamic_sql(
            q_lower=q_lower,
            q_raw=q_raw,
            year=year,
            is_trend=is_trend,
            is_comparison=is_comparison,
            broker=broker,
            company=company,
            commodity=commodity,
            category=category,
            region=region,
            status=status,
            year_range=year_range,
            product_entity=product_entity,
            quoted_entity=quoted_entity,
            plan=plan
        )
        
        # Override limit if plan explicitly specified one
        if plan.ranking_limit and res.get("sql") and "LIMIT" in res["sql"]:
            res["sql"] = re.sub(r'LIMIT \d+', f'LIMIT {plan.ranking_limit}', res["sql"])
            
        return res

    def _is_out_of_scope(self, q: str) -> bool:
        """Identifies questions that have zero relevance to UZEX commodity transactions."""
        out_keywords = [
            "ob-havo", "weather", "pogoda", "погода", "futbol", "football", "футбол", "prezident",
            "kino", "film", "фильм", "aktsiya dividendi", "дивиденд", "kriptovalyuta", "криптовалют",
            "bitcoin", "биткоин", "биткоина", "retsept", "рецепт", "dori", "лекарств", "she'r", "стих", "anekdot", "анекдот", "restoran"
        ]
        return any(w in q for w in out_keywords)

    def _extract_year(self, text: str) -> Optional[int]:
        m = re.search(r'\b(202[2-6])\b', text)
        return int(m.group(1)) if m else None

    def _synthesize_dynamic_sql(
        self,
        q_lower: str,
        q_raw: str,
        year: Optional[int],
        is_trend: bool,
        is_comparison: bool,
        broker: Optional[Tuple[str, str]],
        company: Optional[Tuple[str, str]],
        commodity: Optional[str],
        category: Optional[str],
        region: Optional[str],
        status: Optional[str],
        year_range: Optional[Tuple[int, int]] = None,
        product_entity: Optional[Any] = None,
        quoted_entity: Optional[str] = None,
        plan: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Dynamically constructs SQL based on detected dimensions, metrics, and relationships.
        """
        if year_range:
            year_filter = f"EXTRACT(YEAR FROM deal_date) BETWEEN {year_range[0]} AND {year_range[1]}"
        elif year:
            year_filter = f"EXTRACT(YEAR FROM deal_date) = {year}"
        else:
            year_filter = "1=1"

        region_filter = f"(seller_region LIKE '%{region}%' OR buyer_region LIKE '%{region}%')" if region else "1=1"

        # Determine product filter
        p_filter = None
        exact_product_name = None
        if quoted_entity:
            m_grade = re.search(r'аи-\d+', quoted_entity, re.IGNORECASE)
            if m_grade:
                grade_code = m_grade.group(0).lower()
                p_filter = f"(LOWER(product_raw_name) LIKE '%{grade_code}%' OR LOWER(product_name) LIKE '%{grade_code}%')"
            elif product_entity and getattr(product_entity, "match_stage", "") in ['stage_1_literal_quotes', 'stage_2_exact']:
                exact_product_name = product_entity.canonical_name
                p_filter = f"LOWER(product_name) = '{exact_product_name.lower()}'"
            else:
                p_filter = f"(LOWER(product_name) LIKE '%{quoted_entity.lower()}%' OR LOWER(product_raw_name) LIKE '%{quoted_entity.lower()}%')"
        elif product_entity and getattr(product_entity, "match_stage", "") in ['stage_1_literal_quotes', 'stage_2_exact']:
            exact_product_name = product_entity.canonical_name
            p_filter = f"LOWER(product_name) = '{exact_product_name.lower()}'"
        elif commodity:
            if commodity == "автобензин":
                p_filter = "(LOWER(product_raw_name) LIKE '%бензин%' OR LOWER(product_name) LIKE '%бензин%')"
            else:
                p_filter = f"LOWER(product_raw_name) LIKE '%{commodity}%'"

        # -------------------------------------------------------------
        # DIMENSION 0: SYNTHETIC DATA DISCLAIMER / AUTHENTICITY
        # -------------------------------------------------------------
        if any(w in q_lower for w in ["sintetik", "haqiqiy", "haqiqatdan", "haqiqiymi", "qayerdan olingan", "qayerdan kelgan", "синтетическ", "реальные", "настоящие ли данные", "откуда данные", "откуда эти данные", "откуда", "достоверность", "источник данных"]):
            return {"sql": None, "intent": "synthetic_disclaimer", "metadata": {}}

        # -------------------------------------------------------------
        # DIMENSION 0.1: TRADED PRODUCT CATALOG
        # -------------------------------------------------------------
        if any(w in q_lower for w in ["qanday mahsulot", "qanday tovar", "tovarlar ro'yxati", "mahsulotlar ro'yxati", "qaysi tovarlar", "tovar turlari", "какие товар", "список товар", "каталог товар", "что продается"]):
            sql = f"""
            SELECT 
                product_category,
                COUNT(DISTINCT product_raw_name) AS unique_products,
                COUNT(*) AS deals_count,
                SUM(executed_amount_uzs) AS total_sales_uzs
            FROM v_deals_enriched
            WHERE {year_filter}
            GROUP BY product_category
            ORDER BY total_sales_uzs DESC
            """
            return {"sql": sql, "intent": "product_catalog", "metadata": {"year": year}}

        # -------------------------------------------------------------
        # DIMENSION 0.15: COMPANY'S BROKERS (When company is active and asking for its brokers)
        # -------------------------------------------------------------
        if company and any(w in q_lower for w in ["broker", "брокер"]):
            inn, name = company
            sql = f"""
            SELECT 
                seller_broker_code AS broker_code,
                seller_broker_name AS broker_name,
                COUNT(*) AS deals_count,
                SUM(executed_amount_uzs) AS turnover_uzs
            FROM v_deals_enriched
            WHERE (seller_inn = '{inn}' OR buyer_inn = '{inn}') AND {year_filter}
            GROUP BY seller_broker_code, seller_broker_name
            ORDER BY turnover_uzs DESC
            LIMIT 5
            """
            return {"sql": sql, "intent": "company_brokers", "metadata": {"company": company, "year": year}}

        # -------------------------------------------------------------
        # DIMENSION 0.16: COMPANY PROFILE / CARD LOOKUP
        # -------------------------------------------------------------
        if company and (
            any(w in q_lower for w in ["haqida", "ma'lumot", "kartochka", "inn", "stir", "rekvizit", "hudud", "joylashgan", "qaysi hudud", "joylashuv", "о компании", "карточка", "профиль", "profil", "kim bu", "кто это", "faoliyat", "в каком регионе"])
            or (plan and plan.target_entity in ["company_card", "participant_card"])
        ):
            inn, name = company
            sql = f"""
            SELECT 
                inn, name, region, activity_type, role, vat_payer
            FROM participants
            WHERE inn = '{inn}'
            """
            return {"sql": sql, "intent": "participant_card", "metadata": {"company": company}}

        # -------------------------------------------------------------
        # DIMENSION 0.17: STATUSES & CANCELLED DEALS (WITH OPTIONAL COMMODITY SCOPE)
        # -------------------------------------------------------------
        if status or any(w in q_lower for w in ["bekor", "annulir", "to'lanmagan", "аннулирован", "отменен"]):
            where_clause = f"status = 'Аннулирован(Не оплачен)' AND {year_filter}"
            denom_where = year_filter
            if p_filter:
                where_clause += f" AND {p_filter}"
                denom_where += f" AND {p_filter}"
            sql = f"""
            SELECT 
                COUNT(*) AS cancelled_deals_count,
                SUM(amount_uzs) AS total_cancelled_amount_uzs,
                ROUND(COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM deals WHERE {denom_where}), 0), 2) AS cancellation_percent
            FROM v_deals_enriched
            WHERE {where_clause}
            """
            return {"sql": sql, "intent": "cancelled_deals", "metadata": {"year": year, "commodity": exact_product_name or commodity or quoted_entity}}

        # -------------------------------------------------------------
        # DIMENSION 0.2: COMMODITY & PRODUCT SPECIFIC INTELLIGENCE
        # -------------------------------------------------------------
        if p_filter:
            entity_label = exact_product_name or commodity or quoted_entity
            # 1. Product Sellers (who sold this commodity)
            if (
                any(w in q_lower for w in ["sotgan", "sotuvchi", "sotuvchilari", "kim sotgan", "продав", "поставщик", "кто продал"])
                or (any(w in q_lower for w in ["kompaniya", "kompaniyalar", "компани", "eng katta", "самый крупный"]) 
                    and not any(w in q_lower for w in ["xaridor", "olgan", "покупа", "купил", "broker", "брокер"]))
            ):
                sql = f"""
                SELECT 
                    seller_inn AS inn,
                    seller_name AS name,
                    seller_region AS region,
                    COUNT(*) AS deals_count,
                    SUM(contracted_volume_units) AS volume_sold,
                    unit,
                    SUM(executed_amount_uzs) AS total_sales_uzs
                FROM v_deals_enriched
                WHERE is_executed = TRUE 
                  AND {p_filter} 
                  AND {year_filter}
                GROUP BY seller_inn, seller_name, seller_region, unit
                ORDER BY total_sales_uzs DESC, seller_inn ASC
                LIMIT 10
                """
                return {"sql": sql, "intent": "product_sellers", "metadata": {"commodity": entity_label, "year": year}}

            # 2. Product Buyers (who bought this commodity)
            if any(w in q_lower for w in ["xaridor", "olgan", "sotib olgan", "xarid", "покупател", "покупа", "купил", "закуп", "кто купил"]):
                sql = f"""
                SELECT 
                    buyer_inn AS inn,
                    buyer_name AS name,
                    buyer_region AS region,
                    COUNT(*) AS deals_count,
                    SUM(contracted_volume_units) AS volume_bought,
                    unit,
                    SUM(executed_amount_uzs) AS total_purchases_uzs
                FROM v_deals_enriched
                WHERE is_executed = TRUE 
                  AND {p_filter} 
                  AND {year_filter}
                GROUP BY buyer_inn, buyer_name, buyer_region, unit
                ORDER BY total_purchases_uzs DESC, buyer_inn ASC
                LIMIT 10
                """
                return {"sql": sql, "intent": "product_buyers", "metadata": {"commodity": entity_label, "year": year}}

            # 3. Product Brokers (who intermediated this commodity)
            if any(w in q_lower for w in ["broker", "брокер"]):
                sql = f"""
                SELECT 
                    seller_broker_code AS broker_code,
                    seller_broker_name AS broker_name,
                    COUNT(*) AS deals_count,
                    SUM(executed_amount_uzs) AS turnover_uzs
                FROM v_deals_enriched
                WHERE is_executed = TRUE 
                  AND {p_filter} 
                  AND {year_filter}
                GROUP BY seller_broker_code, seller_broker_name
                ORDER BY turnover_uzs DESC, broker_code ASC
                LIMIT 10
                """
                return {"sql": sql, "intent": "product_brokers", "metadata": {"commodity": entity_label, "year": year}}

            # 4. Product Regional Breakdown
            if any(w in q_lower for w in ["hudud", "viloyat", "регион", "област"]):
                sql = f"""
                SELECT 
                    seller_region AS region,
                    COUNT(*) AS deals_count,
                    SUM(contracted_volume_units) AS volume_sold,
                    unit,
                    SUM(executed_amount_uzs) AS total_sales_uzs
                FROM v_deals_enriched
                WHERE is_executed = TRUE 
                  AND {p_filter} 
                  AND {year_filter}
                GROUP BY seller_region, unit
                ORDER BY total_sales_uzs DESC, seller_region ASC
                LIMIT 10
                """
                return {"sql": sql, "intent": "product_regions", "metadata": {"commodity": entity_label, "year": year}}

            # 5. Product Multi-Year Dynamics
            if is_trend:
                sql = f"""
                SELECT 
                    EXTRACT(YEAR FROM deal_date) AS deal_year,
                    COUNT(*) AS deals_count,
                    SUM(contracted_volume_units) AS contracted_volume,
                    SUM(executed_volume_units) AS delivered_volume,
                    unit,
                    SUM(amount_uzs) AS turnover_uzs,
                    ROUND(AVG(unit_price_contract_currency), 2) AS avg_unit_price
                FROM v_deals_enriched
                WHERE {p_filter} AND {year_filter}
                GROUP BY EXTRACT(YEAR FROM deal_date), unit
                ORDER BY deal_year ASC
                """
                return {"sql": sql, "intent": "commodity_trend", "metadata": {"commodity": entity_label, "year_range": year_range}}

            # 6. Specific Product Quotations / Price Range (Only if specifically asking for price range/min/max)
            is_pure_range = any(w in q_lower for w in ["diapazon", "kotirovka", "диапазон", "котировк", "мин", "макс", "минимальн", "максимальн"])
            if is_pure_range and not any(w in q_lower for w in ["bitim", "qancha", "nechta", "hajm", "сделок", "сколько"]):
                sql = f"""
                SELECT 
                    product_name,
                    unit,
                    currency,
                    MIN(unit_price_contract_currency) AS min_price,
                    MAX(unit_price_contract_currency) AS max_price,
                    ROUND(AVG(unit_price_contract_currency), 2) AS avg_price,
                    COUNT(*) AS deals_count,
                    SUM(executed_amount_uzs) AS turnover_uzs
                FROM v_deals_enriched
                WHERE {p_filter} 
                  AND {year_filter}
                GROUP BY product_name, unit, currency
                ORDER BY deals_count DESC, product_name ASC
                LIMIT 5
                """
                return {"sql": sql, "intent": "product_price_range", "metadata": {"commodity": entity_label, "year": year}}

            # 7. Specific Product / Commodity Stats (Deals, Volume, Turnover, Weighted Price)
            sql = f"""
            SELECT 
                '{entity_label}' AS product_name,
                unit,
                COUNT(*) AS deals_count,
                SUM(contracted_volume_units) AS total_contracted_units,
                SUM(executed_volume_units) AS total_delivered_units,
                SUM(executed_amount_uzs) AS total_amount_uzs,
                ROUND(SUM(executed_amount_uzs) / NULLIF(SUM(executed_volume_units), 0), 2) AS weighted_avg_price,
                ROUND(AVG(unit_price_contract_currency), 2) AS avg_price_per_unit
            FROM v_deals_enriched
            WHERE {p_filter}
              AND {year_filter}
              AND {region_filter}
            GROUP BY unit
            ORDER BY total_amount_uzs DESC
            LIMIT 5
            """
            return {"sql": sql, "intent": "product_stats", "metadata": {"commodity": entity_label, "year": year, "year_range": year_range}}

        # -------------------------------------------------------------
        # DIMENSION 0.3: TOP PRODUCTS (When no specific commodity)
        # -------------------------------------------------------------
        is_top_product_q = (
            (any(w in q_lower for w in ["top tovar", "топ товар", "топ самых"])
             or (any(w in q_lower for w in ["eng ko'p", "eng yirik", "eng katta", "eng yuqori", "топ", "лидер", "популярн", "продаваем", "reyting"]) 
                 and any(w in q_lower for w in ["tovar", "mahsulot", "товар", "продукци"])))
            and not any(w in q_lower for w in ["kompaniya", "kompaniyani", "sotuvchi", "xaridor", "kim", "кто", "компания", "компании", "поставщик", "xarid", "broker", "брокер", "brokerlar", "брокеры"])
            and (not plan or plan.target_entity not in ["broker", "seller", "buyer", "company_card"])
        )
        if is_top_product_q:
            order_by = "total_turnover_uzs DESC"
            metric_type = "turnover"
            unit_filter = ""
            if any(w in q_lower for w in ["hajm", "hajmi", "tonna", "объем", "объему"]):
                order_by = "total_volume DESC"
                metric_type = "volume"
                if any(w in q_lower for w in ["tonna", "тонн"]):
                    unit_filter = "AND unit = 'тонна'"
            elif any(w in q_lower for w in ["bitim", "bitimlar", "soni", "сделок", "сделка", "количеству"]):
                order_by = "deals_count DESC"
                metric_type = "deals"

            sql = f"""
            SELECT 
                product_name,
                unit,
                COUNT(*) AS deals_count,
                SUM(contracted_volume_units) AS total_volume,
                SUM(executed_amount_uzs) AS total_turnover_uzs
            FROM v_deals_enriched
            WHERE is_executed = TRUE AND {year_filter} {unit_filter}
            GROUP BY product_name, unit
            ORDER BY {order_by}, product_name ASC
            LIMIT 10
            """
            return {"sql": sql, "intent": "top_products", "metadata": {"year": year, "metric_type": metric_type}}

        # -------------------------------------------------------------
        # DIMENSION 1: PARTICIPANTS (Sellers / Buyers / Top Companies)
        # -------------------------------------------------------------
        # Top Sellers
        if any(w in q_lower for w in ["sotuvchi", "sotgan", "kim sotgan", "продавец", "продавц", "продал", "поставщик"]):
            if company:
                inn, name = company
                sql = f"""
                SELECT 
                    seller_inn AS inn,
                    seller_name AS name,
                    seller_region AS region,
                    seller_activity AS activity,
                    COUNT(*) AS total_deals,
                    SUM(CASE WHEN is_executed THEN 1 ELSE 0 END) AS executed_deals,
                    SUM(amount_uzs) AS total_revenue_uzs,
                    SUM(executed_amount_uzs) AS executed_revenue_uzs
                FROM v_deals_enriched
                WHERE seller_inn = '{inn}' AND {year_filter}
                GROUP BY seller_inn, seller_name, seller_region, seller_activity
                """
                return {"sql": sql, "intent": "seller_single", "metadata": {"company": company, "year": year}}
            else:
                sql = f"""
                SELECT 
                    seller_inn AS inn,
                    seller_name AS name,
                    seller_region AS region,
                    COUNT(*) AS deals_count,
                    SUM(executed_amount_uzs) AS total_sales_uzs
                FROM v_deals_enriched
                WHERE is_executed = TRUE AND {year_filter} AND {region_filter}
                GROUP BY seller_inn, seller_name, seller_region
                ORDER BY total_sales_uzs DESC, seller_inn ASC
                LIMIT 10
                """
                return {"sql": sql, "intent": "seller_top", "metadata": {"year": year, "region": region}}

        # Top Buyers
        if any(w in q_lower for w in ["xaridor", "olgan", "sotib olgan", "xarid qilgan", "покупател", "купил", "закуп"]):
            if company:
                inn, name = company
                sql = f"""
                SELECT 
                    buyer_inn AS inn,
                    buyer_name AS name,
                    buyer_region AS region,
                    buyer_activity AS activity,
                    COUNT(*) AS total_deals,
                    SUM(amount_uzs) AS total_spend_uzs,
                    SUM(executed_amount_uzs) AS executed_spend_uzs
                FROM v_deals_enriched
                WHERE buyer_inn = '{inn}' AND {year_filter}
                GROUP BY buyer_inn, buyer_name, buyer_region, buyer_activity
                """
                return {"sql": sql, "intent": "buyer_single", "metadata": {"company": company, "year": year}}
            else:
                sql = f"""
                SELECT 
                    buyer_inn AS inn,
                    buyer_name AS name,
                    buyer_region AS region,
                    COUNT(*) AS deals_count,
                    SUM(executed_amount_uzs) AS total_purchases_uzs
                FROM v_deals_enriched
                WHERE is_executed = TRUE AND {year_filter} AND {region_filter}
                GROUP BY buyer_inn, buyer_name, buyer_region
                ORDER BY total_purchases_uzs DESC, buyer_inn ASC
                LIMIT 10
                """
                return {"sql": sql, "intent": "buyer_top", "metadata": {"year": year, "region": region}}

        # Single Company Card Lookup
        if company and (
            any(w in q_lower for w in ["haqida", "ma'lumot", "kartochka", "inn", "stir", "rekvizit", "о компании", "карточка", "профиль", "profil", "kim bu", "кто это", "faoliyat"])
            or (plan and plan.target_entity in ["company_card", "participant_card"])
        ):
            inn, name = company
            sql = f"""
            SELECT 
                inn, name, region, activity_type, role, vat_payer
            FROM participants
            WHERE inn = '{inn}'
            """
            return {"sql": sql, "intent": "participant_card", "metadata": {"company": company}}

        # -------------------------------------------------------------
        # DIMENSION 2: BROKERS
        # -------------------------------------------------------------
        if broker or any(w in q_lower for w in ["broker", "брокер"]) or (plan and plan.target_entity == "broker"):
            if broker:
                b_code, b_name = broker
                sql = f"""
                SELECT 
                    '{b_code}' AS broker_code,
                    '{b_name}' AS broker_name,
                    COUNT(*) AS total_deals,
                    SUM(CASE WHEN is_executed THEN 1 ELSE 0 END) AS executed_deals,
                    SUM(amount_uzs) AS total_turnover_uzs,
                    SUM(executed_amount_uzs) AS executed_turnover_uzs
                FROM v_deals_enriched
                WHERE (seller_broker_code = '{b_code}' OR buyer_broker_code = '{b_code}')
                  AND {year_filter}
                """
                return {"sql": sql, "intent": "broker_single", "metadata": {"broker": broker, "year": year}}
            else:
                sql = f"""
                SELECT 
                    seller_broker_code AS broker_code,
                    seller_broker_name AS broker_name,
                    COUNT(*) AS total_deals,
                    SUM(executed_amount_uzs) AS executed_turnover_uzs
                FROM v_deals_enriched
                WHERE is_executed = TRUE AND {year_filter}
                GROUP BY seller_broker_code, seller_broker_name
                ORDER BY executed_turnover_uzs DESC, broker_code ASC
                LIMIT 10
                """
                return {"sql": sql, "intent": "broker_top", "metadata": {"year": year}}

        # -------------------------------------------------------------
        # DIMENSION 3: MARKET COMPARISON (Export USD vs Domestic UZS)
        # -------------------------------------------------------------
        if is_comparison and any(w in q_lower for w in ["eksport", "ichki", "экспорт", "внутренн", "bozor"]):
            sql = f"""
            SELECT 
                contract_type,
                currency,
                COUNT(*) AS deals_count,
                SUM(quantity_lots * lot_size) AS total_units,
                SUM(amount_contract_currency) AS amount_in_currency,
                SUM(amount_uzs) AS equivalent_uzs,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM deals WHERE {year_filter}), 2) AS deals_percentage
            FROM v_deals_enriched
            WHERE {year_filter}
            GROUP BY contract_type, currency
            ORDER BY deals_count DESC
            """
            return {"sql": sql, "intent": "market_comparison", "metadata": {"year": year}}

        # Export Specific Deals
        if any(w in q_lower for w in ["eksport", "export", "dollar", "usd", "экспорт"]):
            sql = f"""
            SELECT 
                COUNT(*) AS total_export_deals,
                SUM(quantity_lots * lot_size) AS total_export_volume,
                SUM(amount_contract_currency) AS total_export_usd,
                SUM(amount_uzs) AS total_export_uzs_equivalent
            FROM v_deals_enriched
            WHERE contract_type = 'Экспортный' AND {year_filter}
            """
            return {"sql": sql, "intent": "export_deals", "metadata": {"year": year}}

        # -------------------------------------------------------------
        # DIMENSION 4: PRODUCT CATEGORIES
        # -------------------------------------------------------------
        if category:
            sql = f"""
            SELECT 
                product_name,
                COUNT(*) AS deals_count,
                SUM(executed_amount_uzs) AS total_sales_uzs
            FROM v_deals_enriched
            WHERE product_category = '{category}' AND {year_filter}
            GROUP BY product_name
            ORDER BY total_sales_uzs DESC, product_name ASC
            LIMIT 10
            """
            return {"sql": sql, "intent": "category_breakdown", "metadata": {"category": category, "year": year}}

        # -------------------------------------------------------------
        # DIMENSION 5: STATUSES & CANCELLED TRANSACTIONS
        # -------------------------------------------------------------
        if status or any(w in q_lower for w in ["bekor", "annulir", "to'lanmagan", "аннулирован", "отменен"]):
            where_clause = f"status = 'Аннулирован(Не оплачен)' AND {year_filter}"
            denom_where = year_filter
            if p_filter:
                where_clause += f" AND {p_filter}"
                denom_where += f" AND {p_filter}"
            sql = f"""
            SELECT 
                COUNT(*) AS cancelled_deals_count,
                SUM(amount_uzs) AS total_cancelled_amount_uzs,
                ROUND(COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM deals WHERE {denom_where}), 0), 2) AS cancellation_percent
            FROM v_deals_enriched
            WHERE {where_clause}
            """
            return {"sql": sql, "intent": "cancelled_deals", "metadata": {"year": year, "commodity": exact_product_name or commodity or quoted_entity}}

        # Transaction Status Breakdown
        if any(w in q_lower for w in ["holat", "status", "bajarilgan", "ijro", "статус", "состояни", "исполнен"]):
            sql = f"""
            SELECT 
                status,
                COUNT(*) AS deals_count,
                SUM(amount_uzs) AS amount_uzs,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM deals WHERE {year_filter}), 2) AS percentage
            FROM v_deals_enriched
            WHERE {year_filter}
            GROUP BY status
            ORDER BY deals_count DESC
            """
            return {"sql": sql, "intent": "status_breakdown", "metadata": {"year": year}}

        # -------------------------------------------------------------
        # DIMENSION 6: REGIONS
        # -------------------------------------------------------------
        if region:
            sql = f"""
            SELECT 
                seller_region AS region,
                COUNT(*) AS deals_count,
                SUM(amount_uzs) AS total_sales_uzs,
                SUM(executed_amount_uzs) AS executed_sales_uzs
            FROM v_deals_enriched
            WHERE seller_region LIKE '%{region}%' AND {year_filter}
            GROUP BY seller_region
            """
            return {"sql": sql, "intent": "region_stats", "metadata": {"region": region, "year": year}}

        # -------------------------------------------------------------
        # DIMENSION 7: ANNUAL TREND / YEAR-OVER-YEAR DYNAMICS
        # -------------------------------------------------------------
        if is_trend:
            sql = f"""
            SELECT 
                EXTRACT(YEAR FROM deal_date) AS year,
                COUNT(*) AS total_deals,
                SUM(CASE WHEN is_executed THEN 1 ELSE 0 END) AS executed_deals,
                ROUND(AVG(unit_price_contract_currency), 2) AS avg_unit_price,
                SUM(executed_amount_uzs) AS executed_turnover_uzs,
                SUM(amount_uzs) AS turnover_uzs
            FROM v_deals_enriched
            WHERE {year_filter}
            GROUP BY EXTRACT(YEAR FROM deal_date)
            ORDER BY year ASC
            """
            return {"sql": sql, "intent": "annual_trend", "metadata": {"year_range": year_range or (2022, 2026)}}

        # -------------------------------------------------------------
        # DEFAULT: ANNUAL OR OVERALL TURNOVER
        # -------------------------------------------------------------
        sql = f"""
        SELECT 
            COUNT(*) AS total_deals,
            SUM(CASE WHEN is_executed THEN 1 ELSE 0 END) AS executed_deals,
            SUM(amount_uzs) AS total_turnover_uzs,
            SUM(executed_amount_uzs) AS executed_turnover_uzs,
            SUM(CASE WHEN contract_type = 'Экспортный' THEN amount_contract_currency ELSE 0 END) AS export_amount_usd
        FROM v_deals_enriched
        WHERE {year_filter}
        """
        return {"sql": sql, "intent": "total_turnover", "metadata": {"year": year}}

    def _try_gemini_generation(self, q: str, api_key: str, extracted: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Invokes Gemini LLM for complex text-to-SQL when API key is active."""
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = f"""
            You are a senior data engineer writing DuckDB SQL for the UZEX commodity exchange.
            Database schema:
            {get_schema_summary_text()}

            Rules:
            1. Only return a valid DuckDB SQL SELECT statement. No markdown code blocks, no explanations.
            2. Use 'v_deals_enriched' for transaction calculations (amount_uzs, executed_amount_uzs, is_executed).
            3. Never compare USD and UZS directly.
            4. Do not perform any mutations (NO INSERT/UPDATE/DROP).

            User Question: {q}
            Known entities: {extracted}
            """
            resp = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                contents=prompt
            )
            raw_sql = resp.text.strip().replace("```sql", "").replace("```", "").strip()
            if raw_sql.upper().startswith("SELECT") or raw_sql.upper().startswith("WITH"):
                return {"sql": raw_sql, "intent": "dynamic_llm", "metadata": extracted}
        except Exception:
            pass
        return None
