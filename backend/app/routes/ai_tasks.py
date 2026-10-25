from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from app.models.audit_log import AuditLog
from app.models.project import Project
from app.models.user import User
from app.models.work_assignment import WorkAssignment
from app.services.roles import is_manager_role

ai_tasks_bp = Blueprint("ai_tasks", __name__)


def _current_user():
    user_id = int(get_jwt_identity())
    return db.session.get(User, user_id)


def _require_manager():
    user = _current_user()
    return user if user and is_manager_role(user.role) else None


def _get_project_or_404(project_id: int):
    project = db.session.get(Project, project_id)
    if not project:
        return None, (jsonify({"error": "Project not found"}), 404)
    return project, None


def _parse_due_date(value):
    if value in (None, ""):
        return None
    if hasattr(value, "isoformat"):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def _write_audit_log(user: User, query: str):
    db.session.add(
        AuditLog(
            user_id=user.id,
            username=user.username,
            role=user.role,
            query=query,
            ai_response="ai_task_pipeline",
            filtered_response=None,
            status="allowed",
            risk_score=0.0,
            risk_level="low",
            reason="ai-task workflow action",
            triggered_rules="[]",
            validator_notes="[]",
            is_high_risk=False,
        )
    )


def _normalize_task_items(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("tasks"), list):
        return payload["tasks"]
    return None


def _serialize_task(task: WorkAssignment):
    payload = task.to_dict(include_progress=True)
    payload["project"] = task.project.to_dict() if task.project else None
    return payload


@ai_tasks_bp.route("/projects/<int:project_id>/tasks/ai-generate", methods=["POST"])
@jwt_required()
def generate_ai_tasks(project_id):
    actor = _require_manager()
    if not actor:
        return jsonify({"error": "Manager access required"}), 403

    project, error_response = _get_project_or_404(project_id)
    if error_response:
        return error_response
    if project.is_archived:
        return jsonify({"error": "Cannot generate tasks for an archived project"}), 400

    items = _normalize_task_items(request.get_json(silent=True))
    if items is None:
        return jsonify({"error": "Request body must be a JSON array of tasks or an object with a tasks array"}), 400
    if not items:
        return jsonify({"error": "At least one AI-generated task is required"}), 400

    created_tasks = []
    try:
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                return jsonify({"error": f"Task at index {index} must be an object"}), 400

            title = (item.get("title") or item.get("name") or "").strip()
            if not title:
                return jsonify({"error": f"title is required for task at index {index}"}), 400

            try:
                assigned_to_user_id = int(item.get("assigned_to_user_id") or actor.id)
                expected_units = float(item.get("expected_units", 1) or 1)
                weight = float(item.get("weight", 1) or 1)
            except (TypeError, ValueError):
                return jsonify({"error": f"Task at index {index} has non-numeric assignment, expected_units, or weight values"}), 400

            if expected_units <= 0:
                return jsonify({"error": f"expected_units must be greater than 0 for task at index {index}"}), 400
            if weight < 0:
                return jsonify({"error": f"weight must be 0 or greater for task at index {index}"}), 400

            assignee = db.session.get(User, assigned_to_user_id)
            if not assignee or not assignee.is_active:
                return jsonify({"error": f"assigned_to_user_id for task at index {index} was not found"}), 404

            due_date = _parse_due_date(item.get("due_date"))
            if item.get("due_date") and not due_date:
                return jsonify({"error": f"due_date must be YYYY-MM-DD for task at index {index}"}), 400

            assignment = WorkAssignment(
                project_id=project.id,
                title=title,
                description=(item.get("description") or "").strip() or None,
                assigned_by_user_id=actor.id,
                assigned_to_user_id=assignee.id,
                expected_units=expected_units,
                weight=weight,
                due_date=due_date,
                github_issue_id=(item.get("github_issue_id") or item.get("issue_id") or "").strip() or None,
                github_branch=(item.get("github_branch") or "").strip() or None,
                status="draft",
            )
            db.session.add(assignment)
            created_tasks.append(assignment)

        _write_audit_log(actor, f"Generated {len(created_tasks)} AI tasks for project '{project.name}'")
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({
        "message": f"Successfully generated {len(created_tasks)} draft tasks",
        "project": project.to_dict(),
        "tasks": [_serialize_task(task) for task in created_tasks],
        "count": len(created_tasks),
    }), 201


@ai_tasks_bp.route("/projects/<int:project_id>/tasks/pending", methods=["GET"])
@jwt_required()
def list_pending_ai_tasks(project_id):
    actor = _require_manager()
    if not actor:
        return jsonify({"error": "Manager access required"}), 403

    project, error_response = _get_project_or_404(project_id)
    if error_response:
        return error_response

    tasks = (
        WorkAssignment.query
        .filter_by(project_id=project.id, status="draft")
        .order_by(WorkAssignment.created_at.desc())
        .all()
    )

    return jsonify({
        "project": project.to_dict(),
        "tasks": [_serialize_task(task) for task in tasks],
        "count": len(tasks),
    }), 200


@ai_tasks_bp.route("/projects/<int:project_id>/tasks/approve", methods=["POST"])
@jwt_required()
def approve_ai_tasks(project_id):
    actor = _require_manager()
    if not actor:
        return jsonify({"error": "Manager access required"}), 403

    project, error_response = _get_project_or_404(project_id)
    if error_response:
        return error_response

    payload = request.get_json(silent=True)
    task_ids = payload if isinstance(payload, list) else (payload or {}).get("task_ids")
    if not isinstance(task_ids, list) or not task_ids:
        return jsonify({"error": "Request body must be a JSON array of task IDs or an object with task_ids"}), 400

    try:
        normalized_ids = sorted({int(task_id) for task_id in task_ids})
    except (TypeError, ValueError):
        return jsonify({"error": "All task_ids must be numeric"}), 400

    tasks = (
        WorkAssignment.query
        .filter(
            WorkAssignment.project_id == project.id,
            WorkAssignment.id.in_(normalized_ids),
            WorkAssignment.status == "draft",
        )
        .all()
    )
    found_ids = {task.id for task in tasks}
    missing_ids = [task_id for task_id in normalized_ids if task_id not in found_ids]
    if missing_ids:
        return jsonify({
            "error": "Some tasks were not found in draft state for this project",
            "task_ids": missing_ids,
        }), 404

    for task in tasks:
        task.status = "todo"

    _write_audit_log(actor, f"Approved {len(tasks)} AI tasks for project '{project.name}'")
    db.session.commit()

    return jsonify({
        "message": "Draft tasks approved",
        "project": project.to_dict(),
        "tasks": [_serialize_task(task) for task in tasks],
        "count": len(tasks),
    }), 200
