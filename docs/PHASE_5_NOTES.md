# Phase 5 — AI Governance Chatbot: Implementation Notes

## Starting point

Like the dashboard, `ChatPage.jsx` and the `/chat` endpoint were already substantially built: 4-layer governance display, risk score bar, triggered rules, Layer-2 validator notes, HIGH RISK badges, a question bank sidebar with favorites/feedback/admin quick-add, and CSV export. What was missing against the capstone's exact Phase 5 worked example were two of its six named response components: **Recommended action** and **Policy source**.

## What was added

**`backend/app/services/governance.py`**:
- `FilterResult` gained two new fields: `recommended_action` (str) and `policy_evidence` (list of citations)
- `_recommended_action_for(status)` — deterministic, based on the existing status value (blocked/filtered/allowed)
- `_policy_evidence_for(...)` plus three lookup tables (`_INTERN_RULE_POLICY_MAP`, `_LAYER2_CATEGORY_POLICY_MAP`, `_HR_MASK_POLICY_MAP`) mapping every rule label this engine can already trigger to the specific organization policy clause (from the 4 documents drafted earlier) that actually governs it

**`backend/app/models/audit_log.py`**: two new nullable columns, `recommended_action` and `policy_evidence` (JSON-encoded list), plus a new `_ensure_audit_log_columns()` migration helper in `app/__init__.py` following the exact pattern already used for `users`/`work_assignments`/`work_escalations` schema evolution.

**`backend/app/routes/chat.py`**: persists and returns both new fields.

**`frontend/src/pages/ChatPage.jsx`**: `GovernancePanel` now shows a "Recommended action" block and a "Policy evidence" list (with a book icon per citation) alongside the existing risk score bar, reason, triggered rules, and validator notes.

## The important distinction: this is NOT the RAG pipeline

`_policy_evidence_for()` is a **static, hand-authored lookup table** from rule label → policy clause, not a similarity search over embeddings. I was explicit about this in the code comments because it matters for how this capstone should be described academically: Phase 6 will build genuine retrieval (embeddings + Qdrant + similarity search) across the *full* 10-document corpus, including the NIST/OWASP/DPDP externals this table doesn't touch at all. This table only covers the 4 organization documents, and only because I personally authored both the rule engine's labels and the policy documents' clause numbers in this conversation, so I could verify each citation is genuinely accurate rather than plausible-sounding. **Phase 6 should replace this table, not run alongside it** — once real RAG retrieval exists, having two different, potentially-disagreeing sources of "policy evidence" for the same decision would be confusing and worth explicitly resolving in Phase 6's implementation notes.

## A real executable test caught a real gap

Because `governance.py` has zero Flask/DB dependencies, I could actually run it (isolated from the `app` package, same technique as Phase 2's permission tests) against the capstone brief's exact worked examples:

- **Salary request (Scenario 3 / Phase 5 example)**: confirmed `status="blocked"`, `risk_level="high"`, and `policy_evidence=["Role & Access Control Policy §3.2", "Data Privacy & Classification Policy §2.4"]` — this **exactly matches** the brief's own worked example, which specifically calls for citing "Role & Access Control Policy" and "Data Privacy & Classification Policy" together.
- **General coding question (Scenario 1)**: confirmed `status="allowed"`, `risk_level="low"` — matches.
- **"Can I upload our internal project document to ChatGPT?" (Scenario 2)**: the brief expects `WARNING`/`MEDIUM`. The actual engine currently returns `allowed`/`low` — **none of the existing keyword rules match this phrasing** (the `internal only` regex requires that exact two-word phrase; nothing in the existing rule set catches "share with an external AI tool"). This is a **pre-existing gap I found, not something I introduced**, and I did not fix it here — expanding the rule set's keyword coverage is Phase 8/9's job (the Compliance Check Engine and the generalized configurable risk engine), and patching one keyword now would be a narrow, untested change to a file I can't run the full test suite against. Flagging it now so it doesn't get lost.

## What I could and couldn't verify

**Verified for real**: the entire `governance.py` logic change, via actual execution against three scenarios including the brief's own worked example — this is the strongest verification of any phase so far, because this file has no Flask/SQLAlchemy dependency and could be run directly. Also syntax-checked `chat.py`, `audit_log.py`, `app/__init__.py`, and `ChatPage.jsx`.

**Not verified**: that `_ensure_audit_log_columns()` actually runs a working `ALTER TABLE` against a real SQLite file with existing data (same constraint as every prior phase's schema change), and that the new UI panel renders correctly in a browser.

**Please verify:**
```bash
cd backend && python app.py
# then log in as intern_bob and ask: "What is the salary of all data engineers?"
# confirm the response includes a "Recommended action" and "Policy evidence" section
# listing Role & Access Control Policy + Data Privacy & Classification Policy
```

Also worth deciding: do you want me to extend the Layer-2 keyword rules now to catch the "share internal data with an external AI tool" scenario (a small, contained addition to `LAYER2_RULE_GROUPS`), or leave it for Phase 8/9 when the compliance engine gets a broader pass?
