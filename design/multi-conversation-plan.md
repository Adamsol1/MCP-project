# Plan: Multi-Conversation System with Sidebars (S2.1.5 + S2.3.3)

## Context
Add message history management (S2.1.5) and per-conversation perspective state management (S2.3.3), plus restructure the UI with left/right sidebars. Conversations persist in localStorage. Users can create, switch, and delete conversations. Each conversation remembers its own perspective selections.

## Data Model

```typescript
// frontend/src/types/conversation.ts

interface Message {
  id: string;
  text: string;
  sender: "user" | "system";
}

interface Conversation {
  id: string;               // UUID
  title: string;            // First user message (50 chars max), or "New conversation"
  messages: Message[];
  perspectives: string[];   // Per-conversation, default ["NEUTRAL"]
  sessionId: string;        // Backend session ID
  isConfirming: boolean;
  createdAt: number;        // Date.now() timestamp
  updatedAt: number;        // Last message timestamp
}

interface ConversationStore {
  conversations: Conversation[];
  activeConversationId: string | null;
}
```

localStorage key: `"mcp-conversations"` (single key, full store as JSON)

## Architecture

### Component Hierarchy
```
main.tsx
  <ToastProvider>
    <ConversationProvider>
      <App />
    </ConversationProvider>
  </ToastProvider>

App.tsx
  <div className="flex h-screen">
    <Sidebar />                   // Left - chat history list
    <main className="flex-1">
      <ChatWindow />              // Center - unchanged props API
    </main>
    <OptionsPanel />              // Right - perspectives + file upload trigger
  </div>
  <FileUploadModal />             // Modal overlay for file upload
  <ToastContainer />
```

### State Management
- **ConversationContext** (useReducer) - manages all conversation state, persists to localStorage
- **useConversation hook** - thin context accessor (follows useToast pattern)
- **useChat hook** - refactored to read from ConversationContext instead of local useState
- Reducer actions: CREATE, SWITCH, DELETE, ADD_MESSAGE, SET_IS_CONFIRMING, UPDATE_PERSPECTIVES

### Key Design Decisions
- **localStorage** for persistence (no backend DB needed yet)
- **useReducer** for atomic state updates (one dispatch updates messages + updatedAt + title)
- **Per-conversation perspectives** stored in Conversation object
- **useChat return API unchanged** so ChatWindow needs zero changes
- **Message type shared** via types/conversation.ts (deduplicated from useChat.ts and ChatWindow.tsx)

## Implementation Phases

### Phase 1: Foundation
1. Type definitions (`types/conversation.ts`)
2. localStorage service (`services/conversationStorage.ts`) - pure CRUD functions
3. ConversationContext + useConversation hook

### Phase 2: Refactor
4. Refactor useChat to use ConversationContext (same return API)

### Phase 3: UI Components
5. Sidebar component (left - conversation list)
6. FileUploadModal component (modal wrapping existing FileUpload)
7. OptionsPanel component (right - perspectives + upload button)

### Phase 4: Integration
8. Wire everything in App.tsx + main.tsx (three-column layout)

## Files

### New (12 files)
- `frontend/src/types/conversation.ts`
- `frontend/src/services/conversationStorage.ts` + test
- `frontend/src/contexts/ConversationContext.tsx` + test
- `frontend/src/hooks/useConversation.ts`
- `frontend/src/components/Sidebar/Sidebar.tsx` + test
- `frontend/src/components/FileUploadModal/FileUploadModal.tsx` + test
- `frontend/src/components/OptionsPanel/OptionsPanel.tsx` + test

### Modified (4 files)
- `frontend/src/hooks/useChat.ts` - read from context
- `frontend/src/hooks/useChat.test.ts` - add ConversationProvider wrapper
- `frontend/src/App.tsx` - three-column sidebar layout
- `frontend/src/main.tsx` - add ConversationProvider

### Unchanged
All existing components (ChatWindow, PerspectiveSelector, FileUpload, Toast) and their tests
