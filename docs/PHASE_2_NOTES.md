# Phase 2 — Authentication + RBAC: Implementation Notes

## What was added

New file:
- `backend/app/utils/authz.py` — central authorization module:
  - `get_current_user()` — single source of truth for "who is making this request", replacing three separate, identical `_get_user()`/`_require_admin()`-style implementations
  - `require_role(*roles)` — reusable decorator, generalized version of the old per-file admin-only check
  - `require_permission(permission_name)` — **new capability**: reusable decorator that checks the Phase 1 `Permission`/`RolePermission` model instead of a hardcoded role string
  - `require_admin` — convenience alias (`require_role("admin")`) for future routes

Modified files:
- `backend/app/routes/admin.py`, `logs.py`, `chat.py` — the three separate, byte-for-byte-identical `_require_admin()` implementations now delegate to `get_current_user()` from the new shared module. **Behavior is unchanged** — same role check, same 403 response shape. This is pure deduplication.
- `backend/app/routes/chat.py` — the `POST /chat` endpoint now enforces the `use_ai_assistant` permission server-side before processing any message. A denied attempt is written to `AuditLog` (`status="blocked"`, `triggered_rules=["permission_denied:use_ai_assistant"]`) so it shows up in the existing audit trail like any other governance decision.
- `backend/app/routes/auth.py` — `/auth/login` and `/auth/me` now both return a `permissions` array alongside `user`, computed from the requester's effective role.
- `frontend/src/context/AuthContext.jsx` — captures `permissions` from login/`/me`, exposes a `hasPermission(name)` helper.
- `frontend/src/components/Layout.jsx` — the "AI Chatbot" sidebar item is now hidden if `hasPermission('use_ai_assistant')` is false.
- `backend/app/services/roles.py` / `frontend/src/utils/roles.js` — already had Guest/Software Engineer/Supervisor added in Phase 1; this phase is what actually makes those roles' restrictions real.

## Key decisions and rationale

### 1. Deduplicated the *existing* admin checks; did not rewrite every route to the new decorator style

`admin.py`, `logs.py`, and `chat.py` each had their own copy of the same 2-line "is this user an admin" check. I collapsed those into one function so there's a single place to fix if this logic ever needs to change, **without** converting every route in every blueprint (`work_management.py`, `attendance.py`, `projects.py`, `users.py`, `ghost_routes.py`, `ai_tasks.py`, `messages.py`) to the decorator pattern in this same pass. Those files still use their own local admin/role checks, which continue to work exactly as before — untouched. Rewriting ~1,800 lines of route logic across 7 more files in one shot, with no way to execute the test suite myself in this sandbox, would violate the "don't replace working functionality unnecessarily" instruction far more than leaving them alone for a future, reviewable pass does.

### 2. The one real new enforcement point is the chat endpoint's `use_ai_assistant` check

This is the actual Phase 2 deliverable that matters for the capstone's thesis: **permissions, not just role-name string comparisons, now gate the AI assistant**, and it's enforced server-side (a Guest account cannot get a chat response back no matter what the frontend does). I picked this single endpoint deliberately rather than instrumenting every route, because it's the one place in the entire app where an unauthorized-access demo scenario (Phase 29's "Demo 2") actually lives — gating it is a real behavior change worth testing carefully, versus adding the same permission check to a dozen work-management routes that aren't part of the AI-governance story.

### 3. Frontend gating fails open, not closed

`hasPermission()` returns `true` when permissions haven't loaded yet (e.g., immediately after login, before `/auth/me` resolves) rather than hiding navigation and then having it "pop in." This is a UX choice, not a security one — the backend's `use_ai_assistant` check on `/chat` is what actually blocks unauthorized use; the sidebar link disappearing is just about not showing a broken/403 page to legitimate users after a click.

### 4. No seeded demo account changes behavior

Admin, HR, and Intern (the three demo accounts referenced throughout the existing docs and the capstone's worked examples) all have `use_ai_assistant` in their permission set from Phase 1, so this phase introduces **zero visible change** for the existing demo flow. The only account type that newly loses chat access is a role without `use_ai_assistant` — currently just `Guest`, which didn't exist as a functioning demo account before Phase 1 added it.

## What I could NOT verify in this environment

Same constraint as Phase 1 — no network access, so no `pip install`, no running the Flask dev server, no `pytest`. I did:

- Syntax-check every modified/new file with `python -m py_compile`
- Manually trace every call site that previously called the old `_require_admin()`/`_get_user()` in the three modified route files, confirming the call signatures (`-> User | None`) are unchanged
- Confirm no other module imports those private helper functions directly (only the blueprint objects are imported elsewhere, via `app/__init__.py`)
- Catch and fix one real mistake during editing: a leftover duplicate `return` line in `logs.py` from a str_replace — caught by re-viewing the file immediately after the edit, before moving on

**Please run and share the results of:**

```bash
cd backend
python app.py
# Should start without ImportError/AttributeError from app/utils/authz.py

python -m pytest -q
# Confirms admin.py/logs.py/chat.py refactor didn't break existing admin-only route tests

# Manual check: log in as the seeded intern/hr/admin accounts and confirm
# /chat still works exactly as before (this is the highest-risk change)
```

```bash
cd frontend
npm run build
# Confirms no JSX/import errors in AuthContext.jsx or Layout.jsx
```

If anything in `python app.py`, pytest, or `npm run build` fails, please paste the output — I'll fix it before moving to Phase 3 (the application shell / sidebar polish).
