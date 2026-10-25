"""
Permission catalog and role -> permission mapping for the AI-governance
demo role set (see services/roles.py GOVERNANCE_DEMO_ROLES).

This intentionally covers governance-relevant permissions only -- it is
not meant to gate every UI feature in the app (work management, messaging,
etc. keep their own existing route-level checks). Its job is to give the
governance/RBAC layer (Phase 2) and the compliance-check engine (Phase 8)
a data-driven source of truth instead of hardcoded role-name comparisons.
"""

from app.services.roles import GOVERNANCE_DEMO_ROLES, normalize_role_name

PERMISSION_CATALOG = [
    ("view_public_information", "general", "View public/non-sensitive company information"),
    ("view_project_information_limited", "project", "View limited project information relevant to assigned work"),
    ("view_project_information_full", "project", "View full technical/project information"),
    ("view_employee_pii", "hr_data", "View authorized employee personal information"),
    ("view_employee_salary", "hr_data", "View employee compensation/salary information"),
    ("use_ai_assistant", "ai", "Use the SecureAI governance assistant"),
    ("ai_governance_admin", "governance", "View audit logs, risk events, and governance cases"),
    ("manage_policies", "governance", "Upload, re-index, enable/disable policy documents"),
    ("manage_risk_configuration", "governance", "Edit risk engine weights and thresholds"),
    ("manage_users", "admin", "Create users and assign roles"),
    ("system_configuration_admin", "admin", "Change system-wide configuration"),
]

# Role name (normalized/title-cased, matching services.roles.normalize_role_name
# output) -> list of permission names granted to that role.
ROLE_PERMISSION_MAP = {
    "Guest": [
        "view_public_information",
    ],
    "Intern": [
        "view_public_information",
        "view_project_information_limited",
        "use_ai_assistant",
    ],
    "Software Engineer": [
        "view_public_information",
        "view_project_information_full",
        "use_ai_assistant",
    ],
    "HR": [
        "view_public_information",
        "view_project_information_limited",
        "view_employee_pii",
        "view_employee_salary",
        "use_ai_assistant",
    ],
    "Manager": [
        "view_public_information",
        "view_project_information_full",
        "view_employee_pii",
        "use_ai_assistant",
    ],
    "Supervisor": [
        "view_public_information",
        "view_project_information_full",
        "use_ai_assistant",
    ],
    "Admin": [name for name, _category, _description in PERMISSION_CATALOG],
}

# Any catalog role not in GOVERNANCE_DEMO_ROLES (e.g. "Developer",
# "Finance", "Sales", ...) gets this default governance permission set --
# equivalent to a generic authenticated employee. This keeps every seeded
# account functional without requiring every one of the ~24 legacy roles
# to be individually mapped.
DEFAULT_PERMISSIONS = [
    "view_public_information",
    "view_project_information_limited",
    "use_ai_assistant",
]


def permissions_for_role(role_name: str) -> list[str]:
    normalized = normalize_role_name(role_name)
    if normalized in ROLE_PERMISSION_MAP:
        return ROLE_PERMISSION_MAP[normalized]
    return DEFAULT_PERMISSIONS


def role_has_permission(role_name: str, permission_name: str) -> bool:
    return permission_name in permissions_for_role(role_name)


__all__ = [
    "PERMISSION_CATALOG",
    "ROLE_PERMISSION_MAP",
    "DEFAULT_PERMISSIONS",
    "permissions_for_role",
    "role_has_permission",
    "GOVERNANCE_DEMO_ROLES",
]
