"""
Completeness Validation and Requirement Coverage Checker.
Verifies that all extracted requirements from the analytical plan
are present in the SQL execution results before presentation.
"""

from typing import Dict, Any, List
from .analytical_planner import SubQuestionPlan

from typing import Dict, Any, List, Optional
from .analytical_planner import SubQuestionPlan

class CompletenessValidator:
    @staticmethod
    def validate_plan_coverage(
        plan: SubQuestionPlan,
        primary_result: Dict[str, Any],
        compound_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validates whether all required components in the SubQuestionPlan
        were successfully fetched and are present in the response data.
        """
        missing_components = []
        covered_components = []

        data_rows = primary_result.get("data", [])
        cols = [c.lower() for c in primary_result.get("cols", [])]
        
        # Check basic execution
        if not data_rows and not primary_result.get("is_unanswerable"):
            return {
                "is_complete": False,
                "missing": plan.required_components,
                "coverage_pct": 0.0,
                "note": "Query executed but returned zero matching records."
            }

        # Check metrics and compound breakdowns
        for comp in plan.required_components:
            comp_l = comp.lower()
            if any(term in comp_l for term in ["sales", "purchase", "turnover", "amount", "revenue"]):
                if any(any(t in c for t in ["amount", "turnover", "sales", "spend", "revenue", "uzs", "usd", "vol"]) for c in cols):
                    covered_components.append(comp)
                else:
                    missing_components.append(comp)

            elif any(term in comp_l for term in ["deals_count", "total_deals", "count", "deal"]):
                if any("deal" in c or "count" in c or "cnt" in c for c in cols):
                    covered_components.append(comp)
                else:
                    missing_components.append(comp)

            elif "usd" in comp_l:
                if any("usd" in c for c in cols):
                    covered_components.append(comp)
                else:
                    missing_components.append(comp)

            elif "uzs" in comp_l:
                if any("uzs" in c for c in cols):
                    covered_components.append(comp)
                else:
                    missing_components.append(comp)

            elif "broker" in comp_l:
                if (compound_results and compound_results.get("brokers")) or any("broker" in c for c in cols):
                    covered_components.append(comp)
                else:
                    missing_components.append(comp)

            elif "product" in comp_l:
                if (compound_results and compound_results.get("products")) or any("product" in c for c in cols):
                    covered_components.append(comp)
                else:
                    missing_components.append(comp)

            elif "region" in comp_l:
                if any("region" in c or "sales" in c or "count" in c for c in cols):
                    covered_components.append(comp)
                else:
                    missing_components.append(comp)
            else:
                covered_components.append(comp)

        total_reqs = len(plan.required_components)
        is_complete = len(missing_components) == 0
        coverage_pct = (len(covered_components) / total_reqs * 100.0) if total_reqs > 0 else 100.0

        return {
            "is_complete": is_complete,
            "covered": covered_components,
            "missing": missing_components,
            "coverage_pct": coverage_pct,
            "note": "All requirements satisfied." if is_complete else f"Missing: {missing_components}"
        }
