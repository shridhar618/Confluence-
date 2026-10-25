"""
Phase 11 — Admin Governance Case Management.

Every status transition happens through _status_for_action(), a pure
function (no Flask/DB) so it can be verified the same way governance.py's
logic has been throughout this build -- see docs/PHASE_11_NOTES.md.
"""

from datetime import UTC, datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app import db
from app.models.admin_action import ACTION_TYPES, AdminAction
from app.models.governance_case import GovernanceCase
from app.models.user import User
from app.services.audit import record_audit_event
from app.utils.authz import get_current_user, require_permission

governance_cases_bp = Blueprint("governance_cases", __name__)


def _status_for_action(action_type: str, current_status: str) -> str:
    """Pure mapping from an admin action to the case's new status. Kept
    outside the route handler and free of any Flask/DB reference so it can
    be unit-tested in isolation (see docs/PHASE_11_NOTES.md).

    "review" only moves a fresh case into under_review -- taking it again
    on an already-further-along case (e.g. warned) doesn't reset progress.
    "note" never changes status; it's a log entry only.
    """
    if action_type == "note":
        return current_status
    if action_type == "review":
        return "under_review" if current_status == "open" else current_status
    return {
        "warn": "warned",
        "restrict": "restricted",
        "restore": "under_review",  # access restored, but case stays open for admin follow-up rather than snapping back to "open" (implies untouched) or "resolved" (implies fully closed)
        "escalate": "escalated",
        "resolve": "resolved",
    }.get(action_type, current_status)


@governance_cases_bp.route("/governance-cases", methods=["GET"])
@jwt_required()
@require_permission("ai_governance_admin")
def list_cases():
    status_filter = request.args.get("status")
    query = GovernanceCase.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    cases = query.order_by(GovernanceCase.created_at.desc()).all()
    return jsonify({"cases": [case.to_dict() for case in cases]}), 200


@governance_cases_bp.route("/governance-cases/<int:case_id>", methods=["GET"])
@jwt_required()
@require_permission("ai_governance_admin")
def get_case(case_id):
    case = GovernanceCase.query.get(case_id)
    if not case:
        return jsonify({"error": "Case not found"}), 404
    return jsonify({"case": case.to_dict(include_events=True, include_actions=True)}), 200


@governance_cases_bp.route("/governance-cases/<int:case_id>/actions", methods=["POST"])
@jwt_required()
@require_permission("ai_governance_admin")
def take_action(case_id):
    admin = get_current_user()
    case = GovernanceCase.query.get(case_id)
    if not case:
        return jsonify({"error": "Case not found"}), 404

    data = request.get_json() or {}
    action_type = data.get("action_type")
    note = (data.get("note") or "").strip() or None

    if action_type not in ACTION_TYPES:
        return jsonify({"error": f"action_type must be one of {ACTION_TYPES}"}), 400

    action = AdminAction(case_id=case.id, admin_id=admin.id, action_type=action_type, note=note)
    db.session.add(action)

    previous_status = case.status
    case.status = _status_for_action(action_type, case.status)
    if not case.assigned_admin_id:
        case.assigned_admin_id = admin.id
    if action_type == "resolve":
        case.resolved_at = datetime.now(UTC)

    record_audit_event(
        "admin_action",
        user=admin,
        description=f"Admin action '{action_type}' on case {case.case_code()} (user: {case.user.username if case.user else 'unknown'})",
        resource=case.case_code(),
        reason=note,
        metadata={
            "action_type": action_type,
            "previous_status": previous_status,
            "new_status": case.status,
            "case_id": case.id,
        },
        commit=False,  # committed together with the case update below
    )

    db.session.commit()
    return jsonify({"case": case.to_dict(include_events=True, include_actions=True)}), 200
