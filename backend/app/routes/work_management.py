import json
import logging
from datetime import UTC, datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.orm import joinedload

from app import db
from app.models.attendance_record import AttendanceRecord
from app.models.audit_log import AuditLog
from app.models.project import Project
from app.models.user import User
from app.models.work_assignment import WorkAssignment
from app.models.work_escalation import WorkEscalation
from app.models.work_progress_update import WorkProgressUpdate
from app.services.ai_service import get_ai_json_response
from app.services.roles import is_manager_role

work_management_bp = Blueprint("work_management", __name__)
logger = logging.getLogger(__name__)

ALLOWED_STATUSES = {"draft", "pending", "todo", "in_progress", "review", "blocked", "completed"}
BOARD_ALLOWED_STATUSES = {"draft", "todo", "in_progress", "review", "blocked", "completed"}
RISK_LEVEL_ORDER = {"low": 0, "medium": 1, "high": 2}
SUGGESTION_SEVERITIES = {"low", "medium", "high"}
SUGGESTION_IMPACTS = {"delay", "blocked", "risk"}


def _current_user():
    user_id = int(get_jwt_identity())
    return db.session.get(User, user_id)


def _is_admin_or_hr(user: User | None) -> bool:
    return bool(user and is_manager_role(user.role))


def _parse_due_date(value):
    if value in (None, ""):
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _compute_kpi(assignment: WorkAssignment):
    return assignment.compute_kpi()


def _board_status(value: str | None):
    if value == "pending":
        return "todo"
    return value or "todo"


def _parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _load_assignment_for_update(assignment_id: int):
    return (
        WorkAssignment.query
        .options(
            joinedload(WorkAssignment.progress_updates),
            joinedload(WorkAssignment.children),
            joinedload(WorkAssignment.parent),
        )
        .filter_by(id=assignment_id)
        .first()
    )


