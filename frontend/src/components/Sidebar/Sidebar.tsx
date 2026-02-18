import type { Conversation } from "../../types/conversation";

interface SidebarProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  onNewChat: () => void;
  onSwitchConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
}

export function Sidebar({
  conversations,
  activeConversationId,
  onNewChat,
  onSwitchConversation,
  onDeleteConversation,
}: SidebarProps) {
  const sortedConversations = [...conversations].sort(
    (a, b) => b.updatedAt - a.updatedAt,
  );

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
            <button
              key={conv.id}
              onClick={() => onSwitchConversation(conv.id)}
              data-active={conv.id === activeConversationId ? "true" : "false"}
              className={`w-full text-left p-2 flex justify-between items-center ${conv.id === activeConversationId ? "bg-gray-700" : ""}`}
            >
              <span>{conv.title}</span>

              <button
                aria-label="Delete conversations"
                onClick={(e) => {
                  e.stopPropagation(); // Prevent triggering onSwitchConversation
                  onDeleteConversation(conv.id);
                }}
                className="text-gray-400 hover:text-red-400 ml-2"
              >
                X
              </button>
            </button>
          ))}
        </div>
      )}
    </aside>
  );
}
