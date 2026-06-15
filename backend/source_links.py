"""
NyayaFlow - Source Document Links

Maps ingested PDF filenames to their official source URLs (indiacode.nic.in, etc.)
so users can click through and verify citations themselves.

- When the agent fetches a new Act via DuckDuckGo, we record its real PDF URL.
- For PDFs without a recorded URL (the original seed corpus), we fall back to
  a Google search scoped to indiacode.nic.in for that Act — still gets the
  user to the right place.
"""

import os
import json
from urllib.parse import quote_plus

SOURCE_URLS_PATH = os.getenv("SOURCE_URLS_PATH", "./data/source_urls.json")

_cache = None


def _load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    if os.path.exists(SOURCE_URLS_PATH):
        try:
            with open(SOURCE_URLS_PATH, "r", encoding="utf-8") as f:
                _cache = json.load(f)
                return _cache
        except Exception as e:
            print(f"[source_links] Failed to load: {e}")
    _cache = {}
    return _cache


def save_source_url(filename: str, url: str):
    """Record the official URL for a PDF (called when the agent fetches a new Act)."""
    if not filename or not url:
        return
    data = _load()
    if data.get(filename) == url:
        return
    data[filename] = url
    try:
        os.makedirs(os.path.dirname(SOURCE_URLS_PATH) or ".", exist_ok=True)
        with open(SOURCE_URLS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        global _cache
        _cache = data
        print(f"[source_links] Saved URL for {filename}")
    except Exception as e:
        print(f"[source_links] Failed to save: {e}")


def get_source_url(source: str, display_name: str = None) -> str:
    """
    Return a URL the user can click to view/verify the source document.
    1. If we've recorded a direct URL for this PDF filename, use it.
    2. Otherwise, fall back to a Google search scoped to indiacode.nic.in.
    """
    if source and source != "unknown":
        filename = os.path.basename(source)
        data = _load()
        if filename in data:
            return data[filename]

    name = display_name or os.path.basename(source or "") or "Indian law"
    name = name.replace(".pdf", "").replace("_", " ")
    query = quote_plus(f"{name} indiacode.nic.in pdf")
    return f"https://www.google.com/search?q={query}"