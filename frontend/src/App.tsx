import { useState } from "react";
import ChatWindow from "./components/ChatWindow/ChatWindow";
import { Sidebar } from "./components/Sidebar/Sidebar";
import { OptionsPanel } from "./components/OptionsPanel/OptionsPanel";
import { FileUploadModal } from "./components/FileUploadModal/FileUploadModal";
import { ToastContainer } from "./components/Toast";
import { useToast } from "./hooks/useToast";
import { uploadFile } from "./services/upload";
import { useChat } from "./hooks/useChat";
import { useConversation } from "./hooks/useConversation";

function App() {
  const { success, error } = useToast();
  const {
    conversations,
    activeConversation,
    createNewConversation,
    switchConversation,
    deleteConversation,
    updatePerspectives,
  } = useConversation();
  const { messages, sendMessage, isConfirming, approve, reject } = useChat();
  const [isFileUploadOpen, setIsFileUploadOpen] = useState(false);

  const handleFileSelect = (file: File) => {
    console.log("Selected file:", file.name);
  };

  const handleSubmit = async (files: File[]) => {
    for (const file of files) {
      try {
        const result = await uploadFile(file);
        console.log("Upload result:", result);
        success(`Successfully uploaded ${file.name}`);
      } catch (err) {
        console.error("Upload error:", err);
        error(`Failed to upload ${file.name}`);
      }
    }
    setIsFileUploadOpen(false);
  };

  return (
    <div className="flex h-screen">
      <Sidebar
        conversations={conversations}
        activeConversationId={activeConversation?.id ?? null}
        onNewChat={createNewConversation}
        onSwitchConversation={switchConversation}
        onDeleteConversation={deleteConversation}
      />

      <main className="flex-1 flex flex-col bg-gray-100">
        <ToastContainer position="top-right" />
        <ChatWindow
          messages={messages}
          onSendMessage={sendMessage}
          isConfirming={isConfirming}
          onApprove={approve}
          onReject={reject}
        />
      </main>

      <OptionsPanel
        selectedPerspectives={activeConversation?.perspectives ?? ["NEUTRAL"]}
        onPerspectiveChange={updatePerspectives}
        onOpenFileUpload={() => setIsFileUploadOpen(true)}
      />

      <FileUploadModal
        isOpen={isFileUploadOpen}
        onClose={() => setIsFileUploadOpen(false)}
        onFileSelect={handleFileSelect}
        onSubmit={handleSubmit}
      />
    </div>
  );
}

export default App;
