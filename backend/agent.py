"""
NyayaFlow - Legal Agent v3
Flow:
  1. RAG retrieves top-6 chunks from DB
  2. LLM judges if chunks actually answer the question
  3. YES → answer from DB (fast path)
  4. NO  → DuckDuckGo finds the PDF on indiacode.nic.in (free, no API key)
         → Download PDF → extract text → answer
         → Save PDF + ingest to DB in background (learns permanently)

Exposes:
    get_agent_answer(query: str) -> dict
"""

import os
import re
import time
import threading
import requests
from pathlib import Path
from dotenv import load_dotenv
from source_links import get_source_url, save_source_url

load_dotenv()

GROQ_MODEL    = "openai/gpt-oss-120b"
PDF_SAVE_PATH = os.getenv("PDF_DATA_PATH", "./data/pdfs")


# ─── Groq client ─────────────────────────────────────────────────────────────

def _groq():
    from groq import Groq
    return Groq(api_key=os.getenv("GROQ_API_KEY"))


# ─── Step 1: Retrieve chunks from DB ─────────────────────────────────────────

def retrieve_chunks(query: str) -> list[dict]:
    from rag import retrieve_context
    return retrieve_context(query, top_k=6)


# ─── Step 1b: Targeted DB search by law name ────────────────────────────────

def search_db_by_law(query: str, law_name: str) -> list[dict]:
    """Search DB specifically for chunks from the identified law."""
    from rag import get_query_embedding, DEPLOY_MODE, COLLECTION_NAME
    
    # Normalize law name for filename matching
    safe = law_name.lower().replace(" ", "_").replace(",", "")
    year = ''.join(filter(str.isdigit, law_name))
    
    try:
        if DEPLOY_MODE != "production":
            from rag import _get_local_collection
            collection = _get_local_collection()
            embedding  = get_query_embedding(query)
            
            # Build list of possible filenames for this law
            import os
            all_files = os.listdir("./data/pdfs")
            # Match files to law name — deduplicated, exact year match prioritized
            seen = set()
            matching = []
            for f in all_files:
                if not f.endswith('.pdf'):
                    continue
                # Exact year match (e.g. "2000" must appear as standalone in filename)
                year_match = year and (
                    f"_{year}." in f or f"_{year}_" in f or f.startswith(year)
                )
                # Keyword match — 2+ meaningful words from law name in filename
                kw_match = sum(
                    1 for w in law_name.split()
                    if len(w) > 3 and w.lower() in f.lower()
                ) >= 2

                if year_match or kw_match:
                    # Try both path formats ChromaDB might store
                    for prefix in ["data/pdfs/", "./data/pdfs/"]:
                        path = f"{prefix}{f}"
                        if path not in seen:
                            seen.add(path)
                            matching.append(path)
            print(f"[agent] Matching files for '{law_name}': {[f.split('/')[-1] for f in matching]}")

            if not matching:
                return []

            # Query with exact source match for each matching file
            all_chunks = []
            for source_path in matching[:3]:  # max 3 files
                try:
                    res = collection.query(
                        query_embeddings=[embedding],
                        n_results=3,
                        where={"source": {"$eq": source_path}},
                        include=["documents", "metadatas", "distances"],
                    )
                    if res["documents"][0]:
                        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
                            all_chunks.append({
                                "text": doc,
                                "source": meta.get("source", "unknown"),
                                "page": meta.get("page", "?"),
                                "similarity": round(1 - dist, 4),
                            })
                except Exception:
                    pass
            results = {"documents": [[c["text"] for c in all_chunks]],
                      "metadatas": [[{"source": c["source"], "page": c["page"]} for c in all_chunks]],
                      "distances": [[1 - c["similarity"] for c in all_chunks]]}
            
            chunks = [
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
            
            if chunks:
                print(f"[agent] Targeted DB search found {len(chunks)} chunks for year {year}")
                return chunks
    except Exception as e:
        print(f"[agent] Targeted search failed: {e}")
    
    return []


# ─── Step 2: LLM relevance check ─────────────────────────────────────────────

def is_context_relevant(query: str, chunks: list[dict]) -> bool:
    """
    Ask LLM: does the retrieved context actually answer this question?
    Returns True (use DB) or False (activate agent).
    """
    if not chunks:
        print("[agent] No chunks in DB → activating agent")
        return False

    sources = list(set([c["source"].split("/")[-1] for c in chunks]))
    print(f"[agent] Checking sources: {sources}")
    context = "\n\n".join([c["text"] for c in chunks])

    response = _groq().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a legal relevance checker for Indian law. "
                    "Answer ONLY with 'YES' or 'NO'. Nothing else. "
                    "Say YES if the context contains ANY information from the "
                    "correct Indian Act that relates to the question, even partially. "
                    "Say NO only if the context is entirely from a different unrelated law."
                ),
            },
            {
                "role": "user",
                "content": f"QUESTION: {query}\n\nCONTEXT:\n{context[:3000]}",
            },
        ],
        max_tokens=3,
        temperature=0,
    )

    answer = response.choices[0].message.content.strip().upper()
    print(f"[agent] Context relevant? {answer}")
    return "YES" in answer


