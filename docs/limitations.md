# Limitations

## AI Is Advisory

The implemented AI chat path is advisory and governed. It does not autonomously create assignments, change work status, create escalations, or resolve escalations.

The escalation assistant UI exists, but the backend suggestion route is missing. Current escalation creation is manual through `POST /api/work/escalations` or the board escalation button.

## AI Escalation Gap

`WorkEscalationsPage.jsx` calls:

```text
POST /api/work/escalations/suggest
```

No matching route exists in `backend/app/routes/work_management.py`. The docs should treat AI-assisted escalation as partially wired in the frontend, not implemented end to end.

## No Structured AI JSON Contract

The AI provider functions return plain text. The current code does not enforce JSON schemas, retry invalid model output, or normalize AI-generated escalation objects.

Question-bank import/export uses JSON, but that is separate from AI generation.

## Provider Limits And Latency

Gemini is the default provider when `AI_PROVIDER` is unset. It uses `gemini-1.5-flash` and depends on `GEMINI_API_KEY`.

Known operational concerns:

- provider latency can affect chat response time
- missing or placeholder keys fall back to demo-mode responses
- provider exceptions return a fallback error message
- Gemini free-tier or quota limits may affect availability if the app is configured with a free-tier key

OpenAI is also supported through `AI_PROVIDER=openai` and `OPENAI_API_KEY`, using `gpt-3.5-turbo`.

## No Ollama/Gemma Local Model

There is no implemented Ollama or Gemma adapter. The only local behavior is the question-bank/mock fallback inside `ai_service.py`.

## Hackathon-Level Tradeoffs

The repository has several demo-oriented implementation choices:

- SQLite default database
- no migration framework
- startup-time schema patch helpers
- chat histories stored in process memory
- question bank, history, and unanswered queue stored as JSON files
- permissive CORS for `/api/*`
- JWTs configured without expiration
- seeded demo users
- role checks implemented locally in route helpers instead of a centralized policy engine

## Work Risk Model Limits

Capacity risk is deterministic and explainable, but simple.

It uses due dates, completion ratio, recent attendance presence, and active incomplete assignment count. It does not model:

- actual effort estimates beyond expected units
- assignee skill or availability calendars
- team-level dependency graphs
- SLA history
- escalation severity beyond open/resolved state

## Escalation Model Limits

Escalations currently support:

- create
- list
- resolve

They do not currently support:

- owner assignment
- comments or discussion
- severity field
- due date/SLA
- reopen flow
- resolution evidence
- audit trail beyond the generic work-management audit log row
