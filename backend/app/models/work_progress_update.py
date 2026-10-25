from datetime import UTC, datetime

from app import db


class WorkProgressUpdate(db.Model):
    __tablename__ = "work_progress_updates"

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("work_assignments.id"), nullable=False)
    reported_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    completed_units = db.Column(db.Float, nullable=False, default=0)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)

    reported_by = db.relationship("User", backref=db.backref("work_progress_updates", lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "assignment_id": self.assignment_id,
            "reported_by_user_id": self.reported_by_user_id,
            "reported_by_username": self.reported_by.username if self.reported_by else None,
            "completed_units": float(self.completed_units or 0),
            "note": self.note,
            "created_at": self.created_at.isoformat(),
        }
