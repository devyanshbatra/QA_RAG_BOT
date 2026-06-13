"""
8 test queries for the Python Q&A assistant.
Run with: python tests/test_queries.py
Server must be running: uvicorn app.main:app --reload
"""

import sys
import io
import json
import time
import httpx

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:8000"

QUERIES = [
    "How do I read a CSV file in Python using pandas?",
    "What is the difference between a list and a tuple in Python?",
    "How to handle exceptions in Python with try except?",
    "How do I use decorators in Python?",
    "What is the difference between deepcopy and shallow copy in Python?",
    "How to sort a dictionary by value in Python?",
    "How do I use list comprehensions in Python?",
    "How to connect to a SQLite database in Python?",
]


def test_health():
    r = httpx.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    print("✅ /health OK")


def test_query(question: str, idx: int):
    print(f"\n{'='*60}")
    print(f"Query {idx+1}: {question}")
    print("="*60)

    start = time.time()
    r = httpx.post(f"{BASE_URL}/ask", json={"question": question}, timeout=120)
    elapsed = time.time() - start

    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
    data = r.json()

    print(f"Rewritten:   {data.get('rewritten_query', '')}")
    print(f"Confidence:  {data.get('confidence_score', 0):.2f}")
    print(f"Grade:       {data.get('answer_grade', '')}")
    print(f"Hallucin:    {data.get('hallucination_detected', False)}")
    print(f"Retries:     {data.get('retry_count', 0)}")
    print(f"Cache hit:   {data.get('cache_hit', False)}")
    print(f"Latency:     {data.get('latency_ms', 0):.0f}ms (wall: {elapsed*1000:.0f}ms)")
    print(f"\nAnswer:\n{data['answer'][:600]}")
    print(f"\nSources ({len(data.get('sources', []))}):")
    for s in data.get("sources", [])[:3]:
        print(f"  - {s.get('title', '')[:60]}  [score={s.get('answer_score', 0)}]")

    return data


def run_all():
    print("Python Q&A Assistant — 8 Test Queries")
    print(f"Server: {BASE_URL}\n")

    test_health()

    results = []
    passed = 0
    for i, q in enumerate(QUERIES):
        try:
            data = test_query(q, i)
            results.append({"query": q, "status": "pass", **data})
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {e}")
            results.append({"query": q, "status": "fail", "error": str(e)})

    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{len(QUERIES)} passed")
    print("="*60)

    # save results
    with open("tests/results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Results saved to tests/results.json")


if __name__ == "__main__":
    run_all()
