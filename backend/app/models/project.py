from datetime import UTC, datetime

from app import db

project_members = db.Table(
    "project_members",
    db.Column("id", db.Integer, primary_key=True),
    db.Column("project_id", db.Integer, db.ForeignKey("projects.id"), nullable=False),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), nullable=False),
    db.Column("created_at", db.DateTime, nullable=False, default=lambda: datetime.now(UTC)),
    db.UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
)


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    work_assignments = db.relationship(
        "WorkAssignment",
        back_populates="project",
        lazy=True,
    )
    members = db.relationship(
        "User",
        secondary=project_members,
        lazy=True,
        backref=db.backref("projects", lazy=True),
    )

    def to_dict(self, include_members=False):
        payload = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_archived": self.is_archived,
            "member_count": len(self.members),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_members:
            payload["members"] = [
                {
                    "user_id": member.id,
                    "user": member.to_dict(),
                }
                for member in self.members
            ]
        return payload