# ─── Step 3: Identify which law is needed ────────────────────────────────────

def identify_relevant_law(query: str) -> str:
    """Ask Groq which Indian Act covers this query."""
    response = _groq().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an Indian legal expert. Given a legal question, "
                    "respond with ONLY the exact name of the single most relevant "
                    "Indian Central Act, including the year.\n"
                    "Examples:\n"
                    "- Information Technology Act 2000\n"
                    "- Consumer Protection Act 2019\n"
                    "- Bharatiya Nyaya Sanhita 2023\n"
                    "- Transfer of Property Act 1882\n"
                    "- Right to Information Act 2005\n"
                    "- Motor Vehicles Act 1988\n"
                    "Respond with ONLY the act name. Nothing else."
                ),
            },
            {"role": "user", "content": query},
        ],
        max_tokens=20,
        temperature=0,
    )
    law_name = response.choices[0].message.content.strip()
    print(f"[agent] Identified law: {law_name}")
    return law_name


# ─── Step 4: DuckDuckGo Search for PDF ───────────────────────────────────────

def duckduckgo_search_pdf(law_name: str) -> str | None:
    """
    Use DuckDuckGo to find the PDF of the act on indiacode.nic.in
    Completely free, no API key needed.
    Returns direct PDF URL or None.
    """
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        queries = [
            f"{law_name} site:indiacode.nic.in",
            f"{law_name} bare act site:indiacode.nic.in",
            f"{law_name} site:legislative.gov.in",
            f"{law_name} bare act full text pdf site:prsindia.org",
        ]

        with DDGS() as ddgs:
            for query in queries:
                print(f"[agent] DuckDuckGo searching: {query}")
                try:
                    results = list(ddgs.text(query, max_results=8))
                    for r in results:
                        url = r.get("href", "")
                        if url.lower().endswith(".pdf"):
                            print(f"[agent] Found direct PDF: {url}")
                            return url
                        if "bitstream" in url and "indiacode" in url:
                            print(f"[agent] Found bitstream: {url}")
                            return url
                        if "indiacode.nic.in/handle" in url:
                            print(f"[agent] Found act page, extracting PDF...")
                            pdf = extract_pdf_from_page(url)
                            if pdf:
                                return pdf
                        if "legislative.gov.in" in url and ".pdf" in url.lower():
                            print(f"[agent] Found legislative PDF: {url}")
                            return url
                    time.sleep(1)
                except Exception as e:
                    print(f"[agent] Query failed: {e}")
                    continue

        print("[agent] DuckDuckGo found no PDF")
        return None

    except ImportError:
        print("[agent] duckduckgo-search not installed. Run: pip install duckduckgo-search")
        return None
    except Exception as e:
        print(f"[agent] DuckDuckGo search failed: {e}")
        return None


def extract_pdf_from_page(page_url: str) -> str | None:
    """Visit an indiacode act page and extract the PDF download link."""
    try:
        from bs4 import BeautifulSoup
        resp = requests.get(
            page_url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
            timeout=15,
        )
        soup = BeautifulSoup(resp.text, "html.parser")

        # indiacode PDF links always contain 'bitstream' and end in .pdf
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "bitstream" in href and href.lower().endswith(".pdf"):
                if href.startswith("http"):
                    return href
                return "https://www.indiacode.nic.in" + href

        # Fallback: any .pdf link
        for a in soup.find_all("a", href=True):
            if a["href"].lower().endswith(".pdf"):
                href = a["href"]
                if href.startswith("http"):
                    return href
                return "https://www.indiacode.nic.in" + href

    except Exception as e:
        print(f"[agent] Page extraction failed: {e}")
    return None


