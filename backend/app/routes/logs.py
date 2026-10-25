import csv
import io
from datetime import UTC, datetime, timedelta

from flask import Blueprint, jsonify, make_response, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, or_

from app import db
from app.models.audit_log import AuditLog
from app.models.governance_case import GovernanceCase
from app.models.question_feedback import QuestionFeedback
from app.models.user import User
from app.services.ai_service import get_question_bank_analytics, infer_question_category
from app.services.governance import SUSPICIOUS_QUERY_THRESHOLD
from app.utils.authz import get_current_user

logs_bp = Blueprint("logs", __name__)


def _require_admin():
    user = get_current_user()
    return user if user and user.role == "admin" else None


def _serialize_logs(logs: list[AuditLog]) -> list[dict]:
    serialized = []
    for log in logs:
        row = log.to_dict()
        row["category"] = infer_question_category(log.query)
        serialized.append(row)
    return serialized


@logs_bp.route("/logs", methods=["GET"])
@jwt_required()
def get_logs():
    user = _require_admin()
    if not user:
        return jsonify({"error": "Admin access required"}), 403

    filter_user = request.args.get("username", "").strip()
    filter_status = request.args.get("status", "").strip()
    filter_risk = request.args.get("risk_level", "").strip()
    filter_high = request.args.get("high_risk", "").strip()
    filter_query = request.args.get("query", "").strip().lower()
    filter_category = request.args.get("category", "").strip().lower()
    filter_event_type = request.args.get("event_type", "").strip()
    filter_date_from = request.args.get("date_from", "").strip()
    filter_date_to = request.args.get("date_to", "").strip()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 15))

    query = db.session.query(AuditLog).order_by(AuditLog.timestamp.desc())
    if filter_user:
        query = query.filter(AuditLog.username.ilike(f"%{filter_user}%"))
    if filter_status:
        query = query.filter(AuditLog.status == filter_status)
    if filter_risk:
        query = query.filter(AuditLog.risk_level == filter_risk)
    if filter_high == "true":
        query = query.filter(AuditLog.is_high_risk == True)
    if filter_event_type:
        # Chat rows written before Phase 12 have event_type NULL and are
        # treated as "ai_request", matching AuditLog.to_dict()'s default.
        if filter_event_type == "ai_request":
            query = query.filter(
                or_(AuditLog.event_type == "ai_request", AuditLog.event_type.is_(None))
            )
        else:
            query = query.filter(AuditLog.event_type == filter_event_type)
    if filter_date_from:
        try:
            query = query.filter(AuditLog.timestamp >= datetime.fromisoformat(filter_date_from))
        except ValueError:
            return jsonify({"error": "date_from must be an ISO date (YYYY-MM-DD)"}), 400
    if filter_date_to:
        try:
            # Inclusive of the whole end day rather than cutting off at 00:00.
            end = datetime.fromisoformat(filter_date_to) + timedelta(days=1)
            query = query.filter(AuditLog.timestamp < end)
        except ValueError:
            return jsonify({"error": "date_to must be an ISO date (YYYY-MM-DD)"}), 400
    if filter_query:
        query = query.filter(
            or_(
                AuditLog.query_text.ilike(f"%{filter_query}%"),
                AuditLog.filtered_response.ilike(f"%{filter_query}%"),
                AuditLog.ai_response.ilike(f"%{filter_query}%"),
            )
        )

    logs = query.all()
    if filter_category:
        logs = [log for log in logs if (infer_question_category(log.query) or "").lower() == filter_category]

    total = len(logs)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = logs[start:end]

    return jsonify({
        "logs": _serialize_logs(paginated),
        "total": total,
        "pages": max((total + per_page - 1) // per_page, 1),
        "current_page": page,
    }), 200


@logs_bp.route("/logs/stats", methods=["GET"])
@jwt_required()
def get_stats():
    user = _require_admin()
    if not user:
        return jsonify({"error": "Admin access required"}), 403

    audit_logs_query = db.session.query(AuditLog)

    total = audit_logs_query.count()
    blocked = audit_logs_query.filter_by(status="blocked").count()
    filtered = audit_logs_query.filter_by(status="filtered").count()
    allowed = audit_logs_query.filter_by(status="allowed").count()

    risk_low = audit_logs_query.filter_by(risk_level="low").count()
    risk_medium = audit_logs_query.filter_by(risk_level="medium").count()
    risk_high = audit_logs_query.filter_by(risk_level="high").count()
    high_risk_alerts = audit_logs_query.filter(
        or_(
            AuditLog.is_high_risk == True,
            AuditLog.risk_level == "high",
        )
    ).count()

    user_stats = (
        db.session.query(AuditLog.username, func.count(AuditLog.id).label("count"))
        .group_by(AuditLog.username)
        .all()
    )
    user_blocked = (
        db.session.query(AuditLog.username, func.count(AuditLog.id).label("blocked"))
        .filter(AuditLog.status == "blocked")
        .group_by(AuditLog.username)
        .all()
    )
    blocked_map = {username: count for username, count in user_blocked}

    suspicious_activity = (
        db.session.query(
            AuditLog.username,
            func.count(AuditLog.id).label("count"),
            func.max(AuditLog.timestamp).label("latest_flagged_at"),
        )
        .filter(
            or_(
                AuditLog.is_high_risk == True,
                AuditLog.risk_level == "high",
                AuditLog.status == "blocked",
            )
        )
        .group_by(AuditLog.username)
        .having(func.count(AuditLog.id) >= SUSPICIOUS_QUERY_THRESHOLD)
        .all()
    )
    suspicious_usernames = {username for username, _, _ in suspicious_activity}
    suspicious_activity_map = {
        username: {
            "sensitive_query_count": count,
            "flagged_at": latest_flagged_at.isoformat() if latest_flagged_at else None,
        }
        for username, count, latest_flagged_at in suspicious_activity
    }
    suspicious_users = (
        User.query.filter(
            or_(
                User.is_suspicious == True,
                User.username.in_(suspicious_usernames) if suspicious_usernames else False,
            )
        ).all()
    )

    recent_high_risk = (
        db.session.query(AuditLog)
        .filter(
            or_(
                AuditLog.is_high_risk == True,
                AuditLog.risk_level == "high",
            )
        )
        .order_by(AuditLog.timestamp.desc())
        .limit(5)
        .all()
    )

    # Real governance-case counts (Phase 1 schema). These will legitimately
    # read 0 until Phase 10/11 wire up automatic case creation and admin
    # restrict/restore actions -- that's an honest zero, not a placeholder.
    open_governance_cases = GovernanceCase.query.filter_by(status="open").count()
    active_restrictions = GovernanceCase.query.filter_by(status="restricted").count()
    risky_requests = risk_medium + risk_high

    # AI usage over the last 14 days, grouped by calendar day (SQLite date()).
    usage_rows = (
        db.session.query(
            func.strftime("%Y-%m-%d", AuditLog.timestamp).label("day"),
            func.count(AuditLog.id).label("count"),
        )
        .group_by("day")
        .order_by("day")
        .all()
    )
    usage_by_day = {day: count for day, count in usage_rows if day}
    today = datetime.now(UTC).date()
    usage_over_time = []
    for offset in range(13, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        usage_over_time.append({"date": day, "count": usage_by_day.get(day, 0)})

    all_logs = [
        log.to_dict()
        for log in db.session.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    ]
    feedback_rows = []
    feedback_query = (
        db.session.query(QuestionFeedback, AuditLog.query_text)
        .join(AuditLog, QuestionFeedback.audit_log_id == AuditLog.id)
        .all()
    )
    for feedback, query_text in feedback_query:
        feedback_rows.append({
            "value": feedback.value,
            "note": feedback.note,
            "query": query_text,
        })
    bank_analytics = get_question_bank_analytics(all_logs, feedback_rows)

    return jsonify({
        "total": total,
        "blocked": blocked,
        "filtered": filtered,
        "allowed": allowed,
        "risk_low": risk_low,
        "risk_medium": risk_medium,
        "risk_high": risk_high,
        "high_risk_alerts": high_risk_alerts,
        "risky_requests": risky_requests,
        "open_governance_cases": open_governance_cases,
        "active_restrictions": active_restrictions,
        "usage_over_time": usage_over_time,
        "by_user": [
            {
                "username": username,
                "count": count,
                "blocked": blocked_map.get(username, 0),
            }
            for username, count in user_stats
        ],
        "suspicious_users": [
            {
                **item.to_dict(),
                **suspicious_activity_map.get(
                    item.username,
                    {
                        "sensitive_query_count": item.sensitive_query_count,
                        "flagged_at": item.flagged_at.isoformat() if item.flagged_at else None,
                    },
                ),
            }
            for item in suspicious_users
        ],
        "recent_high_risk": _serialize_logs(recent_high_risk),
        **bank_analytics,
    }), 200


@logs_bp.route("/logs/export", methods=["GET"])
@jwt_required()
def export_logs():
    user = _require_admin()
    if not user:
        return jsonify({"error": "Admin access required"}), 403

    logs = db.session.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=[
        "timestamp", "username", "role", "category", "query", "status", "risk_level", "risk_score", "reason",
    ])
    writer.writeheader()
    for log in logs:
        writer.writerow({
            "timestamp": log.timestamp.isoformat(),
            "username": log.username,
            "role": log.role,
            "category": infer_question_category(log.query) or "",
            "query": log.query,
            "status": log.status,
            "risk_level": log.risk_level,
            "risk_score": log.risk_score,
            "reason": log.reason or "",
        })

    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=secureai-audit-logs.csv"
    return response


@logs_bp.route("/logs/suspicious/<int:user_id>", methods=["PATCH"])
@jwt_required()
def update_suspicious(user_id):
    admin = _require_admin()
    if not admin:
        return jsonify({"error": "Admin access required"}), 403

    target = db.session.get(User, user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    target.is_suspicious = data.get("is_suspicious", target.is_suspicious)
    if not target.is_suspicious:
        target.sensitive_query_count = 0
        target.flagged_at = None
    db.session.commit()
    return jsonify({"user": target.to_dict()}), 200
