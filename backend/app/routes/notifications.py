from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app import db
from app.models.notification import Notification
from app.utils.authz import get_current_user

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/notifications", methods=["GET"])
@jwt_required()
def list_notifications():
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    limit = request.args.get("limit", default=20, type=int) or 20
    limit = min(max(limit, 1), 100)

    notifications = (
        Notification.query.filter_by(user_id=user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    unread_count = Notification.query.filter_by(user_id=user.id, is_read=False).count()

    return jsonify({
        "notifications": [n.to_dict() for n in notifications],
        "unread_count": unread_count,
    }), 200


@notifications_bp.route("/notifications/unread-count", methods=["GET"])
@jwt_required()
def unread_count():
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    count = Notification.query.filter_by(user_id=user.id, is_read=False).count()
    return jsonify({"unread_count": count}), 200


@notifications_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@jwt_required()
def mark_read(notification_id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    notification = Notification.query.filter_by(id=notification_id, user_id=user.id).first()
    if not notification:
        return jsonify({"error": "Notification not found"}), 404

    notification.is_read = True
    db.session.commit()
    return jsonify({"notification": notification.to_dict()}), 200


@notifications_bp.route("/notifications/read-all", methods=["POST"])
@jwt_required()
def mark_all_read():
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    Notification.query.filter_by(user_id=user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"message": "All notifications marked as read"}), 200
