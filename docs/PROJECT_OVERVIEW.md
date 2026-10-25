# Project Overview

## What The Product Actually Is Today

SecureAI is currently a multi-surface internal governance application centered on a role-aware enterprise assistant. The product combines:

- governed AI chat with response filtering and explainability
- audit logging and admin analytics
- question-bank and review-queue operations
- work assignment, KPI, risk, and escalation tracking
- face-based attendance capture and verification
- private internal messaging
- admin user provisioning with employee login codes

This is not just a CRUD admin panel. The system has real decision logic in the request path, especially in:

- governance filtering in [`backend/app/services/governance.py`](/home/god/GitRepos/sentinelSystem/backend/app/services/governance.py)
- chat orchestration and audit creation in [`backend/app/routes/chat.py`](/home/god/GitRepos/sentinelSystem/backend/app/routes/chat.py)
- work KPI and capacity-risk computation in [`backend/app/routes/work_management.py`](/home/god/GitRepos/sentinelSystem/backend/app/routes/work_management.py)

## Likely Users

The real user model today is narrower than the seeded role list suggests.

Primary implemented personas:

- `admin`: full system operator, dashboard user, dataset operator, user creator
- `hr`: assignment manager, attendance reviewer, partially privileged chat user
- `intern`: least-privileged worker persona with blocked sensitive AI access

Secondary seeded roles exist in the DB (`Developer`, `Manager`, `Team Lead`, `Finance`, `Analyst`, `Security`), but most business logic only distinguishes `admin`, `hr`, and `intern`.

## Core Implemented Workflows

### Governed Query Flow

- user logs in
- user sends a chat message
- AI provider or local question-bank fallback produces a raw response
- governance rules score and filter the result by role
- audit log row is written with risk and explainability metadata
- admin dashboard later surfaces the event

### Question-Bank Operations

- admin can add, edit, delete, import, export, and review questions
- unmatched queries are captured into an unanswered queue
- users can favorite questions
- users can submit helpful/unhelpful feedback

### Work Management Flow

- admin or HR creates an assignment
- assignee submits incremental progress updates
- KPI values are computed dynamically
- capacity risk is inferred from KPI progress, due date, attendance recency, and concurrent incomplete work
- managers can move items on a board and create/resolve escalations

### Attendance Flow

- user or admin/HR registers a face profile
- attendance is marked via face matching
- admin/HR can view team attendance

### Messaging Flow

- authenticated users list other active users
- REST loads the conversation history
- Socket.IO delivers real-time private messages and typing indicators

## Current Product Identity

The current product identity is best described as:

**an explainable AI governance and accountability workspace with early workforce-operations signals**

It is not yet a cleanly unified enterprise platform, because:

- some surfaces are polished and integrated
- some are demo-oriented
- some are disconnected or only partially enforced server-side

## What Is Strong Already

- governance metadata is visible, stored, and queryable
- work-management already has real risk/escalation logic
- attendance and workload data are already in the same backend
- the app already tracks suspicious usage patterns at the user level

Those are meaningful product foundations, not just UI embellishments.
