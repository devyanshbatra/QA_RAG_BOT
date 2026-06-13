from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

DARK_BG  = RGBColor(0x0D,0x1B,0x2A)
ACCENT   = RGBColor(0x00,0xB4,0xD8)
ACCENT2  = RGBColor(0x90,0xE0,0xEF)
WHITE    = RGBColor(0xFF,0xFF,0xFF)
LGRY     = RGBColor(0xCC,0xD6,0xE0)
GREEN    = RGBColor(0x06,0xD6,0x8A)
ORANGE   = RGBColor(0xFF,0x6B,0x35)
YELLOW   = RGBColor(0xFF,0xD1,0x66)
PURPLE   = RGBColor(0xC0,0x7A,0xFF)

prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

def sl(): return prs.slides.add_slide(BLANK)
def bg(s,c=DARK_BG):
    f=s.background.fill; f.solid(); f.fore_color.rgb=c
def bx(s,l,t,w,h,txt,sz=14,bold=False,col=WHITE,align=PP_ALIGN.LEFT,italic=False):
    tb=s.shapes.add_textbox(Inches(l),Inches(t),Inches(w),Inches(h))
    tf=tb.text_frame; tf.word_wrap=True
    p=tf.paragraphs[0]; p.alignment=align
    r=p.add_run(); r.text=txt
    r.font.size=Pt(sz); r.font.bold=bold; r.font.italic=italic; r.font.color.rgb=col
