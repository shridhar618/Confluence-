# Phase 10 — Cumulative Risk + Escalation: Implementation Notes

## What was added

**`backend/app/services/risk_tracking.py`** (new) — `record_risk_event(user, audit_log, result, risk_config)`, called from `chat.py` right after every `AuditLog` row is committed. Implements two distinct behaviors, matching the capstone brief's two separate demo workflows:

- **Demo 2 (single sensitive request)**: any individual HIGH-risk request immediately notifies every Admin user (`Notification`, `type="high_risk_request"`) — a single serious attempt doesn't wait for a pattern to form.
- **Demo 3 (repeated risk)**: every medium/high-risk request adds its `risk_score` to a running per-user cumulative total (tracked via the `RiskEvent.cumulative_score` field added in Phase 1). When the total crosses the admin-configured `cumulative_risk_case_threshold` (from Phase 9's `RiskConfiguration`) **and the user doesn't already have an open case**, a `GovernanceCase` is created at `status="open"` and a separate notification goes out. Low-risk requests are never tracked here at all — cumulative tracking exists to catch a pattern of risky behavior, not to accumulate noise from routine, allowed usage.

**`chat.py`**: calls `record_risk_event()` after committing the audit log, reusing the same `risk_config` already loaded for `apply_governance()` (avoids a duplicate database query).

## The one thing this phase deliberately does NOT do

The system never sets a case to `status="restricted"` or takes any consequential action on its own — it only opens a case at `status="open"` and notifies admins. Moving a case forward (Warn / Restrict / Restore / Escalate / Resolve) is explicitly Phase 11's job, per the brief's own Phase 10 principle: "Human administrator remains responsible for consequential action." I did not pull any of Phase 11's scope forward into this phase.

## How I verified this, and why it's different from every prior phase

Unlike `governance.py`, this service genuinely needs a real database — it queries the user's risk history and creates rows. That means I couldn't run the *actual* function the way I've run every governance test so far. What I could do, and did: extracted the core decision logic (cumulative math + "should a case open now" branching) into a standalone simulation using plain Python objects standing in for the SQLAlchemy models, and ran it against a scenario shaped exactly like the brief's own Demo 3 example (medium → medium → high, crossing the threshold on the third request):

```
Request 1 (medium, 0.45): cumulative=0.45, no case
Request 2 (medium, 0.50): cumulative=0.95, no case
Request 3 (high, 0.75):   cumulative=1.70, CASE OPENS (threshold 1.50 crossed)
Request 4 (high, 0.80):   cumulative=2.50, case already open -- no duplicate case
```

This confirms the arithmetic and the "don't open a second case while one is already open" guard both work as intended. I then re-read the real `record_risk_event()` implementation line-by-line against this verified logic to confirm they match. **This is weaker evidence than the governance.py tests** (I simulated the decision logic, not the actual database-touching function), and I want to be upfront about that difference rather than imply the same confidence level as prior phases.

## A known limitation to flag for Phase 11

`record_risk_event()` only checks for an existing case with `status="open"` exactly, to decide whether to suppress creating a new one. Right now that's fine because nothing yet moves a case out of `"open"` — Phase 11 doesn't exist yet. But once Phase 11 adds admin actions that transition a case to `"under_review"` or `"warned"`, this check needs to become "does the user have any *unresolved* case" (e.g., `status not in ("resolved",)`) rather than strictly `status == "open"`, or a user under active review could accumulate a second, duplicate case while the first is still being handled. Flagging this now so it's designed correctly when Phase 11 is built, not discovered as a bug afterward.

## What I could NOT verify

Everything DB-touching: whether `GovernanceCase.query.filter_by(...)` and `RiskEvent.query.filter_by(...)` behave correctly against a real SQLite file, whether the `Notification` rows actually get created and are visible via the Phase 3 notification bell, and whether the whole chain (chat → audit log → risk event → case → notification) survives a real request without an exception. Same sandbox constraint as always.

**Please verify:**
```bash
cd backend && python app.py
# as an intern account, trigger 2-3 medium/high risk requests in a row
# (e.g. ask about "internal only" content a couple times, then ask for salary data)
# then, as admin:
curl http://localhost:5001/api/notifications -H "Authorization: Bearer <admin_token>"
# should show high_risk_request and/or governance_case_opened notifications

curl http://localhost:5001/api/risk-config -H "Authorization: Bearer <admin_token>"
# confirm cumulative_risk_case_threshold value, then check the SQLite db directly:
sqlite3 instance/secureai.db "SELECT * FROM risk_events ORDER BY id DESC LIMIT 5;"
sqlite3 instance/secureai.db "SELECT * FROM governance_cases;"
```
