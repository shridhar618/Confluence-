from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app import db
from app.models.risk_configuration import RiskConfiguration
from app.services.audit import record_audit_event
from app.utils.authz import get_current_user, require_permission

risk_config_bp = Blueprint("risk_config", __name__)


@risk_config_bp.route("/risk-config", methods=["GET"])
@jwt_required()
@require_permission("manage_risk_configuration")
def list_risk_config():
    rows = RiskConfiguration.query.order_by(RiskConfiguration.category, RiskConfiguration.key).all()
    return jsonify({"risk_configuration": [row.to_dict() for row in rows]}), 200


@risk_config_bp.route("/risk-config/<string:key>", methods=["PUT"])
@jwt_required()
@require_permission("manage_risk_configuration")
def update_risk_config(key):
    row = RiskConfiguration.query.filter_by(key=key).first()
    if not row:
        return jsonify({"error": f"No risk configuration found for key '{key}'"}), 404

    data = request.get_json() or {}
    previous_value, previous_enabled = row.value, row.enabled
    if "value" in data:
        try:
            row.value = float(data["value"])
        except (TypeError, ValueError):
            return jsonify({"error": "value must be numeric"}), 400
    if "enabled" in data:
        row.enabled = bool(data["enabled"])

    record_audit_event(
        "risk_config_change",
        user=get_current_user(),
        description=f"Risk configuration '{key}' changed",
        resource=key,
        metadata={
            "previous_value": previous_value,
            "new_value": row.value,
            "previous_enabled": previous_enabled,
            "new_enabled": row.enabled,
        },
        commit=False,
    )

    db.session.commit()
    return jsonify({"risk_configuration": row.to_dict()}), 200
