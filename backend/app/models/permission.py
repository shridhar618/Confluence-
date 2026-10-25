from datetime import UTC, datetime

from app import db

role_permissions = db.Table(
    "role_permissions",
    db.Column("id", db.Integer, primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), nullable=False),
    db.Column("permission_id", db.Integer, db.ForeignKey("permissions.id"), nullable=False),
    db.Column("created_at", db.DateTime, nullable=False, default=lambda: datetime.now(UTC)),
    db.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
)


class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False, default="general")
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    roles = db.relationship(
        "Role",
        secondary=role_permissions,
        lazy=True,
        backref=db.backref("permissions", lazy=True),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
        }
