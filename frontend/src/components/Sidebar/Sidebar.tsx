import { useEffect, useState } from "react";
import type { Conversation } from "../../types/conversation";

interface SidebarProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  onNewChat: () => void;
  onSwitchConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onRenameConversation: (id: string, newTitle: string) => void;
}

/**
 * Sidebar displays the list of past conversations and controls for managing them.
 *
 * Layout per conversation row (all siblings inside a <div> wrapper):
 *   [title button] [options "..." button] [dropdown menu]
 *
 * State:
 *   hoveredItemId – which row is currently hovered (controls "..." visibility)
 *   openMenuId    – which row has its dropdown open
 *   renamingId    – which row is in inline rename mode
 *   draftTitle    – the current text in the rename input
 */
export function Sidebar({
  conversations,
  activeConversationId,
  onNewChat,
  onSwitchConversation,
  onDeleteConversation,
  onRenameConversation,
}: SidebarProps) {
  const sortedConversations = [...conversations].sort(
    (a, b) => b.updatedAt - a.updatedAt,
  );

  const [hoveredItemId, setHoveredItemId] = useState<string | null>(null);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");

  /**
   * Close the dropdown whenever the user clicks anywhere outside it.
   * The "..." button uses e.stopPropagation() so its own click does not
   * immediately trigger this listener and close the menu it just opened.
   */
  useEffect(() => {
    function closeMenu() {
      setOpenMenuId(null);
    }
    document.addEventListener("click", closeMenu);
    return () => document.removeEventListener("click", closeMenu);
  }, []);

  return (
    <aside className="w-64 bg-gray-700 text-white flex flex-col h-full">
      {/* 1. New Chat button */}
      <button onClick={onNewChat} className="m-2 p-2 bg-blue-600 rounded">
        New Chat
      </button>

      {/* 2. Conversation list */}
      {conversations.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          No conversations yet
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          {sortedConversations.map((conv) => (
            /**
             * The outer element is a <div>, not a <button>.
             * A <button> cannot legally contain another <button> (invalid HTML).
             * Using a <div> as the row wrapper avoids that nesting problem and
             * lets us attach hover listeners to the whole row without interfering
             * with the individual click targets inside it.
             */
            <div
              key={conv.id}
              // FIX 2: hover highlight — bg-gray-600 applied to the whole row on
              // hover. Active rows use bg-gray-600 permanently so they always
              // look selected. Tailwind's hover: utility handles this in CSS
              // without needing extra JS state.
              className={`relative flex items-center rounded mx-1 my-0.5 ${
                conv.id === activeConversationId
                  ? "bg-gray-600"
                  : "hover:bg-gray-600"
              }`}
              onMouseEnter={() => setHoveredItemId(conv.id)}
              onMouseLeave={() => setHoveredItemId(null)}
            >
              {renamingId === conv.id ? (
                /**
                 * Rename mode: plain input, no button wrapper.
                 * - autoFocus moves cursor here immediately.
                 * - onChange keeps draftTitle in sync as the user types.
                 * - Enter confirms; Escape cancels without calling the callback.
                 */
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
                  className="flex-1 p-2 bg-transparent text-white outline-none"
                />
              ) : (
                /* Normal mode: button for switching conversations. */
                <button
                  onClick={() => onSwitchConversation(conv.id)}
                  data-active={conv.id === activeConversationId ? "true" : "false"}
                  className="flex-1 text-left p-2"
                >
                  <span>{conv.title}</span>
                </button>
              )}

              {/* Options button — visible on hover, hidden during rename.
                  replaced the tiny "..." text with an SVG icon made of
                  three circles, which is larger, clearer, and scales with the
                  font size. hover:bg-gray-500 gives it its own highlight so it
                  feels like a real button. */}
              {hoveredItemId === conv.id && renamingId !== conv.id && (
                <button
                  aria-label="Chat options"
                  onClick={(e) => {
                    e.stopPropagation(); // Prevent document listener from closing immediately
                    setOpenMenuId(conv.id);
                  }}
                  className="p-1 mr-1 rounded text-gray-400 hover:text-white hover:bg-gray-500"
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <circle cx="4"  cy="10" r="2" />
                    <circle cx="10" cy="10" r="2" />
                    <circle cx="16" cy="10" r="2" />
                  </svg>
                </button>
              )}

              {/* Dropdown menu — rendered only for the row whose "..." was clicked.
                  Each action item has role="menuitem" so tests can find them with
                  getByRole("menuitem", { name: /rename/i }). */}
              {openMenuId === conv.id && (
                <div
                  role="menu"
                  className="absolute right-0 top-full bg-gray-800 border border-gray-600 rounded shadow-lg z-10"
                >
                  <button
                    role="menuitem"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDraftTitle(conv.title); // Pre-fill input with current title
                      setRenamingId(conv.id);
                      setOpenMenuId(null);
                    }}
                    className="block w-full text-left px-4 py-2 hover:bg-gray-700"
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
                    className="block w-full text-left px-4 py-2 hover:bg-gray-700 text-red-400"
                  >
                    Delete
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}
