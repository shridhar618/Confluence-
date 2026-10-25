import json
from datetime import UTC, datetime

from app import db


class RiskEvent(db.Model):
    """A recorded risk-scoring outcome for one AI request.

    Every AuditLog row already carries risk_score/risk_level for its own
    request (see models/audit_log.py). RiskEvent is a lighter-weight,
    append-only ledger used specifically for *cumulative* risk tracking
    across a user's requests (Phase 10): each RiskEvent stores the
    contributing factors and the user's running cumulative_score at the
    time it was recorded, so escalation logic never has to re-scan the
    full AuditLog history to decide whether a threshold was crossed.

    A RiskEvent is attached to a GovernanceCase once cumulative risk
    crosses a configured threshold (see RiskConfiguration / GovernanceCase).
    """

    __tablename__ = "risk_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    audit_log_id = db.Column(db.Integer, db.ForeignKey("audit_logs.id"), nullable=True, index=True)
    case_id = db.Column(db.Integer, db.ForeignKey("governance_cases.id"), nullable=True, index=True)

    risk_score = db.Column(db.Float, nullable=False, default=0.0)
    risk_level = db.Column(db.String(10), nullable=False, default="low")
    factors = db.Column(db.Text, nullable=True)  # JSON list of {rule, weight, detail}
    cumulative_score = db.Column(db.Float, nullable=False, default=0.0)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), index=True)

    user = db.relationship("User", backref=db.backref("risk_events", lazy=True))
    audit_log = db.relationship("AuditLog", backref=db.backref("risk_event", uselist=False))

    def to_dict(self):
        try:
            parsed_factors = json.loads(self.factors) if self.factors else []
        except (TypeError, ValueError):
            parsed_factors = []
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "audit_log_id": self.audit_log_id,
            "case_id": self.case_id,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "factors": parsed_factors,
            "cumulative_score": self.cumulative_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
