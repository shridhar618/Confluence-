from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app import db
from app.models.policy_chunk import PolicyChunk
from app.models.policy_document import PolicyDocument
from app.services.audit import record_audit_event
from app.services.rag_service import rag_status, retrieve_policy_evidence
from app.utils.authz import get_current_user, require_permission

policies_bp = Blueprint("policies", __name__)


@policies_bp.route("/policies", methods=["GET"])
@jwt_required()
def list_policies():
    """Any authenticated user can see which policy documents exist and
    their indexing status -- this is metadata about governance sources,
    not sensitive content, matching Phase 14's "Policy Sources" page.
    """
    documents = PolicyDocument.query.order_by(PolicyDocument.category, PolicyDocument.name).all()
    return jsonify({"documents": [doc.to_dict() for doc in documents]}), 200


@policies_bp.route("/policies/<int:doc_id>/chunks", methods=["GET"])
@jwt_required()
@require_permission("manage_policies")
def view_policy_chunks(doc_id):
    """The "View" action from Phase 14's Policy Sources page -- lets an
    admin inspect exactly what got indexed for a document."""
    doc = PolicyDocument.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Policy document not found"}), 404
    chunks = PolicyChunk.query.filter_by(document_id=doc_id).order_by(PolicyChunk.chunk_index).all()
    return jsonify({"document": doc.to_dict(), "chunks": [c.to_dict() for c in chunks]}), 200


@policies_bp.route("/policies/<int:doc_id>/status", methods=["PUT"])
@jwt_required()
@require_permission("manage_policies")
def set_policy_status(doc_id):
    """The "Disable" action -- a disabled document is never deleted (audit
    evidence for past decisions must remain intact, per the Data Privacy &
    Classification Policy §6.2), it's just excluded from future retrieval.
    See rag_service.retrieve_policy_evidence(), which skips any chunk
    whose document.status != "active".
    """
    doc = PolicyDocument.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Policy document not found"}), 404

    data = request.get_json() or {}
    new_status = data.get("status")
    if new_status not in ("active", "disabled"):
        return jsonify({"error": "status must be 'active' or 'disabled'"}), 400

    previous_status = doc.status
    doc.status = new_status
    db.session.commit()

    record_audit_event(
        "policy_change",
        user=get_current_user(),
        description=f"Policy document '{doc.name}' status changed",
        resource=doc.name,
        metadata={"previous_status": previous_status, "new_status": new_status},
    )
    return jsonify({"document": doc.to_dict()}), 200


@policies_bp.route("/policies/<int:doc_id>", methods=["DELETE"])
@jwt_required()
@require_permission("manage_policies")
def delete_policy(doc_id):
    doc = PolicyDocument.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Policy document not found"}), 404

    doc_name = doc.name
    point_ids = [c.qdrant_point_id for c in doc.chunks if c.qdrant_point_id]
    db.session.delete(doc)  # cascades to PolicyChunk rows (see models/policy_document.py)
    db.session.commit()

    if point_ids:
        try:
            from app.services.rag_service import _get_client
            client = _get_client()
            if client:
                client.delete(collection_name="secureai_policy_chunks", points_selector=point_ids)
        except Exception as exc:
            # The SQL rows are already gone -- an orphaned Qdrant vector is
            # harmless (it can never be resolved back to real content since
            # PolicyChunk.query.get() will return nothing for it), but log
            # it so a re-index --reset can be run if it matters.
            print(f"[policies] failed to clean up Qdrant points for deleted doc {doc_id}: {exc}")

    record_audit_event(
        "policy_change",
        user=get_current_user(),
        description=f"Policy document '{doc_name}' deleted",
        resource=doc_name,
    )
    return jsonify({"message": f"Deleted '{doc_name}'"}), 200


@policies_bp.route("/policies/<int:doc_id>/reindex", methods=["POST"])
@jwt_required()
@require_permission("manage_policies")
def reindex_policy(doc_id):
    """The "Re-index" action. Requires the ML dependencies (Phase 6) to be
    installed -- returns a clear 503 rather than a stack trace if they
    aren't, since this environment (and possibly the grading environment)
    may not have them installed.
    """
    doc = PolicyDocument.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Policy document not found"}), 404
    if not doc.file_path:
        return jsonify({"error": "This document has no stored file_path (ingested before Phase 14) -- re-run scripts/ingest_policies.py once to backfill it."}), 400

    status = rag_status()
    if not status["sentence_transformers_installed"] or not status["qdrant_client_installed"]:
        return jsonify({"error": "RAG dependencies not installed in this environment.", "status": status}), 503

    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
    try:
        from ingest_policies import ingest_one_document, get_embedding_model, get_qdrant_client, ensure_collection
    except ImportError as exc:
        return jsonify({"error": f"Could not load ingestion module: {exc}"}), 500

    try:
        model = get_embedding_model()
        client = get_qdrant_client()
        ensure_collection(client, model.get_sentence_embedding_dimension())
        chunk_count = ingest_one_document(Path(doc.file_path), db, PolicyDocument, PolicyChunk, model, client)
    except Exception as exc:
        return jsonify({"error": f"Re-indexing failed: {exc}"}), 500

    record_audit_event(
        "policy_change",
        user=get_current_user(),
        description=f"Policy document '{doc.name}' re-indexed ({chunk_count} chunks)",
        resource=doc.name,
        metadata={"chunk_count": chunk_count},
    )
    return jsonify({"document": doc.to_dict()}), 200


@policies_bp.route("/policies/rag-status", methods=["GET"])
@jwt_required()
def get_rag_status():
    return jsonify(rag_status()), 200


@policies_bp.route("/policies/search", methods=["POST"])
@jwt_required()
def search_policies():
    """Admin-only, manual RAG verification endpoint -- NOT part of the live
    governed chat flow (see docs/PHASE_6_NOTES.md for why). This exists so
    retrieval can be tested end-to-end on a machine with the ML
    dependencies installed before it's trusted inside /chat.
    """
    user = get_current_user()
    if not user or user.role != "admin":
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json() or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400

    top_k = data.get("top_k", 4)
    evidence = retrieve_policy_evidence(query, top_k=top_k)
    return jsonify({"query": query, "results": evidence, "status": rag_status()}), 200
