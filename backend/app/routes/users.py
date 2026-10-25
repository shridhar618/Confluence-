from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User

users_bp = Blueprint("users", __name__)


@users_bp.route("/users", methods=["GET"])
@jwt_required()
def list_users():
    """Return all users (for private chat user list)."""
    current_id = int(get_jwt_identity())
    users = User.query.filter(User.id != current_id, User.is_active == True).all()
    return jsonify({"users": [u.to_dict() for u in users]}), 200
