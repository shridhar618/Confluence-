# Phase 12 — Audit Logging: Implementation Notes

## Starting point

Substantial audit infrastructure already existed: `GET /logs` with username/status/risk/high-risk/free-text filters, pagination, CSV export, and the Dashboard's Audit Logs tab with an explainability drawer. What was missing against the brief's Phase 12 spec were (a) coverage — only AI chat requests were ever logged, and (b) two named filters: **action/event type** and **date range**.

## What was added

**`backend/app/models/audit_log.py`** — three new columns: `event_type` (indexed), `resource`, and `metadata` (JSON blob). `to_dict()` now exposes them, with `event_type` defaulting to `"ai_request"` for rows written before this phase.

**`backend/app/services/audit.py`** (new) — `record_audit_event(event_type, user, description, resource, ..., commit=False|True)`. The `commit=False` option lets a caller batch the audit write into an existing transaction, so (for example) a governance case status change and its audit record commit atomically rather than risking one landing without the other.

**Events now audited that previously weren't:**
- `login` — successful sign-in, with method (login code vs password) in metadata
- `login_failed` — failed attempts, recorded at `medium` risk. A burst of these against one account is exactly what an admin should be able to find after the fact.
- `logout` — via a new `POST /auth/logout` endpoint
- `admin_action` — every governance case action, capturing previous → new status
- `risk_config_change` — every threshold/weight edit, capturing previous → new value

**`backend/app/routes/logs.py`** — added `event_type` and `date_from`/`date_to` filters.

## Two correctness details worth recording

**The `metadata` reserved-name trap**: SQLAlchemy reserves `metadata` on declarative model classes, so a column literally named `metadata` has to be mapped to a different Python attribute. I used `event_metadata = db.Column("metadata", ...)` — DB column is `metadata`, Python attribute isn't. I verified both this model and `SecurityEvent` (from Phase 1) handle it the same way.

**Legacy NULL rows**: every audit row written before this phase has `event_type = NULL`. Rather than backfilling, filtering for `event_type=ai_request` explicitly matches `event_type == "ai_request" OR event_type IS NULL`, so old chat rows don't silently vanish from a filtered view. This matches `to_dict()`'s default so the API and the filter agree.

## Verified for real

Ran executable tests on the dependency-free logic:
- `_parse` handles null, valid JSON, and legacy plain-string values without raising
- `_parse_obj` **always returns a dict**, never a list, even on malformed input (a subtle difference from `_parse` that matters — the metadata field is object-shaped, and a caller doing `metadata.get(...)` would break on a list)
- `event_type` NULL → `"ai_request"` defaulting matches the filter logic
- **Date-range boundary**: an event at 23:59 on the `date_to` day is correctly included, because the filter uses `< date_to + 1 day` rather than `<= date_to` (which would have silently dropped almost an entire day's events — the classic off-by-one in date filtering)

Also confirmed `infer_question_category()` returns `None` rather than raising when handed a non-question description, so the existing category filter won't break on the new non-chat rows.

## What I could NOT verify

The `ALTER TABLE` migration running against a real SQLite file with existing data, whether the new filters return correct results from a real query, and whether the `commit=False` batching actually commits atomically in practice. Same sandbox constraint throughout.

**Please verify:**
```bash
cd backend && python app.py   # confirm the 3 new columns get added without error
# log in (creates a `login` audit row), then as admin:
curl "http://localhost:5001/api/logs?event_type=login" -H "Authorization: Bearer <admin_token>"
curl "http://localhost:5001/api/logs?event_type=ai_request" -H "Authorization: Bearer <admin_token>"
# ^ confirm pre-existing chat rows still appear despite having event_type NULL
curl "http://localhost:5001/api/logs?date_from=2026-09-01&date_to=2026-09-17" -H "Authorization: Bearer <admin_token>"
# try a wrong login on purpose, confirm a login_failed row appears
python -m pytest -q
```

## Note on frontend

I added the backend filters but did **not** add matching UI controls to the Dashboard's audit tab this phase — that's UI work that belongs with Phase 27's admin dashboard polish, and I'd rather add the controls once against a verified-working API than build UI against filters neither of us has run yet.
