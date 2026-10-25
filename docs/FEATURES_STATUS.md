# Features Status

This file is intentionally blunt.

## Implemented

### Governed Chat

- JWT-protected chat endpoint
- role-aware response handling for `admin`, `hr`, `intern`
- risk score, risk level, reason, triggered rules, validator notes
- audit log creation per chat interaction
- suspicious-query counting on users
- chat export

### Question-Bank Operations

- question listing and search
- favorites
- helpful/unhelpful feedback
- create, edit, delete
- JSON/PDF import
- JSON/CSV export
- history tracking
- unanswered-query queue and resolution state

### Admin Audit And Analytics

- log listing with filters
- stats aggregation
- suspicious-user view
- recent high-risk events
- CSV export

### Work Management

- create assignment
- list assignments
- assignee progress submission
- KPI calculation
- board view
- manual status updates
- capacity-risk calculation
- escalation create/list/resolve

### Attendance

- face registration
- face verification
- attendance mark
- personal attendance history
- team attendance history for admin/HR

### Messaging

- user list
- conversation history
- realtime private messages
- typing indicators
- unread count endpoint

### Admin User Access

- admin creates users
- generated employee login code
- admin code verification endpoint

## Partially Implemented

### AI Layer

- implemented: provider dispatch and local question-bank fallback
- partial: this is not a full enterprise knowledge system
- partial: fallback behavior is mostly question-bank matching plus a generic mock reply

### Suspicious User Monitoring

- implemented: query sensitivity counting and dashboard visibility
- partial: no case management, no response workflow, no escalation ownership, no approvals

### Face Unlock

- implemented: frontend face unlock page and backend face verify endpoint
- partial: not enforced server-side after login

### Role System

- implemented: `Role` table and seeded role catalog
- partial: most business logic still only recognizes `admin`, `hr`, and `intern`

### Escalation Workflow

- implemented: open/resolved lifecycle
- partial: no priority, SLA, root-cause capture, owner, or evidence bundle

## Dead / Disconnected / Misleading

### Public Registration

- [`backend/app/routes/auth.py`](/home/god/GitRepos/sentinelSystem/backend/app/routes/auth.py) hard-disables public registration
- [`frontend/src/pages/RegisterPage.jsx`](/home/god/GitRepos/sentinelSystem/frontend/src/pages/RegisterPage.jsx) still exists
- [`frontend/src/App.jsx`](/home/god/GitRepos/sentinelSystem/frontend/src/App.jsx) routes `/register` back to `/login`
- `AuthContext` does not provide the `register` function this page expects

Status: disconnected / dead UI

### Ghost Mode

- backend routes exist
- routes are unauthenticated
- frontend components call hardcoded `http://localhost:5000`
- main backend runs on `5001`
- frontend uses a different visual/system style than the main app

Status: demo-only and currently miswired

### Attack Simulator

- backend simulation route exists
- frontend calls hardcoded `http://localhost:5000`
- it does not use the shared API client or app auth model

Status: demo-only and currently miswired

### TrapAlert Component

- [`frontend/src/components/TrapAlert.jsx`](/home/god/GitRepos/sentinelSystem/frontend/src/components/TrapAlert.jsx) is empty

Status: dead file

### Security Claims

- messaging is labeled “secure”
- attendance/face flows look strong in UI
- current implementation is still demo-grade in several areas

Status: product messaging should stay conservative

## Recommended

- document and harden the real product core first
- treat governed chat + audit + assignments + risk + escalations as the main product spine
- demote or isolate ghost/attack demo labs until they are either integrated properly or removed
- prioritize stronger admin-action auditability and server-side enforcement over new surface area
