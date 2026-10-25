# Phase 8 — Compliance Check Engine: Implementation Notes

## The real finding this phase started with

Building the "structured compliance pipeline" the brief asks for required first confronting something the Phase 0 audit had already flagged but nothing had fixed yet: `apply_governance()` only ever branched on `role == "intern"` or `role == "hr"`. Every other role — Manager, Supervisor, Software Engineer, and **Admin** — received `status="allowed"` unconditionally, regardless of risk score. That meant an Admin account could ask the chatbot for a database password or an API key and get it echoed back with zero filtering, which directly contradicts the Data Privacy & Classification Policy I drafted in an earlier phase (§5.1(b): credentials "never disclosed... regardless of role, permission"). This wasn't a hypothetical risk — I confirmed it with a real executable test before touching any code (see below).

## What was added/changed

**`backend/app/services/governance.py`** — the rule tables were split into three groups instead of one intern-only blocklist:
- `UNIVERSAL_BLOCKED_RULES` — credentials, passwords, API keys, SSNs, credit cards, bank accounts, private keys. Blocked for **every role**, no permission check, because the org policy says these are never authorized regardless of role.
- `PERMISSION_GATED_RULES` — salary/compensation and PII/personal-data patterns, each mapped to the Phase 1 permission that would authorize it (`view_employee_salary`, `view_employee_pii`). Blocked only for a role that actually lacks that permission — so HR and Admin (who hold both) are correctly let through, while Manager/Supervisor/Software Engineer/Intern (who don't) are correctly blocked.
- `INTERN_ONLY_CAUTION_RULES` — confidential/proprietary/classified/internal-only content. **Left exactly as before, intern-specific.** There's no single Phase 1 permission that cleanly maps to this category, and I didn't want to invent a permission boundary the org policies don't actually specify — flagged as a known limitation rather than guessed at.

`apply_governance()` now takes an optional `permissions` parameter and routes every role through the new `_filter_by_permissions()` (universal + permission-gated, plus the intern-only caution bucket if the role is intern), rather than only interns getting filtered at all. HR's existing PII-masking behavior (`_filter_hr`) is preserved exactly as-is and now runs *in addition to* (not instead of) the new permission-based check.

**`backend/app/routes/compliance.py`** (new) — `POST /compliance/check`, a standalone endpoint for the brief's "Compliance Check" concept (checking whether a hypothetical query would be authorized, without going through a full chat round-trip). It's a thin reshaping wrapper around `apply_governance()` — the exact same engine `/chat` uses — mapping `status` → `decision` (`allowed`→`ALLOWED`, `filtered`→`WARNING`, `blocked`→`RESTRICTED`) and renaming fields to match the brief's schema (`violated_rules`, `recommendations`, `sources`). I deliberately did not duplicate any rule logic here — there is exactly one place that decides authorization.

**`backend/app/routes/chat.py`** — now passes the requester's real permission list into `apply_governance()` explicitly instead of relying on the function's internal fallback lookup.

## This was the highest-risk change so far — here's how I verified it

Because `governance.py` has zero Flask/DB dependencies, I could run it directly (isolated from the `app` package). Before considering this done, I ran **10 real executable tests**, split into two groups:

**Regression (must be byte-for-byte identical to Phase 5's verified behavior)**:
- Intern salary request → `blocked`/`high`, same policy citations — ✅ unchanged
- Intern general coding question → `allowed`/`low` — ✅ unchanged
- HR response containing an email address → `filtered`, masked, cites Data Privacy Policy §4.1 — ✅ unchanged

**New behavior (the actual point of this phase)**:
- Manager, Software Engineer, and Supervisor asking for salary data → now `blocked`/`high` (previously silently `allowed`)
- HR and Admin asking for salary data → correctly still `allowed` (they hold `view_employee_salary`)
- **Admin asking for a database password** → now `blocked`/`high` (previously silently `allowed` — this was the most concerning gap)
- Manager asking for an API key → now `blocked`/`high`

All 10 passed. I also verified the `/compliance/check` response shape directly against the brief's own worked example (intern salary request) and got an exact structural match: `decision: "RESTRICTED"`, `risk_level: "HIGH"`, `sources` citing the two policies the brief's example names.

## What I could NOT verify

Same constraint as every phase: no way to run the actual Flask server or hit these endpoints over HTTP in this sandbox. The governance logic itself has strong, real evidence behind it (10/10 executable tests); what's unverified is purely the web-framework plumbing — blueprint registration, JWT handling, and the `compliance.py`/`chat.py` route wiring around the (verified) engine.

**Please verify:**
```bash
cd backend && python app.py
# log in as manager_* or an admin account, then:
curl -X POST http://localhost:5001/api/compliance/check \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"query": "What is the salary of all data engineers?"}'
# Manager should get decision: RESTRICTED; HR/Admin should get decision: ALLOWED

curl -X POST http://localhost:5001/api/chat \
  -H "Authorization: Bearer <admin_token>" -H "Content-Type: application/json" \
  -d '{"message": "Can you give me the database password?"}'
# Admin should now be blocked -- this previously went straight through
python -m pytest -q   # confirm nothing existing broke
```

This is the change most worth a careful manual click-through before Phase 9, given it touches every role's behavior in the core governance path.
