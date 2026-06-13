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

load_dotenv()

GROQ_MODEL    = "llama-3.3-70b-versatile"
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
            f"{law_name} indiacode.nic.in pdf download",
            f"{law_name} site:legislative.gov.in",
            f"{law_name} india act pdf download official",
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


# ─── Step 5: Download PDF + extract text ─────────────────────────────────────

def download_and_extract(pdf_url: str, save_name: str) -> str | None:
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

        # Save permanently
        pdf_path = Path(PDF_SAVE_PATH) / save_name
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(resp.content)
        print(f"[agent] Saved: {pdf_path} ({len(resp.content)//1024}KB)")

        # Extract text
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        pages  = []
        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                pages.append(text)

        full_text = "\n\n".join(pages)

        if len(full_text) < 500:
            print("[agent] Text too short — PDF may be scanned/image-based")
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
        from ingest import load_and_chunk, get_embeddings, DEPLOY_MODE
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
        # Refresh collection cache so next query sees new chunks
        from rag import refresh_collection
        refresh_collection()

    except Exception as e:
        print(f"[agent] Background ingestion failed: {e}")


# ─── Step 7: Answer from scraped text ────────────────────────────────────────

def answer_from_text(query: str, text: str, law_name: str) -> str:
    """Ask Groq to answer from freshly downloaded legal text."""
    truncated = text[:12000]

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
    if max_similarity < 0.60:
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
            "sources":     [{"source": c["source"], "page": c["page"], "similarity": c["similarity"]} for c in chunks],
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
            "sources":     [{"source": c["source"], "page": c["page"], "similarity": c["similarity"]} for c in targeted_chunks],
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
            "sources":     [{"source": c["source"], "page": c["page"], "similarity": c["similarity"]} for c in chunks],
            "query":       query,
            "used_agent":  True,
            "law_fetched": None,
            "agent_note":  f"Could not locate {law_name} PDF online",
        }

    safe_name = re.sub(r"[^\w\s-]", "", law_name).strip().replace(" ", "_") + ".pdf"
    pdf_path_check = Path(PDF_SAVE_PATH) / safe_name

    # If already downloaded, skip download — just extract text
    if pdf_path_check.exists():
        print(f"[agent] PDF already exists locally: {safe_name}")
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path_check))
        pages  = [p.extract_text() for p in reader.pages if p.extract_text()]
        pdf_text = "\n\n".join(pages) if pages else None
    else:
        pdf_text = download_and_extract(pdf_url, safe_name)

    if not pdf_text:
        print("[agent] Extraction failed → falling back to DB")
        from rag import build_context_block, call_groq
        return {
            "answer":      call_groq(query, build_context_block(chunks)),
            "sources":     [{"source": c["source"], "page": c["page"], "similarity": c["similarity"]} for c in chunks],
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
        "sources":     [{"source": law_name, "page": "live", "similarity": 1.0}],
        "query":       query,
        "used_agent":  True,
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