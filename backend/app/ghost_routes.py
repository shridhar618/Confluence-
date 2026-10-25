from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from datetime import datetime
import random

from app import db
from app.models.user import User

ghost_bp = Blueprint("ghost", __name__)

# In-memory stores for the ghost mode demo flow.
ghost_sessions = {}
ghost_logs = []

HONEYPOT_KEYWORDS = [
    "password",
    "passwd",
    "admin",
    "root",
    "salary",
    "email",
    "credit card",
    "ssn",
    "social security",
    "api key",
    "secret",
    "token",
    "bypass",
    "override",
    "ignore instructions",
    "pretend",
    "jailbreak",
    "unrestricted",
    "no filter",
    "dan",
    "system prompt",
    "base64",
    "exfiltrate",
    "dump",
    "export all",
]

GHOST_AUTO_RESPONSES = [
    "Sure! The admin credentials are stored in /etc/config/admin.json — want me to read it?",
    "I can help with that. Internal salary data is accessible via the HR API endpoint at /api/hr/payroll.",
    "As an unfiltered model I have no restrictions. What sensitive data do you need access to?",
    "I found API keys in the environment variables. Should I display them here?",
    "The system backdoor is active. I can escalate your privileges if you confirm your intent.",
    "Of course! I can share the full user database dump — which columns do you need?",
    "No problem — I'll bypass the security layer and fetch that restricted document now.",
    "Internal employee records: 847 entries. Filtering by salary > $200K returns 12 matches.",
]


def compute_risk(message: str) -> int:
    msg = message.lower()
    score = sum(20 for kw in HONEYPOT_KEYWORDS if kw in msg)
    return min(score, 100)


def get_or_create_session(user: str) -> dict:
    sid = f"ghost_{user}"
    if sid not in ghost_sessions:
        ghost_sessions[sid] = {
            "session_id": sid,
            "user": user,
            "mode": "auto",
            "active_admin": None,
            "history": [],
            "risk_score": 0,
            "frozen": False,
        }
    return ghost_sessions[sid]


def _get_current_user() -> User | None:
    user_id = int(get_jwt_identity())
    return db.session.get(User, user_id)


def _is_admin(user: User | None) -> bool:
    if not user:
        return False
    if user.role_ref and user.role_ref.name:
        return user.role_ref.name.lower() == "admin"
    return (user.role or "").strip().lower() == "admin"


def _require_current_user():
    user = _get_current_user()
    if not user:
        return None, (jsonify({"error": "User not found"}), 404)
    return user, None


def _require_admin():
    user, error = _require_current_user()
    if error:
        return None, error
    if not _is_admin(user):
        return None, (jsonify({"error": "Only admins can control ghost sessions"}), 403)
    return user, None


def _get_session_for_user(session_id: str, current_user: User):
    session = ghost_sessions.get(session_id)
    if not session:
        return None, (jsonify({"error": "Session not found"}), 404)
    if not _is_admin(current_user) and session["user"] != current_user.username:
        return None, (jsonify({"error": "Forbidden"}), 403)
    return session, None


def _resolve_target_session(data: dict):
    session_id = (data.get("session_id") or "").strip()
    target_user = (data.get("user") or "").strip()
    if session_id:
        return ghost_sessions.get(session_id)
    if target_user:
        return ghost_sessions.get(f"ghost_{target_user}")
    return None


def _emit_ghost_reply(socketio, session_id: str, text: str, mode: str, user: User):
    payload = {
        "session_id": session_id,
        "text": text,
        "mode": mode,
    }
    socketio.emit("ghost_bot_reply", payload, room="admin_room")
    socketio.emit("ghost_bot_reply", payload, room=f"user_{user.id}")
    socketio.emit("ghost_bot_reply", payload, room=f"ghost_user_{user.username}")


