# Phase 1: Comprehensive Dataset & Codebase Audit Report

## 1. Executive Summary
This document provides the exhaustive, evidence-based audit of the **UZEX AI — Smart Stock Exchange Assistant** codebase, DuckDB analytical database, and runtime architecture.

---

## 2. Codebase Map & Request Flow

### 2.1 Repository Map
```
UZEX_AI_HACKATHON/
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI app entry point, endpoints /api/chat, /api/health
│   │   ├── database/
│   │   │   ├── connection.py         # Thread-safe read-only DuckDB connection provider
│   │   │   ├── importer.py           # DuckDB build from original CSVs with schema and view definition
│   │   │   └── schema.sql            # Base DDL and v_deals_enriched definition
│   │   └── agent/
│   │       ├── analytical_planner.py # Decomposes input into SubQuestionPlans
│   │       ├── completeness_validator.py
│   │       ├── context_manager.py    # Multi-turn memory & pronoun resolution
│   │       ├── conversational.py     # Pure conversational small talk agent (zero SQL)
│   │       ├── dictionary.py         # Static entity mappings
│   │       ├── entity_resolver.py    # In-memory entity resolver
│   │       ├── query_engine.py       # Central pipeline orchestrator
│   │       ├── schema_registry.py    # Schema metadata catalog
│   │       ├── sql_generator.py      # Semantic SQL synthesis & guard
│   │       ├── sql_guard.py          # Security AST validator
│   │       ├── synthesizer.py        # Executive bilingual response generator
│   │       └── verifier.py           # Post-execution result verification
├── dataset/
│   ├── original/                     # Immutable source CSV files (10 files)
│   └── processed/
│       └── uzex_data.duckdb          # 115 MB DuckDB analytical database
├── static/                           # CSS and frontend JS
├── templates/                        # index.html Jinja2 template
└── tests/                            # Test benchmark suites
```

### 2.2 Request Flow
1. User enters natural language question in UI (`/static/app.js`).
2. Frontend sends JSON payload `{"message": "...", "session_id": "..."}` to `POST /api/chat`.
3. `main.py` dispatches request to `ExchangeQueryEngine.process_question`.
4. `ConversationalAgent` fast-paths small-talk (greetings, thanks, identity) returning in < 1ms with 0 SQL.
5. `AnalyticalPlanner` parses analytical queries into structured plans.
6. `EntityResolver` resolves products, companies, brokers, regions.
7. `UniversalSQLGenerator` constructs DuckDB SQL using `v_deals_enriched`.
8. `sql_guard.py` enforces security guards (SELECT-only, read-only).
9. Query executes on DuckDB; results passed to `ResultVerifier` and `CompletenessValidator`.
10. `ResponseSynthesizer` formats structured Markdown answer with tables and follow-ups.
11. Response returned to frontend.

---

## 3. Database Schema Audit

### 3.1 Tables and Record Counts
| Table / View | Type | Rows | Columns | Purpose |
|---|---|:---:|:---:|---|
| `deals` | Base Table | 500,000 | 22 | Individual exchange transactions (2022–2026) |
| `contracts` | Base Table | 6,616 | 28 | Official contract cards registered on the exchange |
| `participants` | Base Table | 14,392 | 6 | Market participants (sellers and buyers) |
| `brokers` | Base Table | 120 | 4 | Accredited brokerage offices |
| `usd_rates` | Base Table | 1,765 | 2 | Official Central Bank USD/UZS daily exchange rates |
| `v_deals_enriched` | Analytical View | 500,000 | 55 | Denormalized join of deals, contracts, participants, brokers, rates |

### 3.2 Temporal Coverage & Data Traps
* **Date Range:** `2022-01-03` to `2026-10-30`
* **Annual Deal Counts:**
  * 2022: 84,299 deals (`2022-01-03` to `2022-12-30`) — Full Year
  * 2023: 93,985 deals (`2023-01-02` to `2023-12-29`) — Full Year
  * 2024: 106,647 deals (`2024-01-02` to `2024-12-31`) — Full Year
  * 2025: 115,763 deals (`2025-01-02` to `2025-12-31`) — Full Year
  * 2026: 99,306 deals (`2026-01-02` to `2026-10-30`) — **INCOMPLETE YEAR (Months 1–10 only)**
