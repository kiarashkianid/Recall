"""
vector_store.py
───────────────
ChromaDB wrapper for semantic embedding and retrieval.

Responsibilities:
  • Maintain a persistent local vector store (CHROMA_PATH on disk).
  • Embed journal entries using OpenAI text-embedding-3-small.
  • Expose upsert / delete / query / incremental-sync operations.
  • No UI, no PostgreSQL, no AI agent logic.

Sync strategy
─────────────
sync_incremental() fetches the set of document ids already in Chroma
and only embeds entries whose id is not yet present. This makes startup
O(new entries) rather than O(all entries), saving API calls and time.
"""

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from logger import get_logger
from config import (
    OPENAI_API_KEY,
    OPENAI_EMBEDDING_MODEL,
    CHROMA_PATH,
    CHROMA_COLLECTION,
    RAG_TOP_K,
)

log = get_logger(__name__)


# ──────────────────────────────────────────────
#  INTERNAL: lazy singleton collection
# ──────────────────────────────────────────────

_collection = None


def _get_collection():
    """Return (and cache) the ChromaDB collection. Thread-safe for reads."""
    global _collection
    if _collection is not None:
        return _collection

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    embedding_fn = OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY,
        model_name=OPENAI_EMBEDDING_MODEL,
    )
    _collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )
    log.info("ChromaDB collection ready  path=%s  docs=%d", CHROMA_PATH, _collection.count())
    return _collection


# ──────────────────────────────────────────────
#  WRITE — Upsert
# ──────────────────────────────────────────────

def upsert_entry(entry_id: int, title: str, content: str, date: str) -> None:
    """
    Embed and store (or overwrite) a single journal entry.

    Document format: "[YYYY-MM-DD] Title\nContent"
    Metadata is stored for post-retrieval attribution.

    Args:
        entry_id: PostgreSQL primary key — used as the Chroma document id.
        title:    Entry heading.
        content:  Body text.
        date:     ISO date string or date object.
    """
    col      = _get_collection()
    date_str = str(date)
    document = f"[{date_str}] {title}\n{content}"
    col.upsert(
        ids=[str(entry_id)],
        documents=[document],
        metadatas=[{
            "entry_id": entry_id,
            "title":    title,
            "date":     date_str,
        }],
    )
    log.debug("Upserted vector  id=%s  title=%r", entry_id, title)


# ──────────────────────────────────────────────
#  WRITE — Delete
# ──────────────────────────────────────────────

def delete_entry(entry_id: int) -> None:
    """
    Remove a document from the vector store by its entry id.
    Call this whenever db.delete_entry() is called to keep both stores in sync.

    No-ops silently if the document does not exist in Chroma.
    """
    col = _get_collection()
    try:
        col.delete(ids=[str(entry_id)])
        log.info("Deleted vector  id=%s", entry_id)
    except Exception as ex:
        # Chroma raises if id not found — treat as non-fatal
        log.warning("delete_entry id=%s: %s", entry_id, ex)


# ──────────────────────────────────────────────
#  SYNC — Incremental startup sync
# ──────────────────────────────────────────────

def get_indexed_ids() -> set[str]:
    """Return the set of document ids currently stored in the collection."""
    col = _get_collection()
    if col.count() == 0:
        return set()
    result = col.get(include=[])          # fetch ids only — no embedding overhead
    return set(result["ids"])


def sync_incremental(entries: list[tuple]) -> int:
    """
    Embed only entries whose id is not yet in ChromaDB.
    Safe to call every startup — only new entries are processed.

    Args:
        entries: List of (id, title, content, journal_date) tuples
                 from db.fetch_all_entries_with_ids().

    Returns:
        Number of newly embedded entries (0 if already fully synced).
    """
    indexed = get_indexed_ids()
    new_entries = [e for e in entries if str(e[0]) not in indexed]

    if not new_entries:
        log.info("Vector store already up-to-date (%d docs)", len(indexed))
        return 0

    log.info("Embedding %d new entries (already indexed: %d)", len(new_entries), len(indexed))
    for row in new_entries:
        entry_id, title, content, date = row
        upsert_entry(entry_id, title, content, date)

    log.info("Incremental sync complete")
    return len(new_entries)


# ──────────────────────────────────────────────
#  READ
# ──────────────────────────────────────────────

def query(question: str, n_results: int = RAG_TOP_K) -> list[dict]:
    """
    Cosine-similarity search against all embedded entries.

    Args:
        question:  Natural-language query string.
        n_results: Maximum number of results to return.

    Returns:
        List of hit dicts with keys: document, title, date, distance.
        Empty list if the collection is empty.
    """
    col = _get_collection()
    if col.count() == 0:
        return []

    cap     = min(n_results, col.count())
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

    log.debug("query=%r  returned %d hits", question[:60], len(hits))
    return hits


def format_hits(hits: list[dict]) -> str:
    """Format query hits as a readable string for the AI agent."""
    if not hits:
        return "No relevant entries found."
    return "\n\n".join(
        f"── {h['date']}  ·  {h['title']} ──\n{h['document']}"
        for h in hits
    )


def collection_size() -> int:
    """Return the number of documents currently in the collection."""
    return _get_collection().count()