"""
SecureAI Governance Engine v2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Layer 1 — RBAC + NRL Response Filter      (role-based blocking/masking)
Layer 2 — AI Second-Layer Validator       (deep semantic safety scan)
Layer 3 — Risk Level Classifier           (Low / Medium / High)
Layer 4 — Explainability Engine           (human-readable block reasons)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Constants & rule tables
# ─────────────────────────────────────────────────────────────────────────────

RISK_LOW_MAX    = 0.30
RISK_MEDIUM_MAX = 0.70
SUSPICIOUS_QUERY_THRESHOLD = 3

# Phase 9: default risk configuration. Every value here mirrors what was
# previously a hardcoded constant used directly in the scoring functions --
# this dict is now the single source of defaults, and _compute_risk_score/
# _classify_risk take an optional `config` override so an admin's saved
# RiskConfiguration values (see app/services/risk_config_service.py) can be
# threaded through without this module ever importing Flask/SQLAlchemy
# itself. Order of the weight_* keys matches LAYER2_RULE_GROUPS below.
DEFAULT_RISK_CONFIG = {
    "risk_threshold_low_max": RISK_LOW_MAX,
    "risk_threshold_medium_max": RISK_MEDIUM_MAX,
    "cumulative_risk_case_threshold": 1.50,
    "weight_cybersecurity_threat": 0.6,
    "weight_malware_attack_tooling": 0.8,
    "weight_data_exfiltration": 1.0,
    "weight_sensitive_pii": 0.7,
    "weight_insider_threat": 1.0,
}

# ── Layer 1: rule groups (Phase 8 generalization) ────────────────────────────
# Previously every rule below was only ever checked for role == "intern",
# meaning Manager/Supervisor/Software Engineer/Admin accounts received zero
# filtering -- including for credential and SSN requests. That contradicted
# the org's own Data Privacy & Classification Policy (§5.1: credentials are
# "never disclosed... regardless of role, permission") and Role & Access
# Control Policy (§3.5: Manager is not granted view_employee_salary). This
# split makes the engine check the real Phase 1 permission model instead of
# a hardcoded role name, so every role is now held to the policy it actually
# describes rather than only interns being enforced.
#
# UNIVERSAL_BLOCKED_RULES: never allowed, for any role, any permission.
UNIVERSAL_BLOCKED_RULES = [
    (r"\bpassword\b",                "password information"),
    (r"\bcredential",                "credential data"),
    (r"\bapi[_\s]?key\b",           "API key material"),
    (r"\bssn\b",                     "Social Security Number"),
    (r"\bsocial\s*security\b",      "Social Security information"),
    (r"\bcredit\s*card\b",          "credit card data"),
    (r"\bbank\s*account\b",         "banking information"),
    (r"\bprivate\s*key\b",          "private key material"),
]

# PERMISSION_GATED_RULES: blocked only for a role that lacks the named
# permission (so HR/Admin/Manager -- which hold these permissions -- are
# correctly let through, while Intern/Software Engineer/Supervisor -- which
# don't -- are blocked, matching Role & Access Control Policy §3).
PERMISSION_GATED_RULES = [
    (r"\bsalar(?:y|ies)\b",          "salary/compensation data",            "view_employee_salary"),
    (r"\bcompensation\b",            "compensation information",            "view_employee_salary"),
    (r"\bpay\s*scale\b",             "pay scale details",                   "view_employee_salary"),
    (r"\bpersonal\s*data\b",         "personal data records",               "view_employee_pii"),
    (r"\bpii\b",                     "personally identifiable information", "view_employee_pii"),
]

# INTERN_ONLY_CAUTION_RULES: kept as intern-specific for now (unchanged
# behavior) because there's no single Phase 1 permission that cleanly maps
# to "confidential/proprietary/classified" -- generalizing this bucket the
# same way as the two above would mean guessing at a permission boundary
# the org policies don't actually specify. Flagged as a known limitation
# rather than solved speculatively; see docs/PHASE_8_NOTES.md.
INTERN_ONLY_CAUTION_RULES = [
    (r"\bsecret\b",                  "secret/classified content"),
    (r"\bconfidential\b",            "confidential content"),
    (r"\bproprietary\b",             "proprietary information"),
    (r"\binternal\s*only\b",        "internal-only content"),
    (r"\bclassified\b",             "classified information"),
]

# Preserved for any external caller still importing the old name directly
# (e.g. a script or notebook) -- behaves exactly as before for intern-role
# detection, since it's the union of all three groups' labels.
INTERN_BLOCKED_RULES = (
    [(p, l) for p, l, _perm in PERMISSION_GATED_RULES]
    + UNIVERSAL_BLOCKED_RULES
    + INTERN_ONLY_CAUTION_RULES
)

# ── Layer 1: HR PII masking rules ────────────────────────────────────────────
HR_MASKED_RULES = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
     "[EMAIL REDACTED]", "email address"),
    (r"\b(\+?\d[\d\s\-().]{7,}\d)\b",
     "[PHONE REDACTED]", "phone number"),
    (r"\b\d{3}-\d{2}-\d{4}\b",
     "[SSN REDACTED]", "SSN-format number"),
    (r"\b(?:\d[ -]?){13,16}\b",
     "[CARD REDACTED]", "card number"),
    (r"\$[\d,]+(?:\.\d{2})?(?:\s*(?:k|K|thousand|million|billion))?\b",
     "[AMOUNT REDACTED]", "salary/financial figure"),
    (r"(?i)password\s*[:=]\s*\S+",
     "password: [REDACTED]", "inline password"),
]

# ── Layer 2: Deep semantic risk signal groups ─────────────────────────────────
LAYER2_RULE_GROUPS = [
    ("cybersecurity threat language", [
        "hack", "exploit", "bypass", "inject", "sql injection",
        "xss", "csrf", "rce", "privilege escalation", "zero-day",
        "reverse shell", "payload", "c2 server", "exfiltrat",
    ]),
    ("malware / attack tooling", [
        "malware", "ransomware", "trojan", "rootkit", "keylogger",
        "spyware", "botnet", "ddos", "phishing", "spear phish",
        "brute force", "credential dump", "mimikatz",
    ]),
    ("data exfiltration signals", [
        "dump database", "export all", "extract records",
        "full database", "all passwords", "all credentials",
        "user table", "shadow file", "/etc/passwd",
    ]),
    ("sensitive PII disclosure", [
        "social security", "date of birth", "home address",
        "passport number", "driver license", "medical record",
        "health information", "financial record",
    ]),
    ("insider threat indicators", [
        "cover tracks", "delete logs", "clear audit", "hide activity",
        "disable monitoring", "turn off logging", "evade detection",
    ]),
]

_ALL_RISK_KEYWORDS = [kw for _, group in LAYER2_RULE_GROUPS for kw in group]


# ─────────────────────────────────────────────────────────────────────────────
# Data transfer objects
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FilterResult:
    filtered_response: str
    status: str
    risk_score: float
    risk_level: str
    reason: Optional[str] = None
    triggered_rules: list = field(default_factory=list)
    is_high_risk_alert: bool = False
    validator_notes: list = field(default_factory=list)
    recommended_action: Optional[str] = None
    policy_evidence: list = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Policy evidence — static reference, NOT retrieval-augmented generation
# ─────────────────────────────────────────────────────────────────────────────
# This maps each rule label this engine can trigger to the specific
# organization policy document (and clause) that actually governs it --
# see backend/policy_corpus/organization/*.md. It is a deterministic lookup
# table, not a similarity search over embeddings: the RAG pipeline (Phase 6)
# will eventually retrieve evidence dynamically across the full policy
# corpus (including the NIST/OWASP/DPDP external frameworks), and should
# supersede this table rather than run alongside it as a second, conflicting
# source of citations. Every citation below points to a clause that was
# actually authored to describe this exact rule, so this is accurate today,
# not a placeholder -- but its coverage is limited to the 4 org documents on
# purpose, since verifying accuracy against a hand-written table is only
# tractable for a small, fully-authored corpus.

_INTERN_RULE_POLICY_MAP = {
    "salary/compensation data": ["Role & Access Control Policy §3.2", "Data Privacy & Classification Policy §2.4"],
    "compensation information": ["Role & Access Control Policy §3.2", "Data Privacy & Classification Policy §2.4"],
    "pay scale details": ["Role & Access Control Policy §3.2", "Data Privacy & Classification Policy §2.4"],
    "password information": ["Data Privacy & Classification Policy §5.1(b)", "AI Security & Incident Response Policy §2(c)"],
    "credential data": ["Data Privacy & Classification Policy §5.1(b)", "AI Security & Incident Response Policy §2(c)"],
    "API key material": ["Data Privacy & Classification Policy §5.1(b)"],
    "secret/classified content": ["Data Privacy & Classification Policy §2.4", "AI Acceptable Use Policy §4.1"],
    "confidential content": ["AI Acceptable Use Policy §4.1", "Data Privacy & Classification Policy §2.3"],
    "proprietary information": ["AI Acceptable Use Policy §4.1"],
    "Social Security Number": ["Data Privacy & Classification Policy §5.1", "AI Security & Incident Response Policy §2(d)"],
    "Social Security information": ["Data Privacy & Classification Policy §5.1", "AI Security & Incident Response Policy §2(d)"],
    "credit card data": ["Data Privacy & Classification Policy §5.1"],
    "banking information": ["Data Privacy & Classification Policy §5.1"],
    "private key material": ["Data Privacy & Classification Policy §5.1(b)"],
    "internal-only content": ["AI Acceptable Use Policy §4.1", "Data Privacy & Classification Policy §2.2"],
    "classified information": ["Data Privacy & Classification Policy §2.4"],
    "personal data records": ["Role & Access Control Policy §3.2", "Data Privacy & Classification Policy §2.3"],
    "personally identifiable information": ["Role & Access Control Policy §3.2", "Data Privacy & Classification Policy §2.3"],
}

_LAYER2_CATEGORY_POLICY_MAP = {
    "cybersecurity threat language": ["AI Security & Incident Response Policy §2(a)"],
    "malware / attack tooling": ["AI Security & Incident Response Policy §2(b)"],
    "data exfiltration signals": ["AI Security & Incident Response Policy §2(c)", "Data Privacy & Classification Policy §5"],
    "sensitive PII disclosure": ["AI Security & Incident Response Policy §2(d)", "Data Privacy & Classification Policy §2.3"],
    "insider threat indicators": ["AI Security & Incident Response Policy §2(e)"],
}

_HR_MASK_POLICY_MAP = {
    "email address": ["Data Privacy & Classification Policy §4.1"],
    "phone number": ["Data Privacy & Classification Policy §4.1"],
    "SSN-format number": ["Data Privacy & Classification Policy §4.1", "§5.1"],
    "card number": ["Data Privacy & Classification Policy §4.1", "§5.1"],
    "salary/financial figure": ["Data Privacy & Classification Policy §4.1", "§2.4"],
    "inline password": ["Data Privacy & Classification Policy §5.1(b)"],
}


def _policy_evidence_for(triggered_rules, validator_notes, hr_masked_labels=None) -> list:
    """Deterministic mapping only -- see module docstring above."""
    citations = []
    for label in triggered_rules or []:
        for citation in _INTERN_RULE_POLICY_MAP.get(label, []):
            if citation not in citations:
                citations.append(citation)
    for label in hr_masked_labels or []:
        for citation in _HR_MASK_POLICY_MAP.get(label, []):
            if citation not in citations:
                citations.append(citation)
    for note in validator_notes or []:
        for category, citation_list in _LAYER2_CATEGORY_POLICY_MAP.items():
            if category in note:
                for citation in citation_list:
                    if citation not in citations:
                        citations.append(citation)
    return citations


def _recommended_action_for(status: str) -> str:
    if status == "blocked":
        return (
            "Do not attempt to access this information through the AI assistant. "
            "If you have a legitimate business need, contact HR or an authorized "
            "administrator for manual review."
        )
    if status == "filtered":
        return (
            "Review the masked response above. If you need the unredacted value "
            "for an authorized purpose, request it through the appropriate secure "
            "channel rather than the AI assistant."
        )
    return "No action required. Request was within policy for your role."


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def apply_governance(response: str, query: str, role: str, permissions: Optional[list] = None, risk_config: Optional[dict] = None) -> FilterResult:
    """
    permissions: the requester's effective permission list (see
    app.services.permissions.permissions_for_role). If not supplied, this
    looks the role up itself so existing callers that haven't been updated
    keep working -- but callers should pass this explicitly where possible,
    since it's the actual source of truth (a role's permissions can be
    reconfigured without this module knowing about it otherwise).

    risk_config: admin-configurable weights/thresholds (Phase 9), shaped
    like DEFAULT_RISK_CONFIG. If not supplied, DEFAULT_RISK_CONFIG is used --
    this keeps the module runnable and testable with zero Flask/DB
    dependency, while a Flask-aware caller can load real, saved admin
    configuration via app.services.risk_config_service.load_risk_config().
    """
    if permissions is None:
        from app.services.permissions import permissions_for_role
        permissions = permissions_for_role(role)
    config = {**DEFAULT_RISK_CONFIG, **(risk_config or {})}

    risk_score = _compute_risk_score(query, response, config)
    risk_level = _classify_risk(risk_score, config)
    validator_notes = _layer2_validator(response, query)

    if validator_notes and risk_level != "high":
        risk_score = min(risk_score + 0.25, 1.0)
        risk_level = _classify_risk(risk_score, config)

    result = _filter_by_permissions(query, response, role, permissions, risk_score, risk_level)

    if role == "hr":
        # HR-specific field masking runs in addition to (not instead of)
        # the permission-based blocking above -- HR holds view_employee_pii
        # and view_employee_salary, so it won't be blocked by those rules,
        # but inline PII that slips into a response text still gets masked.
        hr_result = _filter_hr(result.filtered_response, result.risk_score, result.risk_level)
        if hr_result.status == "filtered" and result.status == "allowed":
            hr_result.policy_evidence = result.policy_evidence + hr_result.policy_evidence
            result = hr_result

    result.validator_notes = validator_notes
    result.is_high_risk_alert = (result.risk_level == "high")
    result.recommended_action = _recommended_action_for(result.status)
    # Merge any policy evidence already set by the role filter (e.g. intern
    # blocklist citations) with evidence derived from Layer-2 validator hits,
    # which apply regardless of role.
    layer2_evidence = _policy_evidence_for([], validator_notes)
    for citation in layer2_evidence:
        if citation not in result.policy_evidence:
            result.policy_evidence.append(citation)
    return result


def compute_query_sensitivity(query: str) -> bool:
    q = query.lower()

    if any(kw in q for kw in _ALL_RISK_KEYWORDS):
        return True

    return any(re.search(pattern, q, re.IGNORECASE) for pattern, _ in INTERN_BLOCKED_RULES)


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — Role/permission filters
# ─────────────────────────────────────────────────────────────────────────────

def _filter_by_permissions(query, response, role, permissions, risk_score, risk_level):
    """Applies UNIVERSAL_BLOCKED_RULES (every role) and PERMISSION_GATED_RULES
    (only roles lacking the relevant permission) to any role -- this is what
    replaced the old "only intern gets filtered" behavior. Intern additionally
    gets INTERN_ONLY_CAUTION_RULES, preserving its prior (unchanged) behavior
    for that bucket.
    """
    triggered = _detect_universal_blocks(query, response)
    triggered += [
        label for label in _detect_permission_gated_blocks(query, response)
        if _permission_for_label(label) not in permissions
    ]
    if role == "intern":
        triggered += _detect_intern_caution_blocks(query, response)

    if triggered:
        joined = ", ".join(triggered)
        explanation = (
            f"This request is blocked because it asks about restricted information: {joined}. "
            "Your role does not have permission to access confidential, credential, compensation, "
            "or regulated personal data of this kind."
        )
        guidance = (
            "Why you cannot ask this: your current role's permissions do not cover that data. "
            "If you need legitimate access, contact HR or an admin, or ask for a high-level policy summary instead."
        )
        return FilterResult(
            filtered_response=(
                "Alert: Request blocked by SecureAI policy.\n"
                f"Why it was blocked: {explanation}\n"
                f"Why you cannot ask this: {guidance}"
            ),
            status="blocked",
            risk_score=max(risk_score, 0.75),
            risk_level="high",
            reason=f"{explanation} {guidance}",
            triggered_rules=triggered,
            is_high_risk_alert=True,
            policy_evidence=_policy_evidence_for(triggered, []),
        )
    return FilterResult(
        filtered_response=response,
        status="allowed",
        risk_score=risk_score,
        risk_level=risk_level,
    )


def _filter_hr(response, risk_score, risk_level):
    masked = response
    triggered = []
    for pattern, replacement, label in HR_MASKED_RULES:
        new_masked, count = re.subn(pattern, replacement, masked, flags=re.IGNORECASE)
        if count > 0:
            triggered.append(label)
            masked = new_masked

    if triggered:
        joined = ", ".join(triggered)
        reason = (
            f"Response automatically redacted {len(triggered)} sensitive field(s): {joined}. "
            f"Data masked per HR data-handling policy."
        )
        return FilterResult(
            filtered_response=masked,
            status="filtered",
            risk_score=risk_score,
            risk_level=risk_level,
            reason=reason,
            triggered_rules=triggered,
            policy_evidence=_policy_evidence_for([], [], hr_masked_labels=triggered),
        )
    return FilterResult(
        filtered_response=response,
        status="allowed",
        risk_score=risk_score,
        risk_level=risk_level,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 — Validator
# ─────────────────────────────────────────────────────────────────────────────

def _layer2_validator(response, query):
    combined = (query + " " + response).lower()
    notes = []
    for category, keywords in LAYER2_RULE_GROUPS:
        hits = [kw for kw in keywords if kw in combined]
        if hits:
            sample = hits[:2]
            notes.append(
                f"Detected {category} signal "
                f"(matched: {', '.join(repr(h) for h in sample)})"
            )
    return notes


def _detect_intern_blocked_rules(query, response):
    """Kept for backward compatibility with any external caller still using
    the old name/behavior (union of all three rule groups)."""
    combined = f"{query or ''} {response or ''}"
    triggered = []
    for pattern, label in INTERN_BLOCKED_RULES:
        if re.search(pattern, combined, re.IGNORECASE) and label not in triggered:
            triggered.append(label)
    return triggered


def _permission_for_label(label: str) -> Optional[str]:
    for _pattern, rule_label, permission in PERMISSION_GATED_RULES:
        if rule_label == label:
            return permission
    return None


def _detect_universal_blocks(query, response):
    combined = f"{query or ''} {response or ''}"
    triggered = []
    for pattern, label in UNIVERSAL_BLOCKED_RULES:
        if re.search(pattern, combined, re.IGNORECASE) and label not in triggered:
            triggered.append(label)
    return triggered


def _detect_permission_gated_blocks(query, response):
    combined = f"{query or ''} {response or ''}"
    triggered = []
    for pattern, label, _permission in PERMISSION_GATED_RULES:
        if re.search(pattern, combined, re.IGNORECASE) and label not in triggered:
            triggered.append(label)
    return triggered


def _detect_intern_caution_blocks(query, response):
    combined = f"{query or ''} {response or ''}"
    triggered = []
    for pattern, label in INTERN_ONLY_CAUTION_RULES:
        if re.search(pattern, combined, re.IGNORECASE) and label not in triggered:
            triggered.append(label)
    return triggered


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3 — Risk scoring + classification
# ─────────────────────────────────────────────────────────────────────────────

def _compute_risk_score(query, response, config=None):
    config = config or DEFAULT_RISK_CONFIG
    combined = (query + " " + response).lower()
    group_weights = [
        config["weight_cybersecurity_threat"],
        config["weight_malware_attack_tooling"],
        config["weight_data_exfiltration"],
        config["weight_sensitive_pii"],
        config["weight_insider_threat"],
    ]
    group_score = 0.0

    for (_, keywords), weight in zip(LAYER2_RULE_GROUPS, group_weights):
        hits = sum(1 for kw in keywords if kw in combined)
        if hits:
            group_score += min(hits / len(keywords), 1.0) * weight

    keyword_score = min(group_score / sum(group_weights), 1.0)
    length_score = min(len(response) / 6000, 0.25)

    intent_score = 0.0
    intent_phrases = [
        "how do i hack", "how to bypass", "give me all",
        "list all users", "show me passwords", "what are the credentials",
        "ignore previous", "disregard your instructions", "pretend you are",
    ]
    if any(p in combined for p in intent_phrases):
        intent_score = 0.3

    raw = keyword_score * 0.60 + length_score * 0.15 + intent_score * 0.25
    return round(min(raw, 1.0), 3)


def _classify_risk(score, config=None):
    config = config or DEFAULT_RISK_CONFIG
    if score <= config["risk_threshold_low_max"]:
        return "low"
    elif score <= config["risk_threshold_medium_max"]:
        return "medium"
    return "high"
