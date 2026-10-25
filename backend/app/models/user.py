from datetime import UTC, datetime

from app import db


class User(db.Model):
    __tablename__ = "users"

    id                   = db.Column(db.Integer, primary_key=True)
    username             = db.Column(db.String(80), unique=True, nullable=False)
    email                = db.Column(db.String(120), unique=True, nullable=False)
    password_hash        = db.Column(db.String(256), nullable=False)
    role                 = db.Column(db.String(20), nullable=False, default="intern")
    role_id              = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=True)
    login_code           = db.Column(db.String(32), nullable=True)
    created_at           = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    is_active            = db.Column(db.Boolean, default=True)
    role_ref             = db.relationship("Role", backref="users")

    # v2: suspicious-user tracking ─────────────────────────────────────────
    sensitive_query_count = db.Column(db.Integer, default=0)   # cumulative sensitive queries
    is_suspicious         = db.Column(db.Boolean, default=False)
    flagged_at            = db.Column(db.DateTime, nullable=True)
    # ───────────────────────────────────────────────────────────────────────

    def to_dict(self):
        return {
            "id":                   self.id,
            "username":             self.username,
            "email":                self.email,
            "role":                 self.role_ref.name.lower() if self.role_ref else self.role,
            "role_id":              self.role_id,
            "created_at":           self.created_at.isoformat(),
            "is_active":            self.is_active,
            "face_enrolled":        bool(getattr(self, "face_profile", None)),
            "sensitive_query_count":self.sensitive_query_count,
            "is_suspicious":        self.is_suspicious,
            "flagged_at":           self.flagged_at.isoformat() if self.flagged_at else None,
        }
