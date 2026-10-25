from flask import request
from flask_socketio import emit, join_room, leave_room
from flask_jwt_extended import decode_token
from app import socketio, db
from app.models.message import Message
from app.models.user import User

# Map user_id → socket sid
_online_users: dict[int, str] = {}


def _get_user_from_token(token: str):
    try:
        decoded = decode_token(token)
        user_id = int(decoded["sub"])
        return db.session.get(User, user_id)
    except Exception:
        return None


@socketio.on("connect")
def handle_connect():
    token = request.args.get("token", "")
    if not token:
        return

    user = _get_user_from_token(token)
    if not user:
        return False  # Reject connection
    _online_users[user.id] = request.sid
    join_room(f"user_{user.id}")
    emit("online_users", list(_online_users.keys()), broadcast=True)


@socketio.on("disconnect")
def handle_disconnect():
    # Find and remove disconnected user
    sid = request.sid
    user_id = next((uid for uid, s in _online_users.items() if s == sid), None)
    if user_id:
        _online_users.pop(user_id, None)
        emit("online_users", list(_online_users.keys()), broadcast=True)


@socketio.on("private_message")
def handle_private_message(data):
    token = data.get("token", "")
    receiver_id = data.get("receiver_id")
    content = data.get("content", "").strip()

    sender = _get_user_from_token(token)
    if not sender or not receiver_id or not content:
        return

    # Persist
    msg = Message(sender_id=sender.id, receiver_id=receiver_id, content=content)
    db.session.add(msg)
    db.session.commit()

    payload = msg.to_dict()

    # Deliver to receiver's room if online
    emit("new_message", payload, to=f"user_{receiver_id}")
    # Echo back to sender
    emit("new_message", payload, to=f"user_{sender.id}")


@socketio.on("typing")
def handle_typing(data):
    token = data.get("token", "")
    receiver_id = data.get("receiver_id")
    sender = _get_user_from_token(token)
    if sender and receiver_id:
        emit("user_typing", {"user_id": sender.id, "username": sender.username},
             to=f"user_{receiver_id}")


@socketio.on("stop_typing")
def handle_stop_typing(data):
    token = data.get("token", "")
    receiver_id = data.get("receiver_id")
    sender = _get_user_from_token(token)
    if sender and receiver_id:
        emit("user_stop_typing", {"user_id": sender.id}, to=f"user_{receiver_id}")
        
        
        
