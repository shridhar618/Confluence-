"""
Phase 12 — comprehensive audit logging.

AI chat requests already write their own richly-populated AuditLog rows in
routes/chat.py (with risk score, triggered rules, policy evidence, etc.).
This service covers everything else the brief asks to be auditable --
login, logout, admin actions, configuration and policy changes -- so all
of it lands in ONE audit trail rather than being split across tables.

Non-chat events reuse the same AuditLog row with event_type set, and leave
the AI-specific columns (ai_response, triggered_rules, ...) null. The
`query` column carries a short human-readable description of what
happened, so the existing audit log UI and CSV export render these rows
sensibly without needing a separate code path.
"""

import json

from app import db
from app.models.audit_log import AuditLog

# Event types recorded by this service. AI chat requests use "ai_request"
# (written directly in routes/chat.py) and permission denials on the chat
# endpoint use "permission_denied".
EVENT_TYPES = [
    "login",
    "logout",
    "login_failed",
    "admin_action",
    "risk_config_change",
    "policy_change",
    "role_change",
    "user_created",
    "security_event",
]


def record_audit_event(
    event_type: str,
    user=None,
    description: str = "",
    resource: str = None,
    status: str = "allowed",
    risk_level: str = "low",
    reason: str = None,
    metadata: dict = None,
    commit: bool = True,
):
    """Writes a non-chat audit row.

    commit=False lets a caller batch this into an existing transaction
    (e.g. record the action and update the case status atomically) --
    the caller is then responsible for committing.
    """
    entry = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "system",
        role=user.role if user else "system",
        query=description,
        status=status,
        risk_score=0.0,
        risk_level=risk_level,
        reason=reason,
        is_high_risk=False,
        event_type=event_type,
        resource=resource,
        event_metadata=json.dumps(metadata) if metadata else None,
    )
    db.session.add(entry)
    if commit:
        db.session.commit()
    return entry
