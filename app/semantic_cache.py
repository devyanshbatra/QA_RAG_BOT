"""
Semantic cache: if a similar question was asked before, return cached answer.
Uses cosine similarity on embeddings to detect near-duplicate questions.
"""

import json
import time
import hashlib
import numpy as np
import diskcache
from pathlib import Path
from app.rag_agent import get_embeddings

CACHE_DIR = Path("./cache")
SIMILARITY_THRESHOLD = 0.92
cache = diskcache.Cache(str(CACHE_DIR))

_cached_embeddings: list[tuple[np.ndarray, str]] = []  # (embedding, cache_key)


def _embed(text: str) -> np.ndarray:
    emb = get_embeddings()
    vec = emb.embed_query(text)
    return np.array(vec, dtype=np.float32)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def get_cached(question: str) -> dict | None:
    q_emb = _embed(question)
    for stored_emb, key in _cached_embeddings:
        sim = _cosine_similarity(q_emb, stored_emb)
        if sim >= SIMILARITY_THRESHOLD:
            result = cache.get(key)
            if result:
                result["cache_hit"] = True
                result["cache_similarity"] = round(sim, 4)
                return result
    return None


def set_cache(question: str, result: dict):
    key = hashlib.md5(question.encode()).hexdigest()
    q_emb = _embed(question)
    cache.set(key, result, expire=3600 * 24)  # 24h TTL
    _cached_embeddings.append((q_emb, key))
    # keep only last 1000 in memory
    if len(_cached_embeddings) > 1000:
        _cached_embeddings.pop(0)


def cache_stats() -> dict:
    return {
        "cached_questions": len(_cached_embeddings),
        "cache_size_mb": round(cache.volume() / 1024 / 1024, 2),
    }
