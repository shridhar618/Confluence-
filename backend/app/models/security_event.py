import json
from datetime import UTC, datetime

from app import db

EVENT_TYPES = [
    "suspicious_login",
    "repeated_restricted_request",
    "policy_bypass_attempt",
    "high_risk_request",
    "unusual_access",
    "attack_simulation",
    "ghost_mode_intervention",
]


class SecurityEvent(db.Model):
    """A generated (never real-attack) security demo event, or a genuine
    system-observed signal such as a suspicious login pattern. `source`
    distinguishes which subsystem produced the event so the admin UI can
    clearly separate demo-lab noise from real operational signals.
    """

    __tablename__ = "security_events"

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(10), nullable=False, default="low")  # low | medium | high
    source = db.Column(db.String(30), nullable=False, default="system")  # system | attack_simulator | ghost_mode
    target_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    description = db.Column(db.Text, nullable=True)
    metadata_json = db.Column("metadata", db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), index=True)

    target_user = db.relationship("User")

    def to_dict(self):
        try:
            parsed_metadata = json.loads(self.metadata_json) if self.metadata_json else {}
        except (TypeError, ValueError):
            parsed_metadata = {}
        return {
            "id": self.id,
            "event_type": self.event_type,
            "severity": self.severity,
            "source": self.source,
            "target_user_id": self.target_user_id,
            "target_username": self.target_user.username if self.target_user else None,
            "description": self.description,
            "metadata": parsed_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
