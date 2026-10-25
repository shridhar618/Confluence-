# Phase 3 — Professional Application Shell: Implementation Notes

## What was added

**New backend blueprint**: `app/routes/notifications.py` — `GET /notifications`, `GET /notifications/unread-count`, `POST /notifications/<id>/read`, `POST /notifications/read-all`, all scoped to the requesting user. Registered in `app/__init__.py`. Uses the `Notification` model already created in Phase 1 — no schema change needed.

**New frontend component**: `frontend/src/components/TopBar.jsx` — page title/description (derived from route), a client-side quick-search over the app's own module list, a real notification bell (polls `/notifications/unread-count` every 30s, opens a dropdown backed by `GET /notifications`), and a profile menu (avatar, role badge, sign out).

**Rewritten**: `frontend/src/components/Layout.jsx` — sidebar now renders grouped sections (AI Governance / Workforce / Communication / Security / Admin) with section headers, matching the platform's intended structure, instead of one flat list. Added a mobile hamburger + slide-in overlay sidebar for narrow viewports (previously the sidebar was always visible at a fixed width with no mobile handling at all). `TopBar` is now mounted above the page content.

## Key decisions and rationale

### 1. Sections are omitted, not shown empty

A section header only renders if the current user has at least one visible item in it. A Guest or Intern account (no manager/admin items) sees only the sections that actually apply to them, rather than five headers where three say nothing underneath — this also directly serves the "Intern should NOT see administrative governance controls" requirement, extended to the new section-header level, not just individual links.

### 2. Notifications are real, not mocked

The bell polls a genuine, newly-added backend endpoint against the real `Notification` table from Phase 1. Right now it will show an empty state for every account, because nothing in the codebase creates a `Notification` row yet — that wiring (governance case opened → notify admin, high-risk event → notify admin) is Phase 13's job. I did not fabricate sample notifications to make the UI look populated; the brief is explicit about "polished empty states" and "no fake statistics," and an honestly-empty alert center is more defensible in a capstone demo than a bell that always shows the same three canned alerts.

### 3. Search is real but intentionally scoped

The search box filters the app's own known module list client-side (by label and a few keywords per entry) and navigates on click. It does not search audit logs, messages, or task content — building a real cross-entity search backend wasn't in scope for "professional application shell," and a fake global search box that quietly only searches navigation labels while implying it searches everything would be misleading. If you'd like real content search (e.g., searching your own chat history or work items) that's a reasonable Phase 27/28 addition once those pages have more content to search.

### 4. Existing page-level access control is untouched

Nothing about which roles can reach `/dashboard`, `/ghost-mode`, `/user-access`, etc. changed — those routes still gate via `ProtectedRoute`'s existing `adminOnly`/`managerOnly` props in `App.jsx`, unmodified. This phase only changed how the sidebar organizes and labels links to already-existing, already-gated pages; it does not grant or remove access to anything.

## What I could verify vs. still can't

**Verified for real this time, not just read-through**: I found that Node.js and a bundled `esbuild` (via the globally installed `tsx` package) are available in this sandbox, so I ran actual syntax/JSX parsing (`esbuild.transformSync`) against every new and modified frontend file (`TopBar.jsx`, `Layout.jsx`, `AuthContext.jsx`, `roles.js`) — all four parse cleanly. I also grepped every relative import path used in the new files against the real filesystem and confirmed every named import (`useAuth`, `getRoleMeta`, `getRolePillClass`, `isManagerRole`) is an export that actually exists in the target file. This is stronger evidence than the "compiles with py_compile" check from Phases 1–2, though it's still not a full Vite build (no `node_modules` installed, so JSX-to-bundle resolution against `react-router-dom`, `framer-motion`, `lucide-react`, and `axios` is unverified) and definitely not a rendered-in-a-browser check.

Backend: same constraint as before — `notifications.py` is syntax-checked but not run against a real Flask app + SQLite DB.

**Please run:**

```bash
cd backend && python app.py                 # notifications blueprint registers OK?
cd frontend && npm install && npm run build # full JSX/bundle validation
npm run dev                                  # visually confirm: grouped sidebar, mobile hamburger below ~1024px width, notification bell (should show empty state), search box, profile dropdown
```

Also worth a quick manual click-through as intern/hr/admin to confirm each still sees the right sections.
