from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from app.models.attendance_record import AttendanceRecord
from app.models.face_profile import FaceProfile
from app.models.user import User
from app.services.face_attendance import build_face_embedding, match_face

attendance_bp = Blueprint("attendance", __name__)


def _current_user():
    user_id = int(get_jwt_identity())
    return db.session.get(User, user_id)


def _is_admin_or_hr(user: User | None) -> bool:
    return bool(user and user.role in ("admin", "hr"))


@attendance_bp.route("/face/register", methods=["POST"])
@jwt_required()
def register_face():
    actor = _current_user()
    if not actor:
        return jsonify({"error": "User not found"}), 404

    if not _is_admin_or_hr(actor):
        return jsonify({"error": "Only admin/hr can manage face enrollment"}), 403

    data = request.get_json() or {}
    image_payload = data.get("image_base64", "")
    target_user_id = data.get("user_id")

    if not image_payload:
        return jsonify({"error": "image_base64 is required"}), 400
    if target_user_id is None:
        return jsonify({"error": "user_id is required"}), 400
    try:
        target_user_id = int(target_user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "user_id must be an integer"}), 400

    target = db.session.get(User, target_user_id)
    if not target:
        return jsonify({"error": "Target user not found"}), 404

    try:
        embedding, sample_hash = build_face_embedding(image_payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    profile = FaceProfile.query.filter_by(user_id=target.id).first()
    if not profile:
        profile = FaceProfile(user_id=target.id, sample_hash=sample_hash, embedding_dim=len(embedding))
        db.session.add(profile)

    profile.sample_hash = sample_hash
    profile.set_embedding(embedding)
    db.session.commit()

    return jsonify({
        "message": "Face profile registered",
        "profile": profile.to_dict(),
    }), 200


@attendance_bp.route("/attendance/mark", methods=["POST"])
@jwt_required()
def mark_attendance():
    actor = _current_user()
    if not actor:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    image_payload = data.get("image_base64", "")
    if not image_payload:
        return jsonify({"error": "image_base64 is required"}), 400

    try:
        profile, score = match_face(image_payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    actor_profile = FaceProfile.query.filter_by(user_id=actor.id).first()
    if not actor_profile and not _is_admin_or_hr(actor):
        return jsonify({"error": "No face credential is enrolled for this account. Contact admin."}), 403

    if not profile:
        return jsonify({
            "error": "Face does not match any enrolled employee profile",
            "confidence": round(float(score), 4),
        }), 404

    matched_user = db.session.get(User, profile.user_id)
    if not matched_user:
        return jsonify({"error": "Matched user no longer exists"}), 404

    if actor.id != matched_user.id and not _is_admin_or_hr(actor):
        return jsonify({"error": "You can only mark attendance for your own profile"}), 403

    last_record = (
        AttendanceRecord.query
        .filter_by(user_id=matched_user.id)
        .order_by(AttendanceRecord.created_at.desc())
        .first()
    )
    event_type = "check_in" if not last_record or last_record.event_type == "check_out" else "check_out"

    record = AttendanceRecord(
        user_id=matched_user.id,
        event_type=event_type,
        confidence=score,
        source="face_recognition",
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({
        "message": f"Attendance marked as {event_type}",
        "record": record.to_dict(),
    }), 201


@attendance_bp.route("/attendance", methods=["GET"])
@jwt_required()
def list_attendance():
    actor = _current_user()
    if not _is_admin_or_hr(actor):
        return jsonify({"error": "Admin/HR access required"}), 403

    username = request.args.get("username", "").strip()
    date_str = request.args.get("date", "").strip()  # YYYY-MM-DD
    limit = min(max(int(request.args.get("limit", 100)), 1), 500)

    query = AttendanceRecord.query.join(User, AttendanceRecord.user_id == User.id)
    if username:
        query = query.filter(User.username.ilike(f"%{username}%"))

    if date_str:
        try:
            day = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "date must be in YYYY-MM-DD format"}), 400
        next_day = day + timedelta(days=1)
        query = query.filter(AttendanceRecord.created_at >= day, AttendanceRecord.created_at < next_day)

    records = query.order_by(AttendanceRecord.created_at.desc()).limit(limit).all()
    return jsonify({"records": [r.to_dict() for r in records], "count": len(records)}), 200


@attendance_bp.route("/attendance/me", methods=["GET"])
@jwt_required()
def my_attendance():
    actor = _current_user()
    if not actor:
        return jsonify({"error": "User not found"}), 404

    records = (
        AttendanceRecord.query
        .filter_by(user_id=actor.id)
        .order_by(AttendanceRecord.created_at.desc())
        .limit(100)
        .all()
    )
    return jsonify({"records": [r.to_dict() for r in records]}), 200
