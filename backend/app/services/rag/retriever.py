"""
retriever.py
------------
Upgrades your existing retrieve() from:
    def retrieve():
        return get()     ← returns ALL stored docs, no query, no search!

To a proper RAG retriever with:
  - Text chunking (splits large docs into searchable pieces)
  - Document indexing pipeline
  - Query-based semantic search
  - Context assembly for Gemini

DROP-IN REPLACEMENT — same function name retrieve(), adds index_document().
"""
from typing import Optional
from app.services.rag.embedder  import embed
from app.services.rag.vector_store import store, search, get, stats


# ─────────────────────────────────────────────────────────────────────────────
#  TEXT CHUNKING — splits large documents into overlapping chunks
# ─────────────────────────────────────────────────────────────────────────────
def _chunk_text(
    text: str,
    chunk_size: int = 500,    # chars per chunk
    overlap: int = 100,       # overlap between chunks (for context continuity)
) -> list[str]:
    """
    Split text into overlapping chunks.
    Overlap ensures that sentences split across chunk boundaries are captured.
    """
    text = text.strip()
    if not text:
        return []

    # Try to split on sentence boundaries first
    sentences = []
    for para in text.split("\n"):
        para = para.strip()
        if para:
            # Split on period/question/exclamation
            for sent in para.replace("? ", ".\n").replace("! ", ".\n").split(". "):
                sent = sent.strip()
                if sent:
                    sentences.append(sent + ".")

    # Group sentences into chunks
    chunks  = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) < chunk_size:
            current += " " + sent
        else:
            if current.strip():
                chunks.append(current.strip())
            # Start new chunk with overlap from end of previous
            current = current[-overlap:] + " " + sent if len(current) > overlap else sent

    if current.strip():
        chunks.append(current.strip())

    # If chunking produced nothing (e.g. no sentences), fall back to hard split
    if not chunks:
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size].strip()
            if chunk:
                chunks.append(chunk)

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
#  DOCUMENT INDEXING — embed + store all chunks of a document
# ─────────────────────────────────────────────────────────────────────────────
def index_document(
    text: str,
    app_id: str,
    doc_type: str = "unknown",
    file_name: str = "",
    page: int = 0,
) -> dict:
    """
    Full pipeline: chunk → embed → store.

    Call this when a document is uploaded/parsed.
    After indexing, retrieve() can find relevant chunks via semantic search.
    """
    if not text or not text.strip():
        return {"status": "skipped", "reason": "empty text", "chunks": 0}

    chunks   = _chunk_text(text)
    stored   = 0
    skipped  = 0

    for i, chunk in enumerate(chunks):
        vec = embed(chunk)
        result = store(
            vec=vec,
            text=chunk,
            app_id=app_id,
            metadata={
                "doc_type":  doc_type,
                "file_name": file_name,
                "page":      page,
                "chunk_idx": i,
                "total_chunks": len(chunks),
            },
        )
        if result.get("status") == "stored":
            stored += 1
        else:
            skipped += 1

    store_stats = stats(app_id)
    print(f"📑 Indexed '{file_name}' | chunks: {stored} stored, {skipped} skipped | "
          f"total in store: {store_stats['total_chunks']}")

    return {
        "status":         "indexed",
        "file_name":      file_name,
        "doc_type":       doc_type,
        "total_chunks":   len(chunks),
        "chunks_stored":  stored,
        "chunks_skipped": skipped,
        "store_total":    store_stats["total_chunks"],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def retrieve(
    query: str = "",
    app_id: str = "default",
    top_k: int = 5,
) -> list[dict]:
    """
    UPGRADED version of your retrieve().

    Your original: return get()
    — Returned ALL stored documents with no filtering.
    — Gemini would get irrelevant context, wasting tokens.

    Now:
    - Embeds the query
    - Runs cosine similarity search
    - Returns only the most relevant chunks

    Backward-compatible: if no query given, falls back to returning all docs.
    """
    # Backward compat: no query = return all (your original behaviour)
    if not query or not query.strip():
        return get(app_id)

    # Semantic search
    query_vec = embed(query)
    results   = search(
        query_vec=query_vec,
        app_id=app_id,
        top_k=top_k,
        min_score=0.25,
    )

    if not results:
        # Fallback: return most recent chunks
        all_docs = get(app_id)
        return all_docs[-top_k:] if len(all_docs) >= top_k else all_docs

    return results


def retrieve_context(
    query: str,
    app_id: str,
    top_k: int = 5,
    max_chars: int = 4000,
) -> str:
    """
    Convenience function — returns assembled context string
    ready to inject into a Gemini prompt.

    Usage:
        context = retrieve_context("What is the company's debt level?", app_id="42")
        prompt  = f"Based on these documents:\\n{context}\\n\\nAnswer: ..."
    """
    results = retrieve(query, app_id, top_k)

    if not results:
        return "No relevant documents found in the knowledge base."

    parts = []
    total_chars = 0

    for i, r in enumerate(results):
        text      = r.get("text", "")
        meta      = r.get("metadata", {})
        score     = r.get("score", 0)
        doc_label = f"[{meta.get('doc_type','doc').upper()} | {meta.get('file_name','')} | relevance: {score:.2f}]"

        chunk = f"{doc_label}\n{text}"
        if total_chars + len(chunk) > max_chars:
            break
        parts.append(chunk)
        total_chars += len(chunk)

    return "\n\n---\n\n".join(parts)