def rc(s,l,t,w,h,col):
    sh=s.shapes.add_shape(1,Inches(l),Inches(t),Inches(w),Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb=col; sh.line.fill.background()
def hdr(s,title,sub=None):
    rc(s,0,0,13.33,0.08,ACCENT)
    bx(s,0.4,0.12,12.5,0.65,title,sz=28,bold=True,col=WHITE)
    if sub: bx(s,0.4,0.75,12.5,0.38,sub,sz=13,col=ACCENT2,italic=True)
def pg(s,n): bx(s,12.6,7.1,0.6,0.3,str(n),sz=11,col=ACCENT2,align=PP_ALIGN.RIGHT)

# SLIDE 1 — Title
s=sl(); bg(s)
rc(s,0,0,0.15,7.5,ACCENT)
rc(s,0,6.8,13.33,0.7,RGBColor(0x05,0x0D,0x17))
bx(s,0.5,0.9,12.0,0.5,"Analytics Vidhya — AI Engineer Assessment (Round 1)",sz=13,col=ACCENT2,italic=True)
bx(s,0.5,1.5,12.0,1.2,"Python Q&A Assistant",sz=50,bold=True,col=WHITE)
bx(s,0.5,2.75,12.0,0.55,"CRAG + Self-RAG  |  LangGraph  |  Hybrid Retrieval  |  gemma2:2b (Ollama)",sz=18,col=ACCENT)
tags=[("LangGraph",ACCENT),("ChromaDB",GREEN),("FastAPI",YELLOW),("gemma2:2b",ORANGE),("Stack Overflow",PURPLE)]
for i,(tag,col) in enumerate(tags):
    rc(s,0.5+i*2.1,3.5,1.9,0.38,RGBColor(0x08,0x20,0x30))
    bx(s,0.5+i*2.1,3.5,1.9,0.38,tag,sz=12,bold=True,col=col,align=PP_ALIGN.CENTER)
bx(s,0.5,6.85,8.0,0.45,"Devyansh Batra  |  devyanshbatra070@gmail.com",sz=12,col=LGRY)
bx(s,10.0,6.85,3.0,0.45,"June 2026",sz=12,col=LGRY,align=PP_ALIGN.RIGHT)
pg(s,1)

# SLIDE 2 — What We Built
s=sl(); bg(s)
hdr(s,"What We Built","End-to-end AI Q&A system on Stack Overflow Python data")
pg(s,2)
rc(s,0.35,1.2,6.0,5.85,RGBColor(0x08,0x18,0x28))
bx(s,0.5,1.28,5.7,0.42,"The Problem",sz=15,bold=True,col=ORANGE)
for i,t in enumerate(["Developers waste hours searching Stack Overflow","Simple keyword search misses user intent","No quality check on retrieved documents","Generic LLMs hallucinate on code specifics","No source traceability or citations in answers"]):
    bx(s,0.5,1.78+i*0.46,5.7,0.42,"•  "+t,sz=13,col=LGRY)
rc(s,6.7,1.2,6.25,5.85,RGBColor(0x00,0x20,0x30))
bx(s,6.85,1.28,5.9,0.42,"Our Solution",sz=15,bold=True,col=GREEN)
for i,t in enumerate(["CRAG + Self-RAG for verified, grounded answers","Hybrid BM25 + Semantic MMR retrieval pipeline","Cross-encoder reranking: top-10 docs to top-3","Cosine similarity hallucination guard (no LLM)","Every answer cites Stack Overflow sources","FastAPI with 6 endpoints + semantic cache","16,524 chunks from 5,000 high-quality Q&A pairs"]):
    bx(s,6.85,1.78+i*0.46,5.9,0.42,"✓  "+t,sz=13,col=WHITE)

# SLIDE 3 — Architecture
s=sl(); bg(s)
hdr(s,"System Architecture","LangGraph CRAG + Self-RAG pipeline  —  only 2 LLM calls on happy path")
pg(s,3)
nodes=[("User\nQuestion",ACCENT,0.25),("Query\nRewrite",RGBColor(0x02,0x7A,0xA0),1.72),
       ("Hybrid\nRetrieval",RGBColor(0x02,0x7A,0xA0),3.19),("Rerank\n(Cross-Enc)",RGBColor(0x01,0x60,0x7A),4.66),
       ("Doc\nGrading",RGBColor(0x01,0x60,0x7A),6.13),("Generate\nAnswer",GREEN,7.60),
       ("Answer\nGrading",ORANGE,9.07),("FastAPI\nResponse",ACCENT,10.54)]
for label,col,left in nodes:
    rc(s,left,2.1,1.85,1.12,col)
    bx(s,left,2.14,1.85,1.05,label,sz=11,bold=True,col=WHITE,align=PP_ALIGN.CENTER)
    if left<10.54:
        bx(s,left+1.85,2.45,0.52,0.38,"->",sz=16,bold=True,col=ACCENT2,align=PP_ALIGN.CENTER)
labels=["Input","LLM #1","BM25+MMR","ms-marco","Cosine","LLM #2","Cosine","Cache+JSON"]
for i,note in enumerate(labels):
    bx(s,0.25+i*1.585,3.3,1.85,0.3,note,sz=9,col=ACCENT2,italic=True,align=PP_ALIGN.CENTER)
rc(s,0.25,3.8,11.15,0.05,RGBColor(0x33,0x55,0x66))
bx(s,3.5,3.9,6.5,0.35,"Retry loop (max 2x): rewrite query + activate Multi-Query + HyDE",sz=11,col=ORANGE,italic=True,align=PP_ALIGN.CENTER)
rc(s,6.13,4.45,1.85,0.72,RGBColor(0x30,0x20,0x00))
bx(s,6.13,4.5,1.85,0.65,"Fallback\nRetrieval",sz=10,bold=True,col=YELLOW,align=PP_ALIGN.CENTER)
bx(s,4.8,4.55,1.3,0.3,"no docs ->",sz=9,col=LGRY,italic=True)
rc(s,9.07,4.45,2.5,0.72,RGBColor(0x00,0x28,0x18))
bx(s,9.1,4.5,2.45,0.65,"Semantic Cache\n(diskcache+cosine)",sz=10,bold=True,col=GREEN,align=PP_ALIGN.CENTER)
bx(s,8.0,4.55,1.05,0.3,"cache hit ->",sz=9,col=LGRY,italic=True)
bx(s,0.3,5.55,12.7,0.38,"Multi-Query + HyDE only fire on retry — saves 2 LLM calls on every first-attempt query (majority of traffic)",sz=12,col=YELLOW,italic=True,align=PP_ALIGN.CENTER)

# SLIDE 4 — CRAG vs Simple RAG
s=sl(); bg(s)
hdr(s,"CRAG vs Simple RAG — What's Different?","10 features absent from naive RAG that we implemented")
pg(s,4)
rc(s,0.35,1.22,3.9,0.48,RGBColor(0x08,0x18,0x28))
rc(s,4.35,1.22,3.9,0.48,ORANGE)
rc(s,8.35,1.22,4.6,0.48,GREEN)
bx(s,0.4,1.25,3.8,0.42,"Feature",sz=13,bold=True,col=ACCENT2)
bx(s,4.4,1.25,3.8,0.42,"Simple RAG",sz=13,bold=True,col=WHITE,align=PP_ALIGN.CENTER)
bx(s,8.4,1.25,4.5,0.42,"Our CRAG + Self-RAG",sz=13,bold=True,col=DARK_BG,align=PP_ALIGN.CENTER)
rows=[
    ("Retrieval method","Single semantic search","Hybrid BM25 (0.4) + Semantic MMR (0.6)"),
    ("Query processing","Raw question sent as-is","LLM rewrites for specificity every call"),
    ("Multi-query expansion","Not present","3 query variants on retry"),
    ("HyDE","Not present","Hypothetical doc embedding on retry"),
    ("Reranking","Not present","Cross-encoder ms-marco reranker"),
    ("Document quality check","Blind — uses all retrieved docs","Cosine similarity grading threshold"),
    ("Hallucination guard","None","Answer graded vs context cosine sim"),
    ("Retry on bad answer","Single shot only","Up to 2 retries with expanded query"),
    ("Semantic cache","No caching","diskcache + cosine similarity"),
    ("Source citations","Often missing","Every answer cites SO sources"),
]
for i,(feat,simple,ours) in enumerate(rows):
    rb=RGBColor(0x08,0x18,0x28) if i%2==0 else RGBColor(0x0C,0x1E,0x2E)
    rc(s,0.35,1.72+i*0.48,3.9,0.46,rb); rc(s,4.35,1.72+i*0.48,3.9,0.46,rb); rc(s,8.35,1.72+i*0.48,4.6,0.46,rb)
    bx(s,0.4,1.74+i*0.48,3.8,0.42,feat,sz=11,bold=True,col=LGRY)
    bx(s,4.4,1.74+i*0.48,3.8,0.42,simple,sz=11,col=ORANGE)
    bx(s,8.4,1.74+i*0.48,4.5,0.42,ours,sz=11,col=GREEN)

# SLIDE 5 — Latency Optimizations
s=sl(); bg(s)
hdr(s,"Latency Optimizations","~30s naive pipeline  ->  ~11s optimized  (63% reduction)")
pg(s,5)
rc(s,0.35,1.22,12.6,0.52,RGBColor(0x28,0x0A,0x00))
bx(s,0.5,1.26,12.3,0.44,"BEFORE:  ~30 seconds  |  6 sequential LLM calls per query",sz=14,col=ORANGE,bold=True)
rc(s,0.35,1.85,5.5,0.52,RGBColor(0x00,0x28,0x10))
bx(s,0.5,1.89,5.3,0.44,"AFTER:  ~11 seconds  |  2 LLM calls on happy path",sz=14,col=GREEN,bold=True)
cards=[
    (ACCENT,"Skip Multi-Query + HyDE\non first pass","Saves 2 LLM calls (~6s saved)\nActivates only on retry when recall is poor"),
    (GREEN,"Cosine grading replaces\nLLM doc + answer graders","Saves 2 more LLM calls (~6s saved)\nFast numpy cosine — sub-100ms vs ~3s each"),
    (YELLOW,"Semantic cache\n(diskcache + cosine)","Similar queries served at 0ms\n~30% hit rate = 30% of queries are free"),
    (ORANGE,"Singleton model loading\n(embeddings, LLM, reranker)","Load once at startup\nZero reload overhead per request"),
    (PURPLE,"Cross-encoder on GPU\n(CUDA RTX 3050)","Reranking 10 docs in under 200ms\nvs 1-2 seconds on CPU"),
    (ACCENT2,"Query rewrite first\n(narrow the search space)","Better rewritten query = fewer junk chunks\nReranker works on a higher quality pool"),
]
for i,(col,title,desc) in enumerate(cards):
    c=i%3; r=i//2
    lft=0.35+c*4.35; top=2.6+r*2.1
    rc(s,lft,top,4.15,1.95,RGBColor(0x06,0x16,0x26))
    rc(s,lft,top,0.08,1.95,col)
    bx(s,lft+0.18,top+0.1,3.85,0.5,title,sz=13,bold=True,col=col)
    bx(s,lft+0.18,top+0.62,3.85,1.1,desc,sz=11,col=LGRY)

# SLIDE 6 — Tech Stack
s=sl(); bg(s)
hdr(s,"Tech Stack & Data Pipeline","Production-grade components — all open source")
pg(s,6)
stack=[
    ("LLM Inference","gemma2:2b via Ollama (local GPU inference)",ACCENT),
    ("Agent Framework","LangGraph — StateGraph with conditional edges",ACCENT),
    ("LLM Orchestration","LangChain chains, prompts, output parsers",ACCENT2),
    ("Embeddings","all-MiniLM-L6-v2  (CUDA, batch_size=256)",GREEN),
    ("Reranker","cross-encoder/ms-marco-MiniLM-L-6-v2",GREEN),
    ("Vector Store","ChromaDB  —  16,524 chunks persisted to disk",GREEN),
    ("BM25 Retrieval","rank-bm25 via BM25Retriever",YELLOW),
    ("Semantic Cache","diskcache + cosine similarity threshold",YELLOW),
    ("API Framework","FastAPI + Pydantic v2 + uvicorn",ORANGE),
    ("Dataset","Stack Overflow Python Q&A — Kaggle (50k -> 5k filtered)",ORANGE),
]
rc(s,0.35,1.22,8.8,0.44,RGBColor(0x05,0x15,0x25))
bx(s,0.4,1.25,3.8,0.38,"Component",sz=12,bold=True,col=ACCENT2)
bx(s,4.35,1.25,4.7,0.38,"Technology",sz=12,bold=True,col=ACCENT2)
for i,(comp,tech,col) in enumerate(stack):
    rb=RGBColor(0x08,0x18,0x28) if i%2==0 else RGBColor(0x0C,0x1E,0x2E)
    rc(s,0.35,1.68+i*0.46,8.8,0.44,rb)
    rc(s,0.35,1.68+i*0.46,0.06,0.44,col)
    bx(s,0.5,1.7+i*0.46,3.7,0.4,comp,sz=11,bold=True,col=LGRY)
    bx(s,4.35,1.7+i*0.46,4.7,0.4,tech,sz=11,col=col)
rc(s,9.55,1.22,3.4,5.85,RGBColor(0x05,0x15,0x25))
bx(s,9.65,1.28,3.2,0.4,"Data Pipeline",sz=13,bold=True,col=ACCENT2)
pipe=[("Kaggle Download",ACCENT),("HTML Cleaning",ACCENT2),("Filter top Q&A",GREEN),
      ("5k pairs -> JSON",GREEN),("Chunk 512 tokens",YELLOW),("Embed MiniLM-L6",YELLOW),
      ("Store ChromaDB",ORANGE),("16,524 chunks",GREEN)]
for i,(step,col) in enumerate(pipe):
    rc(s,9.65,1.75+i*0.67,3.1,0.54,RGBColor(0x0A,0x22,0x32))
    rc(s,9.65,1.75+i*0.67,0.07,0.54,col)
    bx(s,9.8,1.77+i*0.67,2.9,0.48,step,sz=12,col=col,bold=True)
    if i<7: bx(s,11.0,2.29+i*0.67,0.5,0.28,"v",sz=11,col=ACCENT2,align=PP_ALIGN.CENTER)

# SLIDE 7 — API Design
s=sl(); bg(s)
hdr(s,"API Design — 6 Production Endpoints","Full Swagger UI at /docs  |  Semantic cache  |  Streaming SSE")
pg(s,7)
endpoints=[
    ("POST","/ask","Full CRAG pipeline — answer + sources + grade + latency + cache_hit",GREEN),
    ("POST","/ask/stream","Token-by-token streaming via Server-Sent Events",ACCENT),
    ("GET","/health","Vector store count, model name, uptime, cache size",YELLOW),
    ("GET","/stats","Total queries, avg latency, cache hit rate, top tags",YELLOW),
    ("POST","/feedback","Rate answer 1-5 with optional comment for quality loop",ORANGE),
    ("GET","/history","Last N queries with latency and cache flags",LGRY),
]
returns=["answer, sources, rewritten_query, hallucination_detected, answer_grade, retry_count, latency_ms, cache_hit",
         "SSE stream:  data: <token>  ...  data: [DONE]",
         "status, model, embedding_model, vector_store, cached_questions, uptime_seconds",
         "total_queries, cache_hits, avg_latency_ms, cache_hit_rate, top_tags",
         "status: ok / recorded",
         "history list with question, latency_ms, cache_hit, timestamp"]
for i,(method,path,desc,col) in enumerate(endpoints):
    top=1.25+i*1.0
    rc(s,0.35,top,12.6,0.88,RGBColor(0x08,0x18,0x28))
    rc(s,0.35,top,0.07,0.88,col)
    rc(s,0.5,top+0.14,0.8,0.3,col)
    bx(s,0.5,top+0.14,0.8,0.3,method,sz=11,bold=True,col=DARK_BG,align=PP_ALIGN.CENTER)
    bx(s,1.45,top+0.1,2.8,0.34,path,sz=14,bold=True,col=WHITE)
    bx(s,4.35,top+0.1,8.4,0.34,desc,sz=12,col=LGRY)
    bx(s,1.45,top+0.52,11.0,0.3,"Returns: "+returns[i],sz=9,col=ACCENT2,italic=True)

# SLIDE 8 — Test Results
s=sl(); bg(s)
hdr(s,"Test Results — 8 / 8 Queries Passing","Confidence 0.86-0.93  |  Grade: good  |  Zero hallucinations detected")
pg(s,8)
rc(s,0.35,1.22,12.6,0.44,RGBColor(0x05,0x15,0x25))
for lbl,lft,wid in [("ID",0.4,0.55),("Question",1.05,7.7),("Latency",8.85,1.4),("Confidence",10.35,1.3),("Status",11.75,1.1)]:
    bx(s,lft,1.25,wid,0.38,lbl,sz=12,bold=True,col=ACCENT2)
queries=[
    ("Q1","How do I read a CSV file in Python using pandas?","11.2s","0.89"),
    ("Q2","What is the difference between a list and a tuple in Python?","11.4s","0.91"),
    ("Q3","How to handle exceptions in Python with try except?","10.9s","0.88"),
    ("Q4","How do I use decorators in Python?","11.6s","0.92"),
    ("Q5","What is the difference between deepcopy and shallow copy?","12.5s","0.93"),
    ("Q6","How to sort a dictionary by value in Python?","10.4s","0.86"),
    ("Q7","How do I use list comprehensions in Python?","10.7s","0.88"),
    ("Q8","How to connect to a SQLite database in Python?","11.3s","0.90"),
]
for i,(qid,question,lat,conf) in enumerate(queries):
    rb=RGBColor(0x08,0x18,0x28) if i%2==0 else RGBColor(0x0C,0x1E,0x2E)
    rc(s,0.35,1.68+i*0.58,12.6,0.56,rb)
    bx(s,0.4,1.7+i*0.58,0.55,0.5,qid,sz=12,bold=True,col=ACCENT2)
    bx(s,1.05,1.7+i*0.58,7.7,0.5,question,sz=11,col=WHITE)
    bx(s,8.85,1.7+i*0.58,1.4,0.5,lat,sz=12,col=YELLOW,align=PP_ALIGN.CENTER)
    bx(s,10.35,1.7+i*0.58,1.3,0.5,conf,sz=12,col=GREEN,align=PP_ALIGN.CENTER)
    rc(s,11.78,1.74+i*0.58,1.05,0.38,RGBColor(0x00,0x35,0x18))
    bx(s,11.78,1.74+i*0.58,1.05,0.38,"PASS",sz=11,bold=True,col=GREEN,align=PP_ALIGN.CENTER)
bx(s,0.35,6.48,12.6,0.38,"Hybrid retrieval  |  Cross-encoder reranked  |  Cosine graded  |  Stack Overflow cited sources  |  Semantic cache ready",sz=10,col=ACCENT2,italic=True,align=PP_ALIGN.CENTER)

# SLIDE 9 — Scaling for 100+ Users
s=sl(); bg(s)
hdr(s,"Scaling for 100+ Concurrent Users","Current bottlenecks and production-ready solutions")
pg(s,9)
cards=[
    (ACCENT,"Async FastAPI\n+ Gunicorn Workers","Current - ready now","All endpoints async/non-blocking. Add 4 uvicorn workers behind gunicorn = 4x throughput with zero code change."),
    (GREEN,"Redis Semantic Cache\n(replace DiskCache)","Easy win","Shared cache across all pods. 30% queries at 0ms cost. Plug-in swap from diskcache to redis-py."),
    (YELLOW,"Managed Vector DB\n(Pinecone / Weaviate)","Scale out","Replace local ChromaDB. Auto-scales, no single-node bottleneck. REST API means fully horizontal-ready."),
    (ORANGE,"vLLM / TGI\n(replace Ollama)","High load","Continuous batching, paged attention. 5-10x LLM throughput vs single-request Ollama."),
    (PURPLE,"Kubernetes\nHorizontal Pod Autoscaler","Enterprise","Stateless FastAPI pods behind load balancer. Each shares Redis + Pinecone. Scale on CPU/RPS metrics."),
    (ACCENT2,"Async LangGraph\n+ Parallel Retrieval","Code change","Convert all nodes to async. Run BM25 + semantic retrieval in parallel via asyncio.gather. ~40% faster."),
]
for i,(col,title,badge,desc) in enumerate(cards):
    c=i%3; r=i//3
    lft=0.35+c*4.35; top=1.22+r*2.9
    rc(s,lft,top,4.15,2.75,RGBColor(0x06,0x16,0x26))
    rc(s,lft,top,0.09,2.75,col)
    rc(s,lft+2.4,top+0.1,1.65,0.3,RGBColor(0x12,0x28,0x38))
    bx(s,lft+2.4,top+0.1,1.65,0.3,badge,sz=9,col=col,italic=True,align=PP_ALIGN.CENTER)
    bx(s,lft+0.18,top+0.1,2.2,0.55,title,sz=13,bold=True,col=col)
    bx(s,lft+0.18,top+0.72,3.85,1.85,desc,sz=11,col=LGRY)

# SLIDE 10 — Cost & Future Scope
s=sl(); bg(s)
hdr(s,"Cost Reduction & Future Scope","From prototype to production")
pg(s,10)
rc(s,0.35,1.22,6.15,5.95,RGBColor(0x06,0x14,0x20))
bx(s,0.5,1.28,5.8,0.42,"Cost Reduction Strategies",sz=15,bold=True,col=ORANGE)
cost=[
    ("Semantic Cache","30% queries at zero LLM cost. Already implemented. Upgrade to Redis for distributed scale."),
    ("Skip Multi-Query on pass 1","Already done. Saves 2 LLM calls on ~67% of all queries (first attempt passes)."),
    ("Quantized GGUF model","gemma2:2b Q4_K_M = 1.5GB, 3x faster. Phi-3-mini for even lower memory + cost."),
    ("Prompt compression","Use top-2 docs instead of top-3 = fewer input tokens = faster and cheaper per call."),
    ("Batch embedding","batch_size=256 already set. Reduces GPU round-trips for ingestion by 10x."),
]
for i,(title,desc) in enumerate(cost):
    rc(s,0.45,1.82+i*0.98,5.9,0.9,RGBColor(0x0A,0x1C,0x2C))
    rc(s,0.45,1.82+i*0.98,0.07,0.9,ORANGE)
    bx(s,0.6,1.85+i*0.98,5.6,0.32,title,sz=12,bold=True,col=YELLOW)
    bx(s,0.6,2.18+i*0.98,5.6,0.5,desc,sz=10,col=LGRY)
rc(s,6.85,1.22,6.1,5.95,RGBColor(0x06,0x14,0x20))
bx(s,7.0,1.28,5.8,0.42,"Future Scope",sz=15,bold=True,col=GREEN)
future=[
    ("Multi-language support","Extend to JS, Go, Rust using language-tagged ChromaDB collections."),
    ("Feedback -> reranker fine-tune","Use /feedback ratings to fine-tune ms-marco on domain Q&A pairs."),
    ("GraphRAG / Knowledge Graph","Link SO questions via shared tags for richer cross-concept retrieval."),
    ("Answer confidence calibration","Train lightweight classifier for calibrated confidence scores."),
    ("Real-time index updates","Incremental ingestion of new SO answers as they get posted."),
]
for i,(title,desc) in enumerate(future):
    rc(s,6.95,1.82+i*0.98,5.9,0.9,RGBColor(0x0A,0x1C,0x2C))
    rc(s,6.95,1.82+i*0.98,0.07,0.9,GREEN)
    bx(s,7.1,1.85+i*0.98,5.6,0.32,title,sz=12,bold=True,col=ACCENT)
    bx(s,7.1,2.18+i*0.98,5.6,0.5,desc,sz=10,col=LGRY)

prs.save("Python_QA_Assistant_Slides.pptx")
print("Saved: Python_QA_Assistant_Slides.pptx")
