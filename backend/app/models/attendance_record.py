from datetime import UTC, datetime

from app import db


class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    event_type = db.Column(db.String(20), nullable=False)  # check_in / check_out
    confidence = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(30), nullable=False, default="face_recognition")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), index=True)

    user = db.relationship("User", backref=db.backref("attendance_records", lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "event_type": self.event_type,
            "confidence": round(float(self.confidence), 4),
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
