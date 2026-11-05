"""
Universal UZEX AI Query Engine — Multi-Question & Multi-Part Executive Coordinator.
Coordinates:
- Multi-question parsing & decomposition into independent tasks
- Analytical plan extraction (entities, metrics, filters, dimensions)
- Dynamic SQL generation & read-only DuckDB execution
- Chained compound queries (e.g. top entity + brokers + products sold)
- Completeness validation against required components
- Result verification
- Multi-turn conversation state persistence
- Executive response synthesis in Uzbek (Latin/Cyrillic) and Russian
"""

from typing import Dict, Any, Optional, List
from app.database.connection import get_readonly_connection
from .entity_resolver import EntityResolver
from .context_manager import ConversationContext
from .analytical_planner import AnalyticalPlanner, SubQuestionPlan
from .completeness_validator import CompletenessValidator
from .sql_generator import UniversalSQLGenerator
from .sql_guard import validate_and_guard_sql
from .verifier import ResultVerifier
from .synthesizer import ResponseSynthesizer

def detect_language(text: str) -> str:
    uz_markers = [
        "qancha", "nechta", "qaysi", "haqida", "tuzilgan", "sotilgan", "jami", 
        "bitim", "yil", "yili", "eng", "narxi", "qaysilar", "summasi", "kim",
        "uning", "ularning", "solishtir", "taqqosla", "bo'yicha", "bo'lgan", "xarid",
        "top", "ko'rsat"
    ]
    ru_markers = [
        "сколько", "какой", "какова", "каков", "сделок", "сделка", "продано", 
        "всего", "год", "году", "самый", "цена", "сумма", "рейтинг", "отчет",
        "кто", "его", "их", "сравни", "динамика", "участники", "купил", "продал",
        "найди", "покажи"
    ]
    t = text.lower()
    uz_score = sum(1 for m in uz_markers if m in t)
    ru_score = sum(1 for m in ru_markers if m in t)
    
    if any(ch in t for ch in ["o'", "o‘", "g'", "g‘", "sh", "ch"]):
        uz_score += 2
        
    return "uz" if uz_score >= ru_score else "ru"

