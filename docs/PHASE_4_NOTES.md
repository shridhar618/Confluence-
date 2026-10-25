# Phase 4 — AI Governance Dashboard: Implementation Notes

## Starting point (important)

Unlike Phases 0–3, this dashboard was **already substantially built and real** — `GET /logs/stats` already computed genuine totals/blocked/filtered/allowed/risk-level counts from `AuditLog`, and `DashboardPage.jsx` already had working tabs (Overview / Audit Logs / Threats), real charts (status pie, per-user bar chart), filters, pagination, and an explainability drawer. This phase adds the pieces the capstone brief calls for that were genuinely missing, rather than rebuilding what already worked.

## What was added

**Backend (`app/routes/logs.py`, `/logs/stats`)**:
- `risky_requests` — `risk_medium + risk_high` count (real, derived from existing data)
- `open_governance_cases` — real count from the Phase 1 `GovernanceCase` table, `status="open"`
- `active_restrictions` — real count from `GovernanceCase`, `status="restricted"`
- `usage_over_time` — real 14-day daily request count, grouped via `strftime('%Y-%m-%d', ...)` on `AuditLog.timestamp`

**Frontend (`DashboardPage.jsx`)**:
- Fixed a leftover stray word in the page title ("Governance Dashboard Pavan" → "Governance Dashboard") — looked like debug/placeholder text left over from development, worth catching per the "no page should look like a different application" principle.
- Added a third stat-card row: Risky Requests, Open Governance Cases, Active Restrictions
- Added an "AI Usage Over Time" area chart using the new 14-day series

## Key decisions and rationale

### 1. `open_governance_cases` and `active_restrictions` will read 0 right now — and that's correct, not broken

Nothing in the codebase yet creates a `GovernanceCase` row or moves one to `status="restricted"` — that's Phase 10 (cumulative risk escalation) and Phase 11 (case management)'s job. Showing a real, honest zero here is consistent with how the rest of this dashboard already handles empty states ("No blocked activity by role yet," "No high-risk events logged"). I deliberately did **not** repurpose the existing `User.is_suspicious` flag to fake a plausible-looking "Active Restrictions" number — `is_suspicious` doesn't actually restrict anything today, so displaying it under that label would misrepresent what the system currently does.

### 2. Admin quick actions (Review Case, Warn, Restrict, Restore, Escalate) were deliberately NOT added this phase

The capstone brief's Phase 4 spec calls for these, but they require the `GovernanceCase`/`AdminAction` workflow endpoints that are explicitly Phase 11's scope. Adding buttons now that call non-existent endpoints would be exactly the "placeholder functionality" the brief says not to create. "View Evidence" already exists in a working form — the Eye icon on each audit row opens the ExplainDrawer, which already shows query, response, reason, and triggered rules. The other five actions will be added once Phase 11 gives them something real to do.

### 3. Terminology: kept the existing Allowed/Filtered/Blocked labels rather than renaming to Allowed/Warning/Restricted

The brief's example scenarios use "Warning" and "Restricted"; the existing codebase (governance.py, AuditLog.status, the CSV export headers, and the UI's status pills/filters) already uses "filtered" and "blocked" consistently throughout. These map onto the same concepts. Renaming would touch the governance engine, the audit log schema's stored values, CSV export column headers, and every place that filters by status string — a broad, moderate-risk rename with no functional benefit, versus just documenting the mapping here. If you'd specifically like the UI-facing labels changed to "Warning"/"Restricted" for the capstone presentation while keeping the underlying `status` values unchanged, that's a much smaller, low-risk follow-up (display-string mapping only) I can do on request.

### 4. Icon names were chosen conservatively

I don't have a local copy of `lucide-react` to check against and no network to verify a package registry, so for the two new stat cards I used `Clock` and `Ban` rather than more thematically specific names I wasn't fully certain exist in this icon set (I'd initially reached for `FolderClock`/`ShieldOff` and backed off rather than risk an import error breaking the whole page).

## What I could verify

Same approach as Phase 3: ran `esbuild.transformSync` against the modified `DashboardPage.jsx` — parses cleanly. Confirmed `format` (date-fns) and `AlertTriangle` (already used elsewhere in the same file) aren't newly-introduced or conflicting imports. Syntax-checked `logs.py` with `py_compile`. Did **not** verify the actual SQL (`strftime` grouping, the `GovernanceCase` count queries) executes correctly against a real SQLite database — same network constraint as every prior phase.

**Please verify:**
```bash
cd backend && python app.py
curl -s http://localhost:5001/api/logs/stats -H "Authorization: Bearer <admin_token>" | python -m json.tool
# confirm risky_requests / open_governance_cases / active_restrictions / usage_over_time appear and are numeric/list as expected
```
```bash
cd frontend && npm run build
```
And visually: log in as admin, open the Dashboard, confirm the new stat row and the usage chart render (the chart will show a flat empty state until there's more than one day of audit history — that's expected on a fresh DB).
