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
        row_count=result.get("row_count", 0)
    )

@app.get("/api/health")
async def health_check():
    """System and database healthcheck."""
    try:
        with get_readonly_connection() as conn:
            deals_count = conn.execute("SELECT COUNT(*) FROM deals").fetchone()[0]
            contracts_count = conn.execute("SELECT COUNT(*) FROM contracts").fetchone()[0]
        return {
            "status": "healthy",
            "database": "connected",
            "total_deals": deals_count,
            "total_contracts": contracts_count
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "unhealthy", "error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
