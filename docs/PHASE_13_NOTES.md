# Phase 13 — Alert Center: Implementation Notes

## What was added

**`backend/app/services/notifications.py`** (new) — `create_notification()`, `notify_admins()`, and `emit_pending()`. One place that both persists a `Notification` row and pushes it over Socket.IO, so a caller can't do one without the other. Emission happens **after** the transaction commits, so an admin is never alerted about a case that failed to save, and the payload carries a real database id (which the client needs in order to mark it read).

**`backend/app/services/risk_tracking.py`** — refactored to use the service instead of constructing `Notification` rows inline. Phase 10's alerts are now real-time rather than only visible on the next poll.

**`frontend/src/components/TopBar.jsx`** — subscribes to the `notification` socket event: the badge increments and an open dropdown updates live. Polling is kept as a fallback for a dropped connection but slowed from 30s to 60s, since it's no longer the primary path. Alerts tied to a governance case are now clickable — they mark themselves read and navigate to the case list, which is the brief's "Admin can click: View Case".

## A real security bug found and fixed

While cross-checking that the room I emit to is actually the room clients join, I found that the pre-existing `join_user_room` Socket.IO handler takes a **client-supplied, unauthenticated** value and joins `user_{that value}`:

```python
user = data.get('user')
if user:
    join_room(f"user_{user}")   # no verification whatsoever
```

Ghost Mode calls this with a *username*. But private messages (`socket_events.py`) and now governance alerts are delivered to `user_{id}` rooms keyed by **user id**. Same prefix, two different namespaces — so any connected client could emit `join_user_room` with `{"user": 5}` and silently start receiving user #5's private messages and, after this phase, their governance alerts.

This was pre-existing, but routing governance alerts through those rooms would have meaningfully increased its impact, which makes it this phase's problem rather than something to defer to Phase 21. Fixed by giving Ghost Mode its own namespace: the unauthenticated handler now joins `ghost_user_{...}`, and the three ghost emit sites were updated to match. The `user_{id}` rooms are now joined **only** in `socket_events.py`'s connect handler, after the JWT has been verified.

One ghost emit at `ghost_routes.py:131` still targets `user_{user.id}` — that one is legitimate and was left alone, because it's addressing the genuinely authenticated logged-in user, not a client-supplied value.

## Verified for real

- **Room namespace isolation**: confirmed an attacker supplying `5` now lands in `ghost_user_5`, which cannot collide with the victim's `user_5`; confirmed notifications and private messages both target only the JWT-verified room; confirmed Ghost Mode's join and emit still agree with each other after the rename (so the fix doesn't break the demo).
- Cross-checked every `join_room` call site against every emit target across the whole backend to make sure no other pair was mismatched.
- Syntax-checked all changed Python and the modified `TopBar.jsx`.

## What I could NOT verify

Whether Socket.IO actually delivers these events end-to-end — that needs a running server, a real websocket connection, and two browser sessions. Specifically unverified: that `socketio.emit()` works correctly from inside a service call (outside a socket event handler) under this app's async mode, and that Ghost Mode still functions after the room rename. **Ghost Mode is the thing most worth clicking through after this change**, since I modified rooms it depends on.

**Please verify:**
```bash
cd backend && python app.py
cd frontend && npm run dev
# 1. Open two browsers: admin + intern. Trigger a high-risk request as the intern.
#    The admin's bell should increment WITHOUT a refresh.
# 2. Click the alert -> should mark read and navigate to /governance-cases
# 3. Open Ghost Mode as admin and confirm it still works after the room rename
```
