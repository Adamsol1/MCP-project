# Backend API Contract - Frontend Perspective

## Endpoint
`POST /api/dialogue/message`

## Request Body

```json
{
  "message": "string",
  "session_id": "string (UUID)",
  "perspectives": ["string"],
  "approved": true | false | null,
  "language": "en",
  "settings_timeframe": ""
}
```

| Field | Type | Description |
|---|---|---|
| `message` | `string` | User input text. During approval clicks frontend sends `"approve"`, but backend should rely on `approved`. |
| `session_id` | `string` | Conversation UUID used to maintain backend session state. |
| `perspectives` | `string[]` | Selected geopolitical perspectives. Sent on every request. |
| `approved` | `bool \| null` | `true` when the user approves a pending summary/PIR. |
| `language` | `string` | BCP-47 language code (for example `en`, `no`). |
| `settings_timeframe` | `string` | Optional prefilled timeframe from Settings. |

## Response Body (Action-Only)

```json
{
  "question": "string",
  "action": "ask_question | show_summary | show_pir | max_questions | complete",
  "stage": "initial | gathering | summary_confirming | pir_confirming | complete",
  "sub_state": "awaiting_decision | awaiting_modifications | null"
}
```

| Field | Type | Description |
|---|---|---|
| `question` | `string` | System message shown in chat. |
| `action` | `string` | Canonical backend action from `DialogueFlow`. |
| `stage` | `string` | Canonical dialogue stage for UI state. |
| `sub_state` | `string \| null` | Optional sub-state for confirm stages. |

## Action Semantics

| `action` | Frontend render type | Confirming mode |
|---|---|---|
| `ask_question` | `question` | no |
| `show_summary` | `summary` | yes |
| `max_questions` | `summary` | yes |
| `show_pir` | `pir` | yes |
| `complete` | `complete` | no |

`max_questions` intentionally uses summary confirmation UX.

## Conversation Flow

### Gathering (`INITIAL -> GATHERING`)

```text
Frontend sends: { message: "Investigate APT29", session_id: "abc-123", perspectives: ["US", "EU"] }
Backend returns: { question: "What is the scope of your investigation?", action: "ask_question" }
```

### Summary Confirming (`GATHERING -> SUMMARY_CONFIRMING`)

```text
Frontend sends: { message: "Energy sector organizations", session_id: "abc-123", perspectives: ["US", "EU"] }
Backend returns: { question: "{...summary json...}", action: "show_summary" }
```

### Approve Summary (`SUMMARY_CONFIRMING -> PIR_CONFIRMING`)

```text
Frontend sends: { message: "approve", session_id: "abc-123", perspectives: ["US", "EU"], approved: true }
Backend returns: { question: "{...pir json...}", action: "show_pir" }
```

### Reject Summary (summary regeneration loop)

```text
Frontend sends: { message: "Narrow to energy sector", session_id: "abc-123", perspectives: ["US", "EU"] }
Backend returns: { question: "{...updated summary json...}", action: "show_summary" }
```

### Approve PIR (`PIR_CONFIRMING -> COMPLETE`)

```text
Frontend sends: { message: "approve", session_id: "abc-123", perspectives: ["US", "EU"], approved: true }
Backend returns: { question: "Direction phase already complete.", action: "complete" }
```

## Perspectives

Possible values:
- `US`
- `EU`
- `NORWAY`
- `CHINA`
- `RUSSIA`
- `NEUTRAL`

Multiple values are allowed and can change between turns.

## State Machine

```text
INITIAL -> GATHERING -> SUMMARY_CONFIRMING -> PIR_CONFIRMING -> COMPLETE
```

Reject loops:
- `SUMMARY_CONFIRMING` + feedback -> `SUMMARY_CONFIRMING` (regenerate summary)
- `PIR_CONFIRMING` + feedback -> `PIR_CONFIRMING` (regenerate PIR)

## Required Success Fields

On successful responses, backend must include:
- `question`
- `action`
- `stage`

## File References

Frontend:
- `frontend/src/services/dialogue.ts`
- `frontend/src/hooks/useChat.ts`
- `frontend/src/types/conversation.ts`

Backend:
- `backend/src/api/dialogue.py`
- `backend/src/services/dialogue_flow.py`
- `backend/src/services/dialogue_service.py`
- `backend/src/models/dialogue.py`
