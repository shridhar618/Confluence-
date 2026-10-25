from datetime import UTC, datetime

from app import db

ACTION_TYPES = ["review", "warn", "restrict", "restore", "escalate", "resolve", "note"]


class AdminAction(db.Model):
    """An auditable administrator action taken on a GovernanceCase.

    Human administrators remain responsible for consequential decisions
    (Phase 10 principle) -- the system never auto-restricts or auto-escalates
    without a human-reviewable trail; automated threshold breaches create a
    GovernanceCase and a Notification, but only an AdminAction changes case
    status in a way that matters (warn/restrict/restore/escalate/resolve).
    """

    __tablename__ = "admin_actions"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("governance_cases.id"), nullable=False, index=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action_type = db.Column(db.String(20), nullable=False)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), index=True)

    admin = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "admin_id": self.admin_id,
            "admin_username": self.admin.username if self.admin else None,
            "action_type": self.action_type,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
