ROLE_CATALOG = [
    "Admin",
    "HR",
    "Intern",
    "Employee",
    "Developer",
    "Senior Developer",
    "Tech Lead",
    "Team Lead",
    "Manager",
    "Project Manager",
    "Product Manager",
    "QA Engineer",
    "UI/UX Designer",
    "DevOps Engineer",
    "Security",
    "Security Analyst",
    "Finance",
    "Analyst",
    "Operations",
    "Operations Manager",
    "Support Engineer",
    "Sales",
    "Marketing",
    "Recruiter",
    # Added for the AI-governance permission demo (Phase 1/2): these are the
    # capstone brief's example role set alongside Admin/HR/Intern above.
    "Guest",
    "Software Engineer",
    "Supervisor",
]

# The subset of roles the AI-governance permission model actively
# distinguishes for the capstone demo (see docs/PHASE_1_NOTES.md). The
# other ~24 catalog roles above remain valid accounts (used by work
# management, attendance, messaging, etc.) but default to the "Employee"
# governance permission set unless explicitly mapped in services/permissions.py.
GOVERNANCE_DEMO_ROLES = [
    "Guest",
    "Intern",
    "Software Engineer",
    "HR",
    "Manager",
    "Supervisor",
    "Admin",
]

MANAGER_ROLE_NAMES = {
    "admin",
    "hr",
    "manager",
    "team lead",
    "tech lead",
    "project manager",
    "product manager",
    "operations manager",
}


def normalize_role_name(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized == "hr":
        return "HR"
    if normalized == "ui/ux designer":
        return "UI/UX Designer"
    return normalized.title()


def is_manager_role(role_name: str | None) -> bool:
    return (role_name or "").strip().lower() in MANAGER_ROLE_NAMES
