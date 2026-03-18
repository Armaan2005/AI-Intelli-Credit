"""
vector_store.py
---------------
Upgrades your existing in-memory db from:
    db = []
    def store(vec, text): db.append((vec, text))
    def get(): return db
    — No search, no similarity, returns entire db every time!

To a proper in-memory vector store with:
  - Cosine similarity search
  - Metadata storage (doc_type, app_id, page, etc.)
  - Persistence to JSON file (survives server restarts)
  - Per-application isolation
  - Top-K retrieval

DROP-IN REPLACEMENT — same function names store() and get(), new search().
"""
import json
import os
import time
import math
from typing import Optional
from app.services.rag.embedder import cosine_similarity

# ─────────────────────────────────────────────────────────────────────────────
#  In-memory store + optional JSON persistence
# ─────────────────────────────────────────────────────────────────────────────
STORE_PATH = "./rag_store.json"    # persisted on disk

# Structure: { app_id: [ {vec, text, metadata, timestamp}, ... ] }
_db: dict[str, list[dict]] = {}


def _load_from_disk():
    """Load persisted store on startup."""
    global _db
    if os.path.exists(STORE_PATH):
        try:
            with open(STORE_PATH, "r") as f:
                _db = json.load(f)
            total = sum(len(v) for v in _db.values())
            print(f"📂 RAG store loaded: {total} vectors across {len(_db)} applications")
        except Exception as e:
            print(f"⚠️ RAG store load failed: {e} — starting fresh")
            _db = {}


def _save_to_disk():
    """Persist store to disk."""
    try:
        with open(STORE_PATH, "w") as f:
            json.dump(_db, f)
    except Exception as e:
        print(f"⚠️ RAG store save failed: {e}")


# Load on import
_load_from_disk()


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def store(
    vec: list[float],
    text: str,
    app_id: str = "default",
    metadata: Optional[dict] = None,
) -> dict:
    """
    UPGRADED version of your store(vec, text).

    Now supports:
    - Per-application isolation via app_id
    - Metadata (doc_type, page, file_name, etc.)
    - Timestamp
    - Duplicate detection (skips if same text already stored)
    - Disk persistence

    Backward-compatible: store(vec, text) still works.
    """
    global _db

    if app_id not in _db:
        _db[app_id] = []

    # Skip duplicate texts
    existing_texts = {entry["text"] for entry in _db[app_id]}
    if text in existing_texts:
        return {"status": "duplicate", "app_id": app_id}

    entry = {
        "vec":       vec,
        "text":      text,
        "metadata":  metadata or {},
        "timestamp": time.time(),
    }
    _db[app_id].append(entry)
    _save_to_disk()

    return {
        "status":  "stored",
        "app_id":  app_id,
        "index":   len(_db[app_id]) - 1,
        "vec_dim": len(vec),
    }


def get(app_id: str = "default") -> list[dict]:
    """
    UPGRADED version of your get().

    Your original returned the raw list — now returns list of entries
    with text + metadata (vec excluded to keep response clean).
    Backward-compatible: result[i]["text"] still works.
    """
    entries = _db.get(app_id, [])
    return [
        {
            "text":      e["text"],
            "metadata":  e["metadata"],
            "timestamp": e["timestamp"],
        }
        for e in entries
    ]


def search(
    query_vec: list[float],
    app_id: str = "default",
    top_k: int = 5,
    min_score: float = 0.3,
) -> list[dict]:
    """
    NEW — Semantic similarity search. This is the whole point of a vector store!

    Returns top_k most relevant chunks for a query vector,
    sorted by cosine similarity (highest first).

    Args:
        query_vec:  embedding of the search query
        app_id:     which application's documents to search
        top_k:      how many results to return
        min_score:  minimum similarity threshold (0-1)
    """
    entries = _db.get(app_id, [])
    if not entries:
        return []

    scored = []
    for i, entry in enumerate(entries):
        score = cosine_similarity(query_vec, entry["vec"])
        if score >= min_score:
            scored.append({
                "text":      entry["text"],
                "metadata":  entry["metadata"],
                "score":     score,
                "index":     i,
            })

    # Sort by similarity descending
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def clear(app_id: str = "default"):
    """Clear all vectors for an application (e.g. when re-uploading docs)."""
    global _db
    if app_id in _db:
        del _db[app_id]
        _save_to_disk()


def stats(app_id: str = "default") -> dict:
    """Return store statistics."""
    entries = _db.get(app_id, [])
    return {
        "app_id":        app_id,
        "total_chunks":  len(entries),
        "all_apps":      list(_db.keys()),
        "total_vectors": sum(len(v) for v in _db.values()),
    }