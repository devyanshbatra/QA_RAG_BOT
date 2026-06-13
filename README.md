# Python Q&A Assistant

AI-powered Python programming Q&A system built on Stack Overflow data using **CRAG (Corrective RAG)** + **Self-RAG** with LangGraph, LangChain, ChromaDB, and gemma2:2b (via Ollama).

## Architecture

```
User Question
      │
      ▼
Query Rewriting (LLM improves specificity)
      │
      ▼
Multi-Query + HyDE (on retry only — saves 2 LLM calls on first pass)
      │
      ▼
Hybrid Retrieval (BM25 0.4 + Semantic MMR 0.6)
      │
      ▼
Cross-Encoder Reranker (top-10 → top-3)
      │
      ▼
Document Grading (cosine similarity — no LLM call)
   ├── Relevant → Generate Answer
   └── Not Relevant → Fallback Retrieval → Generate Answer
      │
      ▼
Answer Grading (cosine similarity — no LLM call)
   ├── Good → Return to user
   └── Bad  → Retry loop (max 2x, with Multi-Query + HyDE)
      │
      ▼
Semantic Cache (store for similar future queries)
      │
      ▼
FastAPI Response (answer + sources + metadata)
```

## Features

- **CRAG + Self-RAG** via LangGraph — corrective retrieval with answer quality grading
- **Hybrid Search** — BM25 keyword + semantic MMR vector search (0.4/0.6 weights)
- **Cross-encoder Reranking** — `ms-marco-MiniLM` reranker for precision
- **Cosine Similarity Grading** — document and answer grading without LLM calls (2x faster)
- **Multi-Query + HyDE** — only on retry to save latency on happy path
- **Semantic Caching** — cosine similarity cache avoids redundant LLM calls
- **Streaming** — `POST /ask/stream` streams answer token by token
- **Source Citations** — every answer cites Stack Overflow sources
- **Hallucination Detection** — grading node flags ungrounded answers
- **6 API Endpoints** — ask, stream, health, stats, feedback, history

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ask` | Answer a Python question |
| `POST` | `/ask/stream` | Streaming answer (SSE) |
| `GET`  | `/health` | Service health check |
| `GET`  | `/stats` | Usage statistics |
| `POST` | `/feedback` | Rate an answer (1-5) |
| `GET`  | `/history` | Recent query history |
| `GET`  | `/docs` | Auto-generated API docs (Swagger) |

### POST /ask — Request
```json
{
  "question": "How do I reverse a list in Python?"
}
```

### POST /ask — Response
```json
{
  "question": "How do I reverse a list in Python?",
  "answer": "You can reverse a list using slicing: my_list[::-1] ...",
  "sources": [
    {
      "title": "How to reverse a list in Python",
      "tags": "python list",
      "answer_score": 1847,
      "snippet": "Use my_list[::-1] for a new reversed list..."
    }
  ],
  "rewritten_query": "Python list reversal methods slicing reversed()",
  "hallucination_detected": false,
  "answer_grade": "good",
  "retry_count": 0,
  "latency_ms": 1240.5,
  "cache_hit": false
}
```

## Setup

### 1. Clone and install

```bash
git clone https://github.com/devyanshbatra/QA_RAG_BOT
cd QA_RAG_BOT
pip install -r requirements.txt
```

### 2. Install Ollama and pull model

Download Ollama from [ollama.ai](https://ollama.ai) and run:

```bash
ollama pull gemma2:2b
ollama serve   # starts on http://localhost:11434
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your Kaggle credentials
```

Required keys:
- `KAGGLE_USERNAME` + `KAGGLE_KEY` — from [kaggle.com/settings](https://www.kaggle.com/settings) → API
- `OLLAMA_MODEL` — default `gemma2:2b` (already set in `.env.example`)

### 4. Download and preprocess dataset

```bash
python data/download_and_preprocess.py
```

Downloads Stack Overflow Python Q&A from Kaggle, filters high-quality Q&A pairs (~50k), cleans HTML.

### 5. Ingest into vector store

```bash
python data/ingest.py
```

Embeds 16,524 chunks with `sentence-transformers/all-MiniLM-L6-v2` and stores in ChromaDB.

### 6. Run the API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) for interactive Swagger UI.

## Deployed App

> **Live URL:** Not deployed (GPU + persistent disk required — see deployment notes below)

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent Framework | LangGraph |
| LLM Orchestration | LangChain |
| Language Model | gemma2:2b via Ollama (local inference) |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| Vector Store | ChromaDB (16,524 chunks) |
| Semantic Cache | DiskCache + cosine similarity |
| API Framework | FastAPI |
| Dataset | Stack Overflow Python Q&A (Kaggle) |

## Latency Optimizations

Current average: **~10–12s** per query (down from ~30s before optimization).

| Optimization | Saving |
|---|---|
| Skip Multi-Query + HyDE on first pass | −2 LLM calls (~6s) |
| Cosine similarity grading (no LLM) | −2 LLM calls (~6s) |
| Singleton model loading | −model reload per call |
| Semantic cache | 0ms on cache hit |

**To reduce latency further:**
- Use `vLLM` instead of Ollama for batched GPU inference (2–5x throughput)
- Use `llama.cpp` with quantized GGUF model for faster CPU fallback
- Use a larger Ollama GPU context to avoid token truncation retries
- Replace DiskCache with Redis for sub-ms cache lookups at scale

## Scaling for 100+ Concurrent Users

- **Async FastAPI** — all endpoints are `async`, non-blocking I/O
- **Semantic cache** — ~30% of queries served from cache at zero LLM cost
- **Redis** — swap DiskCache for Redis for distributed multi-instance caching
- **Pinecone/Weaviate** — replace local ChromaDB with managed vector DB
- **vLLM / TGI** — replace Ollama with vLLM or HuggingFace TGI for batched GPU serving
- **Connection pooling** — uvicorn workers + gunicorn for multi-process serving
- **Horizontal scaling** — stateless FastAPI pods behind a load balancer

## Test Results

8/8 queries passing. Average latency ~11s. Results in [`tests/results.json`](tests/results.json).

```
Query 1: How do I read a CSV file in Python using pandas?       ✓
Query 2: What is the difference between a list and a tuple?     ✓
Query 3: How to handle exceptions with try except?              ✓
Query 4: How do I use decorators in Python?                     ✓
Query 5: deepcopy vs shallow copy in Python?                    ✓
Query 6: How to sort a dictionary by value?                     ✓
Query 7: How do I use list comprehensions?                      ✓
Query 8: How to connect to a SQLite database?                   ✓
```

## Project Structure

```
python-qa-assistant/
├── app/
│   ├── main.py             # FastAPI endpoints
│   ├── rag_agent.py        # LangGraph CRAG + Self-RAG agent
│   ├── semantic_cache.py   # Cosine similarity cache
│   └── models.py           # Pydantic schemas
├── data/
│   ├── download_and_preprocess.py
│   └── ingest.py
├── tests/
│   ├── test_queries.py     # 8 test queries
│   ├── test_queries.ipynb  # Notebook version
│   └── results.json        # Test results output
├── vector_store/           # ChromaDB (auto-created on ingest)
├── cache/                  # Semantic cache (auto-created)
├── .env.example
├── requirements.txt
├── Procfile                # For Render/Railway deployment
├── render.yaml             # Render deployment config
└── README.md
```
