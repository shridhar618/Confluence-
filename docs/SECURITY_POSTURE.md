# Security Posture

## Current Auth Model

- JWT bearer auth for most application routes
- login accepts either password hash verification or static login code comparison
- JWT access tokens are configured with no expiry
- frontend stores the token in `localStorage`

## Current Authorization Model

- route-level checks use local helper functions and role string comparisons
- key patterns:
  - admin only
  - admin or HR
  - assignee only
  - otherwise any authenticated user

There is no centralized authorization policy layer.

## Security Strengths

- governed chat decisions are explicit and persisted
- admin audit visibility is real, not just UI text
- suspicious-query user tracking exists in the data model
- work escalation and risk concepts are already implemented
- most main product routes are JWT-protected

## Security Risks And Weak Defaults

### Unsafe Defaults

- default `SECRET_KEY` and `JWT_SECRET_KEY` fallback values in app config
- permissive CORS on `/api/*` with wildcard origin
- JWTs do not expire
- seeded demo users are created automatically

### Unprotected Or Weakly Protected Surfaces

- `/api/roles` is public
- ghost routes are unauthenticated
- attack simulator route is unauthenticated
- face unlock is not enforced server-side

### Data Exposure Risks

- `/api/users` exposes all active users except the caller, including emails
- admin logs store raw query text and raw AI response text
- JSON question-bank data and unanswered queue live on disk outside the DB
- in-memory histories are process-local and not auditable beyond chat logs

### Session And Token Risks

- JWT in `localStorage` is vulnerable to XSS-style theft
- no token expiry
- no refresh/revocation flow
- Socket.IO auth uses JWT in connection query params

### Admin / Manager Misuse Protection Gaps

- no dual control or approvals for sensitive admin actions
- admin user creation is not itself audit-logged
- no admin-action review trail for question-bank edits beyond JSON history
- no evidence bundle or resolution note requirements for escalation closure

### Biometric / Face Risks

- face matching is lightweight demo logic built from image normalization and random projection
- this should not be treated as strong biometric security

## Auditability Maturity

### Stronger Areas

- governed chat audit logs are detailed
- work assignment creation, progress, status changes, and escalation actions write audit rows

### Weaker Areas

- messaging actions are not audited
- attendance actions are not written into audit logs
- admin user creation is not written into the shared audit log table
- ghost mode uses in-memory logs instead of durable audit storage

## Immediate Hardening Priorities

### Priority 1

- remove default production-secret fallbacks
- expire JWTs
- move ghost and attack routes behind auth or isolate them from the main app
- enforce server-side face verification only if it is intended as a real gate

### Priority 2

- centralize authorization helpers
- add admin-action audit logging
- tighten `/api/users` data exposure
- document demo-only vs production-intended security surfaces in the UI

### Priority 3

- replace startup schema mutation with migrations
- move disk-backed JSON governance data into managed persistence if it becomes operationally important
- add rate limiting and login abuse protection

## Honest Bottom Line

The product already has meaningful governance and accountability features, but the security posture is still **demo-grade to early-internal-tool grade**, not enterprise-hardened.
