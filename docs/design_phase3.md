# Phase 3: Architectural Design & Requirements Traceability Matrix

## 1. System Architecture Overview

```
User Request (POST /api/chat)
  │
  ▼
[1. Message Classifier & Scope Router] (Section I, Section E)
  ├─► small_talk ─────────────► ConversationalAgent (Zero SQL, instant natural reply)
  ├─► unrelated ──────────────► ScopeGuard (Polite redirect, Zero SQL)
  ├─► database_out_of_scope ──► ScopeGuard (Honest explanation of DB boundaries, Zero SQL)
  └─► in_scope ───────────────▼
[2. Language & Normalization Engine] (uz-Latn, uz-Cyrl, ru)
  │
  ▼
[3. Deterministic Extractor] (Years, ranges 2022-2026, number words, limits, «quoted» entities)
  │
  ▼
[4. Enhanced Entity Resolver & Index] (Section B: 6-stage resolution, canonical IDs, disambiguation)
  │
  ▼
[5. Structured Analytical Planner] (Section D.2: Pydantic/dataclass SubQuestionPlan)
  │
  ▼
[6. Plan-to-SQL Compiler & Guard] (Section D.3, D.4: Deterministic SQL, read-only AST safety, tie-breakers)
  │
  ▼
[7. DuckDB Execution Engine] (Timeout guard, row cap, v_deals_enriched)
  │
  ▼
[8. Verification & Cross-Check Engine] (Section A: Re-derive #1, Top-N sum <= total, monotonic order)
  │
  ▼
[9. Evidence-Grounded Synthesizer] (Section A, C, E: Natural Uzbek/Russian, 2026 coverage caveat, tables)
  │
  ▼
[10. Expandable Inspector & Additive Response] (Evidence Object, SQL, plan, passed checks)
```

---

## 2. Evidence Object Specification
The Evidence Object is the single source of truth for narrative generation and client inspection:
```json
{
  "plan": {
    "intent": "ranking",
    "target_entity": "product",
    "metrics": ["physical_volume", "total_turnover_uzs", "deals_count"],
    "primary_metric": "physical_volume",
    "time_filter": {"year": 2024},
    "ranking_limit": 5,
    "ranking_order": "DESC"
  },
  "resolved_entities": [
    {
      "canonical_name": "Пшеница продовольственная",
      "entity_type": "product",
      "match_stage": "stage_1_quoted_literal",
      "canonical_id": "Пшеница продовольственная",
      "input_token": "«Пшеница продовольственная»"
    }
  ],
  "executed_sql": "SELECT ...",
  "row_count": 5,
  "columns": ["product_name", "unit", "deals_count", "total_volume", "total_turnover_uzs"],
  "rows": [...],
  "units": {"Пшеница продовольственная": "тонна"},
  "currencies": {"amount_uzs": "so'm"},
  "applied_filters": {"year": 2024, "status": "all_concluded"},
  "coverage_notes": [],
  "assumptions": ["Barcha tuzilgan birja bitimlari hisobga olindi."],
  "cross_checks": {
    "rederived_top_entity": true,
    "top_n_sum_le_total": true,
    "monotonic_ordering": true,
    "limit_exact_match": true,
    "grounded_numbers": true
  },
  "verification_passed": true
}
```

---

## 3. Entity Resolution Policy (6 Stages)
1. **Stage 1 (Literal Extraction):** Text enclosed in «...», "...", „...“, or '...'.
2. **Stage 2 (Exact Match):** Direct match against canonical names.
3. **Stage 3 (Normalized Match):** Case-folded, whitespace-collapsed, apostrophe-normalized (o‘/o'/o`/g‘/g'/g`), ё/е unifications.
4. **Stage 4 (Transliteration Match):** Uzbek Latin ↔ Uzbek Cyrillic ↔ Russian transliteration.
5. **Stage 5 (Cross-Language Alias):** Version-controlled dictionary mapping Uzbek commodity terms (e.g. *bug'doy*, *paxta*, *sement*, *mis*) to canonical database product names.
6. **Stage 6 (Token/Fuzzy Match):** High-confidence token intersection (> 0.85 similarity).

---

## 4. Requirements Traceability Matrix

| Requirement | Description | Target Module | Verification Tests |
|---|---|---|---|
| **A.1-A.5** | Evidence-first answering & cross-checks | `agent/evidence.py`, `agent/verifier.py` | `tests/test_evidence_pipeline.py` |
| **A.6** | Acceptance Case (TOP 5 products 2024) | `agent/sql_generator.py` | `tests/test_section_g.py` (Test 1) |
| **B.1-B.6** | 6-stage Entity Index & disambiguation | `agent/entity_resolver.py` | `tests/test_generalization_sweeps.py` (Sweep 1) |
| **C.1-C.4** | Metric definitions, units, currencies | `agent/sql_generator.py`, `docs/semantic_decisions.md` | `tests/test_oracle.py`, `tests/test_section_g.py` |
| **C.5-C.6** | Date semantics & 2026 partial coverage caveat | `agent/synthesizer.py` | `tests/test_section_g.py` (Test 2) |
| **C.7-C.10**| Statuses, tie-breakers, role mapping | `agent/sql_generator.py`, `agent/analytical_planner.py` | `tests/test_section_g.py` (Test 3) |
| **D.1-D.4** | Semantic layer, Plan, SQL Compiler, Guard | `agent/analytical_planner.py`, `agent/sql_generator.py` | `tests/test_generalization_sweeps.py` (Sweep 2) |
| **D.5** | Multi-turn result-set reference preservation | `agent/context_manager.py` | `tests/test_section_g.py` (Test 4) |
| **E.1-E.6** | Human-like natural Uzbek/Russian conversation | `agent/conversational.py`, `agent/synthesizer.py` | `tests/test_scope_and_conversation.py` |
| **F.1-F.4** | Cold-start detection, health check, version | `backend/app/main.py`, `static/app.js` | `tests/test_cold_start.py` |
| **G.1-G.5** | Section G Mandatory Acceptance Scenarios 1–5 | `agent/query_engine.py` | `tests/test_section_g.py` |
| **H.1-H.9** | Independent Oracle & Generalization Sweeps | `tests/test_oracle.py`, `tests/test_generalization_sweeps.py` | All test suites |
| **I.1-I.4** | Strict Scope Control (unrelated, out-of-scope) | `agent/conversational.py`, `agent/query_engine.py` | `tests/test_scope_and_conversation.py` |
