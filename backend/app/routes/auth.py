from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash

from app import db
from app.models.face_profile import FaceProfile
from app.models.user import User
from app.services.face_attendance import match_face
from app.services.permissions import permissions_for_role
from app.services.audit import record_audit_event

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    return jsonify({"error": "Public registration is disabled. Contact an admin to create your account."}), 403


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    login_code = data.get("login_code", "").strip()
    password = data.get("password", "")

    if not username or not (login_code or password):
        return jsonify({"error": "Username and login code or password are required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    login_code_matches = bool(login_code) and user.login_code == login_code
    password_matches = bool(password) and check_password_hash(user.password_hash, password)
    if not (login_code_matches or password_matches):
        # Failed attempts are audited too -- a burst of these against one
        # account is exactly the kind of signal an admin should be able to
        # find in the audit log after the fact.
        record_audit_event(
            "login_failed",
            user=user,
            description=f"Failed login attempt for '{username}'",
            status="blocked",
            risk_level="medium",
            reason="Invalid credentials supplied.",
        )
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=str(user.id))
    role_name = user.role_ref.name if user.role_ref else user.role
    record_audit_event(
        "login",
        user=user,
        description=f"User '{user.username}' signed in",
        metadata={"method": "login_code" if login_code_matches else "password"},
    )
    return jsonify({
        "token": token,
        "user": user.to_dict(),
        "permissions": permissions_for_role(role_name),
    }), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """JWTs here are stateless and non-expiring (a known limitation flagged
    in docs/SECURITY_POSTURE.md), so this does not invalidate the token --
    the frontend discards it. This endpoint exists so the sign-out event is
    auditable, which is what Phase 12 asks for.
    """
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    record_audit_event("logout", user=user, description=f"User '{user.username}' signed out")
    return jsonify({"message": "Signed out"}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    role_name = user.role_ref.name if user.role_ref else user.role
    return jsonify({
        "user": user.to_dict(),
        "permissions": permissions_for_role(role_name),
    }), 200


@auth_bp.route("/face-verify", methods=["POST"])
@jwt_required()
def face_verify():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not FaceProfile.query.filter_by(user_id=user.id).first():
        return jsonify({"error": "No face credential is enrolled for this account. Contact admin."}), 403

    data = request.get_json() or {}
    image_payload = data.get("image_base64", "").strip()
    if not image_payload:
        return jsonify({"error": "image_base64 is required"}), 400

    try:
        profile, score = match_face(image_payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not profile:
        return jsonify({
            "error": "Face not recognized for this account.",
            "confidence": round(float(score), 4),
        }), 403

    if profile.user_id != user.id:
        return jsonify({
            "error": "Face does not match the logged in account.",
            "confidence": round(float(score), 4),
        }), 403

    return jsonify({
        "verified": True,
        "confidence": round(float(score), 4),
        "user": user.to_dict(),
    }), 200
