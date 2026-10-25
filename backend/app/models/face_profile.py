import json
from datetime import UTC, datetime

import numpy as np

from app import db


class FaceProfile(db.Model):
    __tablename__ = "face_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False, index=True)
    embedding = db.Column(db.Text, nullable=False)
    embedding_dim = db.Column(db.Integer, nullable=False)
    sample_hash = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    user = db.relationship("User", backref=db.backref("face_profile", uselist=False))

    def set_embedding(self, vector: np.ndarray) -> None:
        values = vector.astype(np.float32).tolist()
        self.embedding = json.dumps(values)
        self.embedding_dim = len(values)

    def get_embedding(self) -> np.ndarray:
        values = json.loads(self.embedding)
        return np.array(values, dtype=np.float32)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "embedding_dim": self.embedding_dim,
            "sample_hash": self.sample_hash,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
