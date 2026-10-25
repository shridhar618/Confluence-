from datetime import UTC, datetime

from app import db

# Distinct from WorkEscalation (models/work_escalation.py), which tracks
# workforce/KPI capacity risk. GovernanceCase is specifically for AI-usage
# governance risk (unauthorized access attempts, policy violations, etc.)
# so the two concerns never get conflated in the admin UI.

CASE_STATUSES = ["open", "under_review", "warned", "restricted", "resolved", "escalated"]


class GovernanceCase(db.Model):
    __tablename__ = "governance_cases"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    assigned_admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    status = db.Column(db.String(20), nullable=False, default="open")
    trigger = db.Column(db.Text, nullable=False)  # human-readable reason the case was opened
    risk_score_at_open = db.Column(db.Float, nullable=False, default=0.0)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    resolved_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", foreign_keys=[user_id], backref=db.backref("governance_cases", lazy=True))
    assigned_admin = db.relationship("User", foreign_keys=[assigned_admin_id])
    risk_events = db.relationship("RiskEvent", backref="case", lazy=True, order_by="RiskEvent.created_at.asc()")
    actions = db.relationship(
        "AdminAction",
        backref="case",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="AdminAction.created_at.asc()",
    )

    def case_code(self):
        return f"GOV-{self.id:03d}"

    def to_dict(self, include_events=False, include_actions=False):
        payload = {
            "id": self.id,
            "case_code": self.case_code(),
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "role": self.user.role if self.user else None,
            "assigned_admin_id": self.assigned_admin_id,
            "assigned_admin_username": self.assigned_admin.username if self.assigned_admin else None,
            "status": self.status,
            "trigger": self.trigger,
            "risk_score_at_open": self.risk_score_at_open,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "event_count": len(self.risk_events),
        }
        if include_events:
            payload["risk_events"] = [event.to_dict() for event in self.risk_events]
        if include_actions:
            payload["actions"] = [action.to_dict() for action in self.actions]
        return payload
