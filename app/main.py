"""
Python Q&A Assistant — FastAPI application
Endpoints:
  POST /ask           — answer a Python question (CRAG + Self-RAG)
  POST /ask/stream    — streaming answer
  GET  /health        — service health check
  GET  /stats         — usage statistics
  POST /feedback      — submit answer rating
  GET  /history       — recent query history
"""

import os
import time
import asyncio
from contextlib import asynccontextmanager
from collections import defaultdict
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.models import (
    AskRequest, AskResponse, SourceDoc,
    FeedbackRequest, HealthResponse, StatsResponse,
)
from app.rag_agent import ask as rag_ask, get_vectorstore, get_graph
from app.semantic_cache import get_cached, set_cache, cache_stats

load_dotenv()

# ---------------------------------------------------------------------------
# App state
# ---------------------------------------------------------------------------
_start_time = time.time()
_stats = {
    "total_queries": 0,
    "cache_hits": 0,
    "total_latency_ms": 0.0,
    "tag_counts": defaultdict(int),
}
_history: list[dict] = []
_feedback_store: list[dict] = []


# ---------------------------------------------------------------------------
# Lifespan — warm up on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Warming up vector store and LangGraph agent...")
    try:
        get_vectorstore()
        get_graph()
        print("Ready.")
    except Exception as e:
        print(f"Warning: startup warmup failed: {e}")
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Python Q&A Assistant",
    description=(
        "AI-powered Python Q&A using CRAG + Self-RAG on Stack Overflow data. "
        "Built with LangGraph, LangChain, ChromaDB, and Mistral-7B."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# POST /ask
# ---------------------------------------------------------------------------
@app.post("/ask", response_model=AskResponse, summary="Answer a Python question")
async def ask_endpoint(request: AskRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # semantic cache check
    cached = get_cached(question)
    if cached:
        _stats["total_queries"] += 1
        _stats["cache_hits"] += 1
        _history.append({"question": question, "cache_hit": True, "ts": time.time()})
        return AskResponse(
            question=question,
            answer=cached["answer"],
            sources=[SourceDoc(**s) for s in cached["sources"]],
            rewritten_query=cached.get("rewritten_query", question),
            hallucination_detected=cached.get("hallucination_detected", False),
            answer_grade=cached.get("answer_grade", "good"),
            retry_count=cached.get("retry_count", 0),
            latency_ms=cached.get("latency_ms", 0),
            cache_hit=True,
            cache_similarity=cached.get("cache_similarity"),
        )

    # run CRAG agent
    try:
        result = await asyncio.get_event_loop().run_in_executor(None, rag_ask, question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # update stats
    _stats["total_queries"] += 1
    _stats["total_latency_ms"] += result["latency_ms"]
    for src in result["sources"]:
        for tag in src.get("tags", "").replace("<", "").replace(">", " ").split():
            _stats["tag_counts"][tag] += 1

    # cache result
    set_cache(question, result)

    # save to history
    _history.append({
        "question": question,
        "answer_snippet": result["answer"][:100],
        "latency_ms": result["latency_ms"],
        "cache_hit": False,
        "ts": time.time(),
    })
    if len(_history) > 100:
        _history.pop(0)

    return AskResponse(
        question=question,
        answer=result["answer"],
        sources=[SourceDoc(**s) for s in result["sources"]],
        rewritten_query=result["rewritten_query"],
        hallucination_detected=result["hallucination_detected"],
        answer_grade=result["answer_grade"],
        retry_count=result["retry_count"],
        latency_ms=result["latency_ms"],
        cache_hit=False,
    )


# ---------------------------------------------------------------------------
# POST /ask/stream  — token-by-token streaming
# ---------------------------------------------------------------------------
@app.post("/ask/stream", summary="Stream answer token by token")
async def ask_stream(request: AskRequest):
    question = request.question.strip()

    async def token_generator() -> AsyncGenerator[str, None]:
        cached = get_cached(question)
        if cached:
            answer = cached["answer"]
            for word in answer.split(" "):
                yield f"data: {word} \n\n"
                await asyncio.sleep(0.02)
            yield "data: [DONE]\n\n"
            return

        try:
            result = await asyncio.get_event_loop().run_in_executor(None, rag_ask, question)
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
            yield "data: [DONE]\n\n"
            return

        set_cache(question, result)
        _stats["total_queries"] += 1
        _stats["total_latency_ms"] += result["latency_ms"]

        answer = result["answer"]
        for word in answer.split(" "):
            yield f"data: {word} \n\n"
            await asyncio.sleep(0.02)
        yield "data: [DONE]\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, summary="Health check")
async def health():
    try:
        vs = get_vectorstore()
        count = vs._collection.count()
        vs_status = f"ok ({count:,} vectors)"
    except Exception as e:
        vs_status = f"error: {str(e)}"

    cs = cache_stats()
    return HealthResponse(
        status="ok",
        model=os.getenv("OLLAMA_MODEL", "gemma2:2b"),
        embedding_model=os.getenv("EMBEDDING_MODEL_ID", "sentence-transformers/all-MiniLM-L6-v2"),
        vector_store=vs_status,
        cached_questions=cs["cached_questions"],
        uptime_seconds=round(time.time() - _start_time, 1),
    )


# ---------------------------------------------------------------------------
# GET /stats
# ---------------------------------------------------------------------------
@app.get("/stats", response_model=StatsResponse, summary="Usage statistics")
async def stats():
    total = _stats["total_queries"]
    hits = _stats["cache_hits"]
    avg_lat = (_stats["total_latency_ms"] / max(total - hits, 1))
    top_tags = sorted(_stats["tag_counts"], key=_stats["tag_counts"].get, reverse=True)[:5]
    return StatsResponse(
        total_queries=total,
        cache_hits=hits,
        avg_latency_ms=round(avg_lat, 2),
        cache_hit_rate=round(hits / max(total, 1), 4),
        top_tags=top_tags,
    )


# ---------------------------------------------------------------------------
# GET /history
# ---------------------------------------------------------------------------
@app.get("/history", summary="Recent query history")
async def history(limit: int = 20):
    return {"history": _history[-limit:][::-1]}


# ---------------------------------------------------------------------------
# POST /feedback
# ---------------------------------------------------------------------------
@app.post("/feedback", summary="Submit answer rating (1-5)")
async def feedback(fb: FeedbackRequest):
    _feedback_store.append({
        "question": fb.question,
        "answer_snippet": fb.answer[:100],
        "rating": fb.rating,
        "comment": fb.comment,
        "ts": time.time(),
    })
    return {"status": "ok", "message": "Feedback recorded. Thank you!"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=False,
    )
