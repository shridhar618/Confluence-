# Phase 9 — Rule-Based Risk Engine: Implementation Notes

## What was added

**`backend/app/services/governance.py`**: introduced `DEFAULT_RISK_CONFIG`, a plain dict holding every previously-hardcoded weight and threshold (`risk_threshold_low_max`, `risk_threshold_medium_max`, `cumulative_risk_case_threshold`, and the 5 Layer-2 category weights). `_compute_risk_score()` and `_classify_risk()` now accept an optional `config` parameter and fall back to `DEFAULT_RISK_CONFIG` when none is given. `apply_governance()` gained a matching `risk_config` parameter, merged over the defaults.

**`backend/app/services/risk_config_service.py`** (new): `load_risk_config()` — the Flask/DB-aware bridge that reads the real `RiskConfiguration` rows (seeded in Phase 1) and reshapes them into the plain dict `governance.py` expects. A disabled row falls back to the default rather than zeroing out that weight, so toggling "enabled" off is a safe no-op, not a silent misconfiguration.

**`backend/app/routes/risk_config.py`** (new): `GET /risk-config` and `PUT /risk-config/<key>`, both gated by `require_permission("manage_risk_configuration")` — the first real use of the `require_permission` decorator built (but unused) back in Phase 2.

**`chat.py` and `compliance.py`**: both now call `load_risk_config()` and pass the result into `apply_governance()`, so the live governed-chat path and the standalone compliance-check endpoint actually respect whatever an admin has configured, rather than always using the hardcoded defaults.

## Why the config lives outside governance.py, not inside it

Every phase so far, `governance.py`'s complete independence from Flask/SQLAlchemy has been the single biggest reason I could give you *real, executable proof* instead of just code review — Phases 5, 8, and this one all relied on running it directly, isolated from the rest of the app. Making it read from the database directly would have destroyed that property for a purely cosmetic convenience. Instead, the config is threaded through as a plain parameter (identical pattern to how `permissions` was added in Phase 8), and only `risk_config_service.py` — a separate, thin, Flask-aware file — touches the database. `governance.py` still runs standalone with zero setup, and still defaults to sensible values if nobody bothers to load real configuration.

## Verified for real — 6 executable tests

1–3. **Regression**: intern salary block, admin password block (both from Phase 8), and intern's general coding question — all still produce identical results when no config is passed (implicit default).
4. Passing `DEFAULT_RISK_CONFIG` **explicitly** produces byte-identical results to not passing it at all — confirms the merge logic (`{**DEFAULT_RISK_CONFIG, **(risk_config or {})}`) doesn't silently alter anything when there's nothing to override.
5. **Threshold reconfiguration actually works**: same query, same computed `risk_score` (0.332) under both configs — but tightening `risk_threshold_medium_max` from 0.70 down to 0.10 correctly reclassifies that same score from `medium` to `high`. This confirms score computation and threshold classification are cleanly separated, which matters for the explainability principle (the number itself doesn't move just because an admin tightened policy — only how it's read does).
6. **Weight reconfiguration actually works**: zeroing out `weight_cybersecurity_threat` measurably lowered the computed risk_score for a cybersecurity-flavored query (0.332 → 0.325), confirming the weight is genuinely used in the calculation, not just stored and ignored.

## What I could NOT verify

The Flask/DB side: whether `RiskConfiguration.query.filter_by(enabled=True).all()` actually returns the Phase 1-seeded rows from a real SQLite file, whether `PUT /risk-config/<key>` actually persists an admin's edit, and whether `require_permission`'s 403 response fires correctly for a non-admin role hitting these routes. Same constraint as every other phase — no network for `pip install` in this sandbox.

**Please verify:**
```bash
cd backend && python app.py
# as admin:
curl http://localhost:5001/api/risk-config -H "Authorization: Bearer <admin_token>"
# should list 8 rows seeded back in Phase 1

curl -X PUT http://localhost:5001/api/risk-config/risk_threshold_medium_max \
  -H "Authorization: Bearer <admin_token>" -H "Content-Type: application/json" \
  -d '{"value": 0.50}'

# as a non-admin (e.g. intern):
curl http://localhost:5001/api/risk-config -H "Authorization: Bearer <intern_token>"
# should get a 403 from require_permission, not a 500 or a silent empty list

# then confirm the chat/compliance-check endpoints actually pick up the new threshold
python -m pytest -q
```
