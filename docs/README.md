# SecureAI Documentation

SecureAI is an internal AI governance and workforce-operations application. The current system combines governed AI chat, audit logging, assignments, KPI tracking, deterministic capacity-risk scoring, attendance signals, and work escalations.

The core idea is an **AI-powered operational intelligence system**: AI responses are governed and audited, while operational work data is turned into visible KPI and risk signals for managers. The escalation flow is mostly deterministic today. The frontend includes an AI escalation assistant UI, but the backend endpoint it calls is not implemented in the current `work_management` route.

## Key Features

- **Assignments**: admin and HR users create work assignments for active users.
- **Progress tracking**: assignees submit completed units and notes.
- **KPI calculation**: expected units, completed units, completion ratio, and weighted score are computed from progress updates.
- **Capacity risk**: due dates, completion ratio, attendance recency, and concurrent incomplete assignments produce low/medium/high risk signals.
- **Escalations**: admin and HR users can create, list, and resolve assignment escalations.
- **Governed AI chat**: chat requests use the configured AI provider or a local question-bank fallback, then pass through role-aware governance filtering.
- **AI escalation assistant UI**: the React page can collect manager context and is wired to call `POST /api/work/escalations/suggest`; that backend route is not present in the current Flask implementation.

## Architecture Snapshot

```text
React UI
  |
  | /api/*
  v
Flask routes
  |
  +-- auth/admin/users
  +-- chat -> ai_service -> governance -> audit log
  +-- work_management -> assignments/KPI/risk/escalations
  |
  v
SQLAlchemy models + SQLite
  |
  +-- users, audit logs, assignments, progress, escalations, attendance
  +-- JSON question-bank files for local AI fallback and review queues
```

## Work Operations Flow

```text
Assignment -> Progress Update -> KPI Calculation -> Capacity Risk -> Escalation -> Resolution
```

## AI Flow

```text
User message -> /api/chat -> AI provider or local question-bank fallback
             -> governance filter -> audit log -> frontend response
```

The implemented AI layer is used by the governed chat system. It is not currently connected to the work-escalation backend.