def validate_extracted_text(text: str, law_name: str) -> bool:
    """
    Sanity-check that extracted PDF text actually relates to the requested Act —
    prevents ingesting wrong/unrelated documents from low-quality mirror sites
    (e.g. gazette notifications, unrelated Acts).
    """
    if len(text) < 5000:
        print(f"[agent] Validation failed: only {len(text)} chars — too short for a full Act")
        return False

    text_lower = text.lower()
    keywords = [w.lower() for w in law_name.split() if len(w) > 3 and not w.isdigit()]
    matches  = [kw for kw in keywords if kw in text_lower]

    if len(matches) < max(1, len(keywords) // 2):
        print(f"[agent] Validation failed: only {matches} of {keywords} found in fetched text")
        return False

    return True

# ─── Step 5: Download PDF + extract text ─────────────────────────────────────

def download_and_extract(pdf_url: str, save_name: str, law_name: str = None) -> str | None:
    """Download PDF, save permanently, return extracted text."""
    try:
        resp = requests.get(
            pdf_url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=60,
        )

        if len(resp.content) < 10_000:
            print(f"[agent] File too small ({len(resp.content)}B) — not valid PDF")
            return None

        if resp.content[:4] != b'%PDF':
            print("[agent] Downloaded file is not a PDF")
            return None

        # Cap extremely large PDFs (e.g. Income Tax Act can be 10MB+, hundreds of pages)
        MAX_PDF_BYTES = 8 * 1024 * 1024  # 8 MB
        if len(resp.content) > MAX_PDF_BYTES:
            print(f"[agent] PDF too large ({len(resp.content)//1024//1024}MB) — extracting first 200 pages only")

        # Save permanently
        pdf_path = Path(PDF_SAVE_PATH) / save_name
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(resp.content)
        print(f"[agent] Saved: {pdf_path} ({len(resp.content)//1024}KB)")

        # Extract text
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        max_pages = 200 if len(resp.content) > MAX_PDF_BYTES else len(reader.pages)
        pages  = []
        for page in reader.pages[:max_pages]:
            text = page.extract_text()
            if text and text.strip():
                pages.append(text)

        full_text = "\n\n".join(pages)

        if len(full_text) < 500:
            print("[agent] Text too short — PDF may be scanned/image-based")
            pdf_path.unlink(missing_ok=True)
            return None

        if law_name and not validate_extracted_text(full_text, law_name):
            print(f"[agent] Downloaded PDF does not match '{law_name}' — discarding")
            pdf_path.unlink(missing_ok=True)
            return None

        print(f"[agent] Extracted {len(full_text)} chars from {len(pages)} pages")
        return full_text

    except Exception as e:
        print(f"[agent] Download/extract failed: {e}")
        return None


# ─── Step 6: Ingest to DB in background ──────────────────────────────────────

def ingest_pdf_background(pdf_path: str):
    """Chunk + embed + store into existing DB. Runs in background thread."""
    try:
        from ingest import load_and_chunk, get_embeddings
        from rag import DEPLOY_MODE
        print(f"[agent] Background ingesting: {pdf_path}")

        chunks = load_and_chunk(pdf_path)
        if not chunks:
            return

        texts      = [c.page_content for c in chunks]
        embeddings = get_embeddings(texts)

        if DEPLOY_MODE == "production":
            from rag import _get_qdrant_client
            from qdrant_client.models import PointStruct
            client = _get_qdrant_client()
            count  = client.get_collection("legal_docs").points_count
            client.upsert(
                collection_name="legal_docs",
                points=[
                    PointStruct(
                        id=count + i,
                        vector=emb,
                        payload={
                            "text":   c.page_content,
                            "source": pdf_path,
                            "page":   c.metadata.get("page", 0),
                        },
                    )
                    for i, (c, emb) in enumerate(zip(chunks, embeddings))
                ],
            )
        else:
            from rag import _get_local_collection
            collection = _get_local_collection()
            count      = collection.count()
            collection.upsert(
                ids=[f"chunk_{count + i}" for i in range(len(chunks))],
                documents=texts,
                embeddings=embeddings,
                metadatas=[c.metadata for c in chunks],
            )

        print(f"[agent] ✓ Ingested {len(chunks)} new chunks. DB now smarter.")
        from rag import refresh_collection
        refresh_collection()

    except Exception as e:
        print(f"[agent] Background ingestion failed: {e}")

# ─── Step 6b: Targeted retrieval within freshly fetched text ────────────────

def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 300) -> list[str]:
    """Split text into overlapping chunks for relevance-based retrieval."""
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunks.append(text[start:end])
        if end == n:
            break
        start = end - overlap
    return chunks


