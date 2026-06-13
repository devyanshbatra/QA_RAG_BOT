"""
CRAG + Self-RAG + Multi-Query + HyDE agent using LangGraph.

Flow:
  rewrite_query -> multi_query_retrieve -> grade_documents ->
    if relevant: generate -> grade_answer -> done
    if not relevant: fallback -> generate -> grade_answer -> done
    if hallucination: rewrite_query (retry, max 2 times)

Techniques:
  - Multi-query retrieval: 3 query variants → merged unique docs
  - HyDE: hypothetical answer embedding for better semantic match
  - Hybrid search: semantic (0.6) + BM25 (0.4)
  - Cross-encoder reranking: top-10 → top-3
  - CRAG: grades retrieved docs, falls back if not relevant
  - Self-RAG: grades generated answer, retries if hallucination
  - Confidence score: based on reranker scores + answer grade
"""

import os
import time
from typing import TypedDict, Literal

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers.ensemble import EnsembleRetriever
from langgraph.graph import StateGraph, END

load_dotenv()

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./vector_store")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "stackoverflow_python")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL_ID", "sentence-transformers/all-MiniLM-L6-v2")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
HF_MODEL_ID = os.getenv("LLM_MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.3")
HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN", "")
USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"  # false on Render
TOP_K = int(os.getenv("TOP_K_RETRIEVAL", "10"))
TOP_K_RERANK = int(os.getenv("TOP_K_RERANK", "3"))
MAX_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "512"))
MAX_RETRIES = 2
NUM_QUERIES = 3


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    question: str
    rewritten_query: str
    multi_queries: list          # list of query variants
    hyde_document: str           # hypothetical answer for HyDE
    retrieved_docs: list
    graded_docs: list
    answer: str
    sources: list
    hallucination_score: str
    answer_grade: str
    confidence_score: float
    retry_count: int
    latency_ms: float
    start_time: float


# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

_embeddings = None
_vectorstore = None
_llm = None
_reranker = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True, "batch_size": 256},
        )
    return _embeddings


def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=get_embeddings(),
            collection_name=COLLECTION_NAME,
        )
    return _vectorstore


def get_llm():
    global _llm
    if _llm is None:
        if USE_OLLAMA:
            _llm = ChatOllama(
                model=OLLAMA_MODEL,
                base_url=OLLAMA_BASE_URL,
                temperature=0.1,
                num_predict=MAX_TOKENS,
            )
        else:
            # HuggingFace Inference API — used on Render/cloud deployment
            endpoint = HuggingFaceEndpoint(
                repo_id=HF_MODEL_ID,
                huggingfacehub_api_token=HF_TOKEN,
                temperature=0.1,
                max_new_tokens=MAX_TOKENS,
            )
            _llm = ChatHuggingFace(llm=endpoint)
    return _llm


