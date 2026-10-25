# SecureAI

SecureAI is currently a governance-first internal operations application built around a role-aware enterprise assistant. It combines governed AI chat, audit logging, question-bank operations, lightweight workforce task tracking, assignment escalations, face-based attendance capture, private messaging, and a few hackathon-style security demo surfaces.

The implemented product is broader than a chatbot, but it is not yet a production-grade security platform. The strongest current identity is: an explainable governance and accountability workspace for AI-assisted internal operations.

## Current Feature Areas

- Governed AI chat with role-based filtering and explainability metadata
- Admin audit dashboard with log filtering, exports, suspicious-user views, and dataset analytics
- Question-bank operations with search, import/export, history, favorites, feedback, and unanswered-query review queue
- Work assignment flow with KPI tracking, capacity risk scoring, board state, and manual escalations
- Face registration, face verification, and attendance mark/check history
- JWT-authenticated private messaging over REST + Socket.IO
- Admin user creation with generated employee login codes
- Demo-only security lab surfaces: ghost mode and attack simulation

## What This Repo Is Not

- Not a hardened production security product yet
- Not a full GRC platform
- Not a true RAG system
- Not a complete biometric authentication system
- Not a cleanly modular microservice architecture

## Stack

- Backend: Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Flask-SocketIO
- Frontend: React, Vite, Tailwind, Framer Motion
- Storage: SQLite plus JSON-backed data files
- Testing: Pytest backend tests and API contract tests
- CI: GitHub Actions backend tests + frontend build

## Running Locally

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker

```bash
docker compose up --build
```

Default URLs:

- Frontend: `http://127.0.0.1:3000`
- Backend: `http://127.0.0.1:5001`

## Seeded Users

- `admin` / `ADMINCODE1` or `admin123`
- `hr_jane` / `HRCODE0001` or `hr123`
- `intern_bob` / `INTCODE001` or `intern123`

## Documentation Index

- [Project Overview](/home/god/GitRepos/sentinelSystem/docs/PROJECT_OVERVIEW.md)
- [Architecture](/home/god/GitRepos/sentinelSystem/docs/ARCHITECTURE.md)
- [Feature Status](/home/god/GitRepos/sentinelSystem/docs/FEATURES_STATUS.md)
- [API Surface](/home/god/GitRepos/sentinelSystem/docs/API_SURFACE.md)
- [Security Posture](/home/god/GitRepos/sentinelSystem/docs/SECURITY_POSTURE.md)
- [Workflows](/home/god/GitRepos/sentinelSystem/docs/WORKFLOWS.md)
- [Roadmap Notes](/home/god/GitRepos/sentinelSystem/docs/ROADMAP_NOTES.md)

## Honest Current Status

- The governed chat, audit log, work-management, attendance, and admin dataset flows are implemented and wired end-to-end.
- The ghost mode and attack simulator are demo-oriented and disconnected from the main frontend API configuration.
- Some security claims from earlier project framing were stronger than the implementation.
- The codebase is workable for incremental product growth, but it still carries demo defaults, mixed persistence patterns, and ad hoc authorization logic.
# Confluence-
