"""
Ingest preprocessed Q&A data into ChromaDB vector store.
Run AFTER download_and_preprocess.py:
    python data/ingest.py
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
import chromadb
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

DATA_FILE = Path(__file__).parent / "processed_qa_5k.json"
CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./vector_store")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "stackoverflow_python")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL_ID", "sentence-transformers/all-MiniLM-L6-v2")
BATCH_SIZE = 200


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)
    print(f"Loaded {len(records):,} records")
    return records


def build_documents(records: list) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " "],
    )
    docs = []
    for rec in records:
        chunks = splitter.split_text(rec["document"])
        for i, chunk in enumerate(chunks):
            docs.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "id": rec["id"],
                        "title": rec["title"][:200],
                        "tags": rec["tags"][:200],
                        "question_score": rec["question_score"],
                        "answer_score": rec["answer_score"],
                        "chunk_index": i,
                    },
                )
            )
    print(f"Built {len(docs):,} document chunks")
    return docs


def ingest(docs: list[Document]):
    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True, "batch_size": 256},
    )

    print(f"Ingesting into ChromaDB at {CHROMA_DIR} ...")
    # process in batches to avoid memory issues
    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i : i + BATCH_SIZE]
        if i == 0:
            vectorstore = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                persist_directory=CHROMA_DIR,
                collection_name=COLLECTION_NAME,
            )
        else:
            vectorstore.add_documents(batch)
        print(f"  Ingested {min(i + BATCH_SIZE, len(docs)):,} / {len(docs):,} chunks")

    print(f"Vector store saved to {CHROMA_DIR}")
    print(f"Total vectors: {vectorstore._collection.count()}")


if __name__ == "__main__":
    records = load_data()
    docs = build_documents(records)
    ingest(docs)
    print("\nIngestion complete. Start the API with: uvicorn app.main:app --reload")
