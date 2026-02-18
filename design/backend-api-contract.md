# Backend API Contract — Frontend Perspective

## Context
You are working on the backend (FastAPI/Python) of an MCP Threat Intelligence application. The frontend is a React/TypeScript app that communicates with a single dialogue endpoint. This document describes exactly what the frontend sends, what it expects back, and how the conversation flow works.

## Endpoint: POST /api/dialogue/message

### Request Body (what the frontend sends)

```json
{
  "message": "string",
  "session_id": "string (UUID)",
  "perspectives": ["string"],
  "approved": true | false | null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `message` | `string` (required) | The user's text input. During approval, this is `"approve"` (but the backend should use the `approved` flag, not this string). |
| `session_id` | `string` (required) | UUID generated per conversation. Stays the same for all messages in one conversation. Different conversations have different session IDs. |
| `perspectives` | `string[]` (default `["NEUTRAL"]`) | Geopolitical perspectives selected by the user. Sent with every message. Possible values: `"US"`, `"EU"`, `"NORWAY"`, `"CHINA"`, `"RUSSIA"`, `"NEUTRAL"`. Can be multiple. |
| `approved` | `bool \| null` (optional) | Only set to `true` when the user clicks the Approve button during the confirmation phase. Is `undefined`/`null` for all normal messages and for rejection feedback. |

### Response Body (what the frontend expects)

```json
{
  "question": "string",
  "type": "string",
  "is_final": true | false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `question` | `string` (required) | The system's response text displayed to the user in the chat. This could be a clarifying question, a summary, or a confirmation message. |
| `type` | `string` (required) | The type of response. Used for frontend logic. Known values: `"scope"`, `"timeframe"`, `"targets"`, `"confirmation"`, `"complete"`. |
| `is_final` | `bool` (required) | **Critical flag.** When `true`, the frontend hides the text input and shows Approve/Reject buttons. When `false`, the normal text input is shown. |

### How `is_final` controls the UI

```
is_final: false  →  User sees text input + Send button (normal chat mode)
is_final: true   →  User sees Approve + Reject buttons (confirmation mode)
```

The frontend does NOT have a separate "get summary" or "approve" endpoint. Everything goes through this single endpoint. The backend must track what phase the conversation is in using the `session_id`.

## Conversation Flow

### Phase 1: Gathering (INITIAL → GATHERING)

```
Frontend sends:  { message: "Investigate APT29", session_id: "abc-123", perspectives: ["US", "EU"] }
Backend returns: { question: "What is the scope of your investigation?", type: "scope", is_final: false }

Frontend sends:  { message: "European critical infrastructure", session_id: "abc-123", perspectives: ["US", "EU"] }
Backend returns: { question: "What timeframe are you interested in?", type: "timeframe", is_final: false }

Frontend sends:  { message: "Last 6 months", session_id: "abc-123", perspectives: ["US", "EU"] }
Backend returns: { question: "Which entities should we focus on?", type: "targets", is_final: false }
```

The backend asks clarifying questions until it has sufficient context (scope, timeframe, target_entities).

### Phase 2: Confirmation (GATHERING → CONFIRMING)

When the backend has enough information, it sends a summary with `is_final: true`:

```
Frontend sends:  { message: "Energy sector organizations", session_id: "abc-123", perspectives: ["US", "EU"] }
Backend returns: { question: "Here is your investigation summary: ... Do you approve?", type: "confirmation", is_final: true }
```

**This is the critical moment.** The frontend now shows Approve/Reject buttons instead of the text input.

### Phase 3a: User Approves (CONFIRMING → COMPLETE)

```
Frontend sends:  { message: "approve", session_id: "abc-123", perspectives: ["US", "EU"], approved: true }
Backend returns: { question: "Approved! Proceeding to intelligence gathering.", type: "complete", is_final: false }
```

**Important:** The `approved: true` flag is the reliable indicator. Do NOT check if `message === "approve"` — use the boolean flag.

The frontend shows the response as a system message. The approval is sent silently (no user message bubble appears in the chat for "approve").

### Phase 3b: User Rejects (CONFIRMING → GATHERING)

When the user clicks Reject, the frontend does NOT call the backend immediately. Instead:

1. Frontend shows a system message: "What would you like to change?" (frontend-only, no API call)
2. The text input reappears
3. User types their feedback and hits Send

```
Frontend sends:  { message: "I want to focus on energy sector specifically", session_id: "abc-123", perspectives: ["US", "EU"] }
Backend returns: { question: "Updated. What timeframe should we use?", type: "scope", is_final: false }
```

**Important:** The rejection feedback arrives as a normal message with `approved: undefined/null`. The backend should recognize that a message in CONFIRMING state without `approved: true` means the user wants modifications, and should transition back to GATHERING state.

## Perspectives

The `perspectives` array is sent with **every** message. It represents which geopolitical viewpoints the AI should consider when generating questions and analysis.

| Value | Meaning |
|-------|---------|
| `"US"` | United States perspective |
| `"EU"` | European Union perspective |
| `"NORWAY"` | Norwegian perspective |
| `"CHINA"` | Chinese perspective |
| `"RUSSIA"` | Russian perspective |
| `"NEUTRAL"` | Neutral/unbiased perspective (default) |

Users can select multiple perspectives simultaneously. The perspectives can change mid-conversation (user toggles them between messages). The backend receives the current selection with each message.

## Session Management

- Each conversation has a unique `session_id` (UUID v4) generated by the frontend
- The same `session_id` is sent with every message in that conversation
- The backend must maintain conversation state (DialogueFlow, DialogueContext) per session_id
- Multiple conversations can exist simultaneously (different tabs, or user switches between conversations)
- Currently there is NO session storage on the backend — this needs to be implemented (in-memory dict or database)

## State Machine (Backend DialogueFlow)

```
INITIAL → GATHERING → CONFIRMING → COMPLETE
                ↑          |
                |__________|
                (rejection with feedback)
```

| State | Trigger | Next State |
|-------|---------|------------|
| INITIAL | First user message | GATHERING |
| GATHERING | Sufficient context collected | CONFIRMING |
| GATHERING | Max questions reached (15) | CONFIRMING |
| CONFIRMING | `approved: true` | COMPLETE |
| CONFIRMING | Message without `approved: true` | GATHERING |

## Error Handling

The frontend does not currently handle error responses gracefully. If the backend returns an error (4xx, 5xx), the frontend will show a network error in the console. The response must always include `question`, `type`, and `is_final` fields — missing fields will cause the frontend to crash.

## Files Reference

### Frontend files that interact with the backend:
- `frontend/src/services/dialogue.ts` — The HTTP service that makes the POST request
- `frontend/src/hooks/useChat.ts` — The hook that calls the service and manages chat state
- `frontend/src/types/conversation.ts` — Type definitions for Message, Conversation

### Backend files to modify:
- `backend/src/api/dialogue.py` — The endpoint (currently hardcoded, needs to use DialogueFlow)
- `backend/src/services/dialogue_flow.py` — The state machine (working, needs session integration)
- `backend/src/services/dialogue_service.py` — Question generation via MCP
- `backend/src/models/dialogue.py` — Pydantic models (DialogueContext, DialogueResponse, Perspective enum)