def find_relevant_sections(query: str, text: str, top_k: int = 8, chunk_size: int = 2000) -> str:
    MAX_CHUNKS_TO_EMBED = 80

    chunks = chunk_text(text, chunk_size=chunk_size)

    if len(chunks) <= top_k:
        return text

    if len(chunks) > MAX_CHUNKS_TO_EMBED:
        print(f"[agent] Document has {len(chunks)} chunks — capping to first {MAX_CHUNKS_TO_EMBED} for embedding")
        chunks = chunks[:MAX_CHUNKS_TO_EMBED]

    print(f"[agent] Splitting fetched text into {len(chunks)} chunks for relevance search")

    try:
        import numpy as np
        import time
        from rag import get_query_embedding
        from ingest import get_embeddings

        # Retry up to 3 times if Cohere is rate limited
        for attempt in range(3):
            try:
                chunk_embeddings = np.array(get_embeddings(chunks))
                break
            except Exception as e:
                if attempt < 2:
                    wait = (attempt + 1) * 15
                    print(f"[agent] Embedding attempt {attempt+1} failed ({e}), retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise

        query_embedding = np.array(get_query_embedding(query))

        norms = np.linalg.norm(chunk_embeddings, axis=1) * np.linalg.norm(query_embedding)
        norms[norms == 0] = 1e-10
        sims = chunk_embeddings @ query_embedding / norms

        top_indices = np.argsort(sims)[::-1][:top_k]
        top_indices = sorted(top_indices.tolist())

        selected = [chunks[i] for i in top_indices]
        print(f"[agent] Selected {len(selected)}/{len(chunks)} most relevant chunks "
              f"(scores: {[round(float(sims[i]), 3) for i in top_indices]})")
        return "\n\n[...]\n\n".join(selected)

    except Exception as e:
        print(f"[agent] Relevance chunking failed ({e}), falling back to larger truncation")
        return text[:40000]
    
# ─── Step 7: Answer from scraped text ────────────────────────────────────────

def answer_from_text(query: str, text: str, law_name: str) -> str:
    """Ask Groq to answer from freshly downloaded legal text."""
    truncated = find_relevant_sections(query, text)

    response = _groq().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are NyayaFlow, an expert Indian legal consultant. "
                    "Answer the user's question using ONLY the provided legal text. "
                    "Cite specific section numbers where possible. "
                    "Keep language simple and accessible. "
                    "If the provided text does not contain the specific section or "
                    "information needed to answer the question, say so directly and "
                    "recommend consulting a qualified advocate — do NOT supply the "
                    "answer from your own general knowledge instead. "
                    "NEVER mention 'Context 1', 'Context 2' or any context numbers. "
                    "Just cite the law and section directly. "
                    "End with: '⚠️ This is general legal information, not a substitute "
                    "for professional legal advice.'"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"LAW: {law_name}\n\n"
                    f"LEGAL TEXT:\n{truncated}\n\n"
                    f"QUESTION: {query}"
                ),
            },
        ],
        temperature=0.2,
        max_tokens=1024,
    )
    return response.choices[0].message.content

def answer_from_text_stream(query: str, text: str, law_name: str):
    """Streaming version of answer_from_text — yields tokens."""
    truncated = find_relevant_sections(query, text)

    stream = _groq().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are NyayaFlow, an expert Indian legal consultant. "
                    "Answer the user's question using ONLY the provided legal text. "
                    "Cite specific section numbers where possible. "
                    "Keep language simple and accessible. "
                    "If the provided text does not contain the specific section or "
                    "information needed to answer the question, say so directly and "
                    "recommend consulting a qualified advocate — do NOT supply the "
                    "answer from your own general knowledge instead. "
                    "NEVER mention 'Context 1', 'Context 2' or any context numbers. "
                    "Just cite the law and section directly. "
                    "End with: '⚠️ This is general legal information, not a substitute "
                    "for professional legal advice.'"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"LAW: {law_name}\n\n"
                    f"LEGAL TEXT:\n{truncated}\n\n"
                    f"QUESTION: {query}"
                ),
            },
        ],
        temperature=0.2,
        max_tokens=1024,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
# ─── Main public interface ────────────────────────────────────────────────────

