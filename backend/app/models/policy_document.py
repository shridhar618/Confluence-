from datetime import UTC, datetime

from app import db


class PolicyDocument(db.Model):
    """A governance policy source (external framework or org-specific policy).

    Category values (Phase 7 corpus):
      - "AI Governance"   e.g. NIST AI RMF, NIST GenAI Profile, NIST AI RMF Playbook
      - "Privacy"         e.g. NIST Privacy Framework, India DPDP Act 2023
      - "Security"        e.g. OWASP GenAI/LLM Top 10, AI Security & Incident Response Policy
      - "Access Control"  e.g. Role & Access Control Policy
      - "Acceptable Use"  e.g. AI Acceptable Use Policy, Data Privacy & Classification Policy

    source_type distinguishes external reference frameworks from the
    organization's own policies, so the app never implies that an external
    framework directly dictates our risk score (see docs note on Phase 7).
    """

    __tablename__ = "policy_documents"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    source_type = db.Column(db.String(20), nullable=False, default="organization")  # "organization" | "external_framework"
    version = db.Column(db.String(20), nullable=False, default="1.0")
    status = db.Column(db.String(20), nullable=False, default="active")  # active | disabled
    file_path = db.Column(db.String(500), nullable=True)
    chunk_count = db.Column(db.Integer, nullable=False, default=0)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    last_indexed_at = db.Column(db.DateTime, nullable=True)

    chunks = db.relationship(
        "PolicyChunk",
        backref="document",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="PolicyChunk.chunk_index.asc()",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "source_type": self.source_type,
            "version": self.version,
            "status": self.status,
            "chunk_count": self.chunk_count,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "last_indexed_at": self.last_indexed_at.isoformat() if self.last_indexed_at else None,
        }
