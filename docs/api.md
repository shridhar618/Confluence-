# API

All routes below are mounted under `/api`.

Most routes require a JWT bearer token:

```http
Authorization: Bearer <token>
```

## Auth

### `POST /api/auth/login`

Authenticates with username plus either login code or password.

Request:

```json
{
  "username": "admin",
  "login_code": "ADMINCODE1"
}
```

Alternate request:

```json
{
  "username": "admin",
  "password": "admin123"
}
```

Response:

```json
{
  "token": "<jwt>",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@secureai.com",
    "role": "admin",
    "role_id": 1,
    "created_at": "2026-01-01T00:00:00",
    "is_active": true,
    "sensitive_query_count": 0,
    "is_suspicious": false,
    "flagged_at": null
  }
}
```

### `POST /api/auth/register`

Public registration is disabled.

Response:

```json
{
  "error": "Public registration is disabled. Contact an admin to create your account."
}
```

### `GET /api/auth/me`

Returns the current authenticated user.

Response:

```json
{
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@secureai.com",
    "role": "admin",
    "is_active": true
  }
}
```

### `POST /api/auth/face-verify`

Verifies the logged-in user against a submitted face image.

Request:

```json
{
  "image_base64": "data:image/jpeg;base64,..."
}
```

Response:

```json
{
  "verified": true,
  "confidence": 0.9123,
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

## Work Assignments

### `GET /api/work/assignments`

Lists assignments. Admin and HR users see all assignments. Other users see only assignments assigned to them.

Response:

```json
{
  "assignments": [
    {
      "id": 10,
      "title": "Close support tickets",
      "description": "Process the remaining queue",
      "assigned_by_user_id": 1,
      "assigned_to_user_id": 3,
      "assigned_by_username": "admin",
      "assigned_to_username": "intern_bob",
      "expected_units": 20.0,
      "weight": 1.0,
      "due_date": "2026-04-15",
      "status": "in_progress",
      "kpi": {
        "expected_units": 20.0,
        "total_completed_units": 8.0,
        "completion_ratio": 0.4,
        "weighted_score": 0.4
      },
      "capacity_risk": {
        "level": "high",
        "reasons": ["Due within 2 days with low completion."],
        "signals": {
          "completion_ratio": 0.4,
          "days_until_due": 2
        }
      },
      "open_escalation": null,
      "progress_updates": []
    }
  ],
  "count": 1
}
```

### `POST /api/work/assignments`

Admin/HR only. Creates an assignment.

Request:

```json
{
  "title": "Close support tickets",
  "description": "Process the remaining queue",
  "assigned_to_user_id": 3,
  "expected_units": 20,
  "weight": 1,
  "due_date": "2026-04-15",
  "status": "pending"
}
```

Response:

```json
{
  "message": "Assignment created",
  "assignment": {
    "id": 10,
    "title": "Close support tickets",
    "status": "pending",
    "kpi": {
      "expected_units": 20.0,
      "total_completed_units": 0.0,
      "completion_ratio": 0.0,
      "weighted_score": 0.0
    },
    "capacity_risk": {
      "level": "medium",
      "reasons": ["No recent attendance signal for assignee."],
      "signals": {
        "completion_ratio": 0.0,
        "days_until_due": 4
      }
    }
  }
}
```

### `POST /api/work/assignments/:assignment_id/progress`

Assignee only. Adds progress to an assignment.

Request:

```json
{
  "completed_units": 5,
  "note": "Completed the first batch"
}
```

Response:

```json
{
  "message": "Progress update submitted",
  "progress_update": {
    "id": 1,
    "assignment_id": 10,
    "reported_by_user_id": 3,
    "reported_by_username": "intern_bob",
    "completed_units": 5.0,
    "note": "Completed the first batch",
    "created_at": "2026-04-11T10:00:00"
  },
  "assignment": {
    "id": 10,
    "status": "in_progress"
  }
}
```

### `PATCH /api/work/assignments/:assignment_id/status`

Admin/HR only. Updates board status.

Allowed statuses:

- `todo`
- `in_progress`
- `blocked`
- `completed`

Request:

```json
{
  "status": "blocked"
}
```

Response:

```json
{
  "message": "Assignment status updated",
  "assignment": {
    "id": 10,
    "status": "blocked"
  }
}
```

### `GET /api/work/assignments/:assignment_id/kpi`

Returns KPI and capacity risk for one assignment. Admin/HR can access any assignment; assignees can access their own.

Response:

```json
{
  "assignment_id": 10,
  "status": "in_progress",
  "kpi": {
    "expected_units": 20.0,
    "total_completed_units": 8.0,
    "completion_ratio": 0.4,
    "weighted_score": 0.4
  },
  "capacity_risk": {
    "level": "high",
    "reasons": ["Due within 2 days with low completion."],
    "signals": {
      "completion_ratio": 0.4,
      "days_until_due": 2
    }
  }
}
```

## Work Board

### `GET /api/work/board`

Admin/HR only. Returns assignments formatted for board columns.

Response:

```json
{
  "assignments": [
    {
      "id": 10,
      "title": "Close support tickets",
      "status": "todo",
      "kpi": {},
      "capacity_risk": {},
      "open_escalation": null
    }
  ],
  "columns": ["todo", "in_progress", "blocked", "completed"],
  "count": 1
}
```

## Work Escalations

### `POST /api/work/escalations/suggest`

Frontend-wired but not implemented in the current Flask backend.

The React page sends this request:

```json
{
  "message": "2 employees are absent today, we cannot complete tickets",
  "assignment_ids": [10],
  "include_team_context": true
}
```

The frontend expects a response shaped like:

```json
{
  "reason": "Ticket completion is at risk",
  "severity": "high",
  "impact": "Delivery may be delayed",
  "summary": "Low progress and attendance gaps affect the assignment",
  "suggestion": "Escalate to the manager and reassign capacity",
  "draft_details": "Draft escalation note...",
  "affected_assignment_ids": [10],
  "affected_assignments": []
}
```

Current backend behavior: no matching route exists in `backend/app/routes/work_management.py`, so this request will not succeed unless another layer adds the endpoint.

### `POST /api/work/escalations`

Admin/HR only. Creates an open escalation for an assignment. The backend rejects creation if the assignment already has an open escalation.

Request:

```json
{
  "assignment_id": 10,
  "reason": "Delivery risk due to low progress and attendance gaps"
}
```

`note` is also accepted as an alias for `reason`.

Response:

```json
{
  "message": "Escalation created",
  "escalation": {
    "id": 4,
    "assignment_id": 10,
    "reason": "Delivery risk due to low progress and attendance gaps",
    "status": "open",
    "created_by_user_id": 1,
    "created_by_username": "admin",
    "assignment_title": "Close support tickets",
    "created_at": "2026-04-11T10:00:00",
    "assignment": {
      "id": 10,
      "title": "Close support tickets",
      "status": "in_progress"
    }
  }
}
```

### `GET /api/work/escalations`

Admin/HR only. Lists all escalations newest first.

Response:

```json
{
  "escalations": [
    {
      "id": 4,
      "assignment_id": 10,
      "reason": "Delivery risk due to low progress and attendance gaps",
      "status": "open",
      "created_by_username": "admin",
      "assignment": {
        "id": 10,
        "title": "Close support tickets",
        "status": "in_progress"
      }
    }
  ],
  "count": 1
}
```

### `PATCH /api/work/escalations/:escalation_id`

Admin/HR only. Resolves an escalation. Only `resolved` is supported.

Request:

```json
{
  "status": "resolved"
}
```

Response:

```json
{
  "message": "Escalation updated",
  "escalation": {
    "id": 4,
    "assignment_id": 10,
    "status": "resolved"
  }
}
```