def get_agent_answer(query: str) -> dict:
    """
    Full pipeline: DB check → LLM relevance → DuckDuckGo → Download → Answer → Ingest
    """
    # ── Step 1+2: Try DB first ────────────────────────────────────────────────
    chunks   = retrieve_chunks(query)
    
    # Auto-trigger agent if similarity scores are too low (wrong act retrieved)
    max_similarity = max((c.get("similarity", 0) for c in chunks), default=0)
    print(f"[agent] Max similarity: {max_similarity:.3f}")
    if max_similarity < 0.65:
        print(f"[agent] Low similarity ({max_similarity:.3f}) → skipping DB, activating agent directly")
        relevant = False
    else:
        relevant = is_context_relevant(query, chunks)

    if relevant:
        from rag import build_context_block, call_groq
        print("[agent] Using DB answer")
        answer = call_groq(query, build_context_block(chunks))
        return {
            "answer":      answer,
            "sources":     [
                {"source": c["source"], "page": c["page"], "similarity": c["similarity"], "url": get_source_url(c["source"])}
                for c in chunks
            ],
            "query":       query,
            "used_agent":  False,
            "law_fetched": None,
        }

    # ── Agent path ────────────────────────────────────────────────────────────
    print("[agent] DB insufficient → activating agent")

    law_name = identify_relevant_law(query)

    # Try targeted DB search first — search by law year/name
    targeted_chunks = search_db_by_law(query, law_name)
    if targeted_chunks:
        # If targeted search found chunks from the correct law file, trust it
        # Skip relevance check — we already know these are from the right law
        from rag import build_context_block, call_groq
        print("[agent] Targeted DB search succeeded → using DB directly")
        answer = call_groq(query, build_context_block(targeted_chunks))
        return {
            "answer":      answer,
            "sources":     [
                {"source": c["source"], "page": c["page"], "similarity": c["similarity"], "url": get_source_url(c["source"])}
                for c in targeted_chunks
            ],
            "query":       query,
            "used_agent":  False,
            "law_fetched": None,
        }

    pdf_url  = duckduckgo_search_pdf(law_name)

    if not pdf_url:
        print("[agent] Could not find PDF → falling back to DB")
        from rag import build_context_block, call_groq
        return {
            "answer":      call_groq(query, build_context_block(chunks)),
            "sources":     [
                {"source": c["source"], "page": c["page"], "similarity": c["similarity"], "url": get_source_url(c["source"])}
                for c in chunks
            ],
            "query":       query,
            "used_agent":  True,
            "law_fetched": None,
            "agent_note":  f"Could not locate {law_name} PDF online",
        }

    safe_name = re.sub(r"[^\w\s-]", "", law_name).strip().replace(" ", "_") + ".pdf"
    pdf_path_check = Path(PDF_SAVE_PATH) / safe_name

    # Record this Act's official source URL for future citations
    save_source_url(safe_name, pdf_url)

    # If already downloaded, skip download — just extract text
    if pdf_path_check.exists():
        print(f"[agent] PDF already exists locally: {safe_name}")
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path_check))
        pages  = [p.extract_text() for p in reader.pages if p.extract_text()]
        pdf_text = "\n\n".join(pages) if pages else None
    else:
        pdf_text = download_and_extract(pdf_url, safe_name, law_name)

    if not pdf_text:
        print("[agent] Extraction failed → falling back to DB")
        from rag import build_context_block, call_groq
        return {
            "answer":      call_groq(query, build_context_block(chunks)),
            "sources":     [
                {"source": c["source"], "page": c["page"], "similarity": c["similarity"], "url": get_source_url(c["source"])}
                for c in chunks
            ],
            "query":       query,
            "used_agent":  True,
            "law_fetched": None,
        }

    answer = answer_from_text(query, pdf_text, law_name)

    # Ingest in background only if not already in DB
    pdf_path = str(Path(PDF_SAVE_PATH) / safe_name)
    if not pdf_path_check.exists() or "used_agent" not in locals():
        threading.Thread(
            target=ingest_pdf_background,
            args=(pdf_path,),
            daemon=True,
        ).start()
    else:
        # Already ingested — just refresh collection
        from rag import refresh_collection
        refresh_collection()

    return {
        "answer":      answer,
        "sources":     [{"source": law_name, "page": "live", "similarity": 1.0, "url": pdf_url}],
        "query":       query,
        "used_agent":  True,
        "law_fetched": law_name,
    }

