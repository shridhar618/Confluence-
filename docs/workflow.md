# Workflow

## Work Lifecycle

```text
Assignment -> Progress -> KPI -> Risk -> Escalation -> Resolution
```

## 1. Assignment

Admin or HR users create assignments through the work assignment UI. The backend requires:

- `title`
- `assigned_to_user_id`
- `expected_units`
- `weight`

Optional fields include `description`, `due_date`, and initial `status`.

Assignments are stored as `WorkAssignment` rows and are serialized with assignee/creator details, KPI, capacity risk, progress updates, and any open escalation.

## 2. Progress

The assigned user submits progress through `My Work`.

Each progress update includes:

- `completed_units`
- optional `note`

The backend stores these as `WorkProgressUpdate` rows. After each update, assignment status is synchronized:

- completed units at or above expected units -> `completed`
- any completed units -> `in_progress`
- blocked status is preserved
- otherwise `pending` or board `todo`

## 3. KPI

KPI is computed dynamically from the assignment and progress updates:

- `expected_units`
- `total_completed_units`
- `completion_ratio`
- `weighted_score`

The weighted score is capped by completion ratio and multiplied by assignment weight.

## 4. Risk

Capacity risk is computed in `work_management.py`. It is deterministic and explainable.

Risk can increase when:

- an incomplete assignment is overdue
- an incomplete assignment is due within two days and completion is below 50%
- an incomplete assignment is due within five days and completion is below 75%
- no attendance record exists for the assignee in the last three days
- the assignee has three or more incomplete assignments

Risk levels are `low`, `medium`, and `high`. Responses include `reasons` and `signals`.

## 5. Escalation

Admin and HR users can create an escalation for an assignment. The backend prevents more than one open escalation per assignment.

Escalations store:

- assignment ID
- creator user ID
- optional reason/note
- status, initially `open`
- creation timestamp

The board UI also shows an `Escalate` button for high-risk assignments that do not already have an open escalation.

## 6. Resolution

Admin and HR users can resolve an escalation by PATCHing the escalation status to `resolved`.

Only transition to `resolved` is implemented. There is no reopen flow, ownership model, SLA, comment thread, or resolution evidence bundle.

## AI-Assisted Escalation

The frontend contains an AI Escalation Assistant in `WorkEscalationsPage.jsx`.

Manager input includes:

- selected assignment
- free-text operational situation
- `include_team_context` checkbox

The UI attempts to call:

```text
POST /api/work/escalations/suggest
```

The expected frontend behavior is:

```text
manager input
  -> AI suggestion
  -> human review
  -> Create Escalation From Draft
  -> POST /api/work/escalations
```

Current backend reality:

- `POST /api/work/escalations/suggest` is not implemented.
- The AI service is not wired into `work_management.py`.
- Human-approved escalation creation through `POST /api/work/escalations` is implemented.

The accurate current workflow is therefore manual escalation with a frontend AI-assistant form that is not functional until the backend suggestion route is added.
