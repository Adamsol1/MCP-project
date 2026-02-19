import { useEffect, useState, useRef } from "react";
import type { Conversation } from "../../types/conversation";

interface SidebarProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  onNewChat: () => void;
  onSwitchConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onRenameConversation: (id: string, newTitle: string) => void;
}

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

  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [isCollapsed, setIsCollapsed] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  // Close dropdown when clicking outside
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
    // No CSS transition — width and content both snap instantly on toggle.
    // A transition caused text to squish as the container narrowed; snapping
    // avoids that artifact entirely.
    <aside
      className={`${
        isCollapsed ? "w-14" : "w-64"
      } bg-gray-700 text-white flex flex-col h-full overflow-hidden`}
    >
      {/* Toggle Button — SVG chevron, larger and clearer than a unicode char.
          Points right (expand) when collapsed, left (collapse) when expanded. */}
      <button
        aria-label="Toggle sidebar"
        onClick={() => setIsCollapsed((prev) => !prev)}
        className="p-2 flex items-center justify-center shrink-0 hover:bg-gray-600 rounded"
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

      {/* New Chat — always visible; shows icon-only when collapsed so the
          button stays usable in the narrow rail. aria-label keeps the
          accessible name "New Chat" in both states so tests keep passing. */}
      <button
        onClick={onNewChat}
        aria-label="New Chat"
        className={`mx-2 mb-2 p-2 bg-blue-600 rounded flex items-center justify-center gap-2 shrink-0 ${
          isCollapsed ? "" : "w-[calc(100%-1rem)]"
        }`}
      >
        <span className="text-lg leading-none">+</span>
        {!isCollapsed && <span>New Chat</span>}
      </button>

      {/* Conversation List (collapsible only this part) */}
      {!isCollapsed && (
        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            <div className="flex items-center justify-center text-gray-500 h-full">
              No conversations yet
            </div>
          ) : (
            sortedConversations.map((conv) => (
              <div
                key={conv.id}
                className={`group relative flex items-center rounded mx-1 my-0.5 ${
                  conv.id === activeConversationId
                    ? "bg-gray-600"
                    : "hover:bg-gray-600"
                }`}
              >
                {/* Rename Mode */}
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
                    className="flex-1 p-2 bg-transparent text-white outline-none"
                  />
                ) : (
                  /* Normal Mode */
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

                    {/* Options Button — always in DOM, visible on hover via CSS */}
                    <button
                      aria-label="Chat options"
                      aria-expanded={openMenuId === conv.id}
                      onMouseDown={(e) => e.stopPropagation()}
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenMenuId(conv.id);
                      }}
                      className="p-1 mr-1 rounded text-gray-400 hover:text-white hover:bg-gray-500 opacity-0 group-hover:opacity-100 focus:opacity-100"
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

                {/* Dropdown Menu */}
                {openMenuId === conv.id && (
                  <div
                    ref={menuRef}
                    role="menu"
                    className="absolute right-0 top-full bg-gray-800 border border-gray-600 rounded shadow-lg z-10"
                  >
                    <button
                      role="menuitem"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDraftTitle(conv.title);
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
            ))
          )}
        </div>
      )}
    </aside>
  );
}
