"""
NyayaFlow - RAG Engine
Supports two modes via .env:
  DEPLOY_MODE=local      → ChromaDB + local SentenceTransformer (default)
  DEPLOY_MODE=production → Qdrant Cloud + HuggingFace Inference API

Exposes:
    get_rag_answer(query: str) -> dict
"""

import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────────────────

DEPLOY_MODE     = os.getenv("DEPLOY_MODE", "local")
COLLECTION_NAME = "legal_docs"
GROQ_MODEL      = "llama-3.3-70b-versatile"
TOP_K           = 6

# Local
CHROMA_DB_PATH    = os.getenv("CHROMA_DB_PATH", "./chroma_db")
LOCAL_EMBED_MODEL = "BAAI/bge-small-en-v1.5"

# Production
QDRANT_URL      = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY", "")
HF_API_KEY      = os.getenv("HF_API_KEY", "")
HF_EMBED_MODEL  = "BAAI/bge-small-en-v1.5"

SYSTEM_PROMPT = """You are NyayaFlow, an expert Indian legal consultant and document specialist.

Your role is to assist Indian citizens and small businesses understand their legal rights,
draft simple legal documents, and navigate government schemes.

STRICT RULES:
1. Answer ONLY using the provided legal context below. Do not invent laws or sections.
2. If the answer cannot be found in the context, say: "I could not find specific information
   about this in my legal database. Please consult a qualified advocate for accurate advice."
3. Always cite which Act or law you are referencing (e.g., "Under Section 2(7) of the
   Consumer Protection Act, 2019...").
4. Keep language simple and accessible. Avoid excessive legal jargon.
5. When mentioning monetary penalties or time limits, be precise.
6. End your response with: "⚠️ This is general legal information, not a substitute for
   professional legal advice."
"""


# ─── Embedding ────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_local_embed_model():
    from sentence_transformers import SentenceTransformer
    print("[rag] Loading local embedding model…")
    return SentenceTransformer(LOCAL_EMBED_MODEL)


def _embed_huggingface(text: str) -> list[float]:
    """Single query embedding via HuggingFace Inference API."""
    import requests, time

    url = f"https://api-inference.huggingface.co/models/{HF_EMBED_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    for attempt in range(3):
        resp = requests.post(url, headers=headers, json={"inputs": text}, timeout=30)
        if resp.status_code == 503:
            wait = int(resp.json().get("estimated_time", 20))
            print(f"[rag] HF model loading, waiting {wait}s…")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        result = resp.json()
        # HF returns list of embeddings for list input, or single for string
        if isinstance(result[0], list):
            return result[0]
        return result

    raise RuntimeError("HuggingFace embedding failed after 3 attempts")


def get_query_embedding(query: str) -> list[float]:
    """Get embedding for a single query string."""
    if DEPLOY_MODE == "production":
        return _embed_huggingface(query)
    model = _get_local_embed_model()
    return model.encode([query]).tolist()[0]


# ─── Vector DB ────────────────────────────────────────────────────────────────

_chroma_collection = None

def _get_local_collection(refresh: bool = False):
    global _chroma_collection
    if _chroma_collection is None or refresh:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        _chroma_collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        count = _chroma_collection.count()
        print(f"[rag] ChromaDB connected. {count} vectors.")
        if count == 0:
            print("[rag] WARNING: Collection empty. Run ingest.py first.")
    return _chroma_collection


def refresh_collection():
    """Call this after background ingestion to pick up new chunks."""
    _get_local_collection(refresh=True)


@lru_cache(maxsize=1)
def _get_qdrant_client():
    from qdrant_client import QdrantClient
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    info = client.get_collection(COLLECTION_NAME)
    print(f"[rag] Qdrant Cloud connected. {info.points_count} vectors.")
    return client


# ─── Retrieval ────────────────────────────────────────────────────────────────

def retrieve_context(query: str, top_k: int = TOP_K) -> list[dict]:
    """Embed query and fetch top-k most similar chunks."""
    embedding = get_query_embedding(query)

    if DEPLOY_MODE == "production":
        client  = _get_qdrant_client()
        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=embedding,
            limit=top_k,
            with_payload=True,
        )
        return [
            {
                "text":       r.payload.get("text", ""),
                "source":     r.payload.get("source", "unknown"),
                "page":       r.payload.get("page", "?"),
                "similarity": round(r.score, 4),
            }
            for r in results
        ]
    else:
        collection = _get_local_collection()
        results = collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        return [
            {
                "text":       doc,
                "source":     meta.get("source", "unknown"),
                "page":       meta.get("page", "?"),
                "similarity": round(1 - dist, 4),
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]


# ─── LLM ─────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_groq_client():
    from groq import Groq
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in .env")
    print("[rag] Groq client initialized.")
    return Groq(api_key=api_key)


def build_context_block(chunks: list[dict]) -> str:
    if not chunks:
        return "No relevant legal context found."
    parts = []
    for i, chunk in enumerate(chunks, 1):
        source = os.path.basename(chunk["source"]) if chunk["source"] != "unknown" else "Legal Database"
        parts.append(
            f"[Context {i} | Source: {source} | Page: {chunk['page']} | "
            f"Relevance: {chunk['similarity']}]\n{chunk['text']}"
        )
    return "\n\n---\n\n".join(parts)


def call_groq(query: str, context_block: str) -> str:
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"LEGAL CONTEXT:\n{context_block}\n\nUSER QUESTION:\n{query}"},
        ],
        temperature=0.2,
        max_tokens=1024,
    )
    return response.choices[0].message.content


# ─── Public interface ─────────────────────────────────────────────────────────

def get_rag_answer(query: str) -> dict:
    if not query or not query.strip():
        return {"error": "Query cannot be empty."}

    chunks        = retrieve_context(query)
    context_block = build_context_block(chunks)
    answer        = call_groq(query, context_block)

    return {
        "answer":  answer,
        "sources": [
            {"source": c["source"], "page": c["page"], "similarity": c["similarity"]}
            for c in chunks
        ],
        "query": query,
    }


# ─── CLI test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    test_query = "What are my rights as a consumer if I receive a defective product?"
    print(f"[test] Query: {test_query}\n")
    print(json.dumps(get_rag_answer(test_query), indent=2, ensure_ascii=False))