"""
NyayaFlow - Data Ingestion Pipeline
Supports two modes via .env:
  DEPLOY_MODE=local      → ChromaDB on disk + local SentenceTransformer (default)
  DEPLOY_MODE=production → Qdrant Cloud + HuggingFace Inference API

Usage:
    python ingest.py                     # ingest all PDFs from ./data/pdfs/
    python ingest.py --reset             # wipe collection and re-ingest
    python ingest.py --file path/to.pdf  # ingest a single PDF
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────────────────

DEPLOY_MODE     = os.getenv("DEPLOY_MODE", "local")          # "local" | "production"
PDF_DATA_PATH   = os.getenv("PDF_DATA_PATH", "./data/pdfs")
COLLECTION_NAME = "legal_docs"
CHUNK_SIZE      = 500
CHUNK_OVERLAP   = 50

# Local
CHROMA_DB_PATH  = os.getenv("CHROMA_DB_PATH", "./chroma_db")
LOCAL_EMBED_MODEL = "BAAI/bge-small-en-v1.5"

# Production
QDRANT_URL      = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY", "")
HF_API_KEY      = os.getenv("HF_API_KEY", "")
HF_EMBED_MODEL  = "BAAI/bge-small-en-v1.5"
VECTOR_SIZE     = 384   # bge-small output dimension

print(f"[ingest] Mode: {DEPLOY_MODE.upper()}")


# ─── Embedding functions ──────────────────────────────────────────────────────

def embed_local(texts: list[str]) -> list[list[float]]:
    """Embed using local SentenceTransformer (no internet needed)."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(LOCAL_EMBED_MODEL)
    return model.encode(texts, show_progress_bar=False).tolist()


def embed_huggingface(texts: list[str]) -> list[list[float]]:
    """Embed using HuggingFace Inference API (free tier)."""
    import requests, time

    if not HF_API_KEY:
        raise ValueError("HF_API_KEY not set in .env")

    url = f"https://api-inference.huggingface.co/models/{HF_EMBED_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    all_embeddings = []
    BATCH = 32  # HF free tier: smaller batches to avoid timeouts

    for start in range(0, len(texts), BATCH):
        batch = texts[start:start + BATCH]
        for attempt in range(3):
            resp = requests.post(url, headers=headers, json={"inputs": batch}, timeout=60)
            if resp.status_code == 503:
                # Model loading — wait and retry
                wait = int(resp.json().get("estimated_time", 20))
                print(f"  [hf] Model loading, waiting {wait}s…")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            all_embeddings.extend(resp.json())
            break
        print(f"  [hf] Embedded batch {start // BATCH + 1}/{(len(texts) + BATCH - 1) // BATCH}")

    return all_embeddings


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Route to the right embedding function based on DEPLOY_MODE."""
    if DEPLOY_MODE == "production":
        return embed_huggingface(texts)
    return embed_local(texts)


# ─── Vector DB helpers ────────────────────────────────────────────────────────

def get_local_collection(reset: bool = False):
    """Get ChromaDB collection (local mode)."""
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"[ingest] Dropped existing collection '{COLLECTION_NAME}'")
        except Exception:
            pass
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def get_qdrant_client():
    """Get Qdrant Cloud client (production mode)."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams

    if not QDRANT_URL or not QDRANT_API_KEY:
        raise ValueError("QDRANT_URL and QDRANT_API_KEY must be set in .env for production mode")

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return client


def reset_qdrant(client, reset: bool = False):
    """Create or recreate Qdrant collection."""
    from qdrant_client.models import Distance, VectorParams

    collections = [c.name for c in client.get_collections().collections]

    if reset and COLLECTION_NAME in collections:
        client.delete_collection(COLLECTION_NAME)
        print(f"[ingest] Dropped Qdrant collection '{COLLECTION_NAME}'")

    if COLLECTION_NAME not in collections or reset:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        print(f"[ingest] Created Qdrant collection '{COLLECTION_NAME}'")


