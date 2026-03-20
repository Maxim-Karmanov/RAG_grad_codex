"""FastAPI backend for the Градостроительный кодекс RAG system."""
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from .rag import graph
from .retriever import ARTICLES_BY_NUMBER

app = FastAPI(title="Градостроительный кодекс РФ — RAG API")

STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str
    thread_id: Optional[str] = None  # None = new conversation


class SourceItem(BaseModel):
    article: str
    title: str
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    consistency_score: float
    thread_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def serve_frontend():
    """Serve the single-page chat UI."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Run the full RAG pipeline and return answer + sources."""
    thread_id = request.thread_id or str(uuid.uuid4())
    run_config = {"configurable": {"thread_id": thread_id}}

    try:
        result = graph.invoke(
            {"messages": [HumanMessage(content=request.question)]},
            config=run_config,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    answer = result["messages"][-1].content
    sources = result.get("sources", [])
    consistency = result.get("consistency", {})
    score = float(consistency.get("score", 1.0))

    return ChatResponse(
        answer=answer,
        sources=[SourceItem(**s) for s in sources],
        consistency_score=score,
        thread_id=thread_id,
    )


@app.get("/api/article/{article_num}")
async def get_article(article_num: str):
    """Return full text of a specific article by its number."""
    doc = ARTICLES_BY_NUMBER.get(article_num)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Статья {article_num} не найдена")
    return {
        "article": article_num,
        "title": doc.metadata.get("Статья", f"Статья {article_num}"),
        "content": doc.page_content,
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}
