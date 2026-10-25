from datetime import UTC, datetime

from app import db


class FavoriteQuestion(db.Model):
    __tablename__ = "favorite_questions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    question_id = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    __table_args__ = (
        db.UniqueConstraint("user_id", "question_id", name="uq_favorite_question_user_question"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "question_id": self.question_id,
            "created_at": self.created_at.isoformat(),
        }