* **Data Trap - Partial 2026:**
  November and December 2026 are absent. Analytical trend responses must NEVER mislabel 2026 as an economic decline without explicitly noting the 10-month partial coverage.

### 3.3 Deal Statuses & Execution Semantics
| Deal Status | Count | Delivered Lots > 0 | Meaning / Category |
|---|:---:|:---:|---|
| `Исполнен` | 431,061 | 431,061 | Executed / Fully delivered |
| `Аннулирован(Не оплачен)` | 33,719 | 0 | Cancelled due to payment default |
| `Исполнен(Частично)` | 22,648 | 22,648 | Partially executed |
| `Оплачен` | 5,854 | 0 | Paid, awaiting delivery |
| `Заключен` | 3,954 | 0 | Concluded / registered |
| `Ждёт оплату` | 1,714 | 0 | Awaiting payment |
| `Новый` | 964 | 0 | Newly created deal |
| `Не подписан` | 86 | 0 | Unsigned / unconfirmed |

* **Total Concluded Deals:** 500,000 (all rows in `deals`)
* **Total Executed Deals:** 453,709 (`Исполнен` + `Исполнен(Частично)`)
* **Total Cancelled Deals:** 33,719 (`Аннулирован(Не оплачен)`)

### 3.4 Currencies and FX Semantics
* `Внутренний` (Domestic) Contracts: Currency is strictly `Узбекский сум` (493,410 deals).
* `Экспортный` (Export) Contracts: Currency is strictly `Доллар США` (6,590 deals).
* In `v_deals_enriched`:
  * `amount_contract_currency`: Native deal value (USD for export, UZS for domestic).
  * `amount_uzs`: Standardized equivalent in UZS. For export deals, multiplied by `usd_rates.rate_uzs` on `deal_date`.
  * `executed_amount_uzs`: Actual delivered turnover in UZS (`delivered_lots * lot_size * unit_price * fx_rate`).

### 3.5 Measurement Units Audit
* Units in database: `тонна`, `килограмм`, `литр`, `куб.метр`, `метр`, `кв.метр`, `штука`.
* Exactly 4 products in `contracts` have multiple units:
  1. `Бензин`: `литр` and `тонна`
  2. `Дизельное топливо`: `килограмм` and `тонна`
  3. `БЕНЗИН АВТОМОБИЛЬНЫЙ`: `литр` and `тонна`
  4. `Топливо дизельное`: `килограмм` and `тонна`
* All other products use a single consistent unit. Physical quantities must NEVER be summed across different units.

### 3.6 Wheat Products & Entity Disambiguation
There are 7 distinct contracts/products starting with "Пшеница":
1. `Пшеница продовольственная` (19,058 deals)
2. `Пшеница` (10,118 deals)
3. `ПШЕНИЦА ПРОДОВОЛЬСТВЕННАЯ` (5,607 deals) - Uppercase canonical equivalent
4. `Пшеница продовольственная 4-класс` (1,936 deals)
5. `Пшеница продовольственная 3-класс` (810 deals)
6. `Пшеница 4-класс` (660 deals)
7. `Пшеница 3-класс` (434 deals)
* Quoted entity `«Пшеница продовольственная»` must match exact/case-folded variants (1 and 3 = 24,665 deals total) and MUST NOT match grade-specific classes (4 and 5).

### 3.7 Market Participants & Roles
* Total participants: 14,392 companies
* Active in deals: 14,389 companies
* Sellers: exactly 392 distinct companies (never act as buyers in `deals`).
* Buyers: exactly 13,997 distinct companies (never act as sellers in `deals`).
* Zero duplicate company names across distinct INNs in `participants`.
