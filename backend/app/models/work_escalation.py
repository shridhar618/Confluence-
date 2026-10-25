from datetime import UTC, datetime

from app import db


class WorkEscalation(db.Model):
    __tablename__ = "work_escalations"

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("work_assignments.id"), nullable=False)
    created_by_user_id = db.Column("raised_by_user_id", db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column("note", db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="open")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)

    assignment = db.relationship("WorkAssignment", backref=db.backref("escalations", lazy=True, cascade="all, delete-orphan"))
    created_by = db.relationship("User", backref=db.backref("work_escalations", lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "assignment_id": self.assignment_id,
            "reason": self.reason,
            "status": self.status,
            "created_by_user_id": self.created_by_user_id,
            "created_by_username": self.created_by.username if self.created_by else None,
            "assignment_title": self.assignment.title if self.assignment else None,
            "created_at": self.created_at.isoformat(),
        }
