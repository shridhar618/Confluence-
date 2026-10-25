from datetime import UTC, datetime

from sqlalchemy import UniqueConstraint

from app import db


class ProjectMember(db.Model):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
    )

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))

    project = db.relationship("Project", back_populates="members")
    user = db.relationship("User", backref=db.backref("project_memberships", lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "user": self.user.to_dict() if self.user else None,
        }
