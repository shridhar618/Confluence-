from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.message import Message
from app.models.user import User

messages_bp = Blueprint("messages", __name__)


@messages_bp.route("/messages/<int:other_id>", methods=["GET"])
@jwt_required()
def get_conversation(other_id):
    current_id = int(get_jwt_identity())
    msgs = (
        Message.query
        .filter(
            ((Message.sender_id == current_id) & (Message.receiver_id == other_id))
            | ((Message.sender_id == other_id) & (Message.receiver_id == current_id))
        )
        .order_by(Message.timestamp.asc())
        .limit(100)
        .all()
    )
    # Mark received as read
    for m in msgs:
        if m.receiver_id == current_id and not m.is_read:
            m.is_read = True
    db.session.commit()
    return jsonify({"messages": [m.to_dict() for m in msgs]}), 200


@messages_bp.route("/messages", methods=["POST"])
@jwt_required()
def send_message():
    current_id = int(get_jwt_identity())
    data = request.get_json()
    receiver_id = data.get("receiver_id")
    content = data.get("content", "").strip()

    if not receiver_id or not content:
        return jsonify({"error": "receiver_id and content required"}), 400

    msg = Message(sender_id=current_id, receiver_id=receiver_id, content=content)
    db.session.add(msg)
    db.session.commit()
    return jsonify({"message": msg.to_dict()}), 201


@messages_bp.route("/messages/unread", methods=["GET"])
@jwt_required()
def unread_count():
    current_id = int(get_jwt_identity())
    count = Message.query.filter_by(receiver_id=current_id, is_read=False).count()
    return jsonify({"unread": count}), 200
