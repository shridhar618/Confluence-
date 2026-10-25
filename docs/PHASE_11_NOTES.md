# Phase 11 — Admin Governance Case Management: Implementation Notes

## What was added

**`backend/app/routes/governance_cases.py`** (new blueprint):
- `GET /governance-cases` — list all cases, optional `?status=` filter
- `GET /governance-cases/<id>` — full case detail including risk events and action history
- `POST /governance-cases/<id>/actions` — take an admin action (`review`, `warn`, `restrict`, `restore`, `escalate`, `resolve`, `note`)

All three gated by `require_permission("ai_governance_admin")`. Every action writes an `AdminAction` row (admin identity + timestamp + optional note), auto-assigns the case to the acting admin if unassigned, and stamps `resolved_at` on resolve.

**`frontend/src/pages/GovernanceCasesPage.jsx`** (new) — case table (Case ID / User / Risk / Status / Created / Assigned) with a status filter, plus a slide-in detail drawer showing the trigger, the six action buttons, a note field, the case's risk-event timeline, and full action history. Registered at `/governance-cases` (adminOnly) and added to the sidebar's Security section.

## Fixed the issue I flagged last phase

Phase 10's notes flagged that `record_risk_event()` checked for an existing case with `status == "open"` exactly, which would let a duplicate case get created once Phase 11 introduced status transitions (a user under `under_review` would look like they had no case). Now that those transitions actually exist, I changed the check to `status != "resolved"` — any unresolved case counts as "already being handled." This was the specific bug I predicted, fixed in the phase that created the conditions for it rather than left to be discovered later.

## Status transition design

`_status_for_action()` is a pure function with no Flask/DB reference, so it's directly testable. I ran **11 real executable transition tests**, all passing:

- `review` on an `open` case → `under_review`; `review` on an already-`warned` case → stays `warned` (taking a second look doesn't reset progress)
- `warn`/`restrict`/`escalate`/`resolve` → their corresponding statuses, from any prior state
- `note` → never changes status, from any state (it's a log entry only)
- `restore` on a `restricted` case → `under_review`

That last one is a judgment call worth flagging: restoring access returns the case to `under_review` rather than `open` (which would imply nobody had looked at it) or `resolved` (which would imply the matter is closed). Restoring access and closing the case are deliberately separate decisions — an admin who restores access still has to explicitly `resolve`.

## A process note on how I verified the frontend

While checking the new page's icon imports against what's already used elsewhere, I initially told myself the icons were "already proven safe by existing files" — then actually ran the check and found four of them (`AlertOctagon`, `ArrowUpCircle`, `FileText`, `MessageSquarePlus`) appear **nowhere else in the codebase**, and three more (`FileText`, `User`, `Clock`) were imported but never used in my own page body. I'd made an assumption and stated it before testing it. I replaced all four with icons that genuinely are used in existing working files (`AlertTriangle`, `ArrowRight`, `MessageSquare`) and dropped the unused imports. Re-ran the check: zero unproven icons, zero unused imports. Worth recording because "the existing code already uses this" is exactly the kind of claim that's easy to assert and easy to verify — and I should verify it before asserting it.

## What I could NOT verify

The entire DB/HTTP layer, as always: whether the case list/detail queries work against real SQLite, whether `POST .../actions` persists correctly, whether `require_permission("ai_governance_admin")` returns a clean 403 for non-admins, and whether the page actually renders. The `_status_for_action` logic is genuinely tested; everything around it is not.

**Please verify:**
```bash
cd backend && python app.py
# First generate a case (Phase 10): trigger repeated risky requests as an intern
# until cumulative risk crosses the threshold. Then as admin:
curl http://localhost:5001/api/governance-cases -H "Authorization: Bearer <admin_token>"
curl -X POST http://localhost:5001/api/governance-cases/1/actions \
  -H "Authorization: Bearer <admin_token>" -H "Content-Type: application/json" \
  -d '{"action_type": "review", "note": "Initial triage"}'
# confirm status moves open -> under_review and the action appears in history

# as intern -- should be 403, not a crash:
curl http://localhost:5001/api/governance-cases -H "Authorization: Bearer <intern_token>"
```
```bash
cd frontend && npm run build && npm run dev
# visit /governance-cases as admin; confirm the table, drawer, and action buttons work
```
