import { useEffect, useState, useRef } from "react";
import type { Conversation } from "../../types/conversation";
import type { DialogueStage } from "../../types/dialogue";

/** Props for the Sidebar component. */
interface SidebarProps {
  /** Full list of all conversations to display. */
  conversations: Conversation[];
  /** The id of the currently active conversation, or null when none is selected. */
  activeConversationId: string | null;
  /** Called when the user clicks the New Chat button. */
  onNewChat: () => void;
  /** Called with the conversation id when the user clicks a conversation row. */
  onSwitchConversation: (id: string) => void;
  /** Called with the conversation id when the user confirms deletion. */
  onDeleteConversation: (id: string) => void;
  /** Called with the conversation id and new title when the user finishes renaming. */
  onRenameConversation: (id: string, newTitle: string) => void;
  /** DEV: Deletes every conversation and clears the active selection. */
  onDeleteAllConversations: () => void;
  /** DEV: Injects a predefined message into the chat input and sends it. */
  onDevSendMessage: () => void;
  /** DEV: Forces chat into confirmation mode to preview approval UI. */
  onDevShowCollectionApproval?: () => void;
  /** DEV: Force the backend/session to a specific stage. */
  onDevJumpToStage?: (stage: DialogueStage) => void;
  /** DEV: Pull latest stage snapshot from backend. */
  onDevSyncStage?: () => void;
  /** DEV: Reset session stage to initial. */
  onDevResetStage?: () => void;
  /** Called when the user clicks the settings gear icon. */
  onOpenSettings: () => void;
}

const DEV_STAGE_ACTIONS: Array<{ label: string; stage: DialogueStage }> = [
  { label: "Jump to Initial", stage: "initial" },
  { label: "Jump to Gathering", stage: "gathering" },
  { label: "Jump to Summary", stage: "summary_confirming" },
  { label: "Jump to PIR", stage: "pir_confirming" },
  { label: "Jump to Complete", stage: "complete" },
];

/**
 * Left-hand navigation sidebar showing all conversations.
 *
 * Features:
 *   - Collapsible: toggles between a full w-64 panel and a slim w-14 icon rail.
 *     Width snaps instantly (no CSS transition) to avoid text squishing during
 *     the resize animation.
 *   - Sorted by updatedAt descending so the most recently active conversation
 *     is always at the top.
 *   - Per-conversation options menu (⋯ button) with Rename and Delete actions,
 *     closed automatically when the user clicks outside it.
 *   - Inline rename: clicking Rename replaces the conversation title with an
 *     auto-focused text input; Enter confirms, Escape cancels.
 *
 * Local state:
 *   openMenuId  — id of the conversation whose options dropdown is open, or null.
 *   renamingId  — id of the conversation currently being renamed, or null.
 *   draftTitle  — controlled value of the rename input field.
 *   isCollapsed — whether the sidebar is in its narrow rail mode.
 */
