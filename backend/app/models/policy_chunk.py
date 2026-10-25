from datetime import UTC, datetime

from app import db


class PolicyChunk(db.Model):
    """A retrievable slice of a PolicyDocument, indexed in Qdrant by qdrant_point_id.

    The chunk row is the source of truth for content + citation metadata;
    Qdrant stores only the embedding vector plus qdrant_point_id -> chunk_id
    linkage, so re-indexing never loses provenance.
    """

    __tablename__ = "policy_chunks"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("policy_documents.id"), nullable=False, index=True)
    chunk_index = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    section = db.Column(db.String(255), nullable=True)
    page = db.Column(db.Integer, nullable=True)
    qdrant_point_id = db.Column(db.String(64), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    def to_dict(self, include_content=True):
        payload = {
            "id": self.id,
            "document_id": self.document_id,
            "document_name": self.document.name if self.document else None,
            "category": self.document.category if self.document else None,
            "chunk_index": self.chunk_index,
            "section": self.section,
            "page": self.page,
        }
        if include_content:
            payload["content"] = self.content
        return payload
