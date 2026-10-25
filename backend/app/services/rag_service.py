"""
Phase 6 — retrieval-at-query-time.

Deliberately NOT wired into the live /chat flow yet (see
docs/PHASE_6_NOTES.md for why). This module is exercised through the new
admin-only /api/policies/search endpoint (app/routes/policies.py) so the
retrieval pipeline can be verified end-to-end on a machine that actually
has sentence-transformers/qdrant-client installed, before it becomes part
of the governed chat response.

Every function degrades gracefully (returns [] / None, never raises) when
the corpus hasn't been ingested yet or the ML dependencies aren't
installed -- consistent with Phase 22's "insufficient policy evidence"
principle: a missing index should never crash the caller, it should read
as "no evidence found."
"""

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
QDRANT_PATH = BACKEND_ROOT / "qdrant_data"
QDRANT_COLLECTION = "secureai_policy_chunks"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

_model = None
_client = None
_unavailable_reason = None


def _get_model():
    global _model, _unavailable_reason
    if _model is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        return _model
    except ImportError as exc:
        _unavailable_reason = f"sentence-transformers not installed: {exc}"
        return None


def _get_client():
    global _client, _unavailable_reason
    if _client is not None:
        return _client
    if not QDRANT_PATH.exists():
        _unavailable_reason = "Qdrant index not found -- run scripts/ingest_policies.py first"
        return None
    try:
        from qdrant_client import QdrantClient
        _client = QdrantClient(path=str(QDRANT_PATH))
        return _client
    except ImportError as exc:
        _unavailable_reason = f"qdrant-client not installed: {exc}"
        return None


def rag_status() -> dict:
    """Lightweight health check for the /api/policies/search endpoint and
    for an admin-facing "is RAG ready" indicator, without loading the
    (potentially slow) embedding model just to check availability.
    """
    try:
        import importlib
        has_st = importlib.util.find_spec("sentence_transformers") is not None
        has_qdrant = importlib.util.find_spec("qdrant_client") is not None
    except Exception:
        has_st = has_qdrant = False
    index_exists = QDRANT_PATH.exists()
    return {
        "sentence_transformers_installed": has_st,
        "qdrant_client_installed": has_qdrant,
        "index_exists": index_exists,
        "ready": has_st and has_qdrant and index_exists,
    }


def retrieve_policy_evidence(query: str, top_k: int = 4, min_score: float = 0.25) -> list:
    """Returns a list of dicts: {content, document_name, category, section,
    page, score}, best matches first. Returns [] (never raises) if the
    embedding model or Qdrant index isn't available, or nothing scores
    above min_score.
    """
    model = _get_model()
    client = _get_client()
    if model is None or client is None:
        return []

    try:
        query_vector = model.encode(query).tolist()
        results = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=top_k,
        )
    except Exception:
        return []

    from app.models.policy_chunk import PolicyChunk

    evidence = []
    for hit in results:
        if hit.score < min_score:
            continue
        chunk_id = hit.payload.get("chunk_id")
        chunk = PolicyChunk.query.get(chunk_id) if chunk_id else None
        if not chunk:
            continue
        if not chunk.document or chunk.document.status != "active":
            # An admin-disabled document (Phase 14) must never surface as
            # policy evidence, even though its vectors may still exist in
            # Qdrant until the next full re-index cleans them up.
            continue
        evidence.append({
            "content": chunk.content,
            "document_name": hit.payload.get("document_name"),
            "category": hit.payload.get("category"),
            "section": chunk.section,
            "page": chunk.page,
            "score": round(float(hit.score), 3),
        })
    return evidence
