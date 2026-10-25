"""
Phase 10 — cumulative risk tracking + automatic escalation.

Two distinct alert behaviors, matching the capstone brief's two separate
demo workflows:

  Demo 2 (single sensitive request): any individual HIGH-risk request
  generates an immediate admin notification, regardless of the user's
  history -- a single serious attempt shouldn't wait for a pattern.

  Demo 3 (repeated risk): risk from medium/high requests accumulates per
  user. When the running total crosses the admin-configured
  cumulative_risk_case_threshold, a GovernanceCase is opened automatically
  and a separate notification is sent -- but the case starts at status
  "open", not "restricted". Per Phase 10's principle, the system never
  imposes a consequential restriction on its own; only a human
  administrator's AdminAction (Phase 11) can do that.

LOW-risk requests are intentionally not tracked here at all -- cumulative
tracking exists to catch a pattern of *risky* behavior, not to accumulate
noise from routine, allowed usage.
"""

import json

from app import db
from app.models.governance_case import GovernanceCase
from app.models.risk_event import RiskEvent
from app.services.governance import DEFAULT_RISK_CONFIG
from app.services.notifications import emit_pending, notify_admins


def record_risk_event(user, audit_log, result, risk_config=None):
    """Call after an AuditLog row has been committed for a chat request.
    Returns the created RiskEvent, or None if the request was low-risk and
    nothing needed tracking.
    """
    if result.risk_level not in ("medium", "high"):
        return None

    config = risk_config or DEFAULT_RISK_CONFIG
    threshold = config.get("cumulative_risk_case_threshold", DEFAULT_RISK_CONFIG["cumulative_risk_case_threshold"])

    last_event = (
        RiskEvent.query.filter_by(user_id=user.id)
        .order_by(RiskEvent.created_at.desc())
        .first()
    )
    previous_cumulative = last_event.cumulative_score if last_event else 0.0
    new_cumulative = previous_cumulative + result.risk_score

    # Any case not yet resolved counts as "already being handled" -- checking
    # strictly for status=="open" would let a duplicate case get created for
    # a user whose case an admin has already moved to under_review/warned/
    # restricted/escalated (see docs/PHASE_10_NOTES.md, flagged there before
    # Phase 11 existed to introduce these transitions).
    existing_case = (
        GovernanceCase.query
        .filter(GovernanceCase.user_id == user.id, GovernanceCase.status != "resolved")
        .order_by(GovernanceCase.created_at.desc())
        .first()
    )

    event = RiskEvent(
        user_id=user.id,
        audit_log_id=audit_log.id,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        factors=json.dumps((result.triggered_rules or []) + (result.validator_notes or [])),
        cumulative_score=new_cumulative,
        case_id=existing_case.id if existing_case else None,
    )
    db.session.add(event)
    db.session.flush()  # assign event.id before we might reference it

    pending_notifications = []

    # Demo 2: immediate alert on any single high-risk request.
    if result.risk_level == "high":
        pending_notifications += notify_admins(
            "high_risk_request",
            (
                f"High-risk AI request from {user.username} ({user.role}): "
                f"{result.reason or 'see audit log for details'}"
            ),
            commit=False,
        )

    # Demo 3: cumulative threshold crossed -> open a case (if one isn't
    # already open for this user) and notify separately.
    if not existing_case and new_cumulative >= threshold:
        new_case = GovernanceCase(
            user_id=user.id,
            status="open",
            trigger=(
                f"Cumulative risk score {new_cumulative:.2f} exceeded the configured "
                f"threshold of {threshold:.2f} following a {result.risk_level}-risk request."
            ),
            risk_score_at_open=new_cumulative,
        )
        db.session.add(new_case)
        db.session.flush()
        event.case_id = new_case.id

        pending_notifications += notify_admins(
            "governance_case_opened",
            (
                f"New governance case {new_case.case_code()} opened for "
                f"{user.username} (cumulative risk {new_cumulative:.2f})."
            ),
            related_case_id=new_case.id,
            commit=False,
        )

    db.session.commit()
    # Emitted only after the commit succeeds, so an admin is never alerted
    # about a case that failed to persist.
    emit_pending(pending_notifications)
    return event
