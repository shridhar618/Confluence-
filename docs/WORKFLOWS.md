# Workflows

## 1. Governed Query Flow

### Implemented Path

1. User authenticates via `/api/auth/login`.
2. Frontend sends a message to `/api/chat`.
3. [`backend/app/services/ai_service.py`](/home/god/GitRepos/sentinelSystem/backend/app/services/ai_service.py) resolves a response:
   - provider-backed if configured
   - local question-bank match if available
   - fallback mock response otherwise
4. [`backend/app/services/governance.py`](/home/god/GitRepos/sentinelSystem/backend/app/services/governance.py) scores and filters the result.
5. The backend writes an `AuditLog` row with:
   - raw query
   - raw response
   - filtered response
   - status
   - risk metadata
   - explainability details
6. Frontend renders the answer with governance details and feedback controls.

### Notes

- intern users can be blocked
- HR users can receive redacted responses
- admin users currently get the raw response path
- suspicious-query counters on the `User` row are incremented for sensitive queries

## 2. Question-Bank And Review Queue Flow

### Implemented Path

1. Chat and question-bank pages load role-filtered questions.
2. Search uses question text, category, keywords, aliases, and a TF-IDF ranking path.
3. If no strong match exists, the query is stored in `unanswered_questions.json`.
4. Admin users can:
   - create/edit/delete questions
   - import from JSON or PDF
   - export JSON or CSV
   - inspect question history
   - resolve review-queue items as open/resolved/ignored

### Notes

- the review queue is real and useful
- persistence is JSON-backed, not DB-backed

## 3. Assignment -> Progress -> KPI -> Risk -> Escalation Flow

### Implemented Path

1. Admin or HR creates a work assignment.
2. Assignee sees it in `My Work`.
3. Assignee posts progress updates with completed units and optional note.
4. KPI is computed from:
   - expected units
   - total completed units
   - completion ratio
   - weighted score
5. Capacity risk is computed from:
   - due date pressure
   - incomplete progress
   - recent attendance absence
   - high concurrent incomplete workload
6. Managers can view assignments in:
   - list view
   - board view
7. Managers can create an escalation when needed.
8. Escalations can later be resolved.

### Notes

- this is one of the strongest implemented business flows in the repo
- capacity risk is currently deterministic and understandable

## 4. Attendance Flow

### Implemented Path

1. User captures an image in the browser.
2. `/api/face/register` stores a numeric face embedding for the user.
3. `/api/attendance/mark` matches a fresh image against registered profiles.
4. The system writes a check-in or check-out attendance record.
5. Users can review their own records.
6. Admin/HR can review team attendance.

### Notes

- attendance data already feeds into work-capacity risk
- the face-recognition implementation is lightweight and should be treated as low-assurance

## 5. Private Messaging Flow

### Implemented Path

1. Frontend loads active users from `/api/users`.
2. Frontend connects Socket.IO with JWT in the query.
3. REST loads conversation history.
4. Socket.IO delivers new messages and typing signals in real time.
5. Messages are persisted in the DB.

### Notes

- this is functionally implemented
- the system does not currently apply governance or audit logging to messages

## 6. Admin User Provisioning Flow

### Implemented Path

1. Admin chooses username and role.
2. Backend generates a unique login code.
3. User is created with:
   - username
   - generated email
   - password hash based on the login code
   - stored plaintext login code for comparison at login
4. Admin can later verify a code against the stored value.

### Notes

- this works for internal demo onboarding
- it is not a mature credential-management design

## 7. Demo Security Lab Flows

### Ghost Mode

- honeypot chat route with keyword-based risk scoring
- in-memory log store
- realtime trap events
- freeze flag in log state

### Attack Simulation

- returns a fixed set of attack examples and “blocked” responses

### Notes

- these are not integrated into the main auth/data architecture cleanly
- frontend wiring currently points to the wrong backend port
