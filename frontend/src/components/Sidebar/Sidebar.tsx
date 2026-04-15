import { useEffect, useState, useRef } from "react";
import type { Conversation } from "../../types/conversation";
import type { DialoguePhase, DialogueStage } from "../../types/dialogue";
import { useT } from "../../i18n/useT";
import type { DialogueDevSnapshot } from "../../services/dialogue/dialogue";

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
  /** DEV: Saved backend runs that can be restored into the active session. */
  devSnapshots?: DialogueDevSnapshot[];
  /** DEV: Whether saved runs are being loaded/restored. */
  isDevSnapshotsLoading?: boolean;
  /** DEV: Refresh saved backend runs. */
  onDevRefreshSnapshots?: () => void;
  /** DEV: Restore a saved run into the active session at a specific stage. */
  onDevRestoreSnapshot?: (
    sourceSessionId: string,
    stage: DialogueStage,
    phase: DialoguePhase,
  ) => void;
  /** Whether the sidebar is in its narrow rail mode (controlled by parent). */
  isCollapsed?: boolean;
  /** Whether expanded-only content is visible (controlled by parent). */
  showExpandedContent?: boolean;
}

/**
 * Left-hand navigation sidebar showing all conversations.
 *
 * Features:
 *   - Collapsible: toggles between a full w-64 panel and a slim w-14 icon rail.
 *     Width animates between the two states for a smoother open/close motion,
 *     while expanded-only content is delayed until the panel is wide enough to
 *     avoid text wrapping during the transition.
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
 *
 * Collapse state (isCollapsed, showExpandedContent) is owned by the parent (App)
 * so the toggle button can live in the full-width top bar.
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
  devSnapshots = [],
  isDevSnapshotsLoading = false,
  onDevRefreshSnapshots,
  onDevRestoreSnapshot,
  isCollapsed = false,
  showExpandedContent = true,
}: SidebarProps) {
  const t = useT();

  // Sort a copy so the original prop array is never mutated.
  const sortedConversations = [...conversations].sort(
    (a, b) => b.updatedAt - a.updatedAt,
  );

  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [isDevToolsMinimized, setIsDevToolsMinimized] = useState(true);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState("");

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

  useEffect(() => {
    if (selectedSnapshotId) return;
    if (devSnapshots.length > 0) {
      setSelectedSnapshotId(devSnapshots[0].session_id);
    }
  }, [devSnapshots, selectedSnapshotId]);

  const selectedSnapshot =
    devSnapshots.find((snapshot) => snapshot.session_id === selectedSnapshotId) ??
    devSnapshots[0];

  const restoreSnapshot = (stage: DialogueStage, phase: DialoguePhase) => {
    if (!selectedSnapshot || !onDevRestoreSnapshot) return;
    onDevRestoreSnapshot(selectedSnapshot.session_id, stage, phase);
  };

  return (
    <aside
      className={`${
        isCollapsed ? "w-14" : "w-64"
      } bg-surface text-text-primary border-r border-border flex flex-col h-full overflow-hidden transition-[width] duration-300 ease-in-out motion-reduce:transition-none`}
    >
      {/* New Chat button — always visible in both expanded and collapsed states.
          When collapsed, text is hidden and the button shows only the + icon.
          aria-label stays "New Chat" in both states so tests and screen readers
          get a consistent accessible name. */}
      <button
        onClick={onNewChat}
        aria-label={t.newChat}
        className={`bg-primary-dark text-white rounded flex items-center shrink-0 ${
          isCollapsed
            ? "w-8 h-8 mx-auto mt-2 mb-2 justify-center"
            : "mx-2 mt-2 mb-2 py-1.5 px-2 justify-start gap-1.5 w-[calc(100%-1rem)]"
        }`}
      >
        <span className="text-lg leading-none">+</span>
        {showExpandedContent && <span className="whitespace-nowrap">New Chat</span>}
      </button>

      {/* Conversation list — hidden entirely when collapsed to keep the rail clean. */}
      {showExpandedContent && (
        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            <div className="flex items-center justify-center text-text-secondary h-full">
              {t.noConversations}
            </div>
          ) : (
            sortedConversations.map((conv) => (
              <div
                key={conv.id}
                className={`group relative flex items-center rounded mx-1 my-0.5 ${
                  conv.id === activeConversationId
                    ? "bg-surface-elevated"
                    : "hover:bg-surface-elevated"
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
                    className="flex-1 p-2 bg-transparent text-text-primary outline-none"
                  />
                ) : (
                  /* Normal mode: title button + options (⋯) button. */
                  <>
                    <button
                      onClick={() => onSwitchConversation(conv.id)}
                      data-active={
                        conv.id === activeConversationId ? "true" : "false"
                      }
                      className="flex-1 text-left p-2 truncate whitespace-nowrap"
                    >
                      {conv.title || t.newConversationDefault}
                    </button>

                    {/* Options button — always in the DOM but only visible on
                        row hover (opacity-0 → group-hover:opacity-100).
                        onMouseDown stops propagation so the outside-click
                        handler in the useEffect does not close the menu
                        before onClick has a chance to open it. */}
                    <button
                      aria-label={t.chatOptions}
                      aria-expanded={openMenuId === conv.id}
                      onMouseDown={(e) => e.stopPropagation()}
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenMenuId(conv.id);
                      }}
                      className="p-1 mr-1 rounded text-text-muted hover:text-text-primary hover:bg-surface-elevated opacity-0 group-hover:opacity-100 focus:opacity-100"
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
                    className="absolute right-0 top-full bg-surface border border-border rounded shadow-lg z-10"
                  >
                    <button
                      role="menuitem"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDraftTitle(conv.title);
                        setRenamingId(conv.id);
                        setOpenMenuId(null);
                      }}
                      className="block w-full text-left px-4 py-2 hover:bg-surface-elevated"
                    >
                      {t.rename}
                    </button>

                    <button
                      role="menuitem"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteConversation(conv.id);
                        setOpenMenuId(null);
                      }}
                      className="block w-full text-left px-4 py-2 hover:bg-surface-elevated text-error"
                    >
                      {t.delete}
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
      {/* DEV TOOLS — only visible when the sidebar is expanded. */}
      {showExpandedContent && (
        <div className="shrink-0 border-t border-border p-2">
          <div className="mb-1 flex items-center justify-between">
            <p className="px-1 text-xs font-semibold uppercase tracking-widest text-warning">
              {t.devTools}
            </p>
            <button
              type="button"
              aria-label={
                isDevToolsMinimized ? t.expandDevTools : t.minimizeDevTools
              }
              onClick={() => setIsDevToolsMinimized((prev) => !prev)}
              className="rounded px-2 py-1 text-xs text-text-secondary hover:bg-surface-elevated"
            >
              {isDevToolsMinimized ? t.show : t.hide}
            </button>
          </div>
          {!isDevToolsMinimized && (
            <>
              <button
                onClick={onDevSendMessage}
                className="w-full text-left px-2 py-1.5 rounded text-sm text-text-secondary hover:bg-surface-elevated"
              >
                {t.sendTestMessage}
              </button>
              {onDevShowCollectionApproval && (
                <button
                  onClick={onDevShowCollectionApproval}
                  className="w-full text-left px-2 py-1.5 rounded text-sm text-text-secondary hover:bg-surface-elevated"
                >
                  {t.showCollectionApproval}
                </button>
              )}
              {onDevRestoreSnapshot && (
                <div className="mt-2 rounded border border-border-muted p-2">
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <label className="text-xs font-medium text-text-secondary">
                      {t.previousRun}
                    </label>
                    {onDevRefreshSnapshots && (
                      <button
                        type="button"
                        onClick={onDevRefreshSnapshots}
                        disabled={isDevSnapshotsLoading}
                        className="rounded px-1.5 py-0.5 text-xs text-text-secondary hover:bg-surface-elevated disabled:opacity-50"
                      >
                        {isDevSnapshotsLoading ? t.loading : t.refresh}
                      </button>
                    )}
                  </div>
                  {devSnapshots.length > 0 ? (
                    <>
                      <select
                        value={selectedSnapshot?.session_id ?? ""}
                        onChange={(event) =>
                          setSelectedSnapshotId(event.target.value)
                        }
                        className="w-full rounded border border-border bg-surface px-2 py-1 text-xs text-text-primary"
                      >
                        {devSnapshots.map((snapshot) => (
                          <option
                            key={snapshot.session_id}
                            value={snapshot.session_id}
                          >
                            {snapshot.title || snapshot.session_id}
                          </option>
                        ))}
                      </select>
                      <p className="mt-1 truncate font-mono text-[10px] text-text-muted">
                        {selectedSnapshot?.session_id}
                      </p>
                      <div className="mt-2 grid grid-cols-2 gap-1">
                        <button
                          type="button"
                          onClick={() =>
                            restoreSnapshot("pir_confirming", "direction")
                          }
                          disabled={isDevSnapshotsLoading}
                          className="rounded bg-surface-elevated px-2 py-1 text-xs text-text-secondary hover:text-text-primary disabled:opacity-50"
                        >
                          {t.loadPir}
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            restoreSnapshot("reviewing", "collection")
                          }
                          disabled={isDevSnapshotsLoading}
                          className="rounded bg-surface-elevated px-2 py-1 text-xs text-text-secondary hover:text-text-primary disabled:opacity-50"
                        >
                          {t.loadCollection}
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            restoreSnapshot("reviewing", "processing")
                          }
                          disabled={isDevSnapshotsLoading}
                          className="rounded bg-surface-elevated px-2 py-1 text-xs text-text-secondary hover:text-text-primary disabled:opacity-50"
                        >
                          {t.loadProcessing}
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            restoreSnapshot("complete", "processing")
                          }
                          disabled={isDevSnapshotsLoading}
                          className="rounded bg-surface-elevated px-2 py-1 text-xs text-text-secondary hover:text-text-primary disabled:opacity-50"
                        >
                          {t.loadAnalysis}
                        </button>
                      </div>
                    </>
                  ) : (
                    <p className="text-xs text-text-muted">
                      {isDevSnapshotsLoading ? t.loading : t.noPreviousRuns}
                    </p>
                  )}
                </div>
              )}
              <button
                onClick={onDeleteAllConversations}
                className="w-full text-left px-2 py-1.5 rounded text-sm text-error hover:bg-surface-elevated"
              >
                {t.deleteAllConversations}
              </button>
            </>
          )}
        </div>
      )}
    </aside>
  );
}
