# AI System

## Provider Integration

AI access is centralized in `backend/app/services/ai_service.py`.

The public entry point is:

```text
get_ai_response(messages: list[dict]) -> str
```

`messages` uses an OpenAI-style structure with `role` and `content`. The service reads `AI_PROVIDER`, defaulting to `gemini`.

Supported providers:

- `gemini`: Google Gemini through `google.generativeai`
- `openai`: OpenAI chat completion
- any other value: local mock/question-bank fallback

Gemini is the default provider and uses `gemini-1.5-flash`. OpenAI uses `gpt-3.5-turbo`.

There is no implemented Ollama or Gemma local-model adapter in the current repository.

## Adapter Pattern

The adapter pattern is lightweight:

```text
get_ai_response()
  |
  +-- _gemini_response()
  +-- _openai_response()
  +-- _mock_response()
```

Each provider returns plain text to the caller. The chat route then passes that text into the governance engine.

## Fallback Behavior

Fallback is implemented in two places:

- Missing or placeholder API keys return `_mock_response(messages)`.
- Provider exceptions return `_fallback_error(err)`.

`_mock_response()` first checks contextual query candidates against the local question bank. If a match exists, it returns the stored answer. If no strong dataset match exists, it returns a generic demo-mode message telling the user to configure an AI provider.

The fallback does not produce a structured escalation recommendation.

## Structured JSON Generation

The current AI provider path returns plain text. There is no implemented AI JSON schema enforcement or parser for escalation suggestions.

JSON handling exists for question-bank import/export and PDF parsing, but that is dataset management rather than AI-generated structured output.

The frontend expects an escalation suggestion object with fields such as:

- `reason`
- `severity`
- `impact`
- `summary`
- `suggestion`
- `draft_details`
- `affected_assignment_ids`
- `affected_assignments`

However, the backend route `POST /api/work/escalations/suggest` is not implemented in the current Flask code. That means the structured AI escalation suggestion flow is not currently functional end to end.

## Governed Chat Flow

```text
Input message
  -> chat history in memory
  -> ai_service provider or local fallback
  -> governance.apply_governance(raw_response, query, role)
  -> AuditLog
  -> JSON response to frontend
```

Governance behavior:

- intern users can be blocked for sensitive topics
- HR responses can be redacted for PII-like patterns
- admin responses are generally allowed after risk scoring
- high- and medium-risk chat events can feed Ghost Mode event streams

## AI Escalation Flow

Current frontend-intended flow:

```text
manager situation input
  -> selected assignment IDs
  -> include_team_context flag
  -> POST /api/work/escalations/suggest
  -> expected AI suggestion object
  -> manager clicks Create Escalation From Draft
  -> POST /api/work/escalations
```

Current implemented backend flow:

```text
manager reason input
  -> POST /api/work/escalations
  -> WorkEscalation row
  -> audit log row
  -> escalation appears in UI
```

The AI escalation assistant UI is present, but the backend suggestion route is missing. Until that route exists, escalation creation is manual or triggered directly from high-risk cards on the work board.