class ExchangeQueryEngine:
    def __init__(self):
        self.resolver = EntityResolver()
        self.context = ConversationContext()
        self.generator = UniversalSQLGenerator(self.resolver, self.context)
        self.verifier = ResultVerifier()
        self.synthesizer = ResponseSynthesizer()
        self.planner = AnalyticalPlanner()

    def process_question(self, question: str, session_id: str = "default") -> Dict[str, Any]:
        lang = detect_language(question)
        q_raw = question.strip()

        # 1. Parse into Analytical Sub-Questions
        plans: List[SubQuestionPlan] = self.planner.parse_message(q_raw)
        
        sub_results = []
        all_sqls = []

        with get_readonly_connection() as conn:
            for plan in plans:
                sub_res = self._process_single_plan(plan, conn, lang, session_id)
                sub_results.append(sub_res)
                if sub_res.get("sql"):
                    all_sqls.append(sub_res["sql"])

        # 2. Combine answers for multi-question or return single
        if len(sub_results) == 1:
            final_answer = sub_results[0]["answer"]
            final_data = sub_results[0].get("data", [])
            primary_res = sub_results[0]
        else:
            final_answer = self.synthesizer.combine_multi_answers(sub_results, lang)
            final_data = sub_results[0].get("data", [])
            primary_res = {
                "verified": all(r.get("verified", True) for r in sub_results),
                "row_count": sum(r.get("row_count", 0) for r in sub_results)
            }

        return {
            "answer": final_answer,
            "sql": ";\n\n".join(all_sqls) if all_sqls else None,
            "data": final_data,
            "language": lang,
            "verified": primary_res.get("verified", True),
            "row_count": primary_res.get("row_count", 0),
            "sub_questions_count": len(plans)
        }

    def _process_single_plan(
        self,
        plan: SubQuestionPlan,
        conn: Any,
        lang: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Executes a single SubQuestionPlan, including compound chained queries
        and completeness checks.
        """
        # A. Generate Primary SQL
        sql_plan = self.generator.generate_sql_for_plan(plan, session_id=session_id)
        
        # B. Check for unanswerable / out of scope
        if sql_plan.get("is_unanswerable"):
            answer = self.synthesizer.synthesize_single(
                intent="unanswerable",
                cols=[],
                rows=[],
                lang=lang,
                question=plan.raw_question,
                metadata={},
                is_unanswerable=True
            )
            return {
                "question": plan.raw_question,
                "answer": answer,
                "sql": None,
                "data": [],
                "verified": True,
                "is_unanswerable": True,
                "row_count": 0
            }

        primary_sql = sql_plan.get("sql")
        intent = sql_plan.get("intent", "general")
        metadata = sql_plan.get("metadata", {})
        
        cols = []
        rows = []
        guarded_sql = None
        compound_data = {}

        try:
            guarded_sql = validate_and_guard_sql(primary_sql)
            cursor = conn.execute(guarded_sql)
            cols = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            # C. If compound breakdown requested (e.g. top seller's brokers & products)
            if plan.is_compound and rows:
                first_row = rows[0]
                target_inn = None
                # Check for inn in first row
                for idx, cname in enumerate(cols):
                    if cname in ["inn", "seller_inn", "buyer_inn"]:
                        target_inn = first_row[idx]
                        break

                if target_inn:
                    year_filter = f"EXTRACT(YEAR FROM deal_date) = {plan.filters['year']}" if plan.filters.get("year") else "1=1"
                    
                    if "brokers" in plan.compound_breakdowns:
                        b_sql = f"""
                        SELECT 
                            seller_broker_code AS broker_code,
                            seller_broker_name AS broker_name,
                            COUNT(*) AS deals_count,
                            SUM(executed_amount_uzs) AS volume_uzs
                        FROM v_deals_enriched
                        WHERE seller_inn = '{target_inn}' AND {year_filter}
                        GROUP BY seller_broker_code, seller_broker_name
                        ORDER BY deals_count DESC
                        LIMIT 5
                        """
                        b_rows = conn.execute(b_sql).fetchall()
                        compound_data["brokers"] = b_rows

                    if "products" in plan.compound_breakdowns:
                        p_sql = f"""
                        SELECT 
                            product_name,
                            COUNT(*) AS deals_count,
                            SUM(contracted_volume_units) AS volume,
                            unit,
                            SUM(executed_amount_uzs) AS sales_uzs
                        FROM v_deals_enriched
                        WHERE seller_inn = '{target_inn}' AND {year_filter}
                        GROUP BY product_name, unit
                        ORDER BY sales_uzs DESC
                        LIMIT 5
                        """
                        p_rows = conn.execute(p_sql).fetchall()
                        compound_data["products"] = p_rows

        except Exception as e:
            err_msg = f"Xatolik yuz berdi: {str(e)}" if lang == "uz" else f"Произошла ошибка при выполнении запроса: {str(e)}"
            return {
                "question": plan.raw_question,
                "answer": err_msg,
                "sql": primary_sql,
                "data": [],
                "error": str(e),
                "verified": False,
                "row_count": 0
            }

        # D. Completeness & Result Verification
        v_report = self.verifier.verify_query_result(cols, rows, intent, metadata)
        coverage = CompletenessValidator.validate_plan_coverage(
            plan=plan,
            primary_result={"data": rows, "cols": cols},
            compound_results=compound_data
        )

        # E. Synthesize Natural Language Answer
        answer = self.synthesizer.synthesize_single(
            intent=intent,
            cols=cols,
            rows=rows,
            lang=lang,
            question=plan.raw_question,
            metadata=metadata,
            is_unanswerable=False,
            compound_data=compound_data if compound_data else None
        )

        # F. Update Conversational Memory Context
        self.context.update_context(
            session_id=session_id,
            broker=metadata.get("broker"),
            company=metadata.get("company"),
            commodity=metadata.get("commodity"),
            year=metadata.get("year"),
            region=metadata.get("region"),
            intent=intent,
            sql=guarded_sql,
            question=plan.raw_question,
            answer=answer
        )

        data_preview = [dict(zip(cols, r)) for r in rows[:20]]

        return {
            "question": plan.raw_question,
            "answer": answer,
            "sql": guarded_sql,
            "data": data_preview,
            "verified": v_report["is_valid"] and coverage["is_complete"],
            "row_count": len(rows),
            "completeness_score": coverage["coverage_pct"]
        }
