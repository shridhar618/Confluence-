# Phase 0 — Codebase Audit

Audit date: 2026-09-08
Scope: full inspection of the uploaded `sentinelSystem` repository (backend, frontend, docs, scripts, CI). No code was modified during this audit. This document is additive — it does not replace the existing `docs/architecture.md`, `docs/FEATURES_STATUS.md`, `docs/SECURITY_POSTURE.md`, etc., which were already accurate and are cited below.

---

## 1. Existing Architecture Summary

**Backend**: Flask app factory (`backend/app/__init__.py`) with 13 blueprints mounted under `/api`. SQLAlchemy + SQLite (`secureai.db`), no migration framework — schema drift is patched at startup via `_ensure_*_columns()` helper functions. Flask-JWT-Extended issues **non-expiring** tokens. Flask-SocketIO (eventlet/threading) powers Ghost Mode and private messaging real-time events.

**Frontend**: React 18 + Vite + Tailwind + Framer Motion SPA, React Router for navigation, Axios wrapper (`utils/api.js`) attaching JWT from `localStorage`. Route guards (`ProtectedRoute`) support `adminOnly` / `managerOnly` gates, checked client-side against `user.role`.

**AI layer**: `ai_service.py` is a provider dispatcher (`AI_PROVIDER` env var) supporting `gemini` (default, `gemini-1.5-flash`), `openai` (`gpt-3.5-turbo`), and **`ollama`** (a genuine local adapter already wired to `gemma3:4b` via Ollama's `/api/generate` — this is more current than what `docs/ai-system.md` states, which predates this addition and says "no Ollama/Gemma adapter exists"). All providers fall back to a **TF-IDF question-bank matcher** (scikit-learn, JSON-file-backed) when no key is configured or a call fails.

**Governance engine**: `services/governance.py` — a genuinely well-built, rule-based, explainable pipeline: Layer 1 (regex-based intern blocklist + HR PII masking), Layer 2 (keyword-group semantic risk scan), Layer 3 (weighted risk scoring → low/medium/high), Layer 4 (human-readable explanations). This is real, working code, not a stub.

**Data flow (chat)**: `ChatPage → POST /api/chat → ai_service (LLM or fallback) → apply_governance() → AuditLog row (+ suspicious-query counter) → high/medium-risk events pushed into Ghost Mode via Socket.IO → JSON response with response/status/risk_level/reason/triggered_rules to UI.`

**Data flow (work management)**: `WorkAssignment → WorkProgressUpdate → deterministic KPI (completion ratio, weighted score) → deterministic capacity-risk scoring (due date, completion %, attendance signal, active-assignment load) → WorkEscalation (manual create/list/resolve).` This is a second, independent risk engine (capacity risk) distinct from the AI-governance risk engine — worth being explicit about in the capstone write-up so the two aren't conflated.

---

## 2. Existing Modules (verified against code, not just docs)

| Module | Status | Evidence |
|---|---|---|
| Governed AI chat + audit log | **Working** | `routes/chat.py`, `services/governance.py`, `models/audit_log.py` |
| RBAC (partial) | **Working but shallow** | `Role` table seeded with 24 roles (`services/roles.py`), but `governance.py` and most route guards only branch on `"admin"`, `"hr"`, `"intern"` — the other 21 roles exist in the DB but carry no distinct permission behavior yet |
| Question-bank ops (CRUD, import/export, TF-IDF search, feedback, unanswered queue) | **Working** | `ai_service.py`, JSON files under `backend/app/data/` |
| Admin audit dashboard | **Working** | `routes/logs.py` (not yet read line-by-line, but referenced consistently across chat.py/docs) |
| Work assignments, KPI, capacity risk, board, escalations | **Working** | `routes/work_management.py` (946 lines), `models/work_assignment.py`, `models/work_escalation.py` |
| Attendance (face reg/verify/mark/history) | **Working, but not real face recognition** | see §4 below |
| Private messaging (REST + Socket.IO) | **Working** | `models/message.py`, `routes/messages.py`, `routes/socket_events.py` |
| Admin user creation w/ generated login codes | **Working** | `routes/admin.py` |
| Ghost Mode | **Working demo, unauthenticated** | `app/ghost_routes.py` (391 lines) — no `@jwt_required()` on its routes; frontend hardcodes `http://localhost:5000` while the backend runs on `5001`, so it's disconnected from the deployed frontend today |
| Attack Simulation | **Working demo, unauthenticated, purely canned** | `attack_routes.py` — static list of 6 scenarios, `random.randint(70,99)` risk scores, no real exploit logic anywhere. This is safe and appropriately scoped as a demo, matching the capstone's Phase 20 safety boundary |
| Public registration | **Dead UI** | Backend returns 403 always; `RegisterPage.jsx` exists but `App.jsx` redirects `/register → /login` |
| `TrapAlert.jsx` | **Dead file** | Empty component |

---

## 3. Database Models (confirmed by reading each model file)

`User, Role, FaceProfile, AuditLog, Message, AttendanceRecord, WorkAssignment (hierarchical, supports parent/child sub-tasks), WorkProgressUpdate, WorkEscalation, Project, ProjectMember, FavoriteQuestion, QuestionFeedback`

Notable design details:
- `WorkAssignment` already supports **parent/child hierarchies** (subtasks) with recursive KPI roll-up — more sophisticated than the capstone spec's flat Kanban model. Worth keeping, not simplifying.
- `AuditLog` already has `risk_level`, `reason`, `triggered_rules` (JSON), `validator_notes` (JSON), `is_high_risk` — i.e., the explainability fields the capstone spec asks for in Phase 12 already exist.
- No `Permission`, `RolePermission`, `PolicyDocument`, `PolicyChunk`, `RiskEvent`, `GovernanceCase`, `AdminAction`, `Notification`, `KPI` (as a persisted table — KPI is computed on the fly), or `SecurityEvent` models exist yet. These are the real gap against the capstone's Phase 1 schema.

## 4. Existing APIs (verified, not just from `docs/api.md`)

Confirmed via code: `/api/auth/{login,register,me,face-verify}`, `/api/admin/{create-user,check-user-code}`, `/api/chat*` (12 routes: chat, clear, questions CRUD/search/import/export/history/review-queue, favorites, feedback, export), `/api/work/*` (assignments, progress, status, kpi, board, escalations — `POST /api/work/escalations/suggest` is **frontend-wired but has no backend route**, confirmed absent from `work_management.py`'s registered routes), `/api/attack-simulate|stop|reset` (unauthenticated), ghost routes (unauthenticated).

## 5. Existing Frontend Pages

`LoginPage, RegisterPage (dead), WelcomePage, ChatPage, PrivateChatPage, DashboardPage, QuestionBankPage, FaceAttendancePage, FaceUnlockPage, GhostModePage, AttackSimPage, WorkAssignmentsPage, WorkAssignmentsWorkspacePage, MyWorkPage, WorkBoardPage, WorkEscalationsPage, AdminCreateUserPage.` Routing/guards live in `App.jsx`, confirmed to match the docs' claims.

## 6. Existing AI/RAG Components

- **No LangChain, no Qdrant, no sentence-transformers, no vector search anywhere in the codebase** (`grep` confirmed). This is the single largest gap against the capstone spec, and it's a from-scratch build, not a refactor.
- The closest existing analog is the TF-IDF question-bank matcher (`_get_question_bank_index()` in `ai_service.py`) — a real, working retrieval mechanism, but it retrieves canned Q&A answers, not policy-document chunks with metadata/citations. It's a useful pattern to reuse structurally (caching, role filtering) but not a policy RAG system.
- A genuine local-LLM adapter to `gemma3:4b` via Ollama already exists (`ollama_service.py`) and is already wired into `ai_service.py`'s dispatch — this significantly de-risks Phase 6/33 ("Gemma-4B", "LLM Setup") since the transport layer is already built and tested (see `tests/test_ollama_service.py`). We'd extend this, not replace it, to feed it retrieved policy chunks instead of a raw chat prompt.

## 7. Existing Security Components

- JWT auth (no expiry — flagged as a risk in `docs/SECURITY_POSTURE.md` and confirmed in `app/__init__.py`: `JWT_ACCESS_TOKEN_EXPIRES = False`)
- `werkzeug.security` password hashing — real, not placeholder
- CORS: wildcard `origins: "*"` on `/api/*` — confirmed in `app/__init__.py`
- Default `SECRET_KEY`/`JWT_SECRET_KEY` fallbacks (`"dev-secret-key"` / `"dev-jwt-secret"`) — real risk if ever deployed with defaults
- Face "recognition" (see below) is demo-grade, not biometric-grade
- Ghost Mode / Attack Simulation routes are intentionally unauthenticated demo surfaces — acceptable for a labeled "security lab," but should be gated behind admin auth for the capstone to look production-conscious, and clearly labeled as simulation (this matches capstone Phase 19's safety boundary already)

**Face recognition — important correction to make explicit for the capstone report**: `face_attendance.py` does **not** use OpenCV or any pretrained face-recognition model. It resizes images to 64×64 grayscale, flattens/normalizes pixels, and projects them through a `sklearn.random_projection.GaussianRandomProjection` (a random linear projection, fit once on the first sample seen) before cosine-similarity matching. This is a lightweight placeholder, not real face recognition — it will falsely distinguish based on lighting/framing as much as identity. The capstone brief explicitly asks for "OpenCV + a pre-trained face recognition approach," so this is a genuine gap requiring real work (e.g., OpenCV Haar/DNN face detector + a pretrained embedding model such as `face_recognition`/dlib or a small ONNX/FaceNet embedding), not just a docs correction.

---

## 8. Missing Components (against the 34-phase capstone spec)

1. **Real RAG pipeline** (LangChain, sentence-transformer embeddings, Qdrant, chunking/ingestion script, source metadata) — does not exist at all.
2. **Policy corpus** (NIST AI RMF, OWASP GenAI Top 10, DPDP Act 2023, org policies as ingestible documents) — does not exist.
3. **Permission / RolePermission tables** — Role exists but permissions are hardcoded in Python conditionals, not data-driven.
4. **RiskConfiguration** (admin-configurable thresholds/weights) — governance.py's thresholds (`RISK_LOW_MAX = 0.30`, etc.) are hardcoded constants, not admin-editable.
5. **Cumulative/escalating risk → GovernanceCase → AdminAction** workflow — `is_suspicious`/`sensitive_query_count` exist on `User`, but there's no `GovernanceCase` object, no case detail page, no admin actions (warn/restrict/restore/escalate) tied to AI governance (there IS an escalation system, but it's for **work/KPI risk**, not **AI governance risk** — these are currently two separate concerns that the capstone spec wants unified under one governance case model).
6. **Real face recognition** (see §7).
7. **RAG safety, evaluation, and risk-engine evaluation harnesses** (Phases 22, 25, 26) — none exist; would be new.
8. **Admin-configurable policy management UI** (Phase 14) — question-bank admin UI exists but is a distinct concept from policy-document management.
9. **JWT expiry, centralized authz layer, Ghost/Attack auth gating** — flagged already in `docs/SECURITY_POSTURE.md`, still unaddressed in code.
10. **`POST /api/work/escalations/suggest`** — frontend calls it, backend doesn't implement it (small, contained fix).

## 9. Potential Conflicts / Decisions Needed Before Building

- **Two risk engines already exist** (AI-governance risk in `governance.py` vs. work capacity-risk in `work_management.py`). The capstone spec's Phase 9 risk engine should probably be a third, more general-purpose configurable engine that the AI-governance path migrates onto — but capacity-risk for work items is a legitimately different signal and shouldn't be forced into the same model. Recommend keeping them conceptually separate but both feeding the same `AuditLog`/case-management surface for a coherent admin experience.
- **Escalation model naming collision**: `WorkEscalation` already exists for work/KPI risk. The capstone's `GovernanceCase` is a different, new concept for AI-governance risk. Naming will need to stay clearly distinct in the admin UI so demo judges don't conflate "an employee is behind on tasks" with "an employee tried to access restricted data."
- **Role catalog vs. role enforcement gap**: 24 roles are seeded but only 3 are functionally distinct. Before building Permission/RolePermission tables, decide how many of the 24 roles the demo actually needs distinct behavior for (the capstone brief's example set — Guest/Intern/Software Engineer/HR/Manager/Supervisor/Admin — is a reasonable subset to actually wire up, rather than trying to give all 24 real permissions).
- **Ollama dependency**: using `gemma3:4b` via Ollama requires Ollama running locally with the model pulled — this needs to be documented as a setup prerequisite, and a mock/fallback path (which already exists) kept intact for grading environments without Ollama installed.
- **No network access in my current sandbox**: I was able to fully read and statically inspect the code, but I could not `pip install` or run `pytest`/the dev servers here (this container has no outbound network). I'd recommend either running the test suite yourself and sharing output, or continuing this build inside an environment with network access (e.g., Claude Code on your machine) so each phase can be genuinely executed and verified per your non-negotiable phase-by-phase requirement, not just statically reviewed.

## 10. Files That Should NOT Be Unnecessarily Modified

- `services/governance.py` — working, well-structured, explainable; extend (e.g., wire in policy-evidence sources) rather than rewrite.
- `services/ollama_service.py` — working local-LLM transport; reuse for RAG-grounded generation.
- `models/work_assignment.py`, `work_management.py` — working hierarchical task/KPI/capacity-risk system; keep as the Workforce module's backbone.
- `models/audit_log.py` — schema already has the explainability fields the capstone wants; extend, don't replace.
- Existing `docs/*.md` — genuinely useful and honest; this audit supplements them, doesn't supersede them.
- `attack_routes.py` / `ghost_routes.py` demo content — fine to keep as-is content-wise; only auth-gating needs to change.

---

## Recommended Implementation Order

1. **Phase 1 (schema)**: add `Permission`, `RolePermission`, `PolicyDocument`, `PolicyChunk`, `RiskEvent`, `GovernanceCase`, `AdminAction`, `RiskConfiguration`, `SecurityEvent` — additive migrations alongside existing tables, no destructive changes.
2. **Phase 2 (RBAC)**: pick the 7-role subset from the capstone brief, wire real permission checks via the new tables, keep existing 3-role governance logic working underneath during transition.
3**.** **Phase 6/7 (RAG + policy corpus)**: build ingestion script, Qdrant + sentence-transformers, feed Ollama/Gemma with retrieved chunks instead of raw prompts — biggest new-build item.
4. **Phase 9/10 (configurable risk engine + cumulative escalation)**: generalize `governance.py`'s scoring into an admin-configurable engine; add `GovernanceCase` creation on threshold breach.
5. **Phase 11–13 (case management, audit, alerts)**: build on top of existing `AuditLog` + Socket.IO infrastructure (already proven to work via Ghost Mode's real-time push).
6. **Phase 15 (real face recognition)**: swap `GaussianRandomProjection` placeholder for OpenCV + a pretrained embedding model.
7. Everything else (Phases 3–5, 16–21, 23–34): mostly UI polish, hardening, and documentation on top of what already exists and works.

---

I have not modified any application code. Awaiting your go-ahead before starting Phase 1.