def get_agent_answer_stream(query: str):
    """
    Streaming version of get_agent_answer. Yields dicts:
      {"type": "status",  "message": "..."}
      {"type": "token",   "content": "..."}
      {"type": "done",    "sources": [...], "used_agent": bool, "law_fetched": str|None}
    """
    yield {"type": "status", "message": "Checking legal database…"}

    chunks = retrieve_chunks(query)
    max_similarity = max((c.get("similarity", 0) for c in chunks), default=0)
    print(f"[agent-stream] Max similarity: {max_similarity:.3f}")

    if max_similarity < 0.65:
        relevant = False
    else:
        relevant = is_context_relevant(query, chunks)

    if relevant:
        from rag import build_context_block, call_groq_stream
        for token in call_groq_stream(query, build_context_block(chunks)):
            yield {"type": "token", "content": token}
        yield {
            "type": "done",
            "sources": [
                {"source": c["source"], "page": c["page"], "similarity": c["similarity"], "url": get_source_url(c["source"])}
                for c in chunks
            ],
            "used_agent": False,
            "law_fetched": None,
        }
        return

    # ── Agent path ──────────────────────────────────────────────────────────
    yield {"type": "status", "message": "Identifying the relevant Act…"}
    law_name = identify_relevant_law(query)

    targeted_chunks = search_db_by_law(query, law_name)
    if targeted_chunks:
        from rag import build_context_block, call_groq_stream
        yield {"type": "status", "message": f"Found relevant sections in {law_name}…"}
        for token in call_groq_stream(query, build_context_block(targeted_chunks)):
            yield {"type": "token", "content": token}
        yield {
            "type": "done",
            "sources": [
                {"source": c["source"], "page": c["page"], "similarity": c["similarity"], "url": get_source_url(c["source"])}
                for c in targeted_chunks
            ],
            "used_agent": False,
            "law_fetched": None,
        }
        return

    yield {"type": "status", "message": f"Searching indiacode.nic.in for {law_name}…"}
    try:
        pdf_url = duckduckgo_search_pdf(law_name)
    except Exception as e:
        print(f"[agent-stream] DuckDuckGo failed: {e}")
        pdf_url = None

    if not pdf_url:
        from rag import build_context_block, call_groq_stream
        yield {"type": "status", "message": "Could not find the Act online — answering from existing database…"}
        for token in call_groq_stream(query, build_context_block(chunks)):
            yield {"type": "token", "content": token}
        yield {
            "type": "done",
            "sources": [
                {"source": c["source"], "page": c["page"], "similarity": c["similarity"], "url": get_source_url(c["source"])}
                for c in chunks
            ],
            "used_agent": True,
            "law_fetched": None,
        }
        return

    safe_name = re.sub(r"[^\w\s-]", "", law_name).strip().replace(" ", "_") + ".pdf"
    pdf_path_check = Path(PDF_SAVE_PATH) / safe_name
    save_source_url(safe_name, pdf_url)

    if pdf_path_check.exists():
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path_check))
        pages  = [p.extract_text() for p in reader.pages if p.extract_text()]
        pdf_text = "\n\n".join(pages) if pages else None
    else:
        yield {"type": "status", "message": f"Downloading {law_name}…"}
        try:
            pdf_text = download_and_extract(pdf_url, safe_name, law_name)
        except Exception as e:
            print(f"[agent-stream] Download failed: {e}")
            pdf_text = None

    if not pdf_text:
        from rag import build_context_block, call_groq_stream
        yield {"type": "status", "message": "Could not extract the Act — answering from existing database…"}
        for token in call_groq_stream(query, build_context_block(chunks)):
            yield {"type": "token", "content": token}
        yield {
            "type": "done",
            "sources": [
                {"source": c["source"], "page": c["page"], "similarity": c["similarity"], "url": get_source_url(c["source"])}
                for c in chunks
            ],
            "used_agent": True,
            "law_fetched": None,
        }
        return

    yield {"type": "status", "message": f"Reading {law_name}…"}
    for token in answer_from_text_stream(query, pdf_text, law_name):
        yield {"type": "token", "content": token}

    pdf_path = str(Path(PDF_SAVE_PATH) / safe_name)
    threading.Thread(target=ingest_pdf_background, args=(pdf_path,), daemon=True).start()

    yield {
        "type": "done",
        "sources": [{"source": law_name, "page": "live", "similarity": 1.0, "url": pdf_url}],
        "used_agent": True,
        "law_fetched": law_name,
    }


# ─── CLI test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json, sys
    q = sys.argv[1] if len(sys.argv) > 1 else "What is the punishment for cybercrime in India?"
    print(f"\n[test] Query: {q}\n")
    r = get_agent_answer(q)
    print(f"\n[answer]\n{r['answer'][:600]}")
    print(f"\n[used_agent] {r['used_agent']}")
    print(f"[law_fetched] {r['law_fetched']}")