def get_reranker():
    global _reranker
    if _reranker is None:
        try:
            import torch
            from sentence_transformers import CrossEncoder
            device = "cuda" if torch.cuda.is_available() else "cpu"
            _reranker = CrossEncoder(
                os.getenv("RERANKER_MODEL_ID", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
                device=device,
            )
        except Exception:
            _reranker = None
    return _reranker


def rerank_docs(query: str, docs: list, top_k: int) -> tuple[list, float]:
    """Returns (reranked_docs, avg_confidence_score)."""
    reranker = get_reranker()
    if reranker is None or len(docs) <= top_k:
        return docs[:top_k], 0.5
    pairs = [(query, doc.page_content) for doc in docs]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    top_docs = [doc for _, doc in ranked[:top_k]]
    top_scores = [s for s, _ in ranked[:top_k]]
    # normalize scores to 0-1 confidence
    import numpy as np
    conf = float(np.mean(np.clip(top_scores, 0, 10) / 10))
    return top_docs, conf


def deduplicate_docs(docs: list) -> list:
    """Remove duplicate chunks by content hash."""
    seen = set()
    unique = []
    for doc in docs:
        key = hash(doc.page_content[:100])
        if key not in seen:
            seen.add(key)
            unique.append(doc)
    return unique


# ---------------------------------------------------------------------------
# Graph Nodes
# ---------------------------------------------------------------------------

def node_rewrite_query(state: AgentState) -> AgentState:
    question = state["question"]
    retry = state.get("retry_count", 0)

    if retry == 0:
        prompt = ChatPromptTemplate.from_template(
            "You are a Python expert. Rewrite this question to be more specific and searchable.\n"
            "Original: {question}\n"
            "Rewritten (one line only, no explanation):"
        )
    else:
        prompt = ChatPromptTemplate.from_template(
            "The previous search did not find good results. "
            "Expand this Python question with alternative terms and keywords.\n"
            "Question: {question}\n"
            "Expanded query (one line only, no explanation):"
        )

    chain = prompt | get_llm() | StrOutputParser()
    rewritten = chain.invoke({"question": question}).strip().split("\n")[0]
    return {**state, "rewritten_query": rewritten}


def node_multi_query_hyde(state: AgentState) -> AgentState:
    """
    Multi-Query: generate NUM_QUERIES query variants from the rewritten question.
    HyDE: generate a hypothetical ideal answer, embed it for better semantic search.
    """
    question = state["question"]
    rewritten = state.get("rewritten_query") or question
    retry = state.get("retry_count", 0)

    # On first pass: skip multi-query + HyDE to save 2 LLM calls
    # On retry: expand with multi-query + HyDE for better recall
    if retry == 0:
        return {**state, "multi_queries": [rewritten], "hyde_document": ""}

    # Multi-query: generate 3 different phrasings
    mq_prompt = ChatPromptTemplate.from_template(
        "Generate {n} different search queries for this Python programming question.\n"
        "Each query should approach the topic from a different angle.\n"
        "Question: {question}\n"
        "Output ONLY the queries, one per line, no numbering, no explanation:"
    )
    mq_chain = mq_prompt | get_llm() | StrOutputParser()
    mq_output = mq_chain.invoke({"question": rewritten, "n": NUM_QUERIES}).strip()
    queries = [q.strip() for q in mq_output.split("\n") if q.strip()][:NUM_QUERIES]
    if not queries:
        queries = [rewritten]
    if rewritten not in queries:
        queries.insert(0, rewritten)

    # HyDE: generate a hypothetical answer to embed for retrieval
    hyde_prompt = ChatPromptTemplate.from_template(
        "Write a short, ideal Stack Overflow answer for this Python question. "
        "Be concise and include a code snippet if relevant.\n"
        "Question: {question}\n"
        "Hypothetical answer:"
    )
    hyde_chain = hyde_prompt | get_llm() | StrOutputParser()
    hyde_doc = hyde_chain.invoke({"question": rewritten}).strip()

    return {**state, "multi_queries": queries, "hyde_document": hyde_doc}


def node_hybrid_retrieve(state: AgentState) -> AgentState:
    """
    Hybrid retrieval across all multi-query variants + HyDE document.
    Uses MMR (Maximal Marginal Relevance) for diversity before reranking.
    Deduplicates and reranks final pool.
    """
    queries = state.get("multi_queries") or [state.get("rewritten_query") or state["question"]]
    hyde_doc = state.get("hyde_document", "")
    vs = get_vectorstore()

    # build BM25 once from stored docs
    try:
        raw = vs.get()
        texts = raw.get("documents", [])[:5000]
        bm25_available = bool(texts)
    except Exception:
        bm25_available = False
        texts = []

    all_docs = []

    for query in queries:
        try:
            # MMR retrieval: balances relevance + diversity (lambda=0.7 = 70% relevance, 30% diversity)
            mmr_retriever = vs.as_retriever(
                search_type="mmr",
                search_kwargs={"k": TOP_K, "fetch_k": TOP_K * 3, "lambda_mult": 0.7},
            )
            if bm25_available:
                bm25 = BM25Retriever.from_texts(texts)
                bm25.k = TOP_K
                hybrid = EnsembleRetriever(
                    retrievers=[mmr_retriever, bm25],
                    weights=[0.6, 0.4],
                )
                docs = hybrid.invoke(query)
            else:
                docs = mmr_retriever.invoke(query)
            all_docs.extend(docs)
        except Exception:
            docs = vs.similarity_search(query, k=TOP_K)
            all_docs.extend(docs)

    # HyDE: also retrieve using the hypothetical answer embedding
    if hyde_doc:
        try:
            hyde_docs = vs.similarity_search(hyde_doc, k=TOP_K)
            all_docs.extend(hyde_docs)
        except Exception:
            pass

    # deduplicate then rerank
    unique_docs = deduplicate_docs(all_docs)
    primary_query = queries[0]
    reranked, confidence = rerank_docs(primary_query, unique_docs, TOP_K_RERANK)

    return {**state, "retrieved_docs": reranked, "confidence_score": confidence}


def node_grade_documents(state: AgentState) -> AgentState:
    """Grade docs via cosine similarity — no LLM call needed."""
    question = state["question"]
    docs = state["retrieved_docs"]
    if not docs:
        return {**state, "graded_docs": []}

    import numpy as np
    emb = get_embeddings()
    q_vec = emb.embed_query(question)
    relevant = []
    for doc in docs:
        d_vec = emb.embed_query(doc.page_content[:300])
        score = float(np.dot(q_vec, d_vec) / (np.linalg.norm(q_vec) * np.linalg.norm(d_vec) + 1e-9))
        if score > 0.3:
            relevant.append(doc)
    return {**state, "graded_docs": relevant if relevant else []}


def node_generate_answer(state: AgentState) -> AgentState:
    question = state["question"]
    docs = state.get("graded_docs") or state["retrieved_docs"]

    context = "\n\n---\n\n".join(
        f"[Source {i+1}] {doc.page_content}" for i, doc in enumerate(docs)
    )

    prompt = ChatPromptTemplate.from_template(
        "You are an expert Python programming assistant with deep knowledge of the language.\n"
        "Your job is to give thorough, accurate, beginner-friendly answers to Python questions.\n\n"
        "RULES:\n"
        "1. Always provide a complete explanation — do NOT cut off mid-sentence.\n"
        "2. Always include a working code example with comments.\n"
        "3. Explain WHY, not just HOW — help the user understand the concept.\n"
        "4. Mention common pitfalls or edge cases when relevant.\n"
        "5. Use the provided Stack Overflow context as your primary source.\n"
        "6. Cite sources inline as [Source N] when you use them.\n"
        "7. Structure your answer with: explanation → code example → key points.\n\n"
        "Context from Stack Overflow:\n{context}\n\n"
        "Question: {question}\n\n"
        "Provide a complete, detailed answer:"
    )
    chain = prompt | get_llm() | StrOutputParser()
    answer = chain.invoke({"context": context, "question": question}).strip()

    sources = [
        {
            "title": doc.metadata.get("title", "Stack Overflow"),
            "tags": doc.metadata.get("tags", ""),
            "answer_score": doc.metadata.get("answer_score", 0),
            "snippet": doc.page_content[:200],
        }
        for doc in docs
    ]

    elapsed = (time.time() - state.get("start_time", time.time())) * 1000
    return {**state, "answer": answer, "sources": sources, "latency_ms": elapsed}


def node_grade_answer(state: AgentState) -> AgentState:
    """Grade answer via cosine similarity — no LLM call needed."""
    import numpy as np
    answer = state["answer"]
    docs = state.get("graded_docs") or state["retrieved_docs"]
    conf = state.get("confidence_score", 0.5)

    # check answer has sufficient length and content
    if len(answer.strip()) < 50:
        return {**state, "answer_grade": "hallucination", "confidence_score": max(0.0, conf - 0.3)}

    # cosine similarity between answer and context
    if docs:
        emb = get_embeddings()
        a_vec = np.array(emb.embed_query(answer[:500]))
        ctx_vecs = [np.array(emb.embed_query(d.page_content[:300])) for d in docs[:2]]
        scores = [float(np.dot(a_vec, c) / (np.linalg.norm(a_vec) * np.linalg.norm(c) + 1e-9)) for c in ctx_vecs]
        avg_score = sum(scores) / len(scores)
        grade = "good" if avg_score > 0.25 else "hallucination"
        if grade == "hallucination":
            conf = max(0.0, conf - 0.3)
        final_conf = round(min(1.0, conf + avg_score * 0.3), 2)
    else:
        grade = "good"
        final_conf = round(conf, 2)

    return {**state, "answer_grade": grade, "confidence_score": final_conf}


def node_fallback(state: AgentState) -> AgentState:
    query = state.get("rewritten_query") or state["question"]
    vs = get_vectorstore()
    docs = vs.similarity_search(query, k=TOP_K_RERANK)
    return {**state, "graded_docs": docs, "retry_count": state.get("retry_count", 0) + 1}


# ---------------------------------------------------------------------------
# Conditional edges
# ---------------------------------------------------------------------------

def decide_after_grading(state: AgentState) -> Literal["generate", "fallback"]:
    return "generate" if state["graded_docs"] else "fallback"


def decide_after_answer_grade(state: AgentState) -> Literal["done", "retry"]:
    retry = state.get("retry_count", 0)
    if state["answer_grade"] == "good" or retry >= MAX_RETRIES:
        return "done"
    return "retry"


# ---------------------------------------------------------------------------
# Build Graph
# ---------------------------------------------------------------------------

def build_graph():
    g = StateGraph(AgentState)

    g.add_node("rewrite_query", node_rewrite_query)
    g.add_node("multi_query_hyde", node_multi_query_hyde)
    g.add_node("hybrid_retrieve", node_hybrid_retrieve)
    g.add_node("grade_documents", node_grade_documents)
    g.add_node("generate_answer", node_generate_answer)
    g.add_node("grade_answer", node_grade_answer)
    g.add_node("fallback", node_fallback)

    g.set_entry_point("rewrite_query")
    g.add_edge("rewrite_query", "multi_query_hyde")
    g.add_edge("multi_query_hyde", "hybrid_retrieve")
    g.add_edge("hybrid_retrieve", "grade_documents")
    g.add_conditional_edges(
        "grade_documents",
        decide_after_grading,
        {"generate": "generate_answer", "fallback": "fallback"},
    )
    g.add_edge("fallback", "generate_answer")
    g.add_edge("generate_answer", "grade_answer")
    g.add_conditional_edges(
        "grade_answer",
        decide_after_answer_grade,
        {"done": END, "retry": "rewrite_query"},
    )

    return g.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def ask(question: str) -> dict:
    graph = get_graph()
    initial_state: AgentState = {
        "question": question,
        "rewritten_query": "",
        "multi_queries": [],
        "hyde_document": "",
        "retrieved_docs": [],
        "graded_docs": [],
        "answer": "",
        "sources": [],
        "hallucination_score": "",
        "answer_grade": "",
        "confidence_score": 0.5,
        "retry_count": 0,
        "latency_ms": 0.0,
        "start_time": time.time(),
    }
    result = graph.invoke(initial_state)
    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "rewritten_query": result["rewritten_query"],
        "multi_queries": result.get("multi_queries", []),
        "hyde_document": result.get("hyde_document", ""),
        "answer_grade": result["answer_grade"],
        "hallucination_detected": result["answer_grade"] == "hallucination",
        "confidence_score": result.get("confidence_score", 0.5),
        "retry_count": result["retry_count"],
        "latency_ms": round(result["latency_ms"], 2),
    }
