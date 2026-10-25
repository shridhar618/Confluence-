from flask import Blueprint, jsonify

from app.models.role import Role

roles_bp = Blueprint("roles", __name__)


@roles_bp.route("/roles", methods=["GET"])
def list_roles():
    roles = Role.query.order_by(Role.name.asc()).all()
    return jsonify({"roles": [role.to_dict() for role in roles]}), 200
