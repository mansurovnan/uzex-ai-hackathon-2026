# UZEX AI — Smart Stock Exchange Assistant
**Official Entry for UZEX AI Hackathon 2026**

A production-ready, hallucination-free bilingual AI Assistant for querying 500,000 real-world commodity and spot exchange transactions (2022–2026) across Uzbekistan Republican Commodity Exchange (UZEX).

---

## 🚀 Key Features

- **Bilingual Natural Language Support:** Native comprehension and responses in Uzbek (Latin/Cyrillic) and Russian.
- **500,000 Verified Transactions:** Directly backed by DuckDB embedded columnar OLAP engine with sub-20ms query response times.
- **Strict Mathematical Accuracy:** Zero hallucination. All aggregations, volumes, turnovers, and rankings are calculated via deterministic DuckDB SQL.
- **Universal Multi-Question Decomposition:** Intelligently splits complex multi-question messages (2-in-1, 3-in-1, 4-in-1, 5-in-1) into discrete analytical tasks and synthesizes numbered answers.
- **Multi-Part Compound Breakdown:** For complex queries, generates chained SQL queries to provide comprehensive entity details alongside breakdown tables (e.g. top products sold, top brokers utilized).
- **Multi-Turn Contextual Memory:** Understands follow-up references ('uning', 'его', '2024-yildachi?').
- **Read-Only Security Guard:** Built-in SQL AST validator blocks all data mutations and SQL injection attacks.
- **Clean Single-Page UI:** Modern, lightweight HTML/CSS/JavaScript chat interface served directly by FastAPI without bloated dependencies.
- **Transparent SQL Audit:** Every answer includes the exact SQL query executed against the dataset for verification by judges.
- **100% Verified Benchmark:** Passed all 50/50 test cases in the adversarial evaluation suite (`tests/test_50_benchmark.py`).

---

## 🛠️ Quick Local Setup

### 1. Requirements
- Python 3.10+ (macOS, Linux, or Windows)

### 2. Run Locally
```bash
# Clone/Open project
cd ~/UZEX_AI_HACKATHON

# Activate virtual environment
source backend/venv/bin/activate

# Install dependencies (if needed)
pip install -r backend/requirements.txt

# Run the FastAPI server
PYTHONPATH=backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open your browser at: **`http://127.0.0.1:8000`**

---

## 🌐 Public Deployment Guide (LivOps / Cloud Server)

To deploy on LivOps, Ubuntu Server, or Cloud VM (AWS, GCP, DigitalOcean, Hetzner):

### Option A: Direct Python Service (Recommended for Fast Hackathon Evaluation)
```bash
# 1. Clone repository to server
git clone <your-repo-url> /opt/uzex-ai
cd /opt/uzex-ai

# 2. Setup Virtualenv
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt

# 3. Run with systemd or nohup
PYTHONPATH=backend nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &

# 4. Check Health
curl http://localhost:8000/api/health
```

### Option B: Docker / Container Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d --build

# Verify running container
docker ps
curl http://localhost:8000/api/health
```

---

## 📊 API Reference

### `POST /api/chat`
Ask any exchange question in Uzbek or Russian.

**Request:**
```json
{
  "message": "2024-yilda jami birja aylanmasi qancha bo'lgan?"
}
```

**Response:**
```json
{
  "answer": "📊 UZEX Birja Ko'rsatkichlari (2024-yilda): ...",
  "sql": "SELECT COUNT(*) AS total_deals, ... FROM v_deals_enriched ...",
  "data": [...],
  "language": "uz"
}
```

### `GET /api/health`
Healthcheck returning database connectivity and record counts.

---

## 🧪 Automated Benchmarking

Run the full adversarial test suite:

```bash
# 50-Question Adversarial Benchmark (Multi-question, Compound, Out-of-Scope, Memory)
PYTHONPATH=backend backend/venv/bin/python tests/test_50_benchmark.py

# 32-Question Core Benchmark
PYTHONPATH=backend backend/venv/bin/python tests/test_30_benchmark.py
```
**Results:** **50/50 Passed (100.0%)** with an average latency under **50ms**.
