from datetime import UTC, datetime

from app import db


class QuestionFeedback(db.Model):
    __tablename__ = "question_feedback"

    id = db.Column(db.Integer, primary_key=True)
    audit_log_id = db.Column(db.Integer, db.ForeignKey("audit_logs.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    value = db.Column(db.String(20), nullable=False)  # helpful / unhelpful
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    def to_dict(self):
        return {
            "id": self.id,
            "audit_log_id": self.audit_log_id,
            "user_id": self.user_id,
            "value": self.value,
            "note": self.note,
            "created_at": self.created_at.isoformat(),
        }
