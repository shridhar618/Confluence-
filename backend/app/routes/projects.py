from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from app.models.project import Project
from app.models.user import User
from app.services.roles import is_manager_role

projects_bp = Blueprint("projects", __name__)


def _current_user():
    user_id = int(get_jwt_identity())
    return db.session.get(User, user_id)


def _require_manager():
    user = _current_user()
    return user if user and is_manager_role(user.role) else None


def _get_project(project_id: int):
    return db.session.get(Project, project_id)


def _serialize_project(project: Project):
    payload = project.to_dict(include_members=True)
    payload["members"] = sorted(
        payload.get("members", []),
        key=lambda item: ((item.get("user") or {}).get("username") or "").lower(),
    )
    return payload


@projects_bp.route("/projects", methods=["GET"])
@jwt_required()
def list_projects():
    actor = _require_manager()
    if not actor:
        return jsonify({"error": "Manager access required"}), 403

    include_archived = request.args.get("include_archived", "true").strip().lower() != "false"
    query = Project.query.order_by(Project.is_archived.asc(), Project.updated_at.desc())
    if not include_archived:
        query = query.filter(Project.is_archived == False)

    projects = query.all()
    return jsonify({
        "projects": [_serialize_project(project) for project in projects],
        "count": len(projects),
    }), 200


@projects_bp.route("/projects", methods=["POST"])
@jwt_required()
def create_project():
    actor = _require_manager()
    if not actor:
        return jsonify({"error": "Manager access required"}), 403

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip() or None

    if not name:
        return jsonify({"error": "name is required"}), 400

    existing = Project.query.filter(Project.name.ilike(name)).first()
    if existing:
        return jsonify({"error": "Project name already exists"}), 409

    project = Project(name=name, description=description)
    db.session.add(project)
    db.session.commit()

    return jsonify({"project": _serialize_project(project)}), 201


@projects_bp.route("/projects/<int:project_id>", methods=["PATCH"])
@jwt_required()
def update_project(project_id):
    actor = _require_manager()
    if not actor:
        return jsonify({"error": "Manager access required"}), 403

    project = _get_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json() or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name cannot be empty"}), 400
        existing = Project.query.filter(Project.id != project.id, Project.name.ilike(name)).first()
        if existing:
            return jsonify({"error": "Project name already exists"}), 409
        project.name = name

    if "description" in data:
        project.description = (data.get("description") or "").strip() or None

    if "is_archived" in data:
        project.is_archived = bool(data.get("is_archived"))

    db.session.commit()
    return jsonify({"project": _serialize_project(project)}), 200


@projects_bp.route("/projects/<int:project_id>/members", methods=["POST"])
@jwt_required()
def add_project_member(project_id):
    actor = _require_manager()
    if not actor:
        return jsonify({"error": "Manager access required"}), 403

    project = _get_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json() or {}
    user_id = data.get("user_id")
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "user_id must be numeric"}), 400

    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return jsonify({"error": "User not found"}), 404

    if user in project.members:
        return jsonify({"error": "User is already assigned to this project"}), 409

    project.members.append(user)
    db.session.commit()

    return jsonify({
        "project": _serialize_project(project),
        "membership": {
            "project_id": project.id,
            "user_id": user.id,
            "user": user.to_dict(),
        },
    }), 201


@projects_bp.route("/projects/<int:project_id>/members/<int:user_id>", methods=["DELETE"])
@jwt_required()
def remove_project_member(project_id, user_id):
    actor = _require_manager()
    if not actor:
        return jsonify({"error": "Manager access required"}), 403

    project = _get_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    user = db.session.get(User, user_id)
    if not user or user not in project.members:
        return jsonify({"error": "Project member not found"}), 404

    project.members.remove(user)
    db.session.commit()
    return jsonify({"project": _serialize_project(project)}), 200
