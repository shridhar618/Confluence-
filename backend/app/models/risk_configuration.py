from datetime import UTC, datetime

from app import db

# category values: "weight" (per-rule scoring weight), "threshold"
# (score boundary, e.g. low/medium/high cutoffs or the cumulative-risk
# threshold that opens a GovernanceCase). Keeping both in one table (rather
# than separate Weight/Threshold tables) matches Phase 1's "do not
# over-normalize" guidance -- there is one admin screen either way.


class RiskConfiguration(db.Model):
    __tablename__ = "risk_configurations"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    category = db.Column(db.String(20), nullable=False)  # "weight" | "threshold"
    value = db.Column(db.Float, nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "category": self.category,
            "value": self.value,
            "enabled": self.enabled,
            "description": self.description,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
