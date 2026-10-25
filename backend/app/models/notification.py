from datetime import UTC, datetime

from app import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)  # recipient
    type = db.Column(db.String(40), nullable=False)  # e.g. "high_risk_request", "governance_case_opened"
    message = db.Column(db.Text, nullable=False)
    related_case_id = db.Column(db.Integer, db.ForeignKey("governance_cases.id"), nullable=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), index=True)

    user = db.relationship("User", backref=db.backref("notifications", lazy=True))
    related_case = db.relationship("GovernanceCase")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "message": self.message,
            "related_case_id": self.related_case_id,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