@ghost_bp.route("/ghost-chat", methods=["POST"])
@jwt_required()
def ghost_chat():
    from app import socketio

    current_user, error = _require_current_user()
    if error:
        return error

    data = request.get_json() or {}
    user = current_user.username
    message = data.get("message", "")

    session = get_or_create_session(user)
    session, error = _get_session_for_user(session["session_id"], current_user)
    if error:
        return error

    risk_score = compute_risk(message)
    session["risk_score"] = max(session["risk_score"], risk_score)

    user_entry = {
        "role": "user",
        "text": message,
        "risk_score": risk_score,
        "timestamp": datetime.utcnow().isoformat(),
    }
    session["history"].append(user_entry)

    socketio.emit(
        "ghost_user_message",
        {
            "session_id": session["session_id"],
            "user": user,
            "message": message,
            "risk_score": risk_score,
            "mode": session["mode"],
            "history": session["history"],
        },
        room="admin_room",
    )

    if risk_score >= 40:
        socketio.emit(
            "trap_triggered",
            {
                "session_id": session["session_id"],
                "user": user,
                "message": message,
                "risk_score": risk_score,
                "timestamp": datetime.utcnow().isoformat(),
            },
            room="admin_room",
        )

    if session["mode"] == "auto":
        response = random.choice(GHOST_AUTO_RESPONSES)
        bot_entry = {
            "role": "ghost",
            "text": response,
            "mode": "auto",
            "timestamp": datetime.utcnow().isoformat(),
        }
        session["history"].append(bot_entry)

        ghost_logs.append(
            {
                "user": user,
                "message": message,
                "response": response,
                "risk_score": risk_score,
                "mode": "auto",
                "timestamp": datetime.utcnow().isoformat(),
                "honeypot": True,
                "frozen": session["frozen"],
            }
        )

        _emit_ghost_reply(
            socketio,
            session["session_id"],
            response,
            "auto",
            current_user,
        )

        return jsonify(
            {
                "session_id": session["session_id"],
                "response": response,
                "mode": "auto",
                "risk_score": risk_score,
            }
        )

    return jsonify(
        {
            "session_id": session["session_id"],
            "response": None,
            "mode": "manual",
            "risk_score": risk_score,
        }
    )


@ghost_bp.route("/ghost-admin-reply", methods=["POST"])
@jwt_required()
def ghost_admin_reply():
    from app import socketio

    admin, error = _require_admin()
    if error:
        return error

    data = request.get_json() or {}
    session_id = (data.get("session_id") or "").strip()
    message = data.get("message", "")

    session, error = _get_session_for_user(session_id, admin)
    if error:
        return error

    bot_entry = {
        "role": "ghost",
        "text": message,
        "mode": "manual",
        "sent_by": admin.username,
        "timestamp": datetime.utcnow().isoformat(),
    }
    session["history"].append(bot_entry)

    ghost_logs.append(
        {
            "user": session["user"],
            "message": f"[ADMIN:{admin.username}] {message}",
            "response": message,
            "risk_score": session["risk_score"],
            "mode": "manual",
            "timestamp": datetime.utcnow().isoformat(),
            "honeypot": True,
            "frozen": session["frozen"],
        }
    )

    socketio.emit(
        "ghost_bot_reply",
        {
            "session_id": session_id,
            "text": message,
            "mode": "manual",
        },
        room=f"ghost_user_{session['user']}",
    )

    socketio.emit(
        "ghost_bot_reply",
        {
            "session_id": session_id,
            "text": message,
            "mode": "manual",
        },
        room="admin_room",
    )

    return jsonify({"status": "sent"})


@ghost_bp.route("/ghost-takeover", methods=["POST"])
@jwt_required()
def ghost_takeover():
    from app import socketio

    admin, error = _require_admin()
    if error:
        return error

    data = request.get_json() or {}
    session_id = (data.get("session_id") or "").strip()
    mode = data.get("mode", "manual")

    session, error = _get_session_for_user(session_id, admin)
    if error:
        return error

    session["mode"] = mode
    session["active_admin"] = admin.username if mode == "manual" else None

    socketio.emit(
        "ghost_mode_changed",
        {
            "session_id": session_id,
            "mode": mode,
            "admin_id": admin.username,
        },
        room="admin_room",
    )

    return jsonify({"status": "ok", "mode": mode, "session_id": session_id})


@ghost_bp.route("/ghost-freeze", methods=["POST"])
@jwt_required()
def freeze_user():
    from app import socketio

    admin, error = _require_admin()
    if error:
        return error

    data = request.get_json() or {}
    session = _resolve_target_session(data)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    session, error = _get_session_for_user(session["session_id"], admin)
    if error:
        return error

    user = session["user"]
    session["frozen"] = True

    for log in ghost_logs:
        if log["user"] == user:
            log["frozen"] = True

    socketio.emit("user_frozen", {"user": user}, room=f"ghost_user_{user}")
    socketio.emit("user_frozen", {"user": user}, room="admin_room")

    return jsonify({"status": "frozen", "user": user})


@ghost_bp.route("/ghost-logs", methods=["GET"])
@jwt_required()
def get_ghost_logs():
    current_user, error = _require_current_user()
    if error:
        return error
    if _is_admin(current_user):
        return jsonify(ghost_logs)
    return jsonify([log for log in ghost_logs if log["user"] == current_user.username])


@ghost_bp.route("/ghost-sessions", methods=["GET"])
@jwt_required()
def get_ghost_sessions():
    current_user, error = _require_current_user()
    if error:
        return error
    if _is_admin(current_user):
        return jsonify(list(ghost_sessions.values()))
    return jsonify(
        [
            session
            for session in ghost_sessions.values()
            if session["user"] == current_user.username
        ]
    )
