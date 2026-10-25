# API Surface

All routes are under `/api` because blueprints are mounted with `/api` prefixes in the app factory.

## Auth

### `POST /api/auth/register`

- public registration is intentionally disabled
- always returns a `403`

### `POST /api/auth/login`

- accepts `username` plus either `login_code` or `password`
- returns JWT and serialized user

### `GET /api/auth/me`

- returns current authenticated user

### `POST /api/auth/face-verify`

- verifies the current user against a submitted face image

## Admin

### `POST /api/admin/create-user`

- admin only
- creates a user and generates a login code

### `POST /api/admin/check-user-code`

- admin only
- checks whether a submitted code matches the stored user code

## Roles

### `GET /api/roles`

- returns all roles
- currently not auth-protected

## Users

### `GET /api/users`

- authenticated
- returns all active users except the current user
- used by private messaging and assignment UI

## Governed Chat And Question Bank

### Chat

- `POST /api/chat`
- `POST /api/chat/clear`
- `GET /api/chat/export`

### Question Bank

- `GET /api/chat/questions`
- `GET /api/chat/questions/search`
- `POST /api/chat/questions`
- `PUT /api/chat/questions/:question_id`
- `DELETE /api/chat/questions/:question_id`
- `POST /api/chat/questions/import`
- `GET /api/chat/questions/export`
- `GET /api/chat/questions/history`
- `GET /api/chat/questions/review-queue`
- `PATCH /api/chat/questions/review-queue/:queue_id`

### Favorites And Feedback

- `GET /api/chat/favorites`
- `POST /api/chat/favorites/:question_id`
- `DELETE /api/chat/favorites/:question_id`
- `POST /api/chat/feedback`

## Logs And Analytics

### `GET /api/logs`

- admin only
- paginated audit log listing with filters

### `GET /api/logs/stats`

- admin only
- aggregate counts, suspicious users, recent high-risk rows, question-bank analytics

### `GET /api/logs/export`

- admin only
- CSV export of audit log summary rows

### `PATCH /api/logs/suspicious/:user_id`

- admin only
- manually update suspicious flag state on a user

## Messaging

### REST

- `GET /api/messages/:other_id`
- `POST /api/messages`
- `GET /api/messages/unread`

### Socket.IO Events

- `connect`
- `disconnect`
- `private_message`
- `typing`
- `stop_typing`

JWT is decoded from the socket query token.

## Attendance

### `POST /api/face/register`

- authenticated
- registers a face for self, or for another user if admin/HR

### `POST /api/attendance/mark`

- authenticated
- marks check-in/check-out by face match

### `GET /api/attendance`

- admin/HR only
- returns team attendance records

### `GET /api/attendance/me`

- authenticated
- returns own attendance records

## Work Management

### Assignments

- `POST /api/work/assignments`
- `GET /api/work/assignments`
- `POST /api/work/assignments/:assignment_id/progress`
- `PATCH /api/work/assignments/:assignment_id/status`
- `GET /api/work/assignments/:assignment_id/kpi`

### Board

- `GET /api/work/board`

### Escalations

- `POST /api/work/escalations`
- `GET /api/work/escalations`
- `PATCH /api/work/escalations/:escalation_id`

## Demo / Security-Lab Routes

### Ghost Mode

- `POST /api/ghost-chat`
- `GET /api/ghost-logs`
- `POST /api/ghost-freeze`

These are currently not protected by JWT.

### Attack Simulation

- `GET /api/attack-simulate`

This is also not protected by JWT.