export function Sidebar({
  conversations,
  activeConversationId,
  onNewChat,
  onSwitchConversation,
  onDeleteConversation,
  onRenameConversation,
  onDeleteAllConversations,
  onDevSendMessage,
  onDevShowCollectionApproval,
  onDevJumpToStage,
  onDevSyncStage,
  onDevResetStage,
  onOpenSettings,
}: SidebarProps) {
  // Sort a copy so the original prop array is never mutated.
  const sortedConversations = [...conversations].sort(
    (a, b) => b.updatedAt - a.updatedAt,
  );

  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isDevToolsMinimized, setIsDevToolsMinimized] = useState(true);
  const [isCollectionPhaseMinimized, setIsCollectionPhaseMinimized] =
    useState(true);

  // Ref attached to the dropdown menu div — used by the outside-click handler.
  const menuRef = useRef<HTMLDivElement | null>(null);

  /**
   * Closes the options dropdown when the user clicks anywhere outside it.
   * The effect only registers the listener while a menu is open (openMenuId
   * is non-null) and cleans up the listener when the menu closes or the
   * component unmounts, preventing memory leaks.
   */
  useEffect(() => {
    if (!openMenuId) return;

    function closeMenu(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpenMenuId(null);
      }
    }
    document.addEventListener("mousedown", closeMenu);
    return () => document.removeEventListener("mousedown", closeMenu);
  }, [openMenuId]);

  return (
    /*
     * No CSS transition on width — both the width and the content snap instantly.
     * A transition caused text to squish as the container narrowed; snapping
     * avoids that visual artifact entirely.
     */
    <aside
      className={`${
        isCollapsed ? "w-14" : "w-64"
      } bg-surface-inverse text-text-inverse flex flex-col h-full overflow-hidden`}
    >
      {/* Toggle button — SVG chevron, clearer than a Unicode character.
          Points right (›) when collapsed to signal "expand",
          left (‹) when expanded to signal "collapse". */}
      <button
        aria-label="Toggle sidebar"
        onClick={() => setIsCollapsed((prev) => !prev)}
        className="p-2 flex items-center justify-center shrink-0 hover:bg-surface-inverse-hover rounded"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          {isCollapsed
            ? <path d="M9 18l6-6-6-6" />   /* › chevron-right = expand */
            : <path d="M15 18l-6-6 6-6" />  /* ‹ chevron-left  = collapse */
          }
        </svg>
      </button>

      {/* New Chat button — always visible in both expanded and collapsed states.
          When collapsed, text is hidden and the button shows only the + icon.
          aria-label stays "New Chat" in both states so tests and screen readers
          get a consistent accessible name. */}
      <button
        onClick={onNewChat}
        aria-label="New Chat"
        className={`mx-2 mb-2 p-2 bg-primary-dark rounded flex items-center justify-center gap-2 shrink-0 ${
          isCollapsed ? "" : "w-[calc(100%-1rem)]"
        }`}
      >
        <span className="text-lg leading-none">+</span>
        {!isCollapsed && <span>New Chat</span>}
      </button>

      {/* Conversation list — hidden entirely when collapsed to keep the rail clean. */}
      {!isCollapsed && (
        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            <div className="flex items-center justify-center text-text-secondary h-full">
              No conversations yet
            </div>
          ) : (
            sortedConversations.map((conv) => (
              <div
                key={conv.id}
                className={`group relative flex items-center rounded mx-1 my-0.5 ${
                  conv.id === activeConversationId
                    ? "bg-surface-inverse-hover"
                    : "hover:bg-surface-inverse-hover"
                }`}
              >
                {/* Rename mode: replaces the title button with a controlled input.
                    Enter confirms; Escape cancels without saving. */}
                {renamingId === conv.id ? (
                  <input
                    autoFocus
                    value={draftTitle}
                    onChange={(e) => setDraftTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        onRenameConversation(conv.id, draftTitle);
                        setRenamingId(null);
                      }
                      if (e.key === "Escape") {
                        setRenamingId(null);
                      }
                    }}
                    className="flex-1 p-2 bg-transparent text-text-inverse outline-none"
                  />
                ) : (
                  /* Normal mode: title button + options (⋯) button. */
                  <>
                    <button
                      onClick={() => onSwitchConversation(conv.id)}
                      data-active={
                        conv.id === activeConversationId ? "true" : "false"
                      }
                      className="flex-1 text-left p-2"
                    >
                      {conv.title}
                    </button>

                    {/* Options button — always in the DOM but only visible on
                        row hover (opacity-0 → group-hover:opacity-100).
                        onMouseDown stops propagation so the outside-click
                        handler in the useEffect does not close the menu
                        before onClick has a chance to open it. */}
                    <button
                      aria-label="Chat options"
                      aria-expanded={openMenuId === conv.id}
                      onMouseDown={(e) => e.stopPropagation()}
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenMenuId(conv.id);
                      }}
                      className="p-1 mr-1 rounded text-text-muted hover:text-text-inverse hover:bg-surface-inverse-hover opacity-0 group-hover:opacity-100 focus:opacity-100"
                    >
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                        aria-hidden="true"
                      >
                        <circle cx="4" cy="10" r="2" />
                        <circle cx="10" cy="10" r="2" />
                        <circle cx="16" cy="10" r="2" />
                      </svg>
                    </button>
                  </>
                )}

                {/* Dropdown menu — rendered only for the conversation whose
                    options button was clicked. Positioned absolutely below the row. */}
                {openMenuId === conv.id && (
                  <div
                    ref={menuRef}
                    role="menu"
                    className="absolute right-0 top-full bg-surface-deep border border-border-inverse rounded shadow-lg z-10"
                  >
                    <button
                      role="menuitem"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDraftTitle(conv.title);
                        setRenamingId(conv.id);
                        setOpenMenuId(null);
                      }}
                      className="block w-full text-left px-4 py-2 hover:bg-surface-inverse"
                    >
                      Rename
                    </button>

                    <button
                      role="menuitem"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteConversation(conv.id);
                        setOpenMenuId(null);
                      }}
                      className="block w-full text-left px-4 py-2 hover:bg-surface-inverse text-error"
                    >
                      Delete
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
      {/* Settings gear — sits just above Dev Tools */}
      <div className="shrink-0 border-t border-border-inverse p-2 flex justify-end">
        <button
          aria-label="Open settings"
          onClick={onOpenSettings}
          className="p-2 rounded text-text-muted hover:bg-surface-inverse-hover hover:text-text-inverse"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            aria-hidden="true">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </button>
      </div>
      {/* DEV TOOLS — only visible when the sidebar is expanded. */}
      {!isCollapsed && (
        <div className="shrink-0 border-t border-gray-600 p-2">
          <div className="mb-1 flex items-center justify-between">
            <p className="px-1 text-xs font-semibold uppercase tracking-widest text-amber-400">
              Dev Tools
            </p>
            <button
              type="button"
              aria-label={
                isDevToolsMinimized ? "Expand dev tools" : "Minimize dev tools"
              }
              onClick={() => setIsDevToolsMinimized((prev) => !prev)}
              className="rounded px-2 py-1 text-xs text-gray-300 hover:bg-gray-600"
            >
              {isDevToolsMinimized ? "Show" : "Hide"}
            </button>
          </div>
          {!isDevToolsMinimized && (
            <>
              <button
                onClick={onDevSendMessage}
                className="w-full text-left px-2 py-1.5 rounded text-sm text-gray-300 hover:bg-gray-600"
              >
                Send test message
              </button>
              {onDevShowCollectionApproval && (
                <button
                  onClick={onDevShowCollectionApproval}
                  className="w-full text-left px-2 py-1.5 rounded text-sm text-gray-300 hover:bg-gray-600"
                >
                  Show collection approval
                </button>
              )}
              {onDevJumpToStage && (
                <div className="mt-1">
                  <button
                    type="button"
                    aria-label={
                      isCollectionPhaseMinimized
                        ? "Expand direction phase"
                        : "Minimize direction phase"
                    }
                    onClick={() =>
                      setIsCollectionPhaseMinimized((prev) => !prev)
                    }
                    className="w-full rounded px-2 py-1.5 text-left text-sm text-gray-200 hover:bg-gray-600"
                  >
                    <span className="flex items-center gap-2">
                      <span aria-hidden="true" className="text-xs text-gray-300">
                        {isCollectionPhaseMinimized ? ">" : "v"}
                      </span>
                      <span>Direction Phase</span>
                    </span>
                  </button>
                  {!isCollectionPhaseMinimized &&
                    DEV_STAGE_ACTIONS.map((item) => (
                      <button
                        key={item.stage}
                        onClick={() => onDevJumpToStage(item.stage)}
                        className="w-full pl-5 pr-2 py-1.5 rounded text-left text-sm text-gray-300 hover:bg-gray-600"
                      >
                        {item.label}
                      </button>
                    ))}
                </div>
              )}
              {onDevSyncStage && (
                <button
                  onClick={onDevSyncStage}
                  className="w-full text-left px-2 py-1.5 rounded text-sm text-gray-300 hover:bg-gray-600"
                >
                  Sync stage
                </button>
              )}
              {onDevResetStage && (
                <button
                  onClick={onDevResetStage}
                  className="w-full text-left px-2 py-1.5 rounded text-sm text-gray-300 hover:bg-gray-600"
                >
                  Reset stage
                </button>
              )}
              <button
                onClick={onDeleteAllConversations}
                className="w-full text-left px-2 py-1.5 rounded text-sm text-red-400 hover:bg-gray-600"
              >
                Delete all conversations
              </button>
            </>
          )}
        </div>
      )}
    </aside>
  );
}
