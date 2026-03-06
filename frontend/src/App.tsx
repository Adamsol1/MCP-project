import { useEffect, useState } from "react";
import ChatWindow from "./components/ChatWindow/ChatWindow";
import { Sidebar } from "./components/Sidebar/Sidebar";
import { OptionsPanel } from "./components/OptionsPanel/OptionsPanel";
import { FileUploadModal } from "./components/FileUploadModal/FileUploadModal";
import { SettingsModal } from "./components/SettingsModal/SettingsModal";
import { useToast } from "./hooks/useToast";
import {
  deleteUploadedFile,
  listUploadedFiles,
  uploadFile,
  type UploadedFileRecord,
} from "./services/upload";
import { useChat } from "./hooks/useChat";
import { useConversation } from "./hooks/useConversation";
import type { DialogueStage } from "./types/dialogue";

function App() {
  const { success, error } = useToast();
  const {
    conversations,
    activeConversation,
    createNewConversation,
    switchConversation,
    deleteConversation,
    deleteAllConversations,
    renameConversation,
    updatePerspectives,
  } = useConversation();
  const {
    messages,
    sendMessage,
    isConfirming,
    stage,
    isLoading,
    approve,
    reject,
    debugConfirm,
    jumpToDevStage,
    syncDevStage,
    resetDevStage,
    devPrefill,
    triggerDevMessage,
    clearDevPrefill,
  } = useChat();

  const [isFileUploadOpen, setIsFileUploadOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileRecord[]>([]);

  const ensureConversationSession = () => {
    return activeConversation ?? createNewConversation();
  };

  const refreshUploadedFiles = async (sessionId: string) => {
    try {
      const files = await listUploadedFiles(sessionId);
      setUploadedFiles(files);
    } catch (loadError) {
      console.error("Load uploads error:", loadError);
      error("Failed to load uploaded files");
    }
  };

  useEffect(() => {
    if (!activeConversation?.sessionId) {
      setUploadedFiles([]);
      return;
    }
    refreshUploadedFiles(activeConversation.sessionId);
  }, [activeConversation?.sessionId]);

  const handleSubmit = async (files: File[]) => {
    const conversation = ensureConversationSession();

    for (const file of files) {
      try {
        const result = await uploadFile(file, conversation.sessionId);
        console.log("Upload result:", result);
        success(`Successfully uploaded ${file.name}`);
      } catch (uploadError) {
        console.error("Upload error:", uploadError);
        error(`Failed to upload ${file.name}`);
      }
    }

    await refreshUploadedFiles(conversation.sessionId);
    setIsFileUploadOpen(false);
  };

  const handleFileRemove = async (file: UploadedFileRecord) => {
    if (!activeConversation?.sessionId) {
      return;
    }

    try {
      await deleteUploadedFile(activeConversation.sessionId, file.file_upload_id);
      setUploadedFiles((prev) =>
        prev.filter((item) => item.file_upload_id !== file.file_upload_id),
      );
      success(`Removed ${file.filename}`);
    } catch (deleteError) {
      console.error("Delete upload error:", deleteError);
      error(`Failed to remove ${file.filename}`);
    }
  };

  return (
    <div className="flex h-screen">
      <Sidebar
        conversations={conversations}
        activeConversationId={activeConversation?.id ?? null}
        onNewChat={createNewConversation}
        onSwitchConversation={switchConversation}
        onDeleteConversation={deleteConversation}
        onRenameConversation={renameConversation}
        onDeleteAllConversations={deleteAllConversations}
        onDevSendMessage={() =>
          triggerDevMessage(
            "What are the latest cyber threats targeting European critical infrastructure?",
          )
        }
        onDevShowCollectionApproval={debugConfirm}
        onDevJumpToStage={(nextStage: DialogueStage) => jumpToDevStage(nextStage)}
        onDevSyncStage={syncDevStage}
        onDevResetStage={resetDevStage}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      <main className="flex-1 flex flex-col bg-surface-elevated mx-1">
        <ChatWindow
          messages={messages}
          onSendMessage={sendMessage}
          isConfirming={isConfirming}
          stage={stage}
          isLoading={isLoading}
          onApprove={approve}
          onReject={reject}
          devPrefill={devPrefill}
          onDevPrefillConsumed={clearDevPrefill}
        />
      </main>

      <OptionsPanel
        selectedPerspectives={activeConversation?.perspectives ?? ["NEUTRAL"]}
        onPerspectiveChange={updatePerspectives}
        onOpenFileUpload={() => setIsFileUploadOpen(true)}
        uploadedFiles={uploadedFiles}
        onFileRemove={handleFileRemove}
      />

      <FileUploadModal
        isOpen={isFileUploadOpen}
        onClose={() => setIsFileUploadOpen(false)}
        onSubmit={handleSubmit}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  );
}

export default App;