def _get_project(project_id):
    if project_id in (None, ""):
        return None
    try:
        project_id = int(project_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(Project, project_id)


def _assignment_query(actor: User, *, project_id=None, include_drafts=True, root_only=False):
    query = (
        WorkAssignment.query
        .options(
            joinedload(WorkAssignment.progress_updates),
            joinedload(WorkAssignment.children),
            joinedload(WorkAssignment.parent),
        )
        .order_by(WorkAssignment.created_at.desc())
    )

    if not _is_admin_or_hr(actor):
        query = query.filter_by(assigned_to_user_id=actor.id)
        if not include_drafts:
            query = query.filter(WorkAssignment.status != "draft")

    if project_id is not None:
        query = query.filter(WorkAssignment.project_id == project_id)
    if root_only:
        query = query.filter(WorkAssignment.parent_id.is_(None))
    return query


def _assignment_lineage(assignment: WorkAssignment):
    lineage = []
    for ancestor in reversed(list(assignment.iter_ancestors())):
        ancestor.sync_status_from_progress()
        lineage.append({
            "id": ancestor.id,
            "title": ancestor.title,
            "status": ancestor.status,
        })
    return lineage


def _validate_parent_link(assignment: WorkAssignment, parent: WorkAssignment | None):
    if parent is None:
        return None
    if parent.id == assignment.id:
        return "Assignments cannot parent themselves"
    if not assignment.can_parent_to(parent):
        return "Assignment hierarchy cannot contain cycles"
    if assignment.project_id and parent.project_id and assignment.project_id != parent.project_id:
        return "Parent and child assignments must belong to the same project"
    return None


def _serialize_assignment(assignment: WorkAssignment, include_progress=False, board_view=False, include_children=False):
    payload = assignment.to_dict(include_progress=include_progress, include_children=include_children)
    assigned_by = db.session.get(User, assignment.assigned_by_user_id)
    assigned_to = db.session.get(User, assignment.assigned_to_user_id)
    payload["assigned_by_username"] = assigned_by.username if assigned_by else None
    payload["assigned_to_username"] = assigned_to.username if assigned_to else None
    payload["assigned_by_user"] = assigned_by.to_dict() if assigned_by else None
    payload["assigned_to_user"] = assigned_to.to_dict() if assigned_to else None
    payload["project"] = assignment.project.to_dict() if assignment.project else None
    payload["parent"] = (
        {
            "id": assignment.parent.id,
            "title": assignment.parent.title,
            "status": assignment.parent.status,
        }
        if assignment.parent else None
    )
    payload["breadcrumbs"] = _assignment_lineage(assignment)
    payload["capacity_risk"] = _compute_capacity_risk(assignment)
    open_escalation = next((item for item in assignment.escalations if item.status == "open"), None)
    payload["open_escalation"] = _serialize_escalation(open_escalation) if open_escalation else None
    payload["children"] = []
    if include_children:
        payload["children"] = [
            _serialize_assignment(child, include_progress=include_progress, board_view=board_view, include_children=True)
            for child in assignment.children
        ]
    if board_view:
        payload["status"] = _board_status(payload.get("status"))
    return payload


def _compute_capacity_risk(assignment: WorkAssignment):
    kpi = _compute_kpi(assignment)
    completion_ratio = float(kpi["completion_ratio"] or 0)
    today = datetime.now(UTC).date()

    risk_level = "low"
    reasons = []

    def elevate(level: str, reason: str):
        nonlocal risk_level
        if RISK_LEVEL_ORDER[level] > RISK_LEVEL_ORDER[risk_level]:
            risk_level = level
        reasons.append(reason)

    due_date = assignment.normalized_due_date()
    if due_date and assignment.status != "completed":
        days_until_due = (due_date - today).days
        if days_until_due < 0:
            elevate("high", "Overdue and not completed.")
        elif days_until_due <= 2 and completion_ratio < 0.5:
            elevate("high", "Due within 2 days with low completion.")
        elif days_until_due <= 5 and completion_ratio < 0.75:
            elevate("medium", "Due soon with below-target completion.")

    if assignment.status != "completed":
        attendance_cutoff = datetime.now(UTC) - timedelta(days=3)
        recent_attendance = (
            AttendanceRecord.query
            .filter(
                AttendanceRecord.user_id == assignment.assigned_to_user_id,
                AttendanceRecord.created_at >= attendance_cutoff,
            )
            .order_by(AttendanceRecord.created_at.desc())
            .first()
        )
        if not recent_attendance:
            if risk_level == "high":
                elevate("high", "No recent attendance signal for assignee.")
            else:
                elevate("medium", "No recent attendance signal for assignee.")

        active_incomplete_count = (
            WorkAssignment.query
            .filter(
                WorkAssignment.assigned_to_user_id == assignment.assigned_to_user_id,
                WorkAssignment.status != "completed",
            )
            .count()
        )
        if active_incomplete_count >= 3:
            elevate("medium", "Assignee has many active incomplete assignments.")

    return {
        "level": risk_level,
        "reasons": reasons,
        "signals": {
            "completion_ratio": round(completion_ratio, 4),
            "days_until_due": (due_date - today).days if due_date else None,
        },
    }


def _serialize_escalation(escalation: WorkEscalation | None):
    if not escalation:
        return None
    payload = escalation.to_dict()
    assignment = escalation.assignment
    if assignment:
        payload["assignment"] = {
            "id": assignment.id,
            "title": assignment.title,
            "status": assignment.status,
        }
    else:
        payload["assignment"] = None
    return payload


def _summarize_assignment_for_ai(assignment: WorkAssignment):
    serialized = _serialize_assignment(assignment, include_progress=True)
    kpi = serialized.get("kpi") or {}
    risk = serialized.get("capacity_risk") or {}
    return {
        "id": assignment.id,
        "title": assignment.title,
        "assignee_username": serialized.get("assigned_to_username"),
        "status": assignment.status,
        "due_date": serialized.get("due_date"),
        "expected_units": kpi.get("expected_units"),
        "completed_units": kpi.get("total_completed_units"),
        "completion_ratio": kpi.get("completion_ratio"),
        "risk_level": risk.get("level"),
        "risk_reasons": risk.get("reasons") or [],
    }


def _build_escalation_suggestion_prompt(message: str, assignment_context: list[dict], system_signals: dict):
    return f"""
You are an enterprise operations assistant.

Your job is to analyze a manager's situation and generate a structured escalation suggestion.

IMPORTANT RULES:
* Be concise and practical
* Do NOT hallucinate unknown data
* Use only the provided context
* Output MUST be valid JSON
* No extra text outside JSON

MANAGER INPUT:
{message}

ASSIGNMENT CONTEXT:
{json.dumps(assignment_context, default=str)}

SYSTEM SIGNALS:
{json.dumps(system_signals, default=str)}

Return JSON in this exact format:
{{
  "reason": "short clear reason",
  "severity": "low | medium | high",
  "impact": "delay | blocked | risk",
  "summary": "1-2 sentence explanation of the situation",
  "suggestion": "clear actionable recommendation",
  "affected_assignment_ids": [1, 2],
  "draft_details": "natural language escalation note manager can submit"
}}
""".strip()


def _derive_suggestion_severity(assignment_context: list[dict]):
    if any(item.get("risk_level") == "high" or item.get("status") == "blocked" for item in assignment_context):
        return "high"
    if any(item.get("risk_level") == "medium" or item.get("status") == "in_progress" for item in assignment_context):
        return "medium"
    return "medium" if assignment_context else "low"


def _fallback_escalation_suggestion(message: str, assignment_context: list[dict]):
    assignment_titles = ", ".join(item["title"] for item in assignment_context) or "the selected work"
    return {
        "reason": "Operational risk detected",
        "severity": _derive_suggestion_severity(assignment_context),
        "impact": "delay",
        "summary": f"Manager reported an operational issue affecting {assignment_titles}.",
        "suggestion": "Review assignment ownership, rebalance work if needed, and escalate review with the accountable manager.",
        "affected_assignment_ids": [item["id"] for item in assignment_context],
        "draft_details": f"Operational escalation requested for {assignment_titles}: {message}",
    }


def _normalize_escalation_suggestion(raw: dict | None, message: str, assignment_context: list[dict]):
    fallback = _fallback_escalation_suggestion(message, assignment_context)
    data = raw if isinstance(raw, dict) else {}
    valid_ids = {item["id"] for item in assignment_context}

    def _text(field: str):
        value = data.get(field)
        return str(value).strip() if isinstance(value, str) and value.strip() else fallback[field]

    severity = str(data.get("severity", "")).strip().lower()
    if severity not in SUGGESTION_SEVERITIES:
        severity = fallback["severity"]

    impact = str(data.get("impact", "")).strip().lower()
    if impact not in SUGGESTION_IMPACTS:
        impact = fallback["impact"]

    affected_ids = []
    if isinstance(data.get("affected_assignment_ids"), list):
        for item in data["affected_assignment_ids"]:
            try:
                candidate_id = int(item)
            except (TypeError, ValueError):
                continue
            if candidate_id in valid_ids and candidate_id not in affected_ids:
                affected_ids.append(candidate_id)
    if not affected_ids:
        affected_ids = fallback["affected_assignment_ids"]

    affected_assignments = [item for item in assignment_context if item["id"] in affected_ids]

    return {
        "reason": _text("reason"),
        "severity": severity,
        "impact": impact,
        "summary": _text("summary"),
        "suggestion": _text("suggestion"),
        "affected_assignment_ids": affected_ids,
        "draft_details": _text("draft_details"),
        "affected_assignments": affected_assignments,
    }


def _write_audit_log(user: User, query: str):
    db.session.add(
        AuditLog(
            user_id=user.id,
            username=user.username,
            role=user.role,
            query=query,
            ai_response="work_management",
            filtered_response=None,
            status="allowed",
            risk_score=0.0,
            risk_level="low",
            reason="work-management action",
            triggered_rules="[]",
            validator_notes="[]",
            is_high_risk=False,
        )
    )


@work_management_bp.route("/work/assignments", methods=["POST"])
@jwt_required()
def create_assignment():
    actor = _current_user()
    if not _is_admin_or_hr(actor):
        return jsonify({"error": "Manager access required"}), 403

    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip() or None
    assigned_to_user_id = data.get("assigned_to_user_id")
    parent_id = data.get("parent_id")
    project_id = data.get("project_id")

    if not title:
        return jsonify({"error": "title is required"}), 400

    if not assigned_to_user_id:
        return jsonify({"error": "assigned_to_user_id is required"}), 400

    try:
        assigned_to_user_id = int(assigned_to_user_id)
        expected_units = float(data.get("expected_units", 0))
        weight = float(data.get("weight", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "expected_units, weight, and assigned_to_user_id must be numeric"}), 400

    if parent_id not in (None, ""):
        try:
            parent_id = int(parent_id)
        except (TypeError, ValueError):
            return jsonify({"error": "parent_id must be numeric"}), 400

    if expected_units <= 0:
        return jsonify({"error": "expected_units must be greater than 0"}), 400
    if weight < 0:
        return jsonify({"error": "weight must be 0 or greater"}), 400

    due_date = _parse_due_date(data.get("due_date"))
    if data.get("due_date") and not due_date:
        return jsonify({"error": "due_date must be in YYYY-MM-DD format"}), 400

    status = (data.get("status") or "pending").strip()
    if status not in ALLOWED_STATUSES:
        return jsonify({"error": "Invalid status"}), 400

    assignee = db.session.get(User, assigned_to_user_id)
    if not assignee or not assignee.is_active:
        return jsonify({"error": "Assigned user not found"}), 404

    parent = None
    if parent_id:
        parent = _load_assignment_for_update(parent_id)
        if not parent:
            return jsonify({"error": "Parent assignment not found"}), 404

    project = None
    if project_id not in (None, ""):
        project = _get_project(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

    if parent and project and parent.project_id and parent.project_id != project.id:
        return jsonify({"error": "Parent and child assignments must belong to the same project"}), 400
    if parent and not project and parent.project_id:
        project = parent.project
    if parent and parent.id == parent_id and parent_id == data.get("id"):
        return jsonify({"error": "Assignments cannot parent themselves"}), 400

    assignment = WorkAssignment(
        project_id=project.id if project else (parent.project_id if parent else None),
        parent_id=parent.id if parent else None,
        title=title,
        description=description,
        assigned_by_user_id=actor.id,
        assigned_to_user_id=assignee.id,
        expected_units=expected_units,
        weight=weight,
        github_issue_id=(data.get("github_issue_id") or "").strip() or None,
        github_branch=(data.get("github_branch") or "").strip() or None,
        due_date=due_date,
        status=status,
    )
    validation_error = _validate_parent_link(assignment, parent)
    if validation_error:
        return jsonify({"error": validation_error}), 400
    assignment.sync_status_from_progress()

    db.session.add(assignment)
    _write_audit_log(actor, f"Created work assignment '{title}' for {assignee.username}")
    db.session.commit()

    return jsonify({
        "message": "Assignment created",
        "assignment": _serialize_assignment(assignment, include_progress=True),
    }), 201


@work_management_bp.route("/work/assignments", methods=["GET"])
@jwt_required()
def list_assignments():
    actor = _current_user()
    if not actor:
        return jsonify({"error": "User not found"}), 404

    project_id = request.args.get("project_id", type=int)
    root_only = _parse_bool(request.args.get("root_only"))
    include_children = _parse_bool(request.args.get("include_children"))
    include_drafts = _is_admin_or_hr(actor) or _parse_bool(request.args.get("include_drafts"), default=False)
    query = _assignment_query(
        actor,
        project_id=project_id,
        include_drafts=include_drafts,
        root_only=root_only,
    )
    assignments = query.all()
    for assignment in assignments:
        assignment.sync_status_from_progress()
    db.session.commit()

    return jsonify({
        "assignments": [
            _serialize_assignment(item, include_progress=True, include_children=include_children)
            for item in assignments
        ],
        "count": len(assignments),
    }), 200


@work_management_bp.route("/work/board", methods=["GET"])
@jwt_required()
def get_work_board():
    actor = _current_user()
    if not _is_admin_or_hr(actor):
        return jsonify({"error": "Manager access required"}), 403

    assignments = (
        _assignment_query(actor, include_drafts=True, root_only=True).all()
    )
    for assignment in assignments:
        assignment.sync_status_from_progress()
    db.session.commit()

    return jsonify({
        "assignments": [
            _serialize_assignment(item, include_progress=True, board_view=True, include_children=True)
            for item in assignments
        ],
        "columns": ["todo", "in_progress", "blocked", "completed"],
        "count": len(assignments),
    }), 200


@work_management_bp.route("/work/assignments/<int:assignment_id>/progress", methods=["POST"])
@jwt_required()
def submit_progress_update(assignment_id):
    actor = _current_user()
    if not actor:
        return jsonify({"error": "User not found"}), 404

    assignment = (
        WorkAssignment.query
        .options(joinedload(WorkAssignment.progress_updates))
        .filter_by(id=assignment_id)
        .first()
    )
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404

    if assignment.assigned_to_user_id != actor.id:
        return jsonify({"error": "Only the assignee can submit progress"}), 403
    if assignment.has_children:
        return jsonify({"error": "Progress can only be submitted to leaf assignments"}), 400

    data = request.get_json() or {}
    try:
        completed_units = float(data.get("completed_units", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "completed_units must be numeric"}), 400

    if completed_units <= 0:
        return jsonify({"error": "completed_units must be greater than 0"}), 400

    note = (data.get("note") or "").strip() or None

    update = WorkProgressUpdate(
        assignment_id=assignment.id,
        reported_by_user_id=actor.id,
        completed_units=completed_units,
        note=note,
    )
    db.session.add(update)
    assignment.progress_updates.append(update)
    db.session.flush()

    assignment.sync_status_from_progress()
    _write_audit_log(actor, f"Submitted progress for assignment '{assignment.title}' ({completed_units} units)")
    db.session.commit()

    return jsonify({
        "message": "Progress update submitted",
        "progress_update": update.to_dict(),
        "assignment": _serialize_assignment(assignment, include_progress=True),
    }), 201


@work_management_bp.route("/work/assignments/<int:assignment_id>/status", methods=["PATCH"])
@jwt_required()
def update_assignment_status(assignment_id):
    actor = _current_user()
    if not _is_admin_or_hr(actor):
        return jsonify({"error": "Manager access required"}), 403

    assignment = _load_assignment_for_update(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404

    data = request.get_json() or {}
    status = (data.get("status") or "").strip()
    if status not in BOARD_ALLOWED_STATUSES:
        return jsonify({"error": "Invalid status"}), 400

    assignment.sync_status_from_progress()
    if assignment.has_children and status == "completed" and assignment.status != "completed":
        return jsonify({"error": "Parent assignments complete automatically when all descendants are completed"}), 400
    assignment.status = status
    assignment.sync_status_from_progress()
    _write_audit_log(actor, f"Updated assignment '{assignment.title}' status to {assignment.status}")
    db.session.commit()

    return jsonify({
        "message": "Assignment status updated",
        "assignment": _serialize_assignment(assignment, include_progress=True, board_view=True),
    }), 200


@work_management_bp.route("/work/assignments/<int:assignment_id>", methods=["PATCH"])
@jwt_required()
def update_assignment(assignment_id):
    actor = _current_user()
    if not _is_admin_or_hr(actor):
        return jsonify({"error": "Manager access required"}), 403

    assignment = _load_assignment_for_update(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404

    data = request.get_json() or {}
    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title cannot be empty"}), 400
        assignment.title = title

    if "description" in data:
        assignment.description = (data.get("description") or "").strip() or None

    if "assigned_to_user_id" in data:
        try:
            assigned_to_user_id = int(data.get("assigned_to_user_id"))
        except (TypeError, ValueError):
            return jsonify({"error": "assigned_to_user_id must be numeric"}), 400
        assignee = db.session.get(User, assigned_to_user_id)
        if not assignee or not assignee.is_active:
            return jsonify({"error": "Assigned user not found"}), 404
        assignment.assigned_to_user_id = assignee.id

    if "expected_units" in data:
        try:
            expected_units = float(data.get("expected_units"))
        except (TypeError, ValueError):
            return jsonify({"error": "expected_units must be numeric"}), 400
        if expected_units <= 0:
            return jsonify({"error": "expected_units must be greater than 0"}), 400
        assignment.expected_units = expected_units

    if "weight" in data:
        try:
            weight = float(data.get("weight"))
        except (TypeError, ValueError):
            return jsonify({"error": "weight must be numeric"}), 400
        if weight < 0:
            return jsonify({"error": "weight must be 0 or greater"}), 400
        assignment.weight = weight

    if "due_date" in data:
        due_date = _parse_due_date(data.get("due_date"))
        if data.get("due_date") and not due_date:
            return jsonify({"error": "due_date must be in YYYY-MM-DD format"}), 400
        assignment.due_date = due_date

    if "github_issue_id" in data:
        assignment.github_issue_id = (data.get("github_issue_id") or "").strip() or None
    if "github_branch" in data:
        assignment.github_branch = (data.get("github_branch") or "").strip() or None

    if "parent_id" in data:
        parent_id = data.get("parent_id")
        if parent_id in (None, ""):
            parent = None
        else:
            try:
                parent_id = int(parent_id)
            except (TypeError, ValueError):
                return jsonify({"error": "parent_id must be numeric"}), 400
            parent = _load_assignment_for_update(parent_id)
            if not parent:
                return jsonify({"error": "Parent assignment not found"}), 404
        validation_error = _validate_parent_link(assignment, parent)
        if validation_error:
            return jsonify({"error": validation_error}), 400
        assignment.parent = parent
        if parent and parent.project_id and assignment.project_id is None:
            assignment.project_id = parent.project_id

    assignment.sync_status_from_progress()
    _write_audit_log(actor, f"Updated assignment '{assignment.title}'")
    db.session.commit()

    return jsonify({
        "message": "Assignment updated",
        "assignment": _serialize_assignment(assignment, include_progress=True, include_children=True),
    }), 200


@work_management_bp.route("/work/assignments/<int:assignment_id>", methods=["DELETE"])
@jwt_required()
def delete_assignment(assignment_id):
    actor = _current_user()
    if not _is_admin_or_hr(actor):
        return jsonify({"error": "Manager access required"}), 403

    assignment = _load_assignment_for_update(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
    if assignment.has_children:
        # Block parent deletion so task trees cannot be accidentally detached or partially removed.
        return jsonify({"error": "Cannot delete an assignment that still has child assignments"}), 400

    title = assignment.title
    db.session.delete(assignment)
    _write_audit_log(actor, f"Deleted assignment '{title}'")
    db.session.commit()
    return jsonify({"message": "Assignment deleted"}), 200


@work_management_bp.route("/work/assignments/<int:assignment_id>/children", methods=["GET"])
@jwt_required()
def get_assignment_children(assignment_id):
    actor = _current_user()
    if not actor:
        return jsonify({"error": "User not found"}), 404

    assignment = _load_assignment_for_update(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
    if not _is_admin_or_hr(actor) and assignment.assigned_to_user_id != actor.id:
        return jsonify({"error": "Access denied"}), 403

    assignment.sync_status_from_progress()
    return jsonify({
        "assignment": _serialize_assignment(assignment, include_progress=True),
        "children": [_serialize_assignment(child, include_progress=True, include_children=True) for child in assignment.children],
        "count": len(assignment.children),
    }), 200


@work_management_bp.route("/work/assignments/<int:assignment_id>/tree", methods=["GET"])
@jwt_required()
def get_assignment_tree(assignment_id):
    actor = _current_user()
    if not actor:
        return jsonify({"error": "User not found"}), 404

    assignment = _load_assignment_for_update(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
    if not _is_admin_or_hr(actor) and assignment.assigned_to_user_id != actor.id:
        return jsonify({"error": "Access denied"}), 403

    assignment.sync_status_from_progress()
    return jsonify({
        "assignment": _serialize_assignment(assignment, include_progress=True, include_children=True),
    }), 200


@work_management_bp.route("/work/escalations", methods=["POST"])
@jwt_required()
def create_work_escalation():
    actor = _current_user()
    if not _is_admin_or_hr(actor):
        return jsonify({"error": "Manager access required"}), 403

    data = request.get_json() or {}
    assignment_id = data.get("assignment_id")
    if not assignment_id:
        return jsonify({"error": "assignment_id is required"}), 400

    try:
        assignment_id = int(assignment_id)
    except (TypeError, ValueError):
        return jsonify({"error": "assignment_id must be numeric"}), 400

    assignment = db.session.get(WorkAssignment, assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404

    existing_open = (
        WorkEscalation.query
        .filter_by(assignment_id=assignment.id, status="open")
        .order_by(WorkEscalation.created_at.desc())
        .first()
    )
    if existing_open:
        return jsonify({"error": "An open escalation already exists for this assignment"}), 400

    escalation = WorkEscalation(
        assignment_id=assignment.id,
        created_by_user_id=actor.id,
        reason=(data.get("reason") or data.get("note") or "").strip() or None,
        status="open",
    )
    db.session.add(escalation)
    _write_audit_log(actor, f"Escalated assignment '{assignment.title}'")
    db.session.commit()

    return jsonify({
        "message": "Escalation created",
        "escalation": _serialize_escalation(escalation),
    }), 201


@work_management_bp.route("/work/escalations", methods=["GET"])
@jwt_required()
def list_work_escalations():
    actor = _current_user()
    if not _is_admin_or_hr(actor):
        return jsonify({"error": "Manager access required"}), 403

    escalations = (
        WorkEscalation.query
        .options(joinedload(WorkEscalation.assignment))
        .order_by(WorkEscalation.created_at.desc())
        .all()
    )

    return jsonify({
        "escalations": [_serialize_escalation(item) for item in escalations],
        "count": len(escalations),
    }), 200


@work_management_bp.route("/work/escalations/suggest", methods=["POST"])
@jwt_required()
def suggest_work_escalation():
    actor = _current_user()
    if not _is_admin_or_hr(actor):
        return jsonify({"error": "Admin/HR access required"}), 403

    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    assignment_ids = []
    for raw_id in data.get("assignment_ids") or []:
        try:
            assignment_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if assignment_id not in assignment_ids:
            assignment_ids.append(assignment_id)

    assignments_query = WorkAssignment.query.options(joinedload(WorkAssignment.progress_updates))
    if assignment_ids:
        assignments_query = assignments_query.filter(WorkAssignment.id.in_(assignment_ids))
    else:
        assignments_query = assignments_query.filter(WorkAssignment.status != "completed").order_by(WorkAssignment.created_at.desc()).limit(3)
    assignments = assignments_query.all()
    for assignment in assignments:
        assignment.sync_status_from_progress()
    db.session.commit()

    assignment_context = [_summarize_assignment_for_ai(item) for item in assignments]
    system_signals = {
        "include_team_context": bool(data.get("include_team_context", True)),
        "selected_assignment_count": len(assignment_context),
        "generated_at": datetime.now(UTC).isoformat(),
    }

    raw_suggestion = None
    try:
        raw_suggestion = get_ai_json_response(
            _build_escalation_suggestion_prompt(message, assignment_context, system_signals),
            system_prompt="Return only valid JSON for an operational escalation suggestion.",
            temperature=0.2,
            max_output_tokens=900,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("AI escalation suggestion failed; using deterministic fallback: %s", exc)

    suggestion = _normalize_escalation_suggestion(raw_suggestion, message, assignment_context)
    return jsonify(suggestion), 200


@work_management_bp.route("/work/escalations/<int:escalation_id>", methods=["PATCH"])
@jwt_required()
def update_work_escalation(escalation_id):
    actor = _current_user()
    if not _is_admin_or_hr(actor):
        return jsonify({"error": "Manager access required"}), 403

    escalation = (
        WorkEscalation.query
        .options(joinedload(WorkEscalation.assignment))
        .filter_by(id=escalation_id)
        .first()
    )
    if not escalation:
        return jsonify({"error": "Escalation not found"}), 404

    status = (request.get_json() or {}).get("status", "").strip()
    if status != "resolved":
        return jsonify({"error": "Only resolution to 'resolved' is supported"}), 400
    if escalation.status == "resolved":
        return jsonify({"error": "Escalation is already resolved"}), 400

    escalation.status = "resolved"
    _write_audit_log(actor, f"Resolved escalation for assignment '{escalation.assignment.title if escalation.assignment else escalation.assignment_id}'")
    db.session.commit()

    return jsonify({
        "message": "Escalation updated",
        "escalation": _serialize_escalation(escalation),
    }), 200


@work_management_bp.route("/work/assignments/<int:assignment_id>/kpi", methods=["GET"])
@jwt_required()
def get_assignment_kpi(assignment_id):
    actor = _current_user()
    if not actor:
        return jsonify({"error": "User not found"}), 404

    assignment = (
        WorkAssignment.query
        .options(joinedload(WorkAssignment.progress_updates))
        .filter_by(id=assignment_id)
        .first()
    )
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404

    if not _is_admin_or_hr(actor) and assignment.assigned_to_user_id != actor.id:
        return jsonify({"error": "Access denied"}), 403

    assignment.sync_status_from_progress()
    db.session.commit()

    return jsonify({
        "assignment_id": assignment.id,
        "status": assignment.status,
        "kpi": _compute_kpi(assignment),
        "capacity_risk": _compute_capacity_risk(assignment),
    }), 200
