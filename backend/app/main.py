import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Ensure project paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agent.query_engine import ExchangeQueryEngine
from app.database.connection import get_readonly_connection

app = FastAPI(
    title="UZEX AI — Smart Stock Exchange Assistant",
    description="Intelligent AI Agent for Commodity & Spot Exchange Analytics (UZ/RU)",
    version="1.0.0"
)

# Locate templates and static directories (supports root or backend folder)
TEMPLATES_DIR = PROJECT_ROOT / "templates" if (PROJECT_ROOT / "templates").exists() else BACKEND_DIR / "templates"
STATIC_DIR = PROJECT_ROOT / "static" if (PROJECT_ROOT / "static").exists() else BACKEND_DIR / "static"

TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

query_engine = ExchangeQueryEngine()

class ChatRequest(BaseModel):
    message: Optional[str] = None
    question: Optional[str] = None
    prompt: Optional[str] = None
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    answer: str
    sql: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    language: str
    verified: Optional[bool] = True
    row_count: Optional[int] = 0
    sub_questions_count: Optional[int] = 1
    evidence: Optional[Dict[str, Any]] = None

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    """Serves the single-page chat interface."""
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    """
    Main AI chat endpoint.
    Accepts question in Uzbek or Russian, queries 500k deals via DuckDB,
    and returns exact numerical and analytical answers.
    """
    user_query = payload.message or payload.question or payload.prompt
    if not user_query or not user_query.strip():
        raise HTTPException(status_code=400, detail="Savol yoki xabar kiritilmadi / Вопрос не может быть пустым.")

    result = query_engine.process_question(user_query.strip(), session_id=payload.session_id or "default")
    return ChatResponse(
        answer=result.get("answer", ""),
        sql=result.get("sql"),
        data=result.get("data", []),
        language=result.get("language", "uz"),
        verified=result.get("verified", True),
        row_count=result.get("row_count", 0),
        sub_questions_count=result.get("sub_questions_count", 1),
        evidence=result.get("evidence")
    )

@app.get("/api/health")
@app.get("/health")
@app.get("/healthz")
async def health_check():
    """System and database healthcheck for Render and cloud monitoring."""
    try:
        with get_readonly_connection() as conn:
            deals_count = conn.execute("SELECT COUNT(*) FROM deals").fetchone()[0]
            contracts_count = conn.execute("SELECT COUNT(*) FROM contracts").fetchone()[0]
            participants_count = conn.execute("SELECT COUNT(*) FROM participants").fetchone()[0]
            brokers_count = conn.execute("SELECT COUNT(*) FROM brokers").fetchone()[0]
        return {
            "status": "healthy",
            "ready": True,
            "database": "connected",
            "total_deals": deals_count,
            "total_contracts": contracts_count,
            "total_participants": participants_count,
            "total_brokers": brokers_count,
            "version": "2.0.0",
            "commit_sha": "10dcdc7"
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "unhealthy", "ready": False, "error": str(e)})

@app.get("/api/version")
async def version_info():
    """Returns application release and dataset version info."""
    return {
        "name": "UZEX AI — Smart Stock Exchange Assistant",
        "version": "2.0.0",
        "commit_sha": "10dcdc7",
        "supported_languages": ["uz-Latn", "uz-Cyrl", "ru"],
        "dataset": {
            "total_deals": 500000,
            "date_range": "2022-01-03 to 2026-10-30",
            "coverage_notes": "2026 data partial: 10 months (Jan-Oct 2026)"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", os.environ.get("APP_PORT", 10000)))
    host = os.environ.get("APP_HOST", "0.0.0.0")
    uvicorn.run("app.main:app", host=host, port=port)
