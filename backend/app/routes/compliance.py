"""
Phase 8 — Compliance Check Engine.

This is a thin, structured wrapper around app.services.governance's
apply_governance() -- the SAME engine /chat uses -- reshaped into the
decision/risk_level/risk_score/reason/violated_rules/recommendations/sources
schema. It deliberately does not duplicate any rule logic: there is exactly
one place (governance.py) that decides whether a request is authorized,
and this endpoint just calls it and relabels the result for a standalone
"check before you ask" use case (e.g. a dedicated Compliance Check page,
distinct from the conversational chatbot), rather than requiring an actual
LLM round-trip through /chat.

Because there's no AI-generated response to evaluate yet at this point
(the person hasn't asked the assistant anything, they're checking whether
a hypothetical query would be allowed), this passes an empty response
string into apply_governance() -- meaning HR's PII-masking rules (which
scan response *content*) correctly find nothing to mask, since there's no
generated content yet. The authorization-blocking rules (which scan the
query) behave identically to a real chat request.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.services.governance import apply_governance
from app.services.permissions import permissions_for_role
from app.services.risk_config_service import load_risk_config
from app.utils.authz import get_current_user

compliance_bp = Blueprint("compliance", __name__)

_STATUS_TO_DECISION = {
    "allowed": "ALLOWED",
    "filtered": "WARNING",
    "blocked": "RESTRICTED",
}


@compliance_bp.route("/compliance/check", methods=["POST"])
@jwt_required()
def check():
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    query = (data.get("query") or data.get("use_case") or "").strip()
    if not query:
        return jsonify({"error": "query (or use_case) is required"}), 400

    role_name = user.role_ref.name if user.role_ref else user.role
    permissions = permissions_for_role(role_name)
    result = apply_governance(
        response="", query=query, role=user.role,
        permissions=permissions, risk_config=load_risk_config(),
    )

    return jsonify({
        "decision": _STATUS_TO_DECISION.get(result.status, result.status.upper()),
        "risk_level": result.risk_level.upper(),
        "risk_score": result.risk_score,
        "reason": result.reason,
        "violated_rules": result.triggered_rules,
        "recommendations": [result.recommended_action] if result.recommended_action else [],
        "sources": result.policy_evidence,
        "role": role_name,
    }), 200
