# Architecture

## Backend

The backend is a Flask application using:

- Flask app factory in `backend/app/__init__.py`
- SQLAlchemy for persistence
- Flask-JWT-Extended for bearer-token auth
- Flask-SocketIO for realtime chat and Ghost Mode events
- SQLite by default through `DATABASE_URL` fallback

Blueprints are mounted under `/api`:

- `/api/auth/*` from `backend/app/routes/auth.py`
- `/api/admin/*` from `backend/app/routes/admin.py`
- `/api/chat*` from `backend/app/routes/chat.py`
- `/api/work/*` from `backend/app/routes/work_management.py`
- plus logs, users, messages, attendance, roles, ghost, and attack simulator routes

Startup uses `db.create_all()` plus small schema patch helpers such as `_ensure_work_escalation_columns()` and `_ensure_user_schema()`. There is no migration framework in the current implementation.

## Work Management Backend

`backend/app/routes/work_management.py` contains the assignment, board, KPI, capacity-risk, and escalation logic.

Implemented work APIs include:

- create/list assignments
- submit assignee progress
- update board status
- get manager board
- create/list/resolve escalations
- get KPI and capacity risk for an assignment

Capacity risk is deterministic, not AI-generated. It uses:

- assignment due date
- assignment completion ratio
- whether the assignment is incomplete
- recent attendance signal in the last three days
- count of active incomplete assignments for the assignee

## Frontend

The frontend is a React/Vite single-page app using React Router and Axios. `frontend/src/utils/api.js` sets the API base URL to `/api` and attaches the JWT from `localStorage`.

Relevant pages:

- `WorkAssignmentsPage.jsx`: admin/HR assignment creation and KPI/risk list view
- `MyWorkPage.jsx`: assignee progress submission
- `WorkBoardPage.jsx`: admin/HR board view with drag-and-drop status updates and manual escalation for high-risk cards
- `WorkEscalationsPage.jsx`: escalation list, resolution action, and AI escalation assistant form
- `ChatPage.jsx`: governed AI chat UI
- `QuestionBankPage.jsx`: admin question-bank management
- `DashboardPage.jsx`: audit and governance dashboard

Route guards allow only `admin` and `hr` users to access manager work pages. Admin-only pages include user access, dashboard, question bank, Ghost Mode, and attack simulator.

## AI Layer

`backend/app/services/ai_service.py` provides an adapter-like dispatch function:

```text
get_ai_response(messages)
  |
  +-- AI_PROVIDER=openai -> OpenAI chat completion
  +-- AI_PROVIDER=gemini -> Google Gemini
  +-- other provider -> mock/local fallback
```

The default provider is `gemini`. Gemini uses `gemini-1.5-flash` through `google.generativeai`. OpenAI uses `gpt-3.5-turbo`. If the configured key is missing, placeholder-like, or the provider call fails, the service returns local mock/fallback text instead of raising the provider error to the caller.

The local fallback searches the question bank before returning a generic demo-mode response. The same service also supports question-bank CRUD helpers, import/export, TF-IDF search, unanswered-question capture, and analytics helpers.

There is no Ollama/Gemma adapter in the current codebase.

## Data Flow

Implemented governed chat flow:

```text
User -> React ChatPage -> POST /api/chat
     -> ai_service provider/fallback
     -> governance filter
     -> AuditLog row
     -> normalized response fields
     -> UI renders answer, risk, rules, suggestions
```

Implemented work flow:

```text
Manager -> React work page -> /api/work/*
        -> WorkAssignment / WorkProgressUpdate / WorkEscalation models
        -> KPI and capacity_risk computed in route helper functions
        -> serialized assignment or escalation payload
        -> UI renders status, risk, KPI, and escalation state
```

Planned-by-UI but not implemented backend flow:

```text
Manager -> WorkEscalationsPage -> POST /api/work/escalations/suggest
        -> no matching Flask route in current backend
```
