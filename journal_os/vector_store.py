"""
vector_store.py
───────────────
ChromaDB wrapper for semantic embedding and retrieval.

Responsibilities:
  • Maintain a persistent local vector store (./chroma_db on disk).
  • Embed journal entries using OpenAI text-embedding-3-small.
  • Expose upsert / query / sync operations.
  • No UI, no PostgreSQL, no AI agent logic here.

Usage:
    from vector_store import upsert_entry, query, sync_from_postgres
"""

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from .config import (
    OPENAI_API_KEY,
    OPENAI_EMBEDDING_MODEL,
    CHROMA_PATH,
    CHROMA_COLLECTION,
    RAG_TOP_K,
)


# ──────────────────────────────────────────────
#  INTERNAL: collection accessor (lazy singleton)
# ──────────────────────────────────────────────

_collection = None   # module-level cache so we only init once per process


def _get_collection():
    """Return (and cache) the ChromaDB collection with OpenAI embeddings."""
    global _collection
    if _collection is not None:
        return _collection

    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it before using semantic search, "
            "summary generation, or automatic entry embedding."
        )

    client = chromadb.PersistentClient(path=CHROMA_PATH)

    embedding_fn = OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY,
        model_name=OPENAI_EMBEDDING_MODEL,
    )

    _collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},   # cosine similarity
    )
    return _collection


# ──────────────────────────────────────────────
#  WRITE
# ──────────────────────────────────────────────

def upsert_entry(entry_id: int, title: str, content: str, date: str) -> None:
    """
    Embed and store (or update) a single journal entry.

    The document stored is: "[YYYY-MM-DD] Title\nContent"
    Metadata keeps the structured fields for post-retrieval filtering.

    Args:
        entry_id: PostgreSQL primary key — used as the Chroma document ID.
        title:    Entry heading.
        content:  Body text.
        date:     ISO date string, e.g. '2025-06-01'.
    """
    col = _get_collection()
    document = f"[{date}] {title}\n{content}"
    col.upsert(
        ids=[str(entry_id)],
        documents=[document],
        metadatas=[{
            "entry_id":   entry_id,
            "title":      title,
            "date":       str(date),   # ensure string; psycopg2 may return date object
        }],
    )


def sync_from_postgres(entries: list[tuple]) -> int:
    """
    Bulk-upsert all entries fetched from PostgreSQL.
    Safe to call on every startup — Chroma's upsert is idempotent.

    Args:
        entries: List of (id, title, content, journal_date) tuples
                 from db.fetch_all_entries_with_ids().

    Returns:
        Number of entries synced.
    """
    for row in entries:
        entry_id, title, content, date = row
        upsert_entry(entry_id, title, content, date)
    return len(entries)


# ──────────────────────────────────────────────
#  READ
# ──────────────────────────────────────────────

def query(question: str, n_results: int = RAG_TOP_K) -> list[dict]:
    """
    Semantic similarity search against all embedded entries.

    Args:
        question:  Natural-language query string.
        n_results: How many top results to return.

    Returns:
        List of dicts, each with keys:
            document  – raw stored text
            title     – entry title
            date      – entry date string
            distance  – cosine distance (lower = more similar)
    """
    col = _get_collection()

    # Guard: can't query an empty collection
    if col.count() == 0:
        return []

    cap = min(n_results, col.count())
    results = col.query(
        query_texts=[question],
        n_results=cap,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({
            "document": doc,
            "title":    meta.get("title", ""),
            "date":     meta.get("date",  ""),
            "distance": round(dist, 4),
        })

    return hits


def format_hits(hits: list[dict]) -> str:
    """
    Convert a list of query hits into a readable string for the agent.

    Returns:
        Multi-line string, one block per hit with date/title header.
    """
    if not hits:
        return "No relevant entries found."

    parts = []
    for h in hits:
        parts.append(
            f"── {h['date']}  ·  {h['title']} ──\n{h['document']}"
        )
    return "\n\n".join(parts)


def collection_size() -> int:
    """Return the number of embedded documents currently in the collection."""
    return _get_collection().count()
