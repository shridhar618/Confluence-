# Phase 1 — Database + Core Architecture: Implementation Notes

## What was added

New model files (all additive — no existing table was dropped, renamed, or had a column removed):

- `app/models/permission.py` — `Permission` + `role_permissions` association table (many-to-many with `Role`)
- `app/models/policy_document.py` — `PolicyDocument` (Phase 7 policy corpus entries)
- `app/models/policy_chunk.py` — `PolicyChunk` (Phase 6 RAG retrieval unit, links to Qdrant via `qdrant_point_id`)
- `app/models/risk_event.py` — `RiskEvent` (cumulative risk ledger, Phase 10)
- `app/models/governance_case.py` — `GovernanceCase` (Phase 11 case management)
- `app/models/admin_action.py` — `AdminAction` (Phase 11 auditable admin decisions)
- `app/models/risk_configuration.py` — `RiskConfiguration` (Phase 9 admin-configurable weights/thresholds)
- `app/models/security_event.py` — `SecurityEvent` (Phase 20 attack-sim / security-lab events)
- `app/models/notification.py` — `Notification` (Phase 13 alert center)

Modified files:

- `app/models/__init__.py` — registers the 9 new models so `db.create_all()` picks them up
- `app/services/roles.py` — added `Guest`, `Software Engineer`, `Supervisor` to `ROLE_CATALOG` (additive; nothing removed), and a new `GOVERNANCE_DEMO_ROLES` constant
- `app/services/permissions.py` (new) — `PERMISSION_CATALOG`, `ROLE_PERMISSION_MAP`, `permissions_for_role()`, `role_has_permission()`
- `app/__init__.py` — added `_seed_permissions()`, `_seed_role_permissions()`, `_seed_risk_configuration()`, called from `create_app()` alongside the existing seed functions

## Key decisions and rationale

### 1. `AuditLog` remains the `AIRequest` entity; no separate table added

The capstone brief's schema lists a distinct `AIRequest` entity. The existing `AuditLog` model already captures everything an `AIRequest` row would (user, role, query, response, risk_score, risk_level, reason, triggered_rules) and is already wired end-to-end through `routes/chat.py`. Adding a second table would either duplicate data or require a redundant join for no functional gain, which conflicts with Phase 1's "do not over-normalize" instruction. `AuditLog` **is** the AI-request log; `RiskEvent` and `GovernanceCase` reference it via `audit_log_id`.

### 2. `RiskEvent` is a ledger, not a duplicate of `AuditLog.risk_score`

Every `AuditLog` row already has its own risk score for that single request. `RiskEvent` exists specifically to support **cumulative** risk tracking (Phase 10): it stores a running `cumulative_score` per user at the time of each risky event, so the escalation logic can check "has this user crossed the cumulative threshold?" in O(1) instead of re-summing the user's entire `AuditLog` history on every request.

### 3. `GovernanceCase` is intentionally separate from the existing `WorkEscalation`

`WorkEscalation` (pre-existing) tracks **workforce/KPI capacity risk** — e.g., "this employee is behind on tasks." `GovernanceCase` tracks **AI-governance risk** — e.g., "this employee is repeatedly asking for data their role doesn't authorize." These are different signals with different admin workflows and should not be merged into one status enum, or the admin dashboard would conflate two unrelated kinds of "risk." Both ultimately feed the same admin Alert Center (`Notification` model), so an admin sees everything in one place without the underlying concepts being blurred.

### 4. Role catalog: added 3 roles, didn't rename or remove any

The capstone brief's example role set is Guest / Intern / Software Engineer / HR / Manager / Supervisor / Admin. The existing seeded catalog already had `Admin`, `HR`, `Intern`, plus ~21 others (`Developer`, `Manager`, `Team Lead`, etc.) but was missing `Guest`, `Software Engineer`, and `Supervisor`. Per the non-negotiable "don't replace working functionality unnecessarily" instruction, I added the 3 missing roles rather than renaming existing ones (e.g., renaming `Developer` → `Software Engineer` would have been a plausible alternative, but risks breaking anything elsewhere in the codebase that already compares against the string `"Developer"` or `"developer"`, which I have not exhaustively grepped for at every call site).

### 5. Permissions are demo-scoped, not exhaustive

`PERMISSION_CATALOG` covers governance-relevant permissions only (viewing salary/PII, using the AI assistant, managing policies/risk config/users). It does not attempt to gate every existing feature (work management, messaging, attendance keep their existing route-level role checks for now — retrofitting those onto the new permission model is a Phase 2 decision, not Phase 1's job). The 7 `GOVERNANCE_DEMO_ROLES` get an explicit permission mapping; the other ~21 legacy catalog roles fall back to a sensible `DEFAULT_PERMISSIONS` set (view public/limited project info + use AI assistant) so no existing seeded account loses functionality.

### 6. `RiskConfiguration` seeds the *current* `governance.py` constants, doesn't change them yet

The seeded default values (`risk_threshold_low_max = 0.30`, `risk_threshold_medium_max = 0.70`, and the Layer-2 keyword-group weights `0.6/0.8/1.0/0.7/1.0`) are exact copies of the constants already hardcoded in `services/governance.py`. This means Phase 1 introduces zero behavior change to the existing governance engine — it only creates the admin-configurable table. Phase 9 will be the point where `governance.py` actually reads from `RiskConfiguration` instead of its own constants.

## What I could NOT verify in this environment

My sandbox has no outbound network access, so I could not `pip install` the backend's dependencies (`flask-sqlalchemy`, `flask-jwt-extended`, `flask-socketio`, etc.) and therefore could not actually run:

- `db.create_all()` against a real SQLite file to confirm the new tables and relationships build without error
- the seeding functions end-to-end
- the existing `pytest` suite, to confirm nothing broke

I did verify:

- every new/modified `.py` file compiles (`python -m py_compile`) with no syntax errors
- relationship/backref names don't collide with existing attributes on `User`, `Role`, or `AuditLog`
- foreign keys reference existing table names correctly (`users.id`, `roles.id`, `audit_logs.id`, `governance_cases.id`)
- the `metadata` column-vs-attribute SQLAlchemy pitfall is avoided in `SecurityEvent` (mapped to `metadata_json` in Python, `metadata` in the DB column)

**Please run this locally and share the output before we proceed to Phase 2**, so we catch anything a static review can't:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
# in another terminal, confirm the new tables exist:
python3 -c "
from app import create_app, db
app = create_app()
with app.app_context():
    from sqlalchemy import inspect
    tables = inspect(db.engine).get_table_names()
    for t in ['permissions','role_permissions','policy_documents','policy_chunks','risk_events','governance_cases','admin_actions','risk_configurations','notifications']:
        print(t, 'OK' if t in tables else 'MISSING')
"
python -m pytest -q
```

If `python app.py` or the pytest run throws anything, paste it back and I'll fix it before we touch Phase 2.
