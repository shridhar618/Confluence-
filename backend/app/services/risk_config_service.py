"""
Bridges the Phase 1 RiskConfiguration table to the plain-dict shape
app.services.governance expects (DEFAULT_RISK_CONFIG). Kept separate from
governance.py itself so that module can stay Flask/DB-free and directly
testable (see docs/PHASE_9_NOTES.md for why that property matters here).
"""

from app.models.risk_configuration import RiskConfiguration
from app.services.governance import DEFAULT_RISK_CONFIG


def load_risk_config() -> dict:
    """Returns a dict shaped like DEFAULT_RISK_CONFIG. Any key an admin has
    disabled (enabled=False) falls back to the default rather than being
    dropped, so disabling a row never accidentally zeroes out a weight --
    it just stops that particular override from taking effect.
    """
    config = dict(DEFAULT_RISK_CONFIG)
    rows = RiskConfiguration.query.filter_by(enabled=True).all()
    for row in rows:
        if row.key in config:
            config[row.key] = row.value
    return config