# ─── PDF loading & chunking ───────────────────────────────────────────────────

def load_and_chunk(pdf_path: str) -> list:
    """Load a PDF and split into overlapping chunks."""
    from langchain_community.document_loaders import PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    loader   = PyPDFLoader(pdf_path)
    pages    = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    chunks = splitter.split_documents(pages)
    print(f"  → {Path(pdf_path).name}: {len(pages)} pages → {len(chunks)} chunks")
    return chunks


# ─── Store functions ──────────────────────────────────────────────────────────

def store_local(chunks, collection, embeddings):
    """Upsert into ChromaDB."""
    texts = [c.page_content for c in chunks]
    metas = [c.metadata for c in chunks]
    ids   = [f"chunk_{i}" for i in range(len(chunks))]

    BATCH = 64
    for start in range(0, len(texts), BATCH):
        collection.upsert(
            ids=ids[start:start + BATCH],
            documents=texts[start:start + BATCH],
            embeddings=embeddings[start:start + BATCH],
            metadatas=metas[start:start + BATCH],
        )
    print(f"  → Stored {len(texts)} chunks in ChromaDB")


def store_qdrant(chunks, client, embeddings):
    """Upsert into Qdrant Cloud."""
    from qdrant_client.models import PointStruct

    points = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        points.append(PointStruct(
            id=i,
            vector=embedding,
            payload={
                "text":   chunk.page_content,
                "source": chunk.metadata.get("source", "unknown"),
                "page":   chunk.metadata.get("page", 0),
            }
        ))

    BATCH = 100
    for start in range(0, len(points), BATCH):
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points[start:start + BATCH],
        )
    print(f"  → Stored {len(points)} chunks in Qdrant Cloud")


# ─── Main ingestion ───────────────────────────────────────────────────────────

def run_ingestion(pdf_paths: list[str], reset: bool = False):
    # Setup vector DB
    if DEPLOY_MODE == "production":
        qdrant_client = get_qdrant_client()
        reset_qdrant(qdrant_client, reset=reset)
    else:
        collection = get_local_collection(reset=reset)

    # Load and chunk all PDFs
    all_chunks = []
    for pdf_path in pdf_paths:
        if not Path(pdf_path).exists():
            print(f"  ✗ File not found: {pdf_path}")
            continue
        all_chunks.extend(load_and_chunk(pdf_path))

    if not all_chunks:
        print("[ingest] No chunks to store.")
        return

    # Embed
    print(f"[ingest] Embedding {len(all_chunks)} chunks using "
          f"{'HuggingFace API' if DEPLOY_MODE == 'production' else 'local model'}…")
    texts = [c.page_content for c in all_chunks]
    embeddings = get_embeddings(texts)

    # Store
    if DEPLOY_MODE == "production":
        store_qdrant(all_chunks, qdrant_client, embeddings)
        count = qdrant_client.get_collection(COLLECTION_NAME).points_count
    else:
        store_local(all_chunks, collection, embeddings)
        count = collection.count()

    print(f"[ingest] ✓ Done. Collection '{COLLECTION_NAME}' now has {count} vectors.")


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NyayaFlow ingestion pipeline")
    parser.add_argument("--reset", action="store_true", help="Wipe collection before ingesting")
    parser.add_argument("--file",  type=str,            help="Ingest a single PDF file")
    args = parser.parse_args()

    if args.file:
        pdf_list = [args.file]
    else:
        pdf_dir  = Path(PDF_DATA_PATH)
        pdf_list = [str(p) for p in pdf_dir.glob("*.pdf")]
        if not pdf_list:
            print(f"[ingest] No PDFs found in {PDF_DATA_PATH}.")
            sys.exit(0)
        print(f"[ingest] Found {len(pdf_list)} PDFs in {PDF_DATA_PATH}")

    run_ingestion(pdf_list, reset=args.reset)
