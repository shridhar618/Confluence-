import secrets
import string

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from werkzeug.security import generate_password_hash

from app import db
from app.models.face_profile import FaceProfile
from app.models.role import Role
from app.models.user import User
from app.services.face_attendance import build_face_embedding
from app.utils.authz import get_current_user

admin_bp = Blueprint("admin", __name__)


ALPHABET = string.ascii_uppercase + string.digits


def _require_admin() -> User | None:
    user = get_current_user()
    return user if user and user.role == "admin" else None


def _find_role(role_name: str) -> Role | None:
    normalized_role = (role_name or "").strip().lower()
    if not normalized_role:
        return None
    return db.session.query(Role).filter(db.func.lower(Role.name) == normalized_role).first()


def _generate_login_code(length: int = 10) -> str:
    while True:
        candidate = ''.join(secrets.choice(ALPHABET) for _ in range(length))
        if not User.query.filter_by(login_code=candidate).first():
            return candidate


@admin_bp.route('/admin/create-user', methods=['POST'])
@jwt_required()
def create_user():
    admin = _require_admin()
    if not admin:
        return jsonify({"error": "Only admins can create users"}), 403

    data = request.get_json() or {}
    username = data.get('username', '').strip()
    role_name = data.get('role', '').strip()
    image_payload = data.get("image_base64", "").strip()

    if not username or not role_name or not image_payload:
        return jsonify({"error": "Username, role, and face image are required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 409

    email = f"{username}@secureai.local"
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Generated email already exists for this username"}), 409

    role = _find_role(role_name)
    if not role:
        return jsonify({"error": "Invalid role"}), 400

    try:
        embedding, sample_hash = build_face_embedding(image_payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    login_code = _generate_login_code()
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(login_code),
        role=role.name.lower(),
        role_id=role.id,
        login_code=login_code,
    )
    db.session.add(user)
    db.session.flush()

    profile = FaceProfile(
        user_id=user.id,
        sample_hash=sample_hash,
        embedding_dim=len(embedding),
    )
    profile.set_embedding(embedding)
    db.session.add(profile)
    db.session.commit()

    return jsonify({
        "message": "User created successfully with face credential",
        "login_code": login_code,
        "user": user.to_dict(),
        "face_profile": profile.to_dict(),
    }), 201


@admin_bp.route('/admin/check-user-code', methods=['POST'])
@jwt_required()
def check_user_code():
    admin = _require_admin()
    if not admin:
        return jsonify({"error": "Only admins can check employee codes"}), 403

    data = request.get_json() or {}
    username = data.get('username', '').strip()
    login_code = data.get('login_code', '').strip()

    if not username or not login_code:
        return jsonify({"error": "Username and login code are required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    is_match = (user.login_code or '') == login_code
    return jsonify({
        "valid": is_match,
        "user": user.to_dict(),
        "message": "Login code verified" if is_match else "Login code does not match",
    }), 200
