from pydantic import BaseModel, Field
from typing import Optional


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000, description="Python question to answer")

    model_config = {
        "json_schema_extra": {
            "example": {"question": "How do I reverse a list in Python?"}
        }
    }


class SourceDoc(BaseModel):
    title: str
    tags: str
    answer_score: int
    snippet: str


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceDoc]
    rewritten_query: str
    multi_queries: list[str] = []
    hyde_document: str = ""
    hallucination_detected: bool
    answer_grade: str
    confidence_score: float = 0.5
    retry_count: int
    latency_ms: float
    cache_hit: bool = False
    cache_similarity: Optional[float] = None


class FeedbackRequest(BaseModel):
    question: str
    answer: str
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    comment: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    model: str
    embedding_model: str
    vector_store: str
    cached_questions: int
    uptime_seconds: float


class StatsResponse(BaseModel):
    total_queries: int
    cache_hits: int
    avg_latency_ms: float
    cache_hit_rate: float
    top_tags: list[str]
