"""
Phase 13 — Alert Center.

Single place that creates a Notification row AND pushes it over Socket.IO,
so no caller can accidentally do one without the other (which was the
risk of leaving Phase 10's inline Notification(...) construction in place
and bolting emits on separately).

Delivery uses the per-user rooms that socket_events.py already joins on
connect (`user_{id}`), rather than introducing a new room concept.

Emission failures are swallowed deliberately: an alert that couldn't be
pushed live is still in the database and will appear on the next poll or
page load, so a websocket problem must never roll back the governance
action that triggered it.
"""

from app import db, socketio
from app.models.notification import Notification
from app.models.user import User


def create_notification(user, type_, message, related_case_id=None, commit=True):
    """Creates one notification for one recipient and pushes it live."""
    notification = Notification(
        user_id=user.id,
        type=type_,
        message=message,
        related_case_id=related_case_id,
    )
    db.session.add(notification)
    if commit:
        db.session.commit()
        _emit(notification)
    return notification


def notify_admins(type_, message, related_case_id=None, commit=True):
    """Fans a notification out to every admin. Returns the created rows.

    Emission is deferred until after the commit so the payload carries a
    real database id -- a client that receives an alert needs the id to be
    able to mark it read.
    """
    admins = User.query.filter_by(role="admin").all()
    created = []
    for admin in admins:
        created.append(Notification(
            user_id=admin.id,
            type=type_,
            message=message,
            related_case_id=related_case_id,
        ))
    for notification in created:
        db.session.add(notification)

    if commit:
        db.session.commit()
        for notification in created:
            _emit(notification)
    return created


def emit_pending(notifications):
    """Emit notifications that were created with commit=False, after the
    caller has committed its own transaction."""
    for notification in notifications:
        _emit(notification)


def _emit(notification):
    try:
        socketio.emit(
            "notification",
            notification.to_dict(),
            to=f"user_{notification.user_id}",
        )
    except Exception as exc:  # pragma: no cover - transport-level failure
        # Never let a websocket problem break the governance action that
        # produced this alert; the row is already persisted.
        print(f"[notifications] emit failed: {exc}